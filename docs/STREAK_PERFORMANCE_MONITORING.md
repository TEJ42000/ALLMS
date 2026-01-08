# Streak System Performance Monitoring Guide

**Component:** Phase 3 Streak System  
**Related:** PR #153  
**Purpose:** Monitor and optimize streak system performance

---

## Overview

This guide provides comprehensive monitoring strategies for the streak system to ensure optimal performance, reliability, and user experience.

---

## Key Performance Indicators (KPIs)

### System Performance

| Metric | Target | Warning | Critical |
|--------|--------|---------|----------|
| Calendar API Response Time | < 200ms | > 500ms | > 1000ms |
| Consistency API Response Time | < 150ms | > 400ms | > 800ms |
| Activity Logging Latency | < 100ms | > 300ms | > 600ms |
| Maintenance Job Duration | < 5 min | > 8 min | > 10 min |
| Database Query Time | < 50ms | > 150ms | > 300ms |

### User Engagement

| Metric | Target | Notes |
|--------|--------|-------|
| Active Streaks | > 60% of users | Percentage with streak > 0 |
| Weekly Bonus Activation | > 30% of users | Complete all 4 categories |
| Freeze Usage Rate | 40-60% | Freezes used / freezes earned |
| Streak Retention (7-day) | > 70% | Users maintaining 7+ day streak |
| Average Streak Length | > 14 days | Across all active users |

### System Health

| Metric | Target | Notes |
|--------|--------|-------|
| API Error Rate | < 0.1% | 4xx and 5xx errors |
| Maintenance Job Success Rate | > 99% | Daily job completion |
| Database Write Success | > 99.9% | Firestore write operations |
| Memory Usage | < 80% | Cloud Run container memory |
| CPU Usage | < 70% | Cloud Run container CPU |

---

## Monitoring Tools

### 1. Google Cloud Monitoring

**Dashboard:** `monitoring/streak_maintenance_dashboard.json`

**Key Metrics:**
- Request count and latency
- Error rates
- Memory and CPU usage
- Database operations

**Setup:**
```bash
# Import dashboard
gcloud monitoring dashboards create \
    --config-from-file=monitoring/streak_maintenance_dashboard.json
```

### 2. Cloud Logging

**Log Queries:**

**Maintenance Job Execution:**
```
resource.type="cloud_run_revision"
resource.labels.service_name="allms-backend"
textPayload=~"Daily streak maintenance completed"
```

**API Errors:**
```
resource.type="cloud_run_revision"
resource.labels.service_name="allms-backend"
severity>=ERROR
jsonPayload.endpoint=~"/api/gamification/streak/"
```

**Slow Queries:**
```
resource.type="cloud_run_revision"
resource.labels.service_name="allms-backend"
jsonPayload.duration>500
jsonPayload.endpoint=~"/api/gamification/streak/"
```

### 3. Application Performance Monitoring (APM)

**Recommended Tools:**
- Google Cloud Trace
- Google Cloud Profiler
- Custom metrics via OpenTelemetry

**Key Traces:**
- `log_activity` - Activity logging flow
- `get_user_activities` - Activity retrieval
- `run_daily_maintenance` - Maintenance job
- `update_weekly_consistency` - Consistency tracking

---

## Daily Monitoring Checklist

### Morning Review (After 4:00 AM UTC)

1. **Check Maintenance Job Status**
   ```bash
   gcloud scheduler jobs describe streak-maintenance-daily \
       --location=us-central1 \
       | grep -A 5 "lastAttemptTime"
   ```

2. **Review Execution Logs**
   ```bash
   gcloud run services logs read allms-backend \
       --region=us-central1 \
       --limit=50 \
       | grep "streak maintenance"
   ```

3. **Verify Metrics**
   - Users processed
   - Freezes applied
   - Streaks broken
   - Execution time
   - Error count

4. **Check for Anomalies**
   - Unusual spike in streak breaks
   - High error rate
   - Long execution time
   - Memory/CPU spikes

### Throughout the Day

1. **Monitor API Performance**
   - Check response times
   - Review error rates
   - Verify successful requests

2. **Watch for Alerts**
   - Email/SMS notifications
   - Cloud Monitoring alerts
   - Error tracking systems

3. **User Feedback**
   - Support tickets
   - Bug reports
   - Feature requests

---

## Weekly Performance Review

### Metrics Analysis

1. **Trend Analysis**
   - Compare week-over-week metrics
   - Identify patterns and anomalies
   - Track improvement/degradation

2. **User Engagement**
   - Active streak count
   - Bonus activation rate
   - Freeze usage patterns
   - Streak break reasons

3. **System Performance**
   - Average response times
   - Error rate trends
   - Resource utilization
   - Database performance

### Action Items

1. **Optimize Slow Queries**
   - Identify queries > 200ms
   - Add indexes if needed
   - Optimize query structure

2. **Address Errors**
   - Review error logs
   - Fix recurring issues
   - Update error handling

3. **Capacity Planning**
   - Project user growth
   - Plan resource scaling
   - Optimize batch sizes

---

## Performance Optimization Strategies

### 1. Database Optimization

**Indexes:**
```javascript
// Ensure these indexes exist in Firestore
user_stats: {
  indexes: [
    { fields: ["user_id"], order: "ASCENDING" },
    { fields: ["streak.last_activity_date"], order: "DESCENDING" },
    { fields: ["updated_at"], order: "DESCENDING" }
  ]
}

user_activities: {
  indexes: [
    { fields: ["user_id", "timestamp"], order: "DESCENDING" },
    { fields: ["user_id", "activity_type", "timestamp"], order: "DESCENDING" }
  ]
}
```

