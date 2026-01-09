#!/usr/bin/env python3
"""
Automated Code Review Cycle

This script automates the review-fix-iterate workflow:
1. Triggers Claude Code Review by pushing a commit
2. Waits for review to complete
3. Retrieves review comments
4. Parses feedback
5. Returns structured results for AI to implement fixes

Usage:
    python scripts/automated_review_cycle.py --pr 238
"""

import argparse
import time
import sys
import json
from typing import Dict, List, Optional
import requests
import os


class AutomatedReviewCycle:
    def __init__(self, repo: str, pr_number: int, github_token: str, debug: bool = False):
        self.repo = repo
        self.pr_number = pr_number
        self.github_token = github_token
        self.debug = debug
        self.base_url = f"https://api.github.com/repos/{repo}"
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def get_pr_details(self) -> Dict:
        """Get PR details"""
        url = f"{self.base_url}/pulls/{self.pr_number}"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"❌ PR #{self.pr_number} not found in {self.repo}")
            elif e.response.status_code == 401:
                print(f"❌ Authentication failed. Check your GITHUB_TOKEN")
            else:
                print(f"❌ HTTP error: {e}")
            raise
        except Exception as e:
            print(f"❌ Error fetching PR details: {e}")
            raise
    
    def get_workflow_runs(self, sha: str) -> List[Dict]:
        """Get workflow runs for a specific commit"""
        url = f"{self.base_url}/actions/runs"
        params = {
            "event": "pull_request",
            "head_sha": sha,
            "per_page": 10
        }
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()["workflow_runs"]
        except Exception as e:
            print(f"❌ Error fetching workflow runs: {e}")
            raise

    def wait_for_review_completion(self, sha: str, timeout: int = 600) -> Optional[Dict]:
        """Wait for Claude Code Review workflow to complete"""
        print(f"⏳ Waiting for Claude Code Review to complete (timeout: {timeout}s)...")
        print(f"   Commit SHA: {sha}")

        start_time = time.time()
        first_check = True
        while time.time() - start_time < timeout:
            runs = self.get_workflow_runs(sha)

            if first_check and runs:
                print(f"   Found {len(runs)} workflow runs for this commit")
                print(f"   Workflows: {[run['name'] for run in runs]}")
                first_check = False

            # Find Claude Code Review workflow
            review_run = next(
                (run for run in runs if "Claude Code Review" in run["name"]),
                None
            )

            if review_run:
                status = review_run["status"]
                conclusion = review_run.get("conclusion")
                elapsed = int(time.time() - start_time)

                print(f"  [{elapsed}s] Status: {status}, Conclusion: {conclusion}")

                if status == "completed":
                    print(f"✅ Review workflow completed with conclusion: {conclusion}")
                    return review_run
            elif not first_check:
                elapsed = int(time.time() - start_time)
                print(f"  [{elapsed}s] No Claude Code Review workflow found yet...")

            time.sleep(10)

        print("❌ Timeout waiting for review to complete")
        print(f"   Waited {timeout}s but workflow did not complete")
        return None
    
    def get_pr_comments(self) -> List[Dict]:
        """Get all comments on the PR"""
        url = f"{self.base_url}/issues/{self.pr_number}/comments"
        params = {"per_page": 100}
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            comments = response.json()
            print(f"📥 Retrieved {len(comments)} total comments from PR")
            return comments
        except Exception as e:
            print(f"❌ Error fetching PR comments: {e}")
            raise
    
    def parse_review_comments(self, comments: List[Dict]) -> Dict:
        """Parse Claude Code Review comments"""
        # Look for comments from claude[bot] or github-actions[bot] containing review content
        review_comments = [
            c for c in comments
            if (c["user"]["login"] in ["claude[bot]", "github-actions[bot]"] and
                ("CRITICAL" in c["body"] or "HIGH" in c["body"] or
                 "Code Review" in c["body"] or "Priority" in c["body"]))
        ]

        if not review_comments:
            print("⚠️  No review comments found from claude[bot] or github-actions[bot]")
            print(f"   Total comments on PR: {len(comments)}")
            if comments:
                print(f"   Comment authors: {[c['user']['login'] for c in comments]}")
            return {"has_review": False}

        # Use the latest review comment
        latest_review = review_comments[-1]
        body = latest_review["body"]

        print(f"✅ Found review comment from {latest_review['user']['login']}")
        print(f"   Comment ID: {latest_review['id']}")
        print(f"   Created: {latest_review['created_at']}")

        # Parse priority levels
        result = {
            "has_review": True,
            "comment_id": latest_review["id"],
            "created_at": latest_review["created_at"],
            "body": body,
            "critical_issues": [],
            "high_issues": [],
            "medium_issues": [],
            "low_issues": []
        }

        # Improved parsing - extract sections by priority markers
        import re

        # Look for sections marked with emoji and priority levels
        # Patterns: 🔴 CRITICAL, ⚠️ HIGH, ℹ️ MEDIUM, 💡 LOW
        # Also handle: ## 🔴 CRITICAL Issues, ## ⚠️ HIGH Priority Issues, etc.

        # Extract CRITICAL section
        critical_pattern = r'(?:🔴|##\s*🔴|CRITICAL\s+Issues?)(.*?)(?=(?:🟠|⚠️|##\s*⚠️|HIGH\s+Priority|🟡|ℹ️|##\s*ℹ️|MEDIUM\s+Priority|🟢|💡|##\s*💡|LOW\s+Priority|##\s+✅|##\s+Summary|$))'
        critical_match = re.search(critical_pattern, body, re.DOTALL | re.IGNORECASE)
        if critical_match:
            critical_text = critical_match.group(1).strip()
            # Split by numbered items (### 1., ### 2., etc.) or bullet points
            issues = re.split(r'(?:^|\n)(?:###\s*\d+\.|\*\*\d+\.)', critical_text)
            result["critical_issues"] = [issue.strip() for issue in issues if issue.strip() and len(issue.strip()) > 20]

        # Extract HIGH section
        high_pattern = r'(?:🟠|⚠️|##\s*⚠️|##\s*🟠|HIGH\s+Priority\s+Issues?)(.*?)(?=(?:🟡|ℹ️|##\s*ℹ️|MEDIUM\s+Priority|🟢|💡|##\s*💡|LOW\s+Priority|##\s+✅|##\s+Summary|$))'
        high_match = re.search(high_pattern, body, re.DOTALL | re.IGNORECASE)
        if high_match:
            high_text = high_match.group(1).strip()
            issues = re.split(r'(?:^|\n)(?:###\s*\d+\.|\*\*\d+\.)', high_text)
            result["high_issues"] = [issue.strip() for issue in issues if issue.strip() and len(issue.strip()) > 20]

        # Extract MEDIUM section
        medium_pattern = r'(?:🟡|ℹ️|##\s*ℹ️|##\s*🟡|MEDIUM\s+Priority\s+Issues?)(.*?)(?=(?:🟢|💡|##\s*💡|LOW\s+Priority|##\s+✅|##\s+Summary|$))'
        medium_match = re.search(medium_pattern, body, re.DOTALL | re.IGNORECASE)
        if medium_match:
            medium_text = medium_match.group(1).strip()
            issues = re.split(r'(?:^|\n)(?:###\s*\d+\.|\*\*\d+\.)', medium_text)
            result["medium_issues"] = [issue.strip() for issue in issues if issue.strip() and len(issue.strip()) > 20]

        # Extract LOW section
        low_pattern = r'(?:🟢|💡|##\s*💡|##\s*🟢|LOW\s+Priority)(.*?)(?=(?:##\s+✅|##\s+Summary|##\s+Conclusion|$))'
        low_match = re.search(low_pattern, body, re.DOTALL | re.IGNORECASE)
        if low_match:
            low_text = low_match.group(1).strip()
            issues = re.split(r'(?:^|\n)(?:###\s*\d+\.|\*\*\d+\.)', low_text)
            result["low_issues"] = [issue.strip() for issue in issues if issue.strip() and len(issue.strip()) > 20]

        # Calculate summary
        result["has_critical"] = len(result["critical_issues"]) > 0
        result["has_high"] = len(result["high_issues"]) > 0
        result["has_medium"] = len(result["medium_issues"]) > 0
        result["needs_fixes"] = result["has_critical"] or result["has_high"] or result["has_medium"]
        
        return result
    
    def run(self, skip_wait: bool = False, timeout: int = 600) -> Dict:
        """Run the automated review cycle"""
        print(f"🚀 Starting automated review cycle for PR #{self.pr_number}")

        # Get PR details
        pr = self.get_pr_details()
        sha = pr["head"]["sha"]
        print(f"📝 PR: {pr['title']}")
        print(f"🔗 SHA: {sha}")
        print(f"👤 Author: {pr['user']['login']}")
        print(f"🌿 Branch: {pr['head']['ref']}")

        # Wait for review to complete (unless skipped)
        if not skip_wait:
            review_run = self.wait_for_review_completion(sha, timeout=timeout)

            if not review_run:
                print("⚠️  Continuing anyway to check for existing review comments...")
            elif review_run["conclusion"] != "success":
                print(f"⚠️  Review workflow conclusion: {review_run['conclusion']}")
        else:
            print("⏭️  Skipping workflow wait, checking for existing comments...")

        # Get and parse comments
        print("📥 Retrieving review comments...")
        comments = self.get_pr_comments()
        result = self.parse_review_comments(comments)
        
        if not result["has_review"]:
            print("❌ No review comments found")
            return result
        
        # Print summary
        print("\n" + "="*60)
        print("📊 REVIEW SUMMARY")
        print("="*60)
        
        if result["has_critical"]:
            print(f"❌ CRITICAL: {len(result['critical_issues'])} issues")
        if result["has_high"]:
            print(f"⚠️  HIGH: {len(result['high_issues'])} issues")
        if result["has_medium"]:
            print(f"ℹ️  MEDIUM: {len(result['medium_issues'])} issues")
        if result["low_issues"]:
            print(f"💡 LOW: {len(result['low_issues'])} issues")
        
        if result["needs_fixes"]:
            print("\n🔧 Action required: Implement fixes for CRITICAL/HIGH/MEDIUM issues")
        else:
            print("\n✅ No critical issues found!")
        
        return result


