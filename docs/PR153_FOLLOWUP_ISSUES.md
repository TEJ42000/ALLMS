# PR #153 Follow-up Issues

**Date:** 2026-01-08  
**PR:** #153 - Phase 3: Streak System  
**Status:** Critical and High priority issues resolved

---

## Overview

This document tracks MEDIUM and LOW priority improvements that should be addressed in future iterations after PR #153 is merged.

---

## MEDIUM Priority Issues

### Issue: Optimize Batch Processing Performance

**Priority:** MEDIUM  
**Effort:** 2-3 days  
**Impact:** Performance improvement for large user bases

**Description:**
Current batch processing uses a fixed batch size of 100 users. For production scale (10,000+ users), this could be optimized.

**Proposed Solution:**
- Implement dynamic batch sizing based on memory usage
- Add parallel processing for independent batches
- Use Firestore batch writes for better throughput
- Implement cursor-based pagination for better performance

**Acceptance Criteria:**
- [ ] Process 10,000 users in under 2 minutes
- [ ] Memory usage stays under 256 MB
- [ ] No transaction conflicts
- [ ] Comprehensive load tests pass

**Related Files:**
- `app/services/streak_maintenance.py`

---

### Issue: Add Retry Logic for Transient Failures

**Priority:** MEDIUM  
**Effort:** 1-2 days  
**Impact:** Improved reliability

**Description:**
Currently, if a Firestore transaction fails due to transient issues (network, timeout), the operation fails without retry.

**Proposed Solution:**
- Add exponential backoff retry logic
- Implement circuit breaker pattern
- Add dead letter queue for failed operations
- Log retry attempts for monitoring

**Acceptance Criteria:**
- [ ] Automatic retry up to 3 times with exponential backoff
- [ ] Circuit breaker opens after 5 consecutive failures
- [ ] Failed operations logged to dead letter queue
- [ ] Metrics tracked for retry success rate

**Related Files:**
- `app/services/streak_maintenance.py`
- `app/services/gamification_service.py`

---

### Issue: Implement Notification Service Integration

**Priority:** MEDIUM  
**Effort:** 3-4 days  
**Impact:** User engagement

**Description:**
Notification placeholders exist but are not implemented. Users should receive notifications for:
- Streak freeze applied
- Streak broken
- Weekly consistency bonus earned
- Streak milestones (7, 30, 100 days)

**Proposed Solution:**
- Integrate with Firebase Cloud Messaging (FCM)
- Add email notification support
- Implement notification preferences
- Add notification templates

**Acceptance Criteria:**
- [ ] Push notifications sent via FCM
- [ ] Email notifications sent via SendGrid/similar
- [ ] Users can configure notification preferences
- [ ] Notification delivery tracked in analytics

**Related Files:**
- `app/services/streak_maintenance.py` (notification methods)
- New: `app/services/notification_service.py`

---

### Issue: Add Streak Calendar Caching

**Priority:** MEDIUM  
**Effort:** 1 day  
**Impact:** Performance, cost reduction

**Description:**
Streak calendar API queries Firestore for activity history on every request. This could be cached for better performance.

**Proposed Solution:**
- Implement Redis caching for calendar data
- Cache TTL: 1 hour
- Invalidate cache on new activity
- Add cache hit/miss metrics

**Acceptance Criteria:**
- [ ] Calendar data cached in Redis
- [ ] Cache invalidated on activity logging
- [ ] Cache hit rate > 80%
- [ ] Response time < 100ms for cached requests

**Related Files:**
- `app/routes/gamification.py` (calendar endpoint)
- New: `app/services/cache_service.py`

---

### Issue: Improve Error Messages and Logging

**Priority:** MEDIUM  
**Effort:** 1-2 days  
**Impact:** Developer experience, debugging

**Description:**
Current error messages are generic. Improve logging for better debugging and monitoring.

**Proposed Solution:**
- Add structured logging with context
- Include user_id, timestamp, operation in all logs
- Add correlation IDs for request tracing
- Implement log levels properly (DEBUG, INFO, WARNING, ERROR)

**Acceptance Criteria:**
- [ ] All logs include context (user_id, operation, timestamp)
- [ ] Correlation IDs tracked across services
- [ ] Log levels used appropriately
- [ ] Logs queryable in Cloud Logging

**Related Files:**
- All service files

---

## LOW Priority Issues

### Issue: Add Streak Leaderboard

**Priority:** LOW  
**Effort:** 3-5 days  
**Impact:** User engagement (optional feature)

**Description:**
Add a leaderboard showing users with longest streaks for competitive motivation.

**Proposed Solution:**
- Create leaderboard API endpoint
- Cache leaderboard data (updated daily)
- Add privacy controls (opt-in)
- Implement weekly/monthly/all-time views

**Acceptance Criteria:**
- [ ] Leaderboard API endpoint created
- [ ] Data updated daily via cron job
- [ ] Users can opt-in/opt-out
- [ ] Frontend component displays leaderboard

