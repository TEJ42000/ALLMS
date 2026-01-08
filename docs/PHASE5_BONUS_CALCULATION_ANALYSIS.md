# Week 7 Bonus Calculation Analysis

**Date:** 2026-01-08  
**Issue:** MEDIUM - Decide on week7_bonus calculation approach  
**Status:** Analysis & Recommendation

---

## Current Implementation

### Bonus Application Order

```python
# Step 1: Base XP
xp_awarded = 100

# Step 2: Apply consistency bonus (1.5x)
xp_awarded = 100 * 1.5 = 150

# Step 3: Apply Week 7 double XP (2x)
week7_bonus = 150  # Current XP after consistency
xp_awarded = 150 * 2 = 300
```

### Current Behavior

- **Base XP:** 100
- **After Consistency:** 150 (+50 bonus)
- **After Week 7:** 300 (+150 bonus)
- **Total Bonus:** 200 (50 from consistency + 150 from Week 7)
- **week7_bonus tracked:** 150

---

## Problem Analysis

### Issue 1: Bonus Tracking Ambiguity

**Current:** `week7_bonus = xp_awarded` (line 474)
- Tracks 150 (includes consistency bonus)
- Quest shows "150 double XP earned"
- But user only got 100 base XP

**Question:** Should week7_bonus track:
- A) The bonus XP from Week 7 only (100)?
- B) The total XP that gets doubled (150)?

### Issue 2: User Expectation

**User sees:**
- "You earned 100 XP for this activity"
- "Week 7 Quest: +150 bonus XP"
- Total: 250 XP

**But actually gets:**
- Base: 100
- Consistency: +50
- Week 7: +150
- Total: 300 XP

**Confusion:** The "150 bonus XP" message doesn't match the actual bonus received.

---

## Options Analysis

### Option A: Track Base XP Only (RECOMMENDED)

**Implementation:**
```python
# Calculate base XP
base_xp = self.calculate_xp_for_activity(activity_type, activity_data)
xp_awarded = base_xp

# Apply consistency bonus
if consistency_bonus_active:
    xp_awarded = int(xp_awarded * bonus_multiplier)

# Apply Week 7 double XP
if week7_quest_active:
    week7_bonus = base_xp  # Track base XP only
    xp_awarded = xp_awarded * 2
```

**Example:**
- Base XP: 100
- Consistency: 100 * 1.5 = 150
- Week 7: 150 * 2 = 300
- **week7_bonus tracked:** 100
- **Total bonus from Week 7:** 150 (100 base + 50 from consistency)

**Pros:**
- ✅ Clear: "You earned 100 XP, doubled to 200"
- ✅ Consistent with base activity XP
- ✅ Easy to understand
- ✅ Matches user expectation

**Cons:**
- ❌ Doesn't show total bonus XP earned
- ❌ Requires storing base_xp separately

---

### Option B: Track Total Doubled XP (CURRENT)

**Implementation:**
```python
# Apply consistency bonus
xp_awarded = base_xp * consistency_multiplier

# Apply Week 7 double XP
week7_bonus = xp_awarded  # Track current XP
xp_awarded = xp_awarded * 2
```

**Example:**
- Base XP: 100
- Consistency: 150
- Week 7: 300
- **week7_bonus tracked:** 150
- **Total bonus from Week 7:** 150

**Pros:**
- ✅ Shows actual XP that gets doubled
- ✅ Simpler implementation (current)
- ✅ No need to store base_xp

**Cons:**
- ❌ Confusing: "150 bonus" but user got 100 base
- ❌ Includes consistency bonus in Week 7 tracking
- ❌ Harder to explain to users

---

### Option C: Track Actual Bonus XP

**Implementation:**
```python
# Apply consistency bonus
xp_after_consistency = base_xp * consistency_multiplier

# Apply Week 7 double XP
xp_after_week7 = xp_after_consistency * 2
week7_bonus = xp_after_week7 - xp_after_consistency  # Actual bonus
```

**Example:**
- Base XP: 100
- Consistency: 150
- Week 7: 300
- **week7_bonus tracked:** 150 (300 - 150)
- **Total bonus from Week 7:** 150

**Pros:**
- ✅ Shows actual bonus XP from Week 7
- ✅ Clear: "You got +150 bonus XP from Week 7"
- ✅ Accurate tracking

