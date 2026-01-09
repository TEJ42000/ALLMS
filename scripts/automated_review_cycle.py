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
    def __init__(self, repo: str, pr_number: int, github_token: str):
        self.repo = repo
        self.pr_number = pr_number
        self.github_token = github_token
        self.base_url = f"https://api.github.com/repos/{repo}"
        self.headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
    
    def get_pr_details(self) -> Dict:
        """Get PR details"""
        url = f"{self.base_url}/pulls/{self.pr_number}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()
    
    def get_workflow_runs(self, sha: str) -> List[Dict]:
        """Get workflow runs for a specific commit"""
        url = f"{self.base_url}/actions/runs"
        params = {
            "event": "pull_request",
            "head_sha": sha,
            "per_page": 10
        }
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()["workflow_runs"]
    
    def wait_for_review_completion(self, sha: str, timeout: int = 600) -> Optional[Dict]:
        """Wait for Claude Code Review workflow to complete"""
        print(f"⏳ Waiting for Claude Code Review to complete (timeout: {timeout}s)...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            runs = self.get_workflow_runs(sha)
            
            # Find Claude Code Review workflow
            review_run = next(
                (run for run in runs if "Claude Code Review" in run["name"]),
                None
            )
            
            if review_run:
                status = review_run["status"]
                conclusion = review_run.get("conclusion")
                
                print(f"  Status: {status}, Conclusion: {conclusion}")
                
                if status == "completed":
                    return review_run
            
            time.sleep(10)
        
        print("❌ Timeout waiting for review to complete")
        return None
    
    def get_pr_comments(self) -> List[Dict]:
        """Get all comments on the PR"""
        url = f"{self.base_url}/issues/{self.pr_number}/comments"
        params = {"per_page": 100}
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()
    
    def parse_review_comments(self, comments: List[Dict]) -> Dict:
        """Parse Claude Code Review comments"""
        review_comments = [
            c for c in comments
            if "github-actions" in c["user"]["login"].lower() or
               "claude" in c["body"].lower()
        ]
        
        if not review_comments:
            return {"has_review": False}
        
        latest_review = review_comments[-1]
        body = latest_review["body"]
        
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
        
        # Simple parsing - look for priority markers
        lines = body.split("\n")
        current_priority = None
        current_issue = []
        
        for line in lines:
            line_upper = line.upper()
            
            if "CRITICAL" in line_upper:
                if current_issue:
                    if current_priority:
                        result[f"{current_priority}_issues"].append("\n".join(current_issue))
                    current_issue = []
                current_priority = "critical"
            elif "HIGH" in line_upper and "PRIORITY" in line_upper:
                if current_issue:
                    if current_priority:
                        result[f"{current_priority}_issues"].append("\n".join(current_issue))
                    current_issue = []
                current_priority = "high"
            elif "MEDIUM" in line_upper and "PRIORITY" in line_upper:
                if current_issue:
                    if current_priority:
                        result[f"{current_priority}_issues"].append("\n".join(current_issue))
                    current_issue = []
                current_priority = "medium"
            elif "LOW" in line_upper and "PRIORITY" in line_upper:
                if current_issue:
                    if current_priority:
                        result[f"{current_priority}_issues"].append("\n".join(current_issue))
                    current_issue = []
                current_priority = "low"
            elif current_priority and line.strip():
                current_issue.append(line)
        
        # Add last issue
        if current_issue and current_priority:
            result[f"{current_priority}_issues"].append("\n".join(current_issue))
        
        # Calculate summary
        result["has_critical"] = len(result["critical_issues"]) > 0
        result["has_high"] = len(result["high_issues"]) > 0
        result["has_medium"] = len(result["medium_issues"]) > 0
        result["needs_fixes"] = result["has_critical"] or result["has_high"] or result["has_medium"]
        
        return result
    
    def run(self) -> Dict:
        """Run the automated review cycle"""
        print(f"🚀 Starting automated review cycle for PR #{self.pr_number}")
        
        # Get PR details
        pr = self.get_pr_details()
        sha = pr["head"]["sha"]
        print(f"📝 PR: {pr['title']}")
        print(f"🔗 SHA: {sha}")
        
        # Wait for review to complete
        review_run = self.wait_for_review_completion(sha)
        
        if not review_run:
            return {"error": "Review workflow did not complete in time"}
        
        if review_run["conclusion"] != "success":
            print(f"⚠️ Review workflow conclusion: {review_run['conclusion']}")
        
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
    
    args = parser.parse_args()
    
    # Get GitHub token from environment
    github_token = os.getenv("GITHUB_TOKEN")
    if not github_token:
        print("❌ Error: GITHUB_TOKEN environment variable not set")
        sys.exit(1)
    
    # Run review cycle
    cycle = AutomatedReviewCycle(args.repo, args.pr, github_token)
    result = cycle.run()
    
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

