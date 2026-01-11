# Troubleshooting User Access for amberunal13@gmail.com

**Date:** 2026-01-09  
**Issue:** User can be added to allow list but still gets "no access" when trying to log in  
**Deployment:** v2.11.0 deployed successfully at 21:03:52 UTC

---

## ✅ **What's Working**

- ✅ User can be added to allow list (admin panel works)
- ✅ Deployment completed successfully
- ✅ Fix is live in production

## ❌ **What's Not Working**

- ❌ User still gets "no access" when trying to log in

---

## 🔍 **Root Cause Analysis**

### **Possible Causes:**

1. **User was added BEFORE deployment**
   - Old code might have created entry with `active=false`
   - Need to verify and fix the entry

2. **User needs to clear session/cookies**
   - Stale authentication session
   - Old "denied" status cached in browser

3. **IAP/OAuth caching**
   - Google IAP might be caching the authorization decision
   - Need to wait for cache to expire or force refresh

4. **Firestore document issue**
   - Entry might exist but with wrong fields
   - Need to verify document structure

---

## 🛠️ **Step-by-Step Troubleshooting**

### **Step 1: Verify User Status in Firestore**

**Check the user's document:**

1. Go to [Firestore Console](https://console.firebase.google.com/project/vigilant-axis-483119-r8/firestore/data)
2. Navigate to `allowed_users` collection
3. Find document: `amberunal13%40gmail.com`
4. Verify these fields:

```
✅ email: "amberunal13@gmail.com"
✅ active: true  (MUST be true!)
✅ expires_at: null (or future date)
✅ added_at: <recent timestamp>
✅ updated_at: <recent timestamp>
✅ added_by: <admin email>
✅ reason: <some reason>
```

**If `active` is `false`:**
- The user was added before the deployment
- The old code created an inactive entry
- **FIX:** Manually set `active` to `true` in Firestore

---

### **Step 2: Have User Clear Session**

**User should:**

1. **Log out completely**
   - Click logout button
   - Or go to: https://lls-study-portal-sarfwmfd3q-ez.a.run.app/auth/logout

2. **Clear browser cache and cookies**
   - Chrome: Settings → Privacy → Clear browsing data
   - Select "Cookies and other site data"
   - Select "Cached images and files"
   - Time range: "Last hour" or "All time"

3. **Close all browser tabs**

4. **Open new incognito/private window**

5. **Try logging in again**
   - Go to: https://lls-study-portal-sarfwmfd3q-ez.a.run.app
   - Click "Login with Google"
   - Use amberunal13@gmail.com

---

### **Step 3: Check Application Logs**

**Look for authentication logs:**

```bash
# If using Cloud Run
gcloud run services logs read lls-study-portal \
  --region=europe-west4 \
  --project=vigilant-axis-483119-r8 \
  --limit=100 | grep amberunal13
```

**Look for these log entries:**

**✅ Success:**
```
INFO: User found in allow list and has effective access: amberunal13@gmail.com
DEBUG: User authorized via allow list: amberunal13@gmail.com
```

**❌ Failure:**
```
INFO: Allow list entry exists but not effective (active=False, expired=False): amberunal13@gmail.com
DEBUG: Email not found in allow list: amberunal13@gmail.com
INFO: User not authorized: amberunal13@gmail.com (domain: gmail.com)
```

---

### **Step 4: Force Reactivation**

If the user still can't access, **remove and re-add** them:

**Option A: Via Admin UI**

1. Go to admin panel
2. Navigate to "Allow List Management"
3. Find amberunal13@gmail.com
4. Click "Remove" (soft delete)
5. Wait 5 seconds
6. Click "Add User"
7. Enter email: amberunal13@gmail.com
8. Enter reason: "Reactivating after deployment"
9. Click "Add"

**Option B: Via API**

```bash
# Step 1: Remove user
curl -X DELETE https://lls-study-portal-sarfwmfd3q-ez.a.run.app/api/admin/users/allowed/amberunal13%40gmail.com \
  -H "Authorization: Bearer YOUR_TOKEN"

# Step 2: Re-add user
curl -X POST https://lls-study-portal-sarfwmfd3q-ez.a.run.app/api/admin/users/allowed \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "email": "amberunal13@gmail.com",
    "reason": "Reactivating after deployment"
  }'
```

---

### **Step 5: Manual Firestore Fix**

If all else fails, **manually fix the Firestore document:**

1. Go to [Firestore Console](https://console.firebase.google.com/project/vigilant-axis-483119-r8/firestore/data)
2. Navigate to `allowed_users` collection
3. Find document: `amberunal13%40gmail.com`
4. Click "Edit"
5. Set these fields:
   ```
   active: true
   expires_at: null
   updated_at: <current timestamp>
   ```
6. Click "Update"
7. Have user try logging in again (after clearing cache)

---

## 🔍 **Authentication Flow**

Understanding how authentication works:

1. **User tries to access the app**
2. **Middleware checks authentication** (`app/middleware/auth_middleware.py`)
3. **For OAuth mode:** Checks session cookie
4. **For IAP mode:** Checks IAP headers
5. **Calls `is_user_authorized()`** (`app/services/auth_service.py`)
6. **Checks domain:** Is user from @mgms.eu?
   - ✅ Yes → Grant access
   - ❌ No → Check allow list
7. **Calls `check_allow_list()`** (`app/services/auth_service.py:155`)
8. **Calls `is_user_allowed()`** (`app/services/allow_list_service.py:52`)
9. **Checks `entry.is_effective`**
   - `is_effective = active AND not expired`
10. **Returns result:**
    - ✅ True → User authenticated
    - ❌ False → User denied

---

## 📊 **Expected vs Actual**

### **Expected Behavior (After Fix):**

```
User: amberunal13@gmail.com
Document: amberunal13%40gmail.com
Fields:
  active: true
  expires_at: null
  
Authentication Flow:
1. User not from @mgms.eu → Check allow list
2. Document found → Check is_effective
3. active=true AND not expired → is_effective=true
4. Return: User authorized ✅
```

### **Actual Behavior (If Failing):**

```
User: amberunal13@gmail.com
Document: amberunal13%40gmail.com
Fields:
  active: false  ← PROBLEM!
  expires_at: null
  
Authentication Flow:
1. User not from @mgms.eu → Check allow list
2. Document found → Check is_effective
3. active=false → is_effective=false
4. Return: User not authorized ❌
```

---

## ✅ **Quick Fix Checklist**

- [ ] **Verify deployment completed** (v2.11.0 at 21:03:52 UTC) ✅
- [ ] **Check Firestore document** (`active` must be `true`)
- [ ] **User clears browser cache and cookies**
- [ ] **User logs out completely**
- [ ] **User tries in incognito/private window**
- [ ] **Check application logs** for authentication attempts
- [ ] **If still failing:** Remove and re-add user
- [ ] **If still failing:** Manually fix Firestore document

---

## 🎯 **Most Likely Solution**

**The user was added BEFORE the deployment completed.**

The old code (before the fix) would have created a document with `active=false` when trying to add an existing user.

**Solution:**
1. Check Firestore - if `active=false`, set it to `true`
2. OR remove and re-add the user (this will use the new code)
3. Have user clear cache and try again

---

## 📞 **What to Tell the User**

"Hi! The fix has been deployed. Please try these steps:

1. **Log out completely** from the application
2. **Clear your browser cache and cookies**
3. **Close all browser tabs**
4. **Open a new incognito/private window**
5. **Try logging in again**

If that doesn't work, I'll need to check your account status in our database and may need to reset your access. Please let me know if you're still having issues after trying these steps."

---

## 🔧 **For Admins**

**Quick commands to check user status:**

```bash
# Check Firestore document
# (Requires gcloud auth)
gcloud firestore documents get \
  --project=vigilant-axis-483119-r8 \
  --collection=allowed_users \
  --document=amberunal13%40gmail.com

# Check application logs
gcloud run services logs read lls-study-portal \
  --region=europe-west4 \
  --project=vigilant-axis-483119-r8 \
  --limit=100 | grep amberunal13
```

---

**Status:** Deployment complete, troubleshooting user access  
**Next Step:** Verify Firestore document has `active=true`  
**Created:** 2026-01-09 21:10 UTC

