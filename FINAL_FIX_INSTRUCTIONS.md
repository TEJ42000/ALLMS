# FINAL FIX: User is EXPIRED

## 🎯 Problem Found

The log shows:
```
❌ ALLOW LIST: User amberunal2013@gmail.com found but NOT EFFECTIVE 
   (active=True, expired=True, is_effective=False)
```

**The user exists in Firestore but is EXPIRED!**

---

## ✅ Solution: Remove Expiration Date

### **Step 1: Open Firestore Console**

https://console.firebase.google.com/project/vigilant-axis-483119-r8/firestore/data

### **Step 2: Find the User**

1. Click on `allowed_users` collection
2. Find document: `amberunal2013%40gmail.com`
3. Click on it to open

### **Step 3: Check `expires_at` Field**

Look at the `expires_at` field. It probably has a date in the past.

### **Step 4: Fix It**

**Option A: Set to null (recommended)**
1. Click the pencil icon next to `expires_at`
2. Change the value to `null`
3. Click "Update"

**Option B: Set to future date**
1. Click the pencil icon next to `expires_at`
2. Set to a future date (e.g., 2027-01-01)
3. Click "Update"

**Option C: Delete the field**
1. Click the trash icon next to `expires_at`
2. Confirm deletion

### **Step 5: Verify `active` is `true`**

While you're there, make sure:
- `active` field = `true` (boolean)

If it's `false`, change it to `true`.

---

## 🎉 After Fixing

**Have the user try to log in:**

1. Close all browser tabs
2. Open NEW incognito window
3. Go to: https://lls-study-portal-sarfwmfd3q-ez.a.run.app
4. Click "Login with Google"
5. Log in with amberunal2013@gmail.com
6. **Should work immediately!** ✅

---

## 📊 What the Firestore Entry Should Look Like

```
Document ID: amberunal2013%40gmail.com

Fields:
  email: "amberunal2013@gmail.com" (string)
  active: true (boolean)
  added_by: "matej@mgms.eu" (string)
  added_at: <timestamp>
  updated_at: <timestamp>
  reason: "External student access" (string)
  expires_at: null (or future date, or deleted)
  notes: null (optional)
```

---

## 🔍 Why This Happened

The user was probably added with an expiration date that has now passed. The allow list check correctly identified:
- User exists ✅
- User is active ✅
- User is expired ❌ (this is the problem!)

Setting `expires_at` to `null` means the user never expires.

---

**Fix the `expires_at` field in Firestore and have her try again!**

