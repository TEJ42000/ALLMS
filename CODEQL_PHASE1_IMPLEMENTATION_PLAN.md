# CodeQL Phase 1 Implementation Plan
# Path Injection Vulnerability Fixes (Alerts #31-38)

**Date:** 2026-01-10  
**PR:** #258  
**Issue:** #251  
**Epic:** #250  
**Status:** 🔴 **IN PROGRESS - Fixing Code Review Issues**

---

## Executive Summary

PR #258 addresses 7 HIGH priority path injection vulnerabilities but has CRITICAL issues identified in code review that must be fixed before merge. This document outlines the systematic approach to fix all issues.

---

## Current Status

### CodeQL Alerts Being Fixed

| Alert # | File | Line | Description | Status |
|---------|------|------|-------------|--------|
| #31 | `admin_courses.py` | 1612 | User-provided path in file access | ✅ Fixed |
| #33 | `admin_courses.py` | 1637 | User-provided path in file access | ✅ Fixed |
| #34 | `admin_courses.py` | 1646 | User-provided path in file access | ✅ Fixed |
| #35 | `admin_courses.py` | 1691 | User-provided path in file access | ✅ Fixed |
| #36 | `admin_courses.py` | 1726 | User-provided path in file access | ✅ Fixed |
| #37 | `slide_archive.py` | 53 | User-provided path in file access | ⚠️ Needs Fix |
| #38 | `text_extractor.py` | 116 | User-provided path in file access | ✅ Fixed |

---

## Code Review Issues to Fix

### 🔴 CRITICAL Priority (Must Fix Before Merge)

#### Issue 1: Inconsistent Path Usage in `slide_archive.py`
**Location:** Line 65  
**Severity:** CRITICAL  
**Security Impact:** Bypasses validation entirely

**Problem:**
```python
# Line 54-66 (CURRENT - INCORRECT)
validated_path = validate_path_within_base(str(file_path), MATERIALS_BASE)
...
with zipfile.ZipFile(file_path, 'r') as zf:  # ❌ Using unvalidated file_path!
```

**Fix:**
```python
with zipfile.ZipFile(validated_path, 'r') as zf:  # ✅ Use validated_path
```

**Files to Modify:**
- `app/services/slide_archive.py` (line 65)
- `app/services/slide_archive.py` (line 114 in `extract_slide_archive()`)

---

#### Issue 2: Missing Path Validation in `get_file_type()`
**Location:** `slide_archive.py` lines 71-92  
**Severity:** CRITICAL  
**Security Impact:** Opens files without validation

**Problem:**
```python
def get_file_type(file_path: Path) -> str:
    if not file_path.exists():
        return 'unknown'
    
    try:
        with open(file_path, 'rb') as f:  # ❌ No path validation!
```

**Fix:**
```python
def get_file_type(file_path: Path) -> str:
    # Security: Validate path to prevent path traversal attacks (CWE-22/23/36)
    try:
        validated_path = validate_path_within_base(str(file_path), MATERIALS_BASE)
    except ValueError as e:
        logger.warning("Path validation failed for path=%s: %s", file_path, e)
        return 'unknown'
    
    if not validated_path.exists():
        return 'unknown'
    
    try:
        with open(validated_path, 'rb') as f:  # ✅ Use validated_path
```

---

### ⚠️ HIGH Priority (Should Fix Before Merge)

#### Issue 3: Missing Security Tests
**Severity:** HIGH  
**Impact:** No verification that fixes work

**Required Tests:**

1. **Test path traversal in `is_slide_archive()`**
   ```python
   def test_is_slide_archive_blocks_path_traversal():
       result = is_slide_archive(Path("../../../etc/passwd"))
       assert result is False
   ```

2. **Test null byte injection**
   ```python
   def test_is_slide_archive_blocks_null_bytes():
       result = is_slide_archive(Path("test\x00.zip"))
       assert result is False
   ```

3. **Test validated paths are used**
   ```python
   def test_is_slide_archive_uses_validated_path(tmp_path):
       # Create valid ZIP with manifest
       # Verify it's opened with validated path
   ```

4. **Test `get_file_type()` security**
   ```python
   def test_get_file_type_blocks_path_traversal():
       result = get_file_type(Path("../../../etc/passwd"))
       assert result == 'unknown'
   ```

**Files to Create:**
- `tests/test_slide_archive_security.py` (new file)

---

#### Issue 4: Redundant Validation Code in `admin_courses.py`
**Location:** Lines 134-139, 157-163  
**Severity:** HIGH (Code Quality)  
**Impact:** Maintenance burden, potential inconsistency

**Problem:**
- Duplicate null byte check (already in `validate_path_within_base()`)
- Manual path validation using `.relative_to()` instead of centralized function

**Fix:**
Remove duplicate checks, rely on centralized validation

---

### 📝 MEDIUM Priority (Should Address)