**Cons:**
- ❌ Same as Option B (includes consistency in calculation)
- ❌ More complex calculation

---

## Recommendation: Option A (Track Base XP)

### Rationale

1. **User Clarity:** Users understand "100 XP doubled to 200"
2. **Consistency:** Matches base activity XP values
3. **Transparency:** Clear what the quest is doubling
4. **Fairness:** Doesn't inflate numbers with other bonuses

### Implementation

```python
# Calculate base XP
base_xp = self.calculate_xp_for_activity(activity_type, activity_data)
xp_awarded = base_xp

# Apply weekly consistency bonus if active
consistency_bonus = 0
if xp_awarded > 0 and getattr(stats.streak, 'bonus_active', False):
    bonus_multiplier = getattr(stats.streak, 'bonus_multiplier', 1.0)
    
    if bonus_multiplier > 1.0:
        original_xp = xp_awarded
        xp_awarded = int(xp_awarded * bonus_multiplier)
        consistency_bonus = xp_awarded - original_xp

# Apply Week 7 double XP if quest is active
week7_bonus = 0
week7_quest_updates = {}
if stats.week7_quest.active and base_xp > 0:  # Check base_xp, not xp_awarded
    week7_bonus = base_xp  # Track base XP only
    xp_awarded = xp_awarded * 2  # Double current XP (includes consistency)
```

### Example Calculation

**Scenario:** User completes quiz (100 base XP), has consistency bonus (1.5x), Week 7 active

```
Base XP: 100
Apply consistency: 100 * 1.5 = 150
Apply Week 7: 150 * 2 = 300

week7_bonus tracked: 100 (base XP)
Total XP awarded: 300
```

**User sees:**
- "You earned 100 XP for this quiz"
- "Consistency bonus: +50 XP"
- "Week 7 Quest: Doubled your 100 XP to 200 XP"
- "Total: 300 XP"

**Quest progress:**
- "Double XP earned: 100"
- (Actual total XP from Week 7: 200, but we track base)

---

## Alternative: Option B (Keep Current - SIMPLER)

### Rationale

1. **Simplicity:** Current implementation works
2. **Accuracy:** Tracks actual XP that gets doubled
3. **No Breaking Changes:** Already implemented

### Clarification Needed

Just update documentation to clarify:
- "week7_bonus" = XP value that gets doubled (after other bonuses)
- Not the base activity XP
- Not the total bonus XP received

### Documentation Update

```python
# Apply Week 7 double XP if quest is active
week7_bonus = 0
week7_quest_updates = {}
if stats.week7_quest.active and xp_awarded > 0:
    # week7_bonus = XP value that gets doubled (includes consistency bonus)
    # This is the XP amount BEFORE doubling, not the base activity XP
    week7_bonus = xp_awarded
    xp_awarded = xp_awarded * 2
```

---

## Decision Matrix

| Criteria | Option A (Base XP) | Option B (Current) | Option C (Actual Bonus) |
|----------|-------------------|-------------------|------------------------|
| User Clarity | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| Implementation | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| Accuracy | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Consistency | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ |
| No Breaking Changes | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ |

---

## Recommendation

### For Production: Option B (Keep Current)

**Reasons:**
1. Already implemented and working
2. No breaking changes needed
3. Simpler to maintain
4. Just needs documentation clarification

**Action Items:**
- [ ] Add clear documentation to code
- [ ] Update API documentation
- [ ] Clarify in user-facing messages

### For Future: Consider Option A

**If refactoring:**
- Provides better user experience
- Clearer tracking
- More intuitive

---

## Implementation Decision

**DECISION:** Keep Option B (Current Implementation)

**Justification:**
- Works correctly as-is
- No bugs or issues
- Just needs documentation
- Avoid unnecessary refactoring before merge

**Documentation Updates:**
```python
# week7_bonus represents the XP value that gets doubled
# This includes any bonuses applied before Week 7 (e.g., consistency bonus)
# Example: 100 base XP + 50 consistency = 150, then doubled to 300
# week7_bonus = 150 (the value that was doubled)
```

---

**Status:** RESOLVED - Keep current implementation with documentation updates  
**Last Updated:** 2026-01-08

