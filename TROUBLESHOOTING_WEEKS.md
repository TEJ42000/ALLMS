# 🔍 Troubleshooting: Weeks Not Appearing

**Issue:** Week cards not showing up on the Weeks tab  
**Status:** 🔧 DEBUGGING  
**Date:** 2026-01-08

---

## ✅ What We Know

### Backend Status:
- ✅ **Weeks exist in Firestore** (6 weeks for LLS-2025-2026)
- ✅ **API endpoint exists** (`/api/admin/courses/{course_id}`)
- ✅ **Endpoint returns weeks** (when `include_weeks=true`)

### Frontend Status:
- ✅ **Weeks tab added** to navigation
- ✅ **Weeks section added** to HTML
- ✅ **weeks.js loaded** and initialized
- ❓ **Weeks not rendering** (need to check browser console)

---

## 🔍 Debugging Steps

### Step 1: Open Browser Console

1. **Visit your portal:** https://lls-study-portal-sarfwmfd3q-ez.a.run.app
2. **Open Developer Tools:**
   - Chrome/Edge: Press `F12` or `Ctrl+Shift+I` (Windows) / `Cmd+Option+I` (Mac)
   - Firefox: Press `F12` or `Ctrl+Shift+K` (Windows) / `Cmd+Option+K` (Mac)
   - Safari: Enable Developer menu first, then `Cmd+Option+C`
3. **Click the "Console" tab**

### Step 2: Navigate to Weeks Tab

1. Click the **"📅 Weeks"** tab in the navigation
2. Watch the console for log messages

### Step 3: Check Console Logs

Look for these messages (added in latest commit):

```
[WeekContentManager] Initializing...
[WeekContentManager] Course ID: LLS-2025-2026
[WeekContentManager] Weeks grid element: <div id="weeks-grid">
[WeekContentManager] Loading weeks...
[WeekContentManager] Fetching weeks from API...
[WeekContentManager] URL: /api/admin/courses/LLS-2025-2026?include_weeks=true
[WeekContentManager] Response status: 200
[WeekContentManager] Course data: {...}
[WeekContentManager] Weeks found: 6
[WeekContentManager] First week: {...}
[WeekContentManager] renderWeeks called with: [...]
[WeekContentManager] Clearing grid and rendering 6 weeks
[WeekContentManager] Sorted weeks: [Week 1, Week 2, ...]
[WeekContentManager] Creating card 1/6: {...}
[WeekContentManager] ✅ All week cards rendered successfully
```

---

## 🐛 Common Issues & Solutions

### Issue 1: "weeks-grid element not found"

**Symptom:**
```
[WeekContentManager] weeks-grid element not found!
```

**Cause:** The weeks section HTML isn't loaded or has wrong ID

**Solution:**
1. Check if `templates/index.html` has the weeks section:
   ```html
   <section id="weeks-section" class="section">
       <div class="week-grid" id="weeks-grid">
   ```
2. Make sure the section ID is `weeks-section` (matches tab data-tab)
3. Verify the grid ID is `weeks-grid` (matches JavaScript selector)

---

### Issue 2: "Failed to load weeks: 401" or "403"

**Symptom:**
```
[WeekContentManager] Response status: 401
[WeekContentManager] API error: Unauthorized
```

**Cause:** Authentication issue - not logged in or session expired

**Solution:**
1. Make sure you're logged in to the portal
2. Refresh the page
3. Check if other tabs work (Dashboard, AI Tutor)
4. If nothing works, clear cookies and log in again

---

### Issue 3: "Failed to load weeks: 404"

**Symptom:**
```
[WeekContentManager] Response status: 404
[WeekContentManager] API error: Course not found
```

**Cause:** Course ID doesn't exist or is wrong

**Solution:**
1. Check the course ID in console:
   ```
   [WeekContentManager] Course ID: LLS-2025-2026
   ```
2. Verify this course exists in Firestore
3. Check if `window.COURSE_ID` is set correctly in HTML

---

### Issue 4: "Weeks found: 0"

**Symptom:**
```
[WeekContentManager] Weeks found: 0
[WeekContentManager] No weeks to render, showing fallback
```

**Cause:** API returns course but no weeks

**Solution:**
1. Check if weeks exist in Firestore:
   ```bash
   python -c "from google.cloud import firestore; db = firestore.Client(); print(list(db.collection('courses').document('LLS-2025-2026').collection('weeks').stream()))"
   ```
2. If weeks exist, check if API is including them:
   - URL should have `?include_weeks=true`
   - Backend should call `service.get_course(course_id, include_weeks=True)`

---

### Issue 5: JavaScript Error

**Symptom:**
```
Uncaught TypeError: Cannot read property 'appendChild' of null
```

**Cause:** DOM element not found when trying to render

