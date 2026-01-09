# Allow List Diagnostic Guide for amberunal13@gmail.com

**Date:** 2026-01-09  
**User:** amberunal13@gmail.com  
**Issue:** Cannot add user to allow list

---

## Quick Diagnostic Steps

### Step 1: Check Firestore Console

1. Go to [Firebase Console](https://console.firebase.google.com/project/vigilant-axis-483119-r8/firestore/data)
2. Navigate to the `allowed_users` collection
3. Look for document with ID: `amberunal13%40gmail.com`
   - Note: The `@` is URL-encoded as `%40`
   - Full document ID: `amberunal13%40gmail.com`

**What to check:**
- Does the document exist?
- If yes, what are the field values?

---

### Step 2: Check Document Fields

If the document exists, check these fields:

| Field | Expected Value | What It Means |
|-------|---------------|---------------|
| `email` | amberunal13@gmail.com | User's email |
| `active` | true or false | Is user active? |
| `expires_at` | null or timestamp | When access expires |
| `added_at` | timestamp | When user was added |
| `updated_at` | timestamp | Last update time |
| `added_by` | email | Who added the user |
| `reason` | string | Why user was added |
| `notes` | string or null | Additional notes |

---

### Step 3: Determine User Status

Based on the field values:

#### Scenario A: Document Does NOT Exist
```
✅ User can be added
Expected behavior: add_user() creates new document
```

#### Scenario B: Document Exists with `active=true` and NOT expired
```
⚠️  User is ACTIVE and EFFECTIVE
Expected behavior: add_user() returns error
Error message: "User amberunal13@gmail.com is already on the allow list and has active access."
```

#### Scenario C: Document Exists with `active=false`
```
✅ User is INACTIVE (soft-deleted)
Expected behavior: add_user() reactivates user
Should: Update document, set active=true, return 201 Created
```

#### Scenario D: Document Exists with `active=true` but EXPIRED
```
✅ User is EXPIRED
Expected behavior: add_user() renews user
Should: Update document, set new expires_at, return 201 Created
```

---

## Manual Firestore Query

If you have `gcloud` CLI installed and authenticated:

```bash
# Authenticate
gcloud auth application-default login

# Run diagnostic script
python scripts/check_user_simple.py amberunal13@gmail.com
```

---

## Expected Behavior Based on Fix

The recent fix (commit 9074b7d) changed `add_user()` to:

1. **Check if user exists:**
   ```python
   existing = self.get_user(email)
   ```

2. **If user exists:**
   - Check if `existing.is_effective` (active AND not expired)
   - If effective: Return error (user already has access)
   - If NOT effective: Reactivate user with new details

3. **If user does NOT exist:**
   - Create new document

---

## Debugging the Error

### If you're getting "User is already on the allow list":

**Check which error message you're getting:**

#### Error Message A (Expected for active users):
```
User amberunal13@gmail.com is already on the allow list and has active access. 
Use the update endpoint to modify their entry.
```

**Meaning:** User is active and effective. This is correct behavior.

**Solution:** 
- If you want to modify the user, use the UPDATE endpoint
- If you want to remove and re-add, first DELETE the user

---

#### Error Message B (Old error - should NOT happen):
```
User amberunal13@gmail.com is already on the allow list
```

**Meaning:** Old code is still running (fix not deployed)

**Solution:** 
- Verify the fix is deployed to production
- Check commit 9074b7d is in the deployed version

---

### If you're getting a different error:

Please provide:
1. The exact error message
2. The HTTP status code
3. The request you're sending

---

## Testing the Fix

### Test Case 1: Add Active User (Should Fail)

**Setup:**
- User exists with `active=true`, not expired

**Request:**
```bash
POST /api/admin/users/allowed
{
  "email": "amberunal13@gmail.com",
  "reason": "Test"
}
```

**Expected Response:**
```json
{
  "detail": "User amberunal13@gmail.com is already on the allow list and has active access. Use the update endpoint to modify their entry."
}
```

**Status Code:** 400 Bad Request

---

### Test Case 2: Reactivate Inactive User (Should Succeed)

**Setup:**
- User exists with `active=false`

**Request:**
```bash
POST /api/admin/users/allowed
{
  "email": "amberunal13@gmail.com",
  "reason": "Reactivating for new project"
}
```

**Expected Response:**
```json
{
  "email": "amberunal13@gmail.com",
  "active": true,
  "reason": "Reactivating for new project",
  ...
}
```

**Status Code:** 201 Created

**Logs Should Show:**
```
INFO: Reactivating previously removed/expired user: amberunal13@gmail.com (was active=False, expired=False)
INFO: Reactivated user on allow list: amberunal13@gmail.com (by admin@mgms.eu)
```

---

### Test Case 3: Add New User (Should Succeed)

**Setup:**
- User does NOT exist

**Request:**
```bash
POST /api/admin/users/allowed
{
  "email": "amberunal13@gmail.com",
  "reason": "New user"
}
```

**Expected Response:**
```json
{
  "email": "amberunal13@gmail.com",
  "active": true,
  "reason": "New user",
  ...
}
```

**Status Code:** 201 Created

**Logs Should Show:**
```
INFO: Added new user to allow list: amberunal13@gmail.com (by admin@mgms.eu)
```

---

## Troubleshooting Steps

### Step 1: Verify Deployment

Check if the fix is deployed:

```bash
# Check current commit in production
git log --oneline -1

# Should show commit 9074b7d or later
```

If not deployed:
1. Deploy the latest code
2. Restart the application

---

### Step 2: Check Application Logs

Look for log entries related to this user:

```bash
# If using Cloud Run
gcloud run services logs read allms \
  --region=europe-west4 \
  --project=vigilant-axis-483119-r8 \
  --limit=100 | grep amberunal13
```

Look for:
- "Reactivating previously removed/expired user"
- "Added new user to allow list"
- "User X is already on the allow list"
- Any error messages

---

### Step 3: Manual Firestore Fix (If Needed)

If the user is stuck in a bad state, you can manually fix it:

**Option A: Delete the document (hard delete)**
1. Go to Firestore Console
2. Find document `amberunal13%40gmail.com`
3. Delete it
4. Try adding the user again

**Option B: Update the document (reactivate)**
1. Go to Firestore Console
2. Find document `amberunal13%40gmail.com`
3. Set `active` to `true`
4. Set `expires_at` to `null` (or future date)
5. User should now have access

---

## What to Provide for Further Debugging

If the issue persists, please provide:

1. **Firestore Document Screenshot:**
   - Screenshot of the document in Firestore Console
   - Show all fields and values

2. **Error Response:**
   - Exact error message
   - HTTP status code
   - Full response body

3. **Request Details:**
   - Endpoint called
   - Request body
   - Headers (if relevant)

4. **Application Logs:**
   - Any log entries related to this user
   - Timestamp of the request
   - Any error stack traces

5. **Deployment Status:**
   - Current commit hash in production
   - When was the last deployment
   - Is commit 9074b7d deployed?

---

## Quick Fix Commands

### If user is inactive and you want to reactivate:

```bash
# Using the API
curl -X POST https://your-app-url/api/admin/users/allowed \
  -H "Content-Type: application/json" \
  -d '{
    "email": "amberunal13@gmail.com",
    "reason": "Reactivating user"
  }'
```

### If user is active and you want to update:

```bash
# Using the API
curl -X PUT https://your-app-url/api/admin/users/allowed/amberunal13@gmail.com \
  -H "Content-Type: application/json" \
  -d '{
    "reason": "Updated reason",
    "expires_at": null
  }'
```

### If you want to remove and re-add:

```bash
# Step 1: Remove (soft delete)
curl -X DELETE https://your-app-url/api/admin/users/allowed/amberunal13@gmail.com

# Step 2: Re-add (reactivate)
curl -X POST https://your-app-url/api/admin/users/allowed \
  -H "Content-Type: application/json" \
  -d '{
    "email": "amberunal13@gmail.com",
    "reason": "Re-adding user"
  }'
```

---

## Summary

The fix (commit 9074b7d) should handle all these scenarios:

1. ✅ User doesn't exist → Create new
2. ✅ User exists but inactive → Reactivate
3. ✅ User exists but expired → Renew
4. ⚠️ User exists and active → Return helpful error

**Next Step:** Check Firestore Console to see the current state of amberunal13@gmail.com

---

**Created:** 2026-01-09  
**For User:** amberunal13@gmail.com  
**Related Commit:** 9074b7d

