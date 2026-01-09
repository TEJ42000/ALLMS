# EMERGENCY: IAP Access Broken - Admin Cannot Access

**Date:** 2026-01-09 21:20 UTC  
**Severity:** CRITICAL  
**Issue:** 403 Forbidden on /admin/courses and /admin/users  
**Root Cause:** Google Cloud IAP blocking access (NOT application code)

---

## 🚨 **CRITICAL FINDING**

The rollback didn't fix the issue, which means:
- ❌ **NOT a code problem**
- ✅ **IAP (Identity-Aware Proxy) configuration issue**
- ✅ **Your email was removed from IAP or IAP settings changed**

---

## ⚡ **IMMEDIATE FIX: Add Your Email to IAP**

### **Step 1: Go to IAP Console**

1. Open: https://console.cloud.google.com/security/iap?project=vigilant-axis-483119-r8
2. Find the service: **lls-study-portal** (Cloud Run service)
3. Click the checkbox next to it
4. Click **"ADD PRINCIPAL"** on the right side panel

### **Step 2: Add Your Email**

1. In the "New principals" field, enter your email address
   - What is your email? (e.g., `matej@mgms.eu` or `matthewm@augmentcode.com`)
2. In the "Select a role" dropdown, choose:
   - **IAP-secured Web App User**
3. Click **"SAVE"**

### **Step 3: Test Access**

1. Wait 1-2 minutes for IAP to update
2. Try accessing: https://lls-study-portal-sarfwmfd3q-ez.a.run.app/admin/courses
3. Should work now!

---

## 🔍 **How to Check Current IAP Settings**

### **Option 1: Via Console (Recommended)**

1. Go to: https://console.cloud.google.com/security/iap?project=vigilant-axis-483119-r8
2. Find **lls-study-portal** in the list
3. Click on it to see who has access
4. Check if your email is listed

### **Option 2: Via gcloud CLI**

```bash
# List IAP settings for Cloud Run service
gcloud iap web get-iam-policy \
  --resource-type=backend-services \
  --service=lls-study-portal \
  --project=vigilant-axis-483119-r8 \
  --region=europe-west4
```

---

## 🎯 **What Likely Happened**

### **Scenario 1: IAP Was Enabled Recently**

If IAP was just enabled:
- IAP starts with **NO users** by default
- You need to manually add authorized users
- This would explain why you suddenly lost access

### **Scenario 2: Your Email Was Removed**

If someone removed your email from IAP:
- You would get 403 Forbidden
- Need to re-add your email

### **Scenario 3: IAP Settings Changed**

If IAP settings were modified:
- Access list might have been cleared
- Need to reconfigure

---

## 📋 **Quick Diagnostic**

### **Question 1: What is your email address?**

The application expects users from `@mgms.eu` domain to have admin access.

**Is your email:**
- `matej@mgms.eu` ✅ (should work)
- `matthewm@augmentcode.com` ⚠️ (needs to be on allow list)
- Something else?

### **Question 2: Can you access the main page?**

Try: https://lls-study-portal-sarfwmfd3q-ez.a.run.app

**If you get 403 on the main page:**
- IAP is blocking you completely
- Your email is NOT in IAP access list
- **FIX:** Add your email to IAP (see Step 1-3 above)

**If main page works but /admin/* doesn't:**
- IAP is allowing you through
- Application is denying access
- **FIX:** Check if your email domain is `@mgms.eu`

---

## 🛠️ **Emergency Access Methods**

### **Method 1: Disable IAP Temporarily**

**⚠️ WARNING: This makes the app publicly accessible!**

```bash
# Disable IAP for the service
gcloud iap web disable \
  --resource-type=backend-services \
  --service=lls-study-portal \
  --project=vigilant-axis-483119-r8 \
  --region=europe-west4
```

Then:
1. Access the admin panel
2. Fix the issue
3. Re-enable IAP:

```bash
# Re-enable IAP
gcloud iap web enable \
  --resource-type=backend-services \
  --service=lls-study-portal \
  --project=vigilant-axis-483119-r8 \
  --region=europe-west4
```

### **Method 2: Add Yourself via gcloud**

```bash
# Add your email to IAP
gcloud iap web add-iam-policy-binding \
  --resource-type=backend-services \
  --service=lls-study-portal \
  --project=vigilant-axis-483119-r8 \
  --region=europe-west4 \
  --member='user:YOUR_EMAIL@mgms.eu' \
  --role='roles/iap.httpsResourceAccessor'
```

Replace `YOUR_EMAIL@mgms.eu` with your actual email.

---

## 🔧 **Verify IAP Configuration**

### **Check 1: Is IAP Enabled?**

```bash
gcloud iap web get-iam-policy \
  --resource-type=backend-services \
  --service=lls-study-portal \
  --project=vigilant-axis-483119-r8 \
  --region=europe-west4
```

**Expected output:**
```yaml
bindings:
- members:
  - user:matej@mgms.eu
  - user:matthewm@augmentcode.com
  role: roles/iap.httpsResourceAccessor
```

**If output is empty:**
- No users have access
- Need to add users

### **Check 2: Is Your Email Listed?**

Look for your email in the output above.

**If NOT listed:**
- You don't have IAP access
- **FIX:** Add your email (see Method 2 above)

---

## 📞 **What to Tell Me**

Please provide:

1. **Your email address:**
   - What email are you using to access the app?

2. **Can you access the main page?**
   - Try: https://lls-study-portal-sarfwmfd3q-ez.a.run.app
   - Do you get 403 or does it load?

3. **IAP status:**
   - Run: `gcloud iap web get-iam-policy --resource-type=backend-services --service=lls-study-portal --project=vigilant-axis-483119-r8 --region=europe-west4`
   - Share the output

4. **When did this start?**
   - Did you have access before today?
   - Did anything change in IAP settings?

---

## ✅ **Most Likely Fix**

**Add your email to IAP:**

1. Go to: https://console.cloud.google.com/security/iap?project=vigilant-axis-483119-r8
2. Select **lls-study-portal**
3. Click **"ADD PRINCIPAL"**
4. Enter your email
5. Select role: **IAP-secured Web App User**
6. Click **"SAVE"**
7. Wait 1-2 minutes
8. Try accessing /admin/courses again

---

## 🎯 **Why Rollback Didn't Work**

The rollback restored the application code, but:
- IAP is a **separate service** from the application
- IAP settings are **NOT in the code**
- IAP settings are **NOT deployed** with the application
- IAP is configured in **Google Cloud Console**

So if IAP settings changed, rolling back the code won't fix it.

---

**Status:** 🚨 IAP configuration issue  
**Fix:** Add your email to IAP access list  
**ETA:** 2-5 minutes once email is added  
**Created:** 2026-01-09 21:20 UTC

