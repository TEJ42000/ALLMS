# Automated Code Review Workflow

## Overview

This document explains the automated code review workflow for streamlining the review-fix-iterate cycle.

---

## Current Limitations (GitHub API)

### ❌ What's NOT Possible

1. **Cannot trigger workflows via comments** - The GitHub API doesn't support triggering workflows through comments like `@claude review`. This requires either:
   - A `workflow_dispatch` trigger (manual workflow trigger)
   - A push/PR event (automatic)

2. **Cannot read workflow outputs directly** - While we can see that workflows ran, we cannot programmatically access the detailed review comments that the Claude Code Action posts

3. **Cannot impersonate GitHub Actions** - We cannot act as the GitHub Action bot to post reviews

---

## ✅ Implemented Solution: Semi-Automated Workflow

### Approach

Instead of fully automated, we use a **semi-automated workflow** that's significantly better than manual copy-paste:

1. **Trigger review** by pushing a commit (automatic)
2. **Monitor workflow** completion
3. **Retrieve comments** from PR
4. **Parse feedback** into structured format
5. **Return results** for AI to implement fixes

### Components

#### 1. Python Script: `scripts/automated_review_cycle.py`

**Purpose:** Automate the review monitoring and parsing

**Usage:**
```bash
# Set GitHub token
export GITHUB_TOKEN="your_github_token"

# Run for PR #238
python scripts/automated_review_cycle.py --pr 238

# Save results to file
python scripts/automated_review_cycle.py --pr 238 --output review_results.json
```

**Features:**
- ✅ Waits for Claude Code Review workflow to complete (10min timeout)
- ✅ Retrieves all PR comments
- ✅ Parses review feedback by priority (CRITICAL/HIGH/MEDIUM/LOW)
- ✅ Returns structured JSON results
- ✅ Exit code indicates if fixes are needed

**Output Example:**
```json
{
  "has_review": true,
  "comment_id": 123456,
  "created_at": "2026-01-09T19:30:00Z",
  "body": "Full review comment text...",
  "critical_issues": [
    "Issue 1 description...",
    "Issue 2 description..."
  ],
  "high_issues": [...],
  "medium_issues": [...],
  "low_issues": [...],
  "has_critical": true,
  "has_high": false,
  "has_medium": true,
  "needs_fixes": true
}
```

#### 2. GitHub Workflow: `.github/workflows/automated-review-cycle.yml`

**Purpose:** Automatically monitor and summarize reviews

**Triggers:**
- On PR open/update
- Manual workflow dispatch

**Features:**
- ✅ Waits for Claude Code Review to complete
- ✅ Retrieves review comments
- ✅ Posts summary comment on PR
- ✅ Indicates if fixes are needed

---

## Workflow for AI Assistant

### Step 1: Push Commit to Trigger Review

```python
# AI pushes commit to PR branch
git push origin feature/flashcards-ui-phase-2-card-actions
```

This automatically triggers the Claude Code Review workflow.

### Step 2: Monitor Review Completion

```python
# AI runs the monitoring script
result = run_command("python scripts/automated_review_cycle.py --pr 238 --output /tmp/review.json")

# Parse results
with open('/tmp/review.json') as f:
    review_data = json.load(f)
```

### Step 3: Analyze Feedback

```python
if review_data['needs_fixes']:
    critical = review_data['critical_issues']
    high = review_data['high_issues']
    medium = review_data['medium_issues']
    
    # AI implements fixes based on parsed feedback
    implement_fixes(critical + high + medium)
```

### Step 4: Commit Fixes and Iterate

```python
# AI commits fixes
git add .
git commit -m "fix: Address code review feedback"
git push

# Repeat from Step 2 until no CRITICAL/HIGH/MEDIUM issues remain
```

---

## Manual Workflow (Fallback)

If the automated script fails, you can still use a manual workflow:

### Option A: Trigger Review Manually

1. Push a commit to the PR branch
2. Wait for Claude Code Review workflow to complete (~2-5 minutes)
3. Check PR comments for review feedback
4. Copy the review comment
5. Paste to AI assistant for implementation

### Option B: Use GitHub CLI

```bash
# Get PR comments
gh pr view 238 --comments

# Filter for review comments
gh pr view 238 --comments | grep -A 100 "Claude Code Review"
```

---

## Best Practices

### For AI Assistant

1. **Always run the monitoring script** after pushing commits
2. **Parse feedback systematically** - address CRITICAL first, then HIGH, then MEDIUM
3. **Commit fixes incrementally** - one commit per priority level
4. **Re-run review** after each fix batch
5. **Document fixes** in commit messages

### For Developers

1. **Set GITHUB_TOKEN** environment variable for the script
2. **Review AI fixes** before merging
3. **Monitor workflow runs** in GitHub Actions tab
4. **Check for false positives** in review feedback

---

## Troubleshooting

### Script Times Out

**Cause:** Review workflow taking longer than 10 minutes

**Solution:**
```python
# Increase timeout
python scripts/automated_review_cycle.py --pr 238 --timeout 1200
```

### No Review Comments Found

**Cause:** Workflow failed or hasn't posted comments yet

**Solution:**
1. Check GitHub Actions tab for workflow status
2. Verify workflow has `pull-requests: write` permission
3. Check if workflow is configured correctly

### Parse Errors

**Cause:** Review comment format changed

**Solution:**
1. Update parsing logic in `parse_review_comments()`
2. Add more robust regex patterns
3. Handle edge cases

---

## Future Enhancements

### Potential Improvements

1. **Workflow Dispatch Trigger** - Add to Claude Code Review workflow:
```yaml
on:
  pull_request:
    types: [opened, synchronize]
  workflow_dispatch:
    inputs:
      pr_number:
        required: true
```

2. **Review API Integration** - If Anthropic provides a review API:
```python
# Direct API call instead of parsing comments
review = anthropic.code_review.get(pr_number=238)
```

3. **Auto-Fix Implementation** - AI automatically implements fixes:
```python
# AI reads review, implements fixes, commits, and pushes
auto_fix_and_commit(review_data)
```

4. **Slack/Discord Notifications** - Alert when review is complete:
```python
notify_slack(f"Review complete for PR #{pr_number}: {summary}")
```

---

## Summary

### Current Capabilities

✅ **Semi-Automated:** AI can trigger, monitor, and parse reviews  
✅ **Structured Output:** JSON format for easy parsing  
✅ **Priority-Based:** CRITICAL/HIGH/MEDIUM/LOW classification  
✅ **Iterative:** Supports review-fix-iterate cycles  

### Limitations

❌ **Not Fully Automated:** Requires running Python script  
❌ **Comment-Based:** Cannot trigger via `@claude review` comment  
❌ **Parsing-Dependent:** Relies on comment format  

### Recommendation

**Use the semi-automated workflow** with the Python script. It's significantly better than manual copy-paste and provides structured, parseable feedback for the AI to implement fixes efficiently.

---

**Last Updated:** 2026-01-09  
**Version:** 1.0  
**Maintainer:** AI Assistant

