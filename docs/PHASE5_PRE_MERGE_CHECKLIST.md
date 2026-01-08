# Phase 5: Pre-Merge Checklist

**Date:** 2026-01-08  
**PR:** #155  
**Branch:** feature/phase5-week7-boss-quest  
**Status:** Pre-Merge Validation

---

## Overview

This document tracks all critical and medium priority issues that must be addressed before merging PR #155 into main.

---

## 🔴 CRITICAL - Before Merge

### 1. Fix test mismatches ✅ COMPLETE

**Issue:** Unit tests needed for Week 7 Quest service

**Status:** ✅ COMPLETE
- Created `tests/test_week7_quest_service.py` (15 tests)
- All tests passing
- Coverage: Quest activation, exam readiness, updates, edge cases

**Reference:** Issue #1 (if exists)

---

### 2. Verify activity counter field names ⚠️ TODO

**Issue:** Inconsistent field names between service and model

**Problem:**
- `week7_quest_service.py` uses `flashcard_set_completed`
- `gamification_service.py` increments `flashcards_reviewed`
- Exam readiness will always show 0 for flashcards

**Action Required:**
- [ ] Check `ActivityCounters` model for correct field name
- [ ] Update `week7_quest_service.py` to use correct field
- [ ] Add test to verify field name consistency

**Files to Check:**
- `app/models/gamification_models.py` - ActivityCounters model
- `app/services/week7_quest_service.py:271` - Flashcard count
- `app/services/gamification_service.py:562` - Flashcard increment

**Priority:** CRITICAL - Affects exam readiness calculation

---

### 3. Add XP validation ⚠️ TODO

**Issue:** No validation that XP values are non-negative

**Problem:**
- XP calculations could produce negative values
- No bounds checking on XP awards
- Could break level calculations

**Action Required:**
- [ ] Add XP validation in `calculate_xp_for_activity()`
- [ ] Ensure XP is always >= 0
- [ ] Add max XP cap if needed
- [ ] Add test for negative XP handling

**Files to Modify:**
- `app/services/gamification_service.py` - XP calculation
- `tests/test_week7_quest_service.py` - Add XP validation tests

**Priority:** CRITICAL - Data integrity

---

### 4. Fix error message disclosure ⚠️ TODO

**Issue:** Error messages may expose sensitive information

**Problem:**
- Exception messages returned directly to client
- Could expose internal implementation details
- Security risk

**Action Required:**
- [ ] Review all error messages in quest endpoints
- [ ] Use generic error messages for client
- [ ] Log detailed errors server-side only
- [ ] Add error message sanitization

**Files to Check:**
- `app/routes/gamification.py` - Quest endpoints
- `app/services/week7_quest_service.py` - Error handling

**Priority:** CRITICAL - Security

---

### 5. Add course_id validation ✅ COMPLETE

**Issue:** course_id not validated in quest activation

**Status:** ✅ COMPLETE
- Added course_id validation in `check_and_activate_quest()`
- Store course_id with quest data
- Added test for course validation

**Reference:** HIGH Priority Fix #2

---

## 🟡 MEDIUM - Short-term

### 6. Add Firestore transaction for activation ⚠️ TODO

**Issue:** Quest activation not using Firestore transaction

**Problem:**
- Race condition if multiple activations attempted
- Could activate quest twice
- No atomicity guarantee

**Action Required:**
- [ ] Wrap quest activation in Firestore transaction
- [ ] Add test for concurrent activation attempts
- [ ] Ensure idempotency

**Files to Modify:**
- `app/services/week7_quest_service.py:80-91` - Activation logic

**Priority:** MEDIUM - Race condition risk

---

### 7. Fix quiz prediction logic ⚠️ TODO

**Issue:** Quiz prediction assumes all quizzes pass

**Problem:**
```python
# In _predict_stats_after_activity()
if activity_type == "quiz_completed":
    predicted.activities.quizzes_completed += 1
    predicted.activities.quizzes_passed += 1  # ← Assumes pass
```

