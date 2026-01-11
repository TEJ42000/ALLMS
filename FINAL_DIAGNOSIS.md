# Final Diagnosis: Why User Can't Access

**Date:** 2026-01-09  
**User:** amberunal13@gmail.com  
**Issue:** Gets "Access Blocked" white page after Google login

---

## 🔍 **Root Cause**

The user is getting "Access Blocked" at the **OAuth callback authorization check** in `app/routes/auth.py` line 284.

The flow is:
1. ✅ User clicks "Login with Google"
2. ✅ User authenticates with Google successfully
3. ✅ Google redirects back to `/auth/callback`
4. ❌ `check_allow_list(email)` returns `False`
5. ❌ User sees "Access Blocked" (403 error page)

---

## 🎯 **The Problem**

The `check_allow_list()` function in `auth_service.py` is calling `AllowListService.is_user_allowed()` which:

1. Gets the user from Firestore using `_email_to_doc_id(email)`
2. Checks if `entry.is_effective` is True

**Possible issues:**

### **Issue 1: Firestore Service Not Available in Production**
- The Firestore client might not be initialized in production
- `service.is_available` returns `False`
- `check_allow_list()` returns `False`

### **Issue 2: Document ID Mismatch**
- Local: Document ID is `amberunal13%40gmail.com` (URL-encoded)
- Production: Might be using different encoding

### **Issue 3: Model Mismatch**
- There are TWO `AllowListEntry` models:
  - `app/models/allow_list_models.py` (correct, has `is_effective`)
  - `app/models/auth_models.py` (old, has `is_valid`)
- Production might be using the wrong model

---

## ✅ **Solution: Add Detailed Logging**

We need to add logging to production to see exactly what's failing. The issue is that `check_allow_list()` catches all exceptions and returns `False` silently.

---

## 🔧 **Immediate Fix**

Add this logging to `app/services/auth_service.py` in the `check_allow_list()` function:

```python
async def check_allow_list(email: str) -> bool:
    """Check if an email is on the allow list in Firestore."""
    try:
        from app.services.allow_list_service import get_allow_list_service
    except ImportError:
        logger.error("❌ ALLOW LIST: Import failed")  # ADD THIS
        return False
    
    try:
        service = get_allow_list_service()
        
        if not service.is_available:
            logger.error("❌ ALLOW LIST: Service not available (Firestore client is None)")  # ADD THIS
            return False
        
        logger.info("✅ ALLOW LIST: Service is available, checking user: %s", email)  # ADD THIS
        
        is_allowed = service.is_user_allowed(email)
        
        if is_allowed:
            logger.info("✅ ALLOW LIST: User %s is allowed", email)
        else:
            entry = service.get_user(email)
            if entry is None:
                logger.error("❌ ALLOW LIST: User %s NOT FOUND in Firestore", email)  # CHANGE TO ERROR
            else:
                logger.error(
                    "❌ ALLOW LIST: User %s found but not effective (active=%s, expired=%s)",
                    email, entry.active, entry.is_expired
                )  # CHANGE TO ERROR
        
        return is_allowed
        
    except Exception as e:
        logger.exception("❌ ALLOW LIST: Exception for %s: %s", email, str(e))  # CHANGE TO EXCEPTION
        return False
```

---

## 🚀 **Deployment Steps**

1. **Add the logging** (above changes)
2. **Commit and push**
3. **Deploy to production**
4. **Have user try to log in again**
5. **Check logs** to see exact failure

---

## 📋 **Expected Log Output**

### **If Firestore is not available:**
```
❌ ALLOW LIST: Service not available (Firestore client is None)
```

### **If user not found:**
```
✅ ALLOW LIST: Service is available, checking user: amberunal13@gmail.com
❌ ALLOW LIST: User amberunal13@gmail.com NOT FOUND in Firestore
```

### **If user found but not effective:**
```
✅ ALLOW LIST: Service is available, checking user: amberunal13@gmail.com
❌ ALLOW LIST: User amberunal13@gmail.com found but not effective (active=False, expired=False)
```

### **If everything works:**
```
✅ ALLOW LIST: Service is available, checking user: amberunal13@gmail.com
✅ ALLOW LIST: User amberunal13@gmail.com is allowed
```

---

## 🎯 **Next Steps**

1. I'll add the logging changes
2. Commit and deploy
3. Have user try again
4. Check logs to see exact issue
5. Fix based on logs

---

**This will tell us EXACTLY why the allow list check is failing!**

