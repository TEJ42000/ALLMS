# Phase 3: Streak System Implementation

**Parent Issue:** #121  
**Issue:** #124  
**Timeline:** Week 5  
**Priority:** HIGH  
**Dependencies:** Phase 1 (#122), Phase 2 (#123)

## Overview

This document details the implementation of the "Counselor's Creed" Streak System with 4:00 AM reset, streak freezes, and weekly consistency bonus.

---

## Features Implemented

### 1. ✅ 4:00 AM Reset Logic

**Implementation:**
- Streak day starts at 4:00 AM and ends at 3:59:59 AM the next day
- Activities before 4:00 AM count toward the previous day's streak
- Timezone-aware calculations using UTC
- Handles daylight saving time changes

**Code Location:** `app/services/gamification_service.py`

```python
def _get_streak_day(self, dt: datetime) -> datetime:
    """Get the streak day for a given datetime.
    
    A streak day starts at 4:00 AM and ends at 3:59:59 AM the next day.
    """
    # If before 4 AM, it's still the previous day's streak
    if dt.hour < STREAK_RESET_HOUR:
        streak_date = (dt - timedelta(days=1)).date()
    else:
        streak_date = dt.date()
    
    return datetime.combine(streak_date, datetime.min.time()).replace(tzinfo=timezone.utc)
```

---

### 2. ✅ Streak Freeze Mechanism

**Features:**
- Earn 1 freeze every 500 XP
- Auto-applies when user misses exactly 1 day
- Maintains streak without incrementing
- Tracks freeze usage history

**Freeze Logic:**
```python
# Award freeze every 500 XP
freezes_to_add = (new_total_xp // 500) - (old_total_xp // 500)

# Auto-apply freeze on missed day
if days_diff == 2 and stats.streak.freezes_available > 0:
    # Use freeze to maintain streak
    return True, stats.streak.current_count, True
```

---

### 3. ✅ Weekly Consistency Bonus

**Categories Tracked:**
- Flashcards
- Quiz
- Evaluation
- Guide

**Bonus Activation:**
- Complete at least one activity in all 4 categories within a week
- Awards XP multiplier for the following week
- Resets every Monday at 4:00 AM

**Data Structure:**
```python
weekly_consistency: {
    "flashcards": False,
    "quiz": False,
    "evaluation": False,
    "guide": False
}
```

---

### 4. ✅ Daily Maintenance Job

**Purpose:**
- Check all users for missed streak days
- Auto-apply freezes where applicable
- Reset broken streaks
- Send at-risk notifications

**Implementation:**
- Cloud Scheduler job runs at 4:00 AM UTC daily
- Processes users in batches of 100
- Handles failures gracefully with retry logic
- Logs all streak changes

**Code Location:** `app/services/streak_maintenance.py`

---

### 5. ✅ Streak Notifications

**Notification Types:**

1. **Milestone Reached** (7, 14, 30, 60, 100 days)
   - Celebration message
   - Confetti animation
   - Sound effect

2. **Streak At Risk** (no activity today)
   - Warning notification
   - Sent at 8:00 PM local time
   - Shows hours remaining

3. **Streak Broken**
   - Informative message
   - Encouragement to start new streak
   - Shows previous streak length

4. **Freeze Applied**
   - Notification that freeze saved streak
   - Shows remaining freezes
   - Encouragement message

**Code Location:** `app/services/notification_service.py`

---

### 6. ✅ Frontend UI Updates

**Streak Stat Card:**
- Current streak count with fire emoji 🔥
- Freeze count with snowflake emoji ❄️
- Longest streak record
- Progress to next milestone

**Calendar Visualization:**
- 30-day calendar view
- Green squares for activity days
- Blue squares for freeze days
- Gray squares for missed days
- Hover tooltips with details

**Weekly Consistency Tracker:**
- 4 category checkboxes
- Visual progress indicator
- Bonus activation status
- Animated check marks

**Code Location:** `app/static/js/streak-tracker.js`

---

## API Endpoints

### GET /api/gamification/streak/calendar
Get calendar data for streak visualization.

**Response:**
```json
{
  "days": [
    {
      "date": "2026-01-01",
      "has_activity": true,
      "freeze_used": false,
      "activity_count": 5
    }
  ],
  "current_streak": 14,
  "longest_streak": 21
}
```

### GET /api/gamification/streak/consistency
Get weekly consistency status.

**Response:**
```json
{
  "week_start": "2026-01-06",
  "week_end": "2026-01-12",
  "categories": {
    "flashcards": true,
    "quiz": true,
    "evaluation": false,
    "guide": true
  },
  "bonus_active": false,
  "progress": 75
}
```

### POST /api/gamification/streak/freeze/use
Manually use a streak freeze (optional feature).

**Request:**
```json
{
  "date": "2026-01-07"
}
```

---

## Database Schema

### user_stats/{user_id}

**Streak Fields:**
```javascript
{
  "streak": {
    "current_count": 14,
    "longest_streak": 21,
    "last_activity_date": Timestamp,
    "last_activity_day": "2026-01-08",  // For 4AM reset
    "freezes_available": 2,
    "next_reset": Timestamp,
    "weekly_consistency": {
      "flashcards": true,
      "quiz": true,
      "evaluation": false,
      "guide": true
    },
    "week_start": "2026-01-06",  // Monday of current week
    "bonus_active": false,
    "bonus_multiplier": 1.0
  }
}
```

### streak_history/{user_id}/events/{event_id}

**Streak Event Log:**
```javascript
{
  "event_id": "uuid",
  "user_id": "user_iap_id",
  "timestamp": Timestamp,
  "event_type": "milestone | at_risk | broken | freeze_used",
  "streak_count": 14,
  "freeze_used": false,
  "details": {
    "milestone": 14,
    "freezes_remaining": 2
  }
}
```

---

## Testing

### Unit Tests

**Streak Logic:**
- ✅ 4:00 AM reset calculation
- ✅ Streak maintenance (same day, consecutive, missed)
- ✅ Freeze application
- ✅ Timezone edge cases
- ✅ Daylight saving time transitions

**Weekly Consistency:**
- ✅ Category tracking
- ✅ Bonus activation
- ✅ Week reset logic
- ✅ Multiplier calculation

### Integration Tests

**Activity Flow:**
- ✅ Activity → Streak update
- ✅ Activity → Consistency tracking
- ✅ Freeze earning (500 XP)
- ✅ Freeze usage

**Maintenance Job:**
- ✅ Daily streak check
- ✅ Batch processing
- ✅ Notification sending
- ✅ Error handling

### E2E Tests

**User Scenarios:**
- ✅ Maintain streak across multiple days
- ✅ Break streak and verify reset
- ✅ Earn and use freeze
- ✅ Complete weekly consistency
- ✅ Receive milestone notification

---

## Performance Considerations

### Daily Maintenance Job

**Optimization:**
- Process users in batches of 100
- Use Firestore batch writes
- Parallel processing where possible
- Exponential backoff on failures

**Monitoring:**
- Track job execution time
- Monitor failure rate
- Alert on prolonged failures
- Log all streak changes

### Calendar Queries

**Optimization:**
- Cache calendar data for 1 hour
- Limit to 30 days of history
- Use composite indexes
- Paginate if needed

---

## Security & Privacy

**Data Protection:**
- Streak data is user-specific
- No public leaderboards (optional feature)
- Users can view their own streak history
- Admins cannot modify user streaks directly

**Audit Trail:**
- All streak changes logged
- Freeze usage tracked
- Maintenance job actions recorded
- Notification delivery logged

---

## Future Enhancements

- [ ] Streak recovery suggestions
- [ ] Streak sharing (social features)
- [ ] Custom streak goals
- [ ] Streak challenges
- [ ] Team streaks
- [ ] Streak analytics dashboard

---

## Related Documentation

- `docs/GAMIFICATION_UI_POLISH.md` - UI/UX features
- `app/services/gamification_service.py` - Core service
- `app/models/gamification_models.py` - Data models
- `app/routes/gamification.py` - API endpoints

---

**Implementation Status:** ✅ COMPLETE  
**Ready for:** Phase 4 (Badge System)

