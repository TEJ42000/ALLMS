# Deployment Guide - PR #238 Flashcard Features

**Date:** 2026-01-09  
**PR:** #238 - Phase 2: Flashcards UI - Card Actions Enhancement  
**Commit:** dae94d0

---

## Prerequisites

- ✅ All code review fixes committed and pushed
- ✅ PR #238 approved and ready to merge
- ⚠️ Firebase CLI or gcloud CLI authenticated
- ⚠️ Access to Firebase Console for verification

---

## Task 1: Deploy Firestore Composite Indexes

### Option A: Using Firebase CLI (Recommended)

```bash
# Authenticate if needed
firebase login

# Deploy indexes
firebase deploy --only firestore:indexes --project vigilant-axis-483119-r8
```

### Option B: Using gcloud CLI

```bash
# Authenticate if needed
gcloud auth login
gcloud config set project vigilant-axis-483119-r8

# Deploy indexes from file
gcloud firestore indexes composite create --project=vigilant-axis-483119-r8 \
  --collection-group=flashcard_notes \
  --query-scope=COLLECTION \
  --field-config field-path=card_id,order=ASCENDING \
  --field-config field-path=set_id,order=ASCENDING

gcloud firestore indexes composite create --project=vigilant-axis-483119-r8 \
  --collection-group=flashcard_issues \
  --query-scope=COLLECTION \
  --field-config field-path=user_id,order=ASCENDING \
  --field-config field-path=set_id,order=ASCENDING

gcloud firestore indexes composite create --project=vigilant-axis-483119-r8 \
  --collection-group=flashcard_issues \
  --query-scope=COLLECTION \
  --field-config field-path=user_id,order=ASCENDING \
  --field-config field-path=status,order=ASCENDING

gcloud firestore indexes composite create --project=vigilant-axis-483119-r8 \
  --collection-group=flashcard_issues \
  --query-scope=COLLECTION \
  --field-config field-path=set_id,order=ASCENDING \
  --field-config field-path=status,order=ASCENDING
```

### Expected Output

```
Creating composite index...done.
Created index [projects/vigilant-axis-483119-r8/databases/(default)/collectionGroups/flashcard_notes/indexes/...]
```

### Indexes Being Created

1. **flashcard_notes** - `card_id` (ASC) + `set_id` (ASC)
2. **flashcard_issues** - `user_id` (ASC) + `set_id` (ASC)
3. **flashcard_issues** - `user_id` (ASC) + `status` (ASC)
4. **flashcard_issues** - `set_id` (ASC) + `status` (ASC)

---

## Task 2: Wait for Index Build Completion

### Estimated Time
- **Small collections (<1000 docs):** 5-10 minutes
- **Medium collections (1000-10000 docs):** 10-20 minutes
- **Large collections (>10000 docs):** 20-60 minutes

### What Happens During Build
- Firestore scans existing documents
- Creates index structures
- Status changes: `CREATING` → `READY`

### ⚠️ Important
- **Do NOT deploy application code** until indexes are READY
- Queries will fail with "index required" errors if indexes are still building

---

## Task 3: Verify Index Status

### Option A: Firebase Console (Visual)

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select project: `vigilant-axis-483119-r8`
3. Navigate to: **Firestore Database** → **Indexes** tab
4. Look for the 4 new composite indexes
5. Verify status shows: **"Enabled"** or **"Ready"** (green checkmark)

### Option B: gcloud CLI

```bash
# List all composite indexes
gcloud firestore indexes composite list --project=vigilant-axis-483119-r8

# Filter for flashcard indexes
gcloud firestore indexes composite list --project=vigilant-axis-483119-r8 | grep flashcard
```

### Expected Output

```
COLLECTION_GROUP    QUERY_SCOPE  FIELDS                          STATE
flashcard_notes     COLLECTION   card_id ASC, set_id ASC         READY
flashcard_issues    COLLECTION   user_id ASC, set_id ASC         READY
flashcard_issues    COLLECTION   user_id ASC, status ASC         READY
flashcard_issues    COLLECTION   set_id ASC, status ASC          READY
```

### ✅ Success Criteria
- All 4 indexes show `STATE: READY`
- No errors in the output
- Indexes are visible in Firebase Console

---

## Task 4: Deploy Application Code

### Option A: Automated Deployment (GitHub Actions)

```bash
# Tag the commit for production deployment
git tag v2.11.0
git push origin v2.11.0
```

This triggers the GitHub Actions workflow that:
1. Builds Docker image
2. Pushes to Google Container Registry
3. Deploys to Cloud Run (europe-west4)

### Option B: Manual Deployment

```bash
# From repository root
./deploy.sh
```

### Verify Deployment