**Solution:**
1. Check if weeks.js is loaded after DOM is ready
2. Verify script has `defer` attribute:
   ```html
   <script src="/static/js/weeks.js" defer></script>
   ```
3. Make sure weeks-grid exists before JavaScript runs

---

### Issue 6: Weeks Tab Not Showing Section

**Symptom:**
- Weeks tab exists in navigation
- Clicking it does nothing
- Console shows no errors

**Cause:** Tab switching logic not working

**Solution:**
1. Check if section has correct ID:
   ```html
   <section id="weeks-section" class="section">
   ```
2. Check if tab has correct data-tab:
   ```html
   <button class="nav-tab" data-tab="weeks">
   ```
3. Verify app.js tab switching code is working
4. Check if section has `active` class when tab is clicked

---

## 🔧 Manual Testing

### Test 1: Check if weeks.js is loaded

Open console and type:
```javascript
window.weekContentManager
```

**Expected:** Should show the WeekContentManager object  
**If undefined:** Script not loaded or failed to initialize

### Test 2: Check if weeks-grid exists

Open console and type:
```javascript
document.getElementById('weeks-grid')
```

**Expected:** Should show the div element  
**If null:** HTML not loaded or wrong ID

### Test 3: Check course ID

Open console and type:
```javascript
window.COURSE_ID || window.COURSE_CONTEXT?.courseId
```

**Expected:** Should show "LLS-2025-2026" or similar  
**If undefined:** Course context not set

### Test 4: Manually fetch weeks

Open console and type:
```javascript
fetch('/api/admin/courses/LLS-2025-2026?include_weeks=true')
  .then(r => r.json())
  .then(data => console.log('Weeks:', data.weeks))
```

**Expected:** Should show array of weeks  
**If error:** API issue or authentication problem

### Test 5: Manually render fallback

Open console and type:
```javascript
window.weekContentManager.renderFallbackWeeks()
```

**Expected:** Should show 3 placeholder week cards  
**If error:** Rendering logic broken

---

## 📊 Expected Console Output (Success)

When everything works, you should see:

```
[WeekContentManager] Initializing...
[WeekContentManager] Course ID: LLS-2025-2026
[WeekContentManager] Weeks grid element: <div id="weeks-grid" class="week-grid">
[WeekContentManager] Loading weeks...
[WeekContentManager] Fetching weeks from API...
[WeekContentManager] URL: /api/admin/courses/LLS-2025-2026?include_weeks=true
[WeekContentManager] Response status: 200
[WeekContentManager] Course data: {id: "LLS-2025-2026", name: "Law and Legal Skills", weeks: Array(6), ...}
[WeekContentManager] Weeks found: 6
[WeekContentManager] First week: {weekNumber: 1, title: "Test Week", ...}
[WeekContentManager] renderWeeks called with: (6) [{...}, {...}, ...]
[WeekContentManager] Clearing grid and rendering 6 weeks
[WeekContentManager] Sorted weeks: (6) ["Week 1", "Week 2", "Week 3", "Week 4", "Week 5", "Week 6"]
[WeekContentManager] Creating card 1/6: {weekNumber: 1, title: "Test Week"}
[WeekContentManager] Creating card 2/6: {weekNumber: 2, title: "Week 2"}
[WeekContentManager] Creating card 3/6: {weekNumber: 3, title: "Criminal Law"}
[WeekContentManager] Creating card 4/6: {weekNumber: 4, title: "Week 4"}
[WeekContentManager] Creating card 5/6: {weekNumber: 5, title: "Week 5"}
[WeekContentManager] Creating card 6/6: {weekNumber: 6, title: "Week 6"}
[WeekContentManager] ✅ All week cards rendered successfully
```

---

## 🎯 Quick Checklist

Before reporting an issue, verify:

- [ ] Browser console is open
- [ ] Navigated to Weeks tab
- [ ] Checked console for error messages
- [ ] Verified weeks exist in Firestore (6 weeks)
- [ ] Confirmed API endpoint works (manual fetch test)
- [ ] Checked if weeks-grid element exists
- [ ] Verified weeks.js is loaded
- [ ] Tested if fallback weeks render

---

## 📝 What to Report

If weeks still don't appear, please provide:

1. **Browser:** Chrome/Firefox/Safari + version
2. **Console logs:** Copy all `[WeekContentManager]` messages
3. **Network tab:** Check if API request was made
4. **Elements tab:** Check if weeks-grid exists
5. **Manual tests:** Results of Test 1-5 above

---

## 🚀 Next Steps

1. **Open browser console** (F12)
2. **Navigate to Weeks tab**
3. **Copy all console logs**
4. **Share the logs** so we can diagnose the issue

The detailed logging added in commit `ed30bf9` will help us identify exactly where the problem is!

---

**Let's get those weeks showing!** 🎓✨