def main():
    parser = argparse.ArgumentParser(description="Automated Code Review Cycle")
    parser.add_argument("--pr", type=int, required=True, help="Pull request number")
    parser.add_argument("--repo", default="TEJ42000/ALLMS", help="Repository (owner/repo)")
    parser.add_argument("--output", help="Output file for JSON results")
    parser.add_argument("--skip-wait", action="store_true", help="Skip waiting for workflow, just parse existing comments")
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    parser.add_argument("--timeout", type=int, default=600, help="Timeout in seconds for workflow completion (default: 600)")

    args = parser.parse_args()

    # Get GitHub token from environment
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("❌ Error: GITHUB_TOKEN environment variable not set")
        print("   Set it with: export GITHUB_TOKEN='your_token_here'")
        print("   Or create a token at: https://github.com/settings/tokens")
        sys.exit(1)

    if args.debug:
        print(f"🔍 Debug mode enabled")
        print(f"   Repository: {args.repo}")
        print(f"   PR Number: {args.pr}")
        print(f"   Timeout: {args.timeout}s")
        print(f"   Skip Wait: {args.skip_wait}")

    # Run review cycle
    cycle = AutomatedReviewCycle(args.repo, args.pr, github_token, debug=args.debug)
    result = cycle.run(skip_wait=args.skip_wait, timeout=args.timeout)
    
    # Output results
    if args.output:
        with open(args.output, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\n💾 Results saved to {args.output}")
    else:
        print("\n" + "="*60)
        print("📄 FULL RESULTS (JSON)")
        print("="*60)
        print(json.dumps(result, indent=2))
    
    # Exit code based on whether fixes are needed
    sys.exit(1 if result.get("needs_fixes") else 0)


if __name__ == "__main__":
    main()