```bash
# Check Cloud Run service status
gcloud run services describe allms \
  --region=europe-west4 \
  --project=vigilant-axis-483119-r8

# Get service URL
gcloud run services describe allms \
  --region=europe-west4 \
  --project=vigilant-axis-483119-r8 \
  --format='value(status.url)'
```

### Expected Output

```
Service [allms] revision [allms-00xxx-xxx] has been deployed and is serving 100 percent of traffic.
Service URL: https://allms-xxxxxxxxxx-ew.a.run.app
```

---

## Task 5: Monitor Production Logs

### View Real-Time Logs

```bash
# Stream Cloud Run logs
gcloud run services logs tail allms \
  --region=europe-west4 \
  --project=vigilant-axis-483119-r8
```

### Check for Errors

```bash
# Filter for errors
gcloud run services logs read allms \
  --region=europe-west4 \
  --project=vigilant-axis-483119-r8 \
  --limit=50 \
  --filter='severity>=ERROR'
```

### Test Flashcard Endpoints

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe allms \
  --region=europe-west4 \
  --project=vigilant-axis-483119-r8 \
  --format='value(status.url)')

# Test note creation (requires authentication)
curl -X POST "$SERVICE_URL/api/flashcards/notes" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "card_id": "test_card_123",
    "set_id": "test_set_456",
    "note_text": "Test note from deployment verification"
  }'

# Test issue reporting
curl -X POST "$SERVICE_URL/api/flashcards/issues" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "card_id": "test_card_123",
    "set_id": "test_set_456",
    "issue_type": "typo",
    "description": "Test issue from deployment verification"
  }'
```

### ✅ Success Criteria
- No Firestore index errors in logs
- Note creation returns 201 Created
- Issue reporting returns 201 Created
- Queries execute successfully
- No 500 errors related to missing indexes

---

## Task 6: Create Follow-Up PR for Test Suite

### Step 1: Create GitHub Issue

```bash
# Use GitHub CLI or web interface
gh issue create \
  --title "Add comprehensive test suite for flashcard notes and issues (PR #238 follow-up)" \
  --body "$(cat <<EOF
## Overview

Create comprehensive test suite for flashcard notes and issue reporting features implemented in PR #238.

## Related

- Closes deferred HIGH priority item from PR #238 code review
- Follows up on commit dae94d0

## Scope

### Test Files to Create

1. **tests/test_flashcard_notes.py**
   - Test note CRUD operations
   - Test transactional note creation
   - Test user isolation
   - Test input validation
   - Test error handling

2. **tests/test_flashcard_issues.py**
   - Test issue creation
   - Test issue retrieval (user vs admin)
   - Test issue updates (admin only)
   - Test issue deletion (admin only)
   - Test authorization checks

### Test Infrastructure

- Mock Firestore operations
- Mock authentication (get_current_user)
- Mock admin user vs regular user
- Pytest fixtures for common setup

### Coverage Requirements

- Target: >80% code coverage
- All CRUD operations tested
- All validation rules tested
- All authorization checks tested
- All error paths tested

## Test Cases Required

### Flashcard Notes (15+ tests)