**Action Required:**
- [ ] Don't assume quiz passes
- [ ] Use conservative estimate (don't increment passed)
- [ ] Or pass quiz result to prediction method
- [ ] Add test for quiz prediction

**Files to Modify:**
- `app/services/week7_quest_service.py:217-220` - Prediction logic

**Priority:** MEDIUM - Affects exam readiness accuracy

---

### 8. Add course validation to progress endpoint ⚠️ TODO

**Issue:** Progress endpoint doesn't validate course_id

**Problem:**
- Returns quest progress without checking course
- Could show wrong course's quest data

**Action Required:**
- [ ] Add course_id parameter to progress endpoint
- [ ] Validate quest.course_id matches requested course
- [ ] Return 404 if course mismatch

**Files to Modify:**
- `app/routes/gamification.py:502-544` - Progress endpoint

**Priority:** MEDIUM - Data accuracy

---

### 9. Remove deprecated method or deprecation notice ⚠️ TODO

**Issue:** `update_quest_progress()` marked as deprecated but still exists

**Problem:**
- Deprecated method still in codebase
- Could be called accidentally
- Confusing for future developers

**Action Required:**
- [ ] Either remove deprecated method entirely
- [ ] Or add clear deprecation warning with alternative
- [ ] Update documentation

**Files to Modify:**
- `app/services/week7_quest_service.py:227-270` - Deprecated method

**Priority:** MEDIUM - Code cleanliness

---

## 📊 Progress Summary

**CRITICAL:** 2/5 complete (40%)  
**MEDIUM:** 0/4 complete (0%)  

**Overall:** 2/9 complete (22%)

---

## 🔍 Detailed Action Items

### Immediate Actions (CRITICAL)

1. **Verify activity counter field names**
   - Check ActivityCounters model
   - Fix field name in week7_quest_service.py
   - Test exam readiness calculation

2. **Add XP validation**
   - Add bounds checking
   - Ensure non-negative XP
   - Add validation tests

3. **Fix error message disclosure**
   - Review all error messages
   - Sanitize client-facing errors
   - Keep detailed logs server-side

### Short-term Actions (MEDIUM)

4. **Add Firestore transaction for activation**
   - Wrap activation in transaction
   - Test concurrent activations

5. **Fix quiz prediction logic**
   - Don't assume quiz passes
   - Use conservative estimate

6. **Add course validation to progress endpoint**
   - Validate course_id parameter
   - Check quest.course_id matches

7. **Remove deprecated method**
   - Clean up deprecated code
   - Update documentation

---

## ✅ Validation Checklist

Before merging, verify:

- [ ] All CRITICAL issues resolved
- [ ] All tests passing
- [ ] No security vulnerabilities
- [ ] Error messages sanitized
- [ ] Field names consistent
- [ ] XP validation in place
- [ ] Course validation complete
- [ ] Documentation updated
- [ ] Code review approved

---

## 📝 Testing Checklist

Run these tests before merge:

```bash
# Unit tests
pytest tests/test_week7_quest_service.py -v

# Integration tests (if available)
pytest tests/test_gamification_service.py -v

# Check for security issues
bandit -r app/services/week7_quest_service.py

# Verify no hardcoded secrets
git secrets --scan

# Check code quality
pylint app/services/week7_quest_service.py
```

---

## 🚀 Deployment Checklist

After merge, before deploy:

- [ ] Run full test suite
- [ ] Deploy to staging
- [ ] Test quest activation in staging
- [ ] Test exam readiness calculation
- [ ] Test double XP application
- [ ] Monitor error logs
- [ ] Verify Firestore indexes deployed

---

## 📚 Related Documentation

- `docs/PHASE5_ESSENTIAL_FIXES.md` - Essential fixes tracking
- `docs/MERGE_CONFLICT_RESOLUTION.md` - Merge conflict guide
- `tests/test_week7_quest_service.py` - Unit tests

---

**Last Updated:** 2026-01-08  
**Next Review:** After CRITICAL issues resolved

