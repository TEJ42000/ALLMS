# Phase 4.1: Implement Remaining Badges

**Epic:** Badge System Enhancement  
**Priority:** MEDIUM  
**Estimated Effort:** 2-3 weeks  
**Dependencies:** Phase 4 Badge System (PR #154)

---

## Overview

Implement the 12 remaining inactive badges that require additional tracking features. These badges are currently marked as `active=False` and hidden from users.

---

## Inactive Badges (12 total)

### Consistency Badges (4 badges)

These badges require **weekly bonus tracking** to be implemented.

#### 1. Consistent Learner
- **Badge ID:** `consistent_learner`
- **Description:** Earn weekly bonuses for 4 consecutive weeks
- **Category:** consistency
- **Rarity:** uncommon
- **Points:** 50
- **Criteria:** `{"consecutive_weeks_bonus": 4}`
- **Required Feature:** Weekly bonus tracking system

#### 2. Dedication
- **Badge ID:** `dedication`
- **Description:** Earn weekly bonuses for 8 consecutive weeks
- **Category:** consistency
- **Rarity:** rare
- **Points:** 100
- **Criteria:** `{"consecutive_weeks_bonus": 8}`
- **Required Feature:** Weekly bonus tracking system

#### 3. Commitment
- **Badge ID:** `commitment`
- **Description:** Earn weekly bonuses for 12 consecutive weeks
- **Category:** consistency
- **Rarity:** epic
- **Points:** 200
- **Criteria:** `{"consecutive_weeks_bonus": 12}`
- **Required Feature:** Weekly bonus tracking system

#### 4. Unstoppable
- **Badge ID:** `unstoppable`
- **Description:** Earn weekly bonuses for 26 consecutive weeks (half a year!)
- **Category:** consistency
- **Rarity:** legendary
- **Points:** 500
- **Criteria:** `{"consecutive_weeks_bonus": 26}`
- **Required Feature:** Weekly bonus tracking system

---

### Special Badges (8 badges)

These badges require various advanced tracking features.

#### 5. Perfect Week
- **Badge ID:** `perfect_week`
- **Description:** Complete all daily activities for a full week
- **Category:** special
- **Rarity:** epic
- **Points:** 200
- **Criteria:** `{"perfect_week": true}`
- **Required Feature:** Daily activity completion tracking

#### 6. Night Owl
- **Badge ID:** `night_owl`
- **Description:** Complete 10 activities between 10 PM and 2 AM
- **Category:** special
- **Rarity:** uncommon
- **Points:** 50
- **Criteria:** `{"night_activities": 10}`
- **Required Feature:** Activity timestamp tracking (hour of day)

#### 7. Early Bird
- **Badge ID:** `early_bird`
- **Description:** Complete 10 activities between 5 AM and 9 AM
- **Category:** special
- **Rarity:** uncommon
- **Points:** 50
- **Criteria:** `{"early_activities": 10}`
- **Required Feature:** Activity timestamp tracking (hour of day)

#### 8. Weekend Warrior
- **Badge ID:** `weekend_warrior`
- **Description:** Complete 10 activities on weekends
- **Category:** special
- **Rarity:** uncommon
- **Points:** 50
- **Criteria:** `{"weekend_activities": 10}`
- **Required Feature:** Activity timestamp tracking (day of week)

#### 9. Combo King
- **Badge ID:** `combo_king`
- **Description:** Achieve a 10-card combo in flashcards
- **Category:** special
- **Rarity:** rare
- **Points:** 100
- **Criteria:** `{"flashcard_combo": 10}`
- **Required Feature:** Flashcard combo tracking

#### 10. Deep Diver
- **Badge ID:** `deep_diver`
- **Description:** Study for 1 hour in a single session
- **Category:** special
- **Rarity:** rare
- **Points:** 100
- **Criteria:** `{"session_duration": 3600}`
- **Required Feature:** Session duration tracking

#### 11. Hat Trick
- **Badge ID:** `hat_trick`
- **Description:** Complete 3 different activity types in one day
- **Category:** special
- **Rarity:** uncommon
- **Points:** 75
- **Criteria:** `{"same_day_activities": 3}`
- **Required Feature:** Same-day activity type tracking

#### 12. Legal Scholar
- **Badge ID:** `legal_scholar`
- **Description:** Complete all materials in the ECHR course
- **Category:** special
- **Rarity:** epic
- **Points:** 300
- **Criteria:** `{"course_specific": "echr"}`
- **Required Feature:** Course-specific completion tracking

---

## Implementation Requirements

### 1. Weekly Bonus Tracking System

**Required for:** Consistency badges (4 badges)

**Implementation:**

**Data Model:**
```python
class WeeklyBonusTracking(BaseModel):
    user_id: str
    week_start_date: date
    week_end_date: date
    bonus_earned: bool
    consecutive_weeks: int
    last_bonus_date: Optional[date]
```

**Logic:**
- Track when user earns weekly bonus
- Increment consecutive_weeks counter
- Reset counter if week missed
- Check badge criteria after each bonus

**Estimated Effort:** 3-4 days

---

### 2. Activity Timestamp Tracking

**Required for:** Night Owl, Early Bird, Weekend Warrior (3 badges)

**Implementation:**

**Data Model Enhancement:**
```python
class ActivityLog(BaseModel):
    # ... existing fields ...
    hour_of_day: int  # 0-23
    day_of_week: int  # 0-6 (Monday=0)
```

**Logic:**
- Extract hour and day from timestamp
- Track counts by time period
- Check badge criteria after each activity

**Estimated Effort:** 2-3 days

---

### 3. Daily Activity Completion Tracking

**Required for:** Perfect Week (1 badge)

**Implementation:**

**Data Model:**
```python
class DailyActivityTracking(BaseModel):
    user_id: str
    date: date
    activities_completed: List[str]  # Types of activities
    all_types_completed: bool
```

**Logic:**
- Track which activity types completed each day
- Check if all types completed for 7 consecutive days
- Award badge when criteria met

**Estimated Effort:** 2-3 days

---

### 4. Flashcard Combo Tracking

**Required for:** Combo King (1 badge)

**Implementation:**

**Data Model Enhancement:**
```python
class FlashcardSession(BaseModel):
    # ... existing fields ...
    current_combo: int
    max_combo: int
```

**Logic:**
- Increment combo on correct answer
- Reset combo on incorrect answer
- Track max combo achieved
- Check badge criteria after each session

**Estimated Effort:** 2 days

---

### 5. Session Duration Tracking

**Required for:** Deep Diver (1 badge)

**Implementation:**

**Data Model:**
```python
class StudySession(BaseModel):
    user_id: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_seconds: int
    activity_type: str
```

**Logic:**
- Track session start/end times
- Calculate duration
- Check badge criteria after session ends

**Estimated Effort:** 2 days

---

### 6. Same-Day Activity Type Tracking

**Required for:** Hat Trick (1 badge)

**Implementation:**

**Logic:**
- Track unique activity types per day
- Check if 3+ types completed in same day
- Award badge when criteria met

**Estimated Effort:** 1-2 days

---

### 7. Course-Specific Completion Tracking

**Required for:** Legal Scholar (1 badge)

**Implementation:**

**Data Model:**
```python
class CourseProgress(BaseModel):
    user_id: str
    course_id: str
    total_materials: int
    completed_materials: int
    completion_percentage: float
```

**Logic:**
- Track course completion percentage
- Check if 100% complete
- Award badge when criteria met

**Estimated Effort:** 2-3 days

---

## Implementation Plan

### Phase 4.1.1: Consistency Badges (Week 1)
- [ ] Implement weekly bonus tracking system
- [ ] Add database models
- [ ] Implement badge checking logic
- [ ] Add unit tests
- [ ] Activate 4 consistency badges

### Phase 4.1.2: Time-Based Badges (Week 2)
- [ ] Implement activity timestamp tracking
- [ ] Add hour/day extraction logic
- [ ] Implement badge checking logic
- [ ] Add unit tests
- [ ] Activate 3 time-based badges (Night Owl, Early Bird, Weekend Warrior)

### Phase 4.1.3: Advanced Tracking Badges (Week 3)
- [ ] Implement daily activity completion tracking (Perfect Week)
- [ ] Implement flashcard combo tracking (Combo King)
- [ ] Implement session duration tracking (Deep Diver)
- [ ] Implement same-day activity tracking (Hat Trick)
- [ ] Implement course completion tracking (Legal Scholar)
- [ ] Add unit tests for all
- [ ] Activate remaining 5 badges

---

## Testing Requirements

**Unit Tests:**
- Test each tracking system independently
- Test badge criteria checking
- Test edge cases (midnight, week boundaries, etc.)

**Integration Tests:**
- Test complete flow from activity to badge unlock
- Test multiple badges unlocking simultaneously
- Test data persistence

**E2E Tests:**
- Test user completing activities and earning badges
- Test badge progress display
- Test badge notifications

---

## Acceptance Criteria

- [ ] All 12 badges implemented and active
- [ ] All tracking systems working correctly
- [ ] All tests passing (unit, integration, E2E)
- [ ] Documentation updated
- [ ] User can earn all badges
- [ ] Badge progress displays correctly
- [ ] No performance degradation

---

## Risks and Mitigation

**Risk:** Performance impact from additional tracking  
**Mitigation:** Use efficient queries, add Firestore indexes

**Risk:** Complexity of time-based tracking  
**Mitigation:** Use timezone-aware timestamps, test thoroughly

**Risk:** Data migration for existing users  
**Mitigation:** Initialize tracking data for existing users

---

## Success Metrics

- All 12 badges active and earnable
- Users earning new badges within first week
- No increase in API response times
- No errors in production logs
- Positive user feedback

---

**Created:** 2026-01-08  
**Target Completion:** Q1 2026