**Query Optimization:**
- Use pagination for large result sets
- Limit query results to necessary fields
- Cache frequently accessed data
- Use batch operations where possible

### 2. API Optimization

**Caching Strategy:**
```python
# Cache calendar data for 5 minutes
@cache(ttl=300)
def get_streak_calendar(user_id: str, days: int):
    # Implementation
    pass

# Cache consistency data for 1 minute
@cache(ttl=60)
def get_weekly_consistency(user_id: str):
    # Implementation
    pass
```

**Response Compression:**
```python
# Enable gzip compression
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

### 3. Batch Processing Optimization

**Current Settings:**
```python
BATCH_SIZE = 100  # Users per batch
MAX_CONCURRENT_BATCHES = 5  # Parallel processing
```

**Tuning Guidelines:**
- Increase batch size if execution time < 3 minutes
- Decrease batch size if memory usage > 80%
- Adjust based on user count and growth

### 4. Frontend Optimization

**Lazy Loading:**
```javascript
// Load calendar data only when visible
const observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting) {
        loadStreakCalendar();
    }
});
```

**Debouncing:**
```javascript
// Debounce refresh calls
const debouncedRefresh = debounce(() => {
    loadStreakData();
}, 1000);
```

---

## Alert Configuration

### Critical Alerts (Immediate Action)

1. **Maintenance Job Failure**
   - Condition: Job fails 2+ times in 1 hour
   - Action: Investigate logs, manual trigger if needed
   - Notification: Email + SMS

2. **High Error Rate**
   - Condition: Error rate > 5% for 5 minutes
   - Action: Check logs, rollback if needed
   - Notification: Email + SMS

3. **Database Connection Failure**
   - Condition: Firestore connection errors
   - Action: Check service status, verify credentials
   - Notification: Email + SMS

### Warning Alerts (Monitor Closely)

1. **Slow Response Time**
   - Condition: P95 latency > 1 second for 10 minutes
   - Action: Review slow queries, optimize if needed
   - Notification: Email

2. **High Memory Usage**
   - Condition: Memory > 80% for 15 minutes
   - Action: Check for memory leaks, increase limits
   - Notification: Email

3. **Unusual Streak Break Rate**
   - Condition: Streak breaks > 2x normal for 1 day
   - Action: Investigate cause, check for bugs
   - Notification: Email

---

## Troubleshooting Guide

### High Response Times

**Symptoms:**
- API responses > 1 second
- User complaints about slow loading

**Diagnosis:**
```bash
# Check slow queries
gcloud logging read \
    'jsonPayload.duration>1000
     AND jsonPayload.endpoint=~"/api/gamification/streak/"' \
    --limit=20
```

**Solutions:**
1. Add database indexes
2. Implement caching
3. Optimize query structure
4. Increase Cloud Run instances

### Memory Leaks

**Symptoms:**
- Gradual memory increase
- Container restarts
- Out of memory errors

**Diagnosis:**
```bash
# Check memory usage trends
gcloud monitoring time-series list \
    --filter='metric.type="run.googleapis.com/container/memory/utilizations"'
```

**Solutions:**
1. Review batch processing (ensure `del docs`)
2. Check for circular references
3. Implement proper cleanup
4. Increase memory limits

### Database Performance Issues

**Symptoms:**
- Slow queries
- Timeout errors
- High read/write costs

**Diagnosis:**
```bash
# Check Firestore metrics
gcloud monitoring time-series list \
    --filter='metric.type="firestore.googleapis.com/document/read_count"'
```

**Solutions:**
1. Add composite indexes
2. Optimize query filters
3. Implement caching
4. Use batch operations

---

## Performance Testing

### Load Testing

**Tool:** Apache JMeter or Locust

**Test Scenarios:**
1. **Concurrent Users**
   - 100 users accessing calendar simultaneously
   - Target: < 500ms response time

2. **Activity Logging**
   - 1000 activities logged per minute
   - Target: < 200ms per activity

3. **Maintenance Job**
   - Process 10,000 users
   - Target: < 10 minutes total

**Example Locust Test:**
```python
from locust import HttpUser, task, between

class StreakUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def get_calendar(self):
        self.client.get("/api/gamification/streak/calendar?days=30")
    
    @task
    def get_consistency(self):
        self.client.get("/api/gamification/streak/consistency")
```

---

## Best Practices

1. **Monitor Proactively** - Don't wait for user complaints
2. **Set Realistic Targets** - Based on actual usage patterns
3. **Review Regularly** - Weekly performance reviews
4. **Optimize Continuously** - Incremental improvements
5. **Document Changes** - Track optimization efforts
6. **Test Before Deploy** - Load test new features
7. **Plan for Scale** - Design for 10x growth

---

## Related Documentation

- [Cloud Scheduler Deployment](CLOUD_SCHEDULER_DEPLOYMENT.md)
- [Monitoring Deployment Guide](MONITORING_DEPLOYMENT_GUIDE.md)
- [Phase 3 Streak System](PHASE3_STREAK_SYSTEM.md)

---

**Last Updated:** 2026-01-08  
**Maintained By:** DevOps Team