**Related Files:**
- New: `app/routes/leaderboard.py`
- New: `app/services/leaderboard_service.py`

---

### Issue: Add Streak Recovery Feature

**Priority:** LOW  
**Effort:** 2-3 days  
**Impact:** User retention (optional feature)

**Description:**
Allow users to "recover" a broken streak within 24 hours by completing extra activities.

**Proposed Solution:**
- Add recovery window (24 hours after break)
- Require 2x normal activity to recover
- Limit to once per month
- Track recovery usage

**Acceptance Criteria:**
- [ ] Recovery available for 24 hours after break
- [ ] Requires 2x normal activity
- [ ] Limited to once per 30 days
- [ ] Recovery tracked in user stats

**Related Files:**
- `app/services/gamification_service.py`
- `app/models/gamification_models.py`

---

### Issue: Add Streak Insights and Analytics

**Priority:** LOW  
**Effort:** 3-4 days  
**Impact:** User engagement

**Description:**
Provide users with insights about their streak patterns and activity trends.

**Proposed Solution:**
- Best streak day of week
- Average activities per day
- Streak prediction (likelihood of maintaining)
- Activity heatmap

**Acceptance Criteria:**
- [ ] Insights calculated from activity history
- [ ] Displayed in user dashboard
- [ ] Updated weekly
- [ ] Includes visualizations

**Related Files:**
- New: `app/services/analytics_service.py`
- Frontend: streak insights component

---

### Issue: Implement Streak Sharing

**Priority:** LOW  
**Effort:** 2 days  
**Impact:** Social engagement

**Description:**
Allow users to share their streak achievements on social media.

**Proposed Solution:**
- Generate shareable graphics
- Include streak count, badges, level
- Support Twitter, LinkedIn, Facebook
- Track share metrics

**Acceptance Criteria:**
- [ ] Shareable graphics generated
- [ ] Social media integration working
- [ ] Share tracking in analytics
- [ ] Privacy controls implemented

**Related Files:**
- `app/static/js/shareable-graphics.js` (already exists)
- Extend for streak sharing

---

### Issue: Add Streak Challenges

**Priority:** LOW  
**Effort:** 5-7 days  
**Impact:** User engagement (optional feature)

**Description:**
Create time-limited challenges for users to complete (e.g., "7-day study sprint").

**Proposed Solution:**
- Define challenge types and rewards
- Track challenge participation
- Award bonus XP for completion
- Display active challenges in UI

**Acceptance Criteria:**
- [ ] Challenge system implemented
- [ ] Users can join/leave challenges
- [ ] Progress tracked in real-time
- [ ] Rewards distributed on completion

**Related Files:**
- New: `app/models/challenge_models.py`
- New: `app/services/challenge_service.py`

---

### Issue: Optimize Firestore Indexes

**Priority:** LOW  
**Effort:** 1 day  
**Impact:** Query performance

**Description:**
Review and optimize Firestore indexes for streak queries.

**Proposed Solution:**
- Analyze query patterns
- Create composite indexes where needed
- Remove unused indexes
- Document index strategy

**Acceptance Criteria:**
- [ ] All queries use optimal indexes
- [ ] Query performance < 100ms
- [ ] Index usage documented
- [ ] Monitoring alerts for slow queries

**Related Files:**
- `firestore.indexes.json`

---

## Implementation Priority

### Immediate (After PR #153 Merge)
1. ✅ Fix CRITICAL issues (race conditions, memory leaks) - DONE
2. ✅ Fix HIGH issues (test assertions, validation) - DONE
3. ✅ Add integration tests - DONE
4. ✅ Set up monitoring - DONE

### Next Sprint (Week 1-2)
1. Optimize batch processing performance (MEDIUM)
2. Add retry logic for transient failures (MEDIUM)
3. Implement notification service integration (MEDIUM)

### Future Sprints (Week 3+)
1. Add streak calendar caching (MEDIUM)
2. Improve error messages and logging (MEDIUM)
3. Add streak leaderboard (LOW)
4. Add streak recovery feature (LOW)
5. Add streak insights and analytics (LOW)
6. Implement streak sharing (LOW)
7. Add streak challenges (LOW)
8. Optimize Firestore indexes (LOW)

---

## Issue Creation Checklist

When creating GitHub issues for these items:

- [ ] Use appropriate labels (enhancement, performance, feature)
- [ ] Set priority label (medium, low)
- [ ] Estimate effort (story points or days)
- [ ] Link to PR #153
- [ ] Reference this document
- [ ] Assign to appropriate milestone
- [ ] Add acceptance criteria
- [ ] Include technical details

---

## Tracking

**Total Issues:** 13  
**MEDIUM Priority:** 5  
**LOW Priority:** 8  

**Estimated Total Effort:** 30-45 days  
**Recommended Team Size:** 2-3 developers  
**Timeline:** 2-3 months for all items

---

**Last Updated:** 2026-01-08  
**Status:** Ready for issue creation after PR #153 merge