- ✅ Create note (new)
- ✅ Create note (update existing via transaction)
- ✅ Get note by card_id (found)
- ✅ Get note by card_id (not found - 404)
- ✅ Get all notes (no filter)
- ✅ Get all notes (with set_id filter)
- ✅ Update note (success)
- ✅ Update note (not found - 404)
- ✅ Delete note by card_id (success)
- ✅ Delete note by card_id (not found - 404)
- ✅ Validate note_text (empty string - 400)
- ✅ Validate note_text (too long - 400)
- ✅ HTML sanitization (XSS prevention)
- ✅ User isolation (cannot access other user's notes)
- ✅ Transaction prevents race condition

### Flashcard Issues (15+ tests)

- ✅ Create issue (success)
- ✅ Get issue (owner can see)
- ✅ Get issue (non-owner cannot see - 403)
- ✅ Get issue (admin can see any)
- ✅ Get all issues (user sees only own)
- ✅ Get all issues (admin sees all)
- ✅ Get all issues (filter by set_id)
- ✅ Get all issues (filter by status)
- ✅ Update issue (admin only - success)
- ✅ Update issue (non-admin - 403)
- ✅ Delete issue (admin only - success)
- ✅ Delete issue (non-admin - 403)
- ✅ Validate issue_type (invalid - 400)
- ✅ Validate description (empty - 400)
- ✅ HTML sanitization (XSS prevention)

## Acceptance Criteria

- [ ] All test files created
- [ ] All test cases pass
- [ ] Code coverage >80%
- [ ] Mock Firestore properly
- [ ] Mock authentication properly
- [ ] Tests run in CI/CD
- [ ] Documentation updated

## Estimated Effort

- **Time:** 4-6 hours
- **Complexity:** Medium
- **Priority:** HIGH (deferred from PR #238)

EOF
)" \
  --label "testing" \
  --label "high-priority" \
  --label "phase-2"
```

### Step 2: Create Feature Branch

```bash
# Create and checkout new branch
git checkout main
git pull origin main
git checkout -b feature/flashcard-tests

# Push branch to remote
git push -u origin feature/flashcard-tests
```

### Step 3: Create Test Files Structure

```bash
# Create test files
touch tests/test_flashcard_notes.py
touch tests/test_flashcard_issues.py
touch tests/conftest.py  # Shared fixtures

# Create initial structure
cat > tests/test_flashcard_notes.py << 'EOF'
"""
Unit tests for flashcard notes API endpoints.

Tests CRUD operations, validation, authorization, and error handling.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
from fastapi import HTTPException

# TODO: Import routes and models
# from app.routes.flashcard_notes import router
# from app.models.flashcard_models import FlashcardNote, FlashcardNoteCreate


class TestFlashcardNotesCreate:
    """Test note creation endpoint"""
    
    @pytest.mark.asyncio
    async def test_create_note_new(self):
        """Test creating a new note"""
        # TODO: Implement
        pass
    
    @pytest.mark.asyncio
    async def test_create_note_update_existing(self):
        """Test updating existing note via transaction"""
        # TODO: Implement
        pass


class TestFlashcardNotesRead:
    """Test note retrieval endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_note_found(self):
        """Test getting note by card_id (found)"""
        # TODO: Implement
        pass
    
    @pytest.mark.asyncio
    async def test_get_note_not_found(self):
        """Test getting note by card_id (not found)"""
        # TODO: Implement
        pass


# TODO: Add more test classes
EOF
```

### Step 4: Create Pull Request

```bash
# After implementing tests, commit and push
git add tests/
git commit -m "test: Add comprehensive test suite for flashcard features

Implements deferred HIGH priority item from PR #238 code review.

- Created test_flashcard_notes.py with 15+ test cases
- Created test_flashcard_issues.py with 15+ test cases
- Mocked Firestore operations
- Mocked authentication
- Achieved >80% code coverage

Closes #XXX (issue number from step 1)"

git push origin feature/flashcard-tests

# Create PR
gh pr create \
  --title "Add comprehensive test suite for flashcard features (PR #238 follow-up)" \
  --body "Implements deferred HIGH priority testing from PR #238 code review." \
  --base main
```

---

## Deployment Checklist

Use this checklist to track progress:

### Pre-Deployment
- [ ] Code review fixes committed (dae94d0)
- [ ] PR #238 approved
- [ ] Firebase/gcloud CLI authenticated

### Index Deployment
- [ ] Firestore indexes deployed
- [ ] Index build started (10-20 min wait)
- [ ] All 4 indexes show READY status
- [ ] Verified in Firebase Console

### Application Deployment
- [ ] Application code deployed to Cloud Run
- [ ] Deployment successful (no errors)
- [ ] Service is serving traffic

### Verification
- [ ] Production logs checked (no errors)
- [ ] Note creation tested in production
- [ ] Issue reporting tested in production
- [ ] Queries execute successfully
- [ ] No index-related errors

### Follow-Up
- [ ] GitHub issue created for test suite
- [ ] Feature branch created (feature/flashcard-tests)
- [ ] Test files structure created
- [ ] Test implementation in progress

---

## Rollback Plan

If issues are discovered after deployment:

### Rollback Application

```bash
# List recent revisions
gcloud run revisions list \
  --service=allms \
  --region=europe-west4 \
  --project=vigilant-axis-483119-r8

# Rollback to previous revision
gcloud run services update-traffic allms \
  --region=europe-west4 \
  --project=vigilant-axis-483119-r8 \
  --to-revisions=PREVIOUS_REVISION=100
```

### Disable Indexes (if needed)

Indexes cannot be deleted, but queries will fall back to existing indexes if the new ones are not used.

---

## Support

### Logs and Monitoring

- **Cloud Run Logs:** https://console.cloud.google.com/run/detail/europe-west4/allms/logs
- **Firestore Console:** https://console.firebase.google.com/project/vigilant-axis-483119-r8/firestore
- **Error Reporting:** https://console.cloud.google.com/errors

### Common Issues

**Issue:** "Index required" errors in production
**Solution:** Wait for indexes to finish building (check status)

**Issue:** Authentication errors when testing endpoints
**Solution:** Use valid IAP token or test through the web UI

**Issue:** Deployment fails
**Solution:** Check Cloud Run logs for specific error, verify Docker build

---

**Status:** Ready for deployment  
**Next Action:** Deploy Firestore indexes (Task 1)  
**Estimated Total Time:** 30-60 minutes (including index build wait)