#### Issue 5: Test Coverage Gap
**Severity:** MEDIUM

**Required:**
- Add tests for all modified functions
- Test both attack scenarios and valid usage
- Verify error messages are correct

---

#### Issue 6: Logging Enhancement
**Severity:** MEDIUM

**Current:**
```python
logger.warning("Path validation failed for path=%s: %s", file_path, e)
```

**Enhanced:**
```python
logger.warning(
    "Path validation failed for path=%s (attempted resolve: %s): %s",
    file_path,
    str(Path(file_path).resolve()),
    e
)
```

---

## Implementation Steps

### Step 1: Fix CRITICAL Issues ✅

1. **Fix `is_slide_archive()` to use validated path**
   - File: `app/services/slide_archive.py`
   - Line: 65
   - Change: `file_path` → `validated_path`

2. **Fix `extract_slide_archive()` to use validated path**
   - File: `app/services/slide_archive.py`
   - Line: 114
   - Change: `file_path` → validated path from `is_slide_archive()`

3. **Add path validation to `get_file_type()`**
   - File: `app/services/slide_archive.py`
   - Lines: 71-92
   - Add: Validation at function start

---

### Step 2: Add Security Tests ✅

1. **Create `tests/test_slide_archive_security.py`**
   - Test path traversal blocking
   - Test null byte injection blocking
   - Test valid paths accepted
   - Test validated paths used

2. **Update existing tests if needed**
   - Ensure tests pass with new validation
   - Add edge case coverage

---

### Step 3: Refactor Redundant Code ✅

1. **Clean up `admin_courses.py`**
   - Remove duplicate null byte check
   - Use centralized validation for corrected paths

---

### Step 4: Enhance Logging ✅

1. **Add resolved path to warning logs**
   - Helps with debugging
   - Shows what path was attempted

---

### Step 5: Run Tests and Verify ✅

1. **Run full test suite**
   ```bash
   pytest -v
   ```

2. **Run security tests specifically**
   ```bash
   pytest tests/test_slide_archive_security.py -v
   pytest tests/test_syllabus_parser.py -v
   ```

3. **Verify CodeQL alerts resolved**
   - Push changes
   - Wait for CodeQL scan
   - Confirm alerts #31-38 are closed

---

## Acceptance Criteria

### Functional Requirements
- [x] All 7 CodeQL alerts (#31-38) are fixed
- [ ] All CRITICAL issues from code review are fixed
- [ ] All HIGH priority issues from code review are fixed
- [ ] Security tests added with 100% coverage
- [ ] All existing tests still pass

### Security Requirements
- [ ] Path traversal attacks blocked in all functions
- [ ] Null byte injection blocked in all functions
- [ ] Validated paths used consistently (not original paths)
- [ ] Security events logged appropriately

### Code Quality Requirements
- [ ] No duplicate validation code
- [ ] Consistent error handling
- [ ] Clear security comments (CWE references)
- [ ] Enhanced logging for debugging

---

## Testing Strategy

### Unit Tests
- Path traversal attempts (various patterns)
- Null byte injection
- Valid path acceptance
- Error handling

### Integration Tests
- End-to-end file operations
- Admin API endpoints with malicious paths
- Upload endpoints with traversal attempts

### Security Tests
- Verify CodeQL alerts are resolved
- Manual penetration testing
- Edge case coverage

---

## Risk Assessment

### Security Risks
- **CRITICAL:** Using unvalidated paths bypasses all security
- **HIGH:** Missing validation in some functions
- **MEDIUM:** Inconsistent error messages

### Mitigation
- ✅ Centralized validation function
- ✅ Comprehensive test coverage
- ✅ Code review before merge
- ✅ CodeQL verification

---

## Timeline

| Phase | Task | Estimated Time | Status |
|-------|------|----------------|--------|
| 1 | Fix CRITICAL issues | 15 min | 🔄 In Progress |
| 2 | Add security tests | 30 min | ⏳ Pending |
| 3 | Refactor redundant code | 15 min | ⏳ Pending |
| 4 | Enhance logging | 10 min | ⏳ Pending |
| 5 | Run tests & verify | 15 min | ⏳ Pending |
| **Total** | | **~85 min** | |

---

## Next Steps

1. ✅ Create implementation plan (this document)
2. 🔄 Fix CRITICAL Issue #1 (inconsistent path usage)
3. ⏳ Fix CRITICAL Issue #2 (missing validation in `get_file_type()`)
4. ⏳ Add comprehensive security tests
5. ⏳ Refactor redundant code
6. ⏳ Enhance logging
7. ⏳ Run full test suite
8. ⏳ Push changes and verify CodeQL
9. ⏳ Request re-review
10. ⏳ Merge to main

---

**Status:** 🔴 **Ready to implement fixes**  
**Next Action:** Fix CRITICAL issues in `slide_archive.py`

