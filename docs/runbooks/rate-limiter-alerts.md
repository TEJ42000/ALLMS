# Rate Limiter Alerts Runbook

**Last Updated:** 2026-01-09  
**Owner:** Platform Team  
**Severity Levels:** CRITICAL, HIGH, MEDIUM

---

## Overview

This runbook covers incident response for rate limiter alerts in the ALLMS upload system. The rate limiter uses Redis for distributed rate limiting in production, with an in-memory fallback for development.

### Alert Types

1. **Redis Connection Failure** (CRITICAL)
2. **Rate Limiter Backend Failure** (HIGH)
3. **High Rate Limit Hits** (MEDIUM)

---

## Alert 1: Redis Connection Failure (CRITICAL)

### Symptoms
- Cannot connect to Redis instance
- Logs show "Failed to connect to Redis" errors
- Application falling back to in-memory rate limiter
- Rate limiting not working across multiple instances

### Impact
- **HIGH:** Rate limiting degraded (not distributed)
- **MEDIUM:** Potential for abuse across instances
- **LOW:** Service still operational (fail-open design)

### Diagnosis

#### Step 1: Check Redis Instance Status
```bash
# Check Redis instance health
gcloud redis instances describe allms-redis \
  --region=europe-west4 \
  --project=vigilant-axis-483119-r8

# Look for:
# - state: READY (should be READY)
# - currentLocationId: (should match expected zone)
# - host: (note the IP address)
```

#### Step 2: Check Recent Logs
```bash
# Check application logs for Redis errors
gcloud logging read \
  'resource.type="cloud_run_revision"
   severity="ERROR"
   jsonPayload.message=~"Redis"' \
  --limit=20 \
  --format=json \
  --project=vigilant-axis-483119-r8

# Check Redis instance logs
gcloud logging read \
  'resource.type="redis_instance"' \
  --limit=50 \
  --format=json \
  --project=vigilant-axis-483119-r8
```

#### Step 3: Test Connectivity
```bash
# From Cloud Shell (same VPC)
gcloud compute ssh test-vm --zone=europe-west4-a -- \
  'redis-cli -h REDIS_IP -a PASSWORD ping'

# Should return: PONG
```

#### Step 4: Check Environment Variables
```bash
# Verify Cloud Run service has correct Redis config
gcloud run services describe allms \
  --region=europe-west4 \
  --format='value(spec.template.spec.containers[0].env)' \
  --project=vigilant-axis-483119-r8

# Look for:
# - REDIS_HOST
# - REDIS_PORT
# - REDIS_PASSWORD (should be set, value hidden)
# - RATE_LIMIT_BACKEND=redis
```

### Resolution

#### Scenario A: Redis Instance Down
```bash
# Restart Redis instance
gcloud redis instances failover allms-redis \
  --region=europe-west4 \
  --project=vigilant-axis-483119-r8

# Monitor recovery
watch -n 5 'gcloud redis instances describe allms-redis \
  --region=europe-west4 --format="value(state)"'
```

#### Scenario B: Network Connectivity Issue
```bash
# Check VPC peering
gcloud compute networks peerings list \
  --network=default \
  --project=vigilant-axis-483119-r8

# Check firewall rules
gcloud compute firewall-rules list \
  --filter="name~redis" \
  --project=vigilant-axis-483119-r8

# If missing, create firewall rule
gcloud compute firewall-rules create allow-redis \
  --network=default \
  --allow=tcp:6379 \
  --source-ranges=CLOUD_RUN_IP_RANGE \
  --project=vigilant-axis-483119-r8
```

#### Scenario C: Authentication Failure
```bash
# Rotate Redis AUTH password
gcloud redis instances update allms-redis \
  --update-auth-string \
  --region=europe-west4 \
  --project=vigilant-axis-483119-r8

# Update Cloud Run environment variable
gcloud run services update allms \
  --update-env-vars REDIS_PASSWORD=NEW_PASSWORD \
  --region=europe-west4 \
  --project=vigilant-axis-483119-r8
```

### Verification
```bash
# Check application logs for successful connection
gcloud logging read \
  'resource.type="cloud_run_revision"
   jsonPayload.message=~"Redis rate limiter connected"' \
  --limit=5 \
  --format=json \
  --project=vigilant-axis-483119-r8

# Test upload with rate limiting
curl -X POST https://allms.mgms.eu/api/upload \
  -H "Authorization: Bearer TOKEN" \
  -F "file=@test.pdf" \
  -F "course_id=test"
```

---

## Alert 2: Rate Limiter Backend Failure (HIGH)

### Symptoms
- Rate limiter backend (Redis) is failing intermittently
- Logs show "Redis rate limit check failed" errors
- Some requests succeed, others fail

### Impact
- **MEDIUM:** Inconsistent rate limiting
- **LOW:** Fail-open design allows requests through

### Diagnosis

#### Check Error Rate
```bash
# Count Redis errors in last hour
gcloud logging read \
  'resource.type="cloud_run_revision"
   severity="ERROR"
   jsonPayload.message=~"Redis rate limit check failed"
   timestamp>="2026-01-09T15:00:00Z"' \
  --format=json \
  --project=vigilant-axis-483119-r8 | jq length
```

#### Check Redis Performance
```bash
# Get Redis metrics
gcloud monitoring time-series list \
  --filter='metric.type="redis.googleapis.com/stats/cpu_utilization"
            resource.labels.instance_id="allms-redis"' \
  --interval-start-time="2026-01-09T15:00:00Z" \
  --project=vigilant-axis-483119-r8
```

### Resolution

#### Scenario A: Redis Overloaded
```bash
# Scale up Redis instance
gcloud redis instances update allms-redis \
  --size=5 \
  --region=europe-west4 \
  --project=vigilant-axis-483119-r8
```

#### Scenario B: Connection Pool Exhausted
```python
# Update rate_limiter.py connection settings
self.client = redis.Redis(
    ...
    max_connections=50,  # Increase from default
    socket_keepalive=True,
    socket_keepalive_options={
        socket.TCP_KEEPIDLE: 60,
        socket.TCP_KEEPINTVL: 10,
        socket.TCP_KEEPCNT: 3
    }
)
```

#### Scenario C: Transient Network Issues
- Monitor for pattern (time of day, specific operations)
- Consider implementing circuit breaker
- Add retry logic (already implemented in Issue #206)

---

## Alert 3: High Rate Limit Hits (MEDIUM)

### Symptoms
- Many users hitting rate limits
- High volume of 429 (Too Many Requests) responses
- Increased "Rate limit exceeded" log entries

### Impact
- **MEDIUM:** Legitimate users may be blocked
- **LOW:** Service protected from abuse

### Diagnosis

#### Identify Top Users
```bash
# Find users hitting rate limits
gcloud logging read \
  'resource.type="cloud_run_revision"
   jsonPayload.event="rate_limit"
   timestamp>="2026-01-09T15:00:00Z"' \
  --format=json \
  --project=vigilant-axis-483119-r8 | \
  jq -r '.[] | .jsonPayload.user_id' | \
  sort | uniq -c | sort -rn | head -10
```

#### Check Traffic Patterns
```bash
# Get rate limit metrics
gcloud monitoring time-series list \
  --filter='metric.type="custom.googleapis.com/upload/rate_limit_count"' \
  --interval-start-time="2026-01-09T15:00:00Z" \
  --project=vigilant-axis-483119-r8
```

### Resolution

#### Scenario A: Legitimate Traffic Spike
```bash
# Temporarily increase rate limits
# Update environment variables
gcloud run services update allms \
  --update-env-vars RATE_LIMIT_UPLOADS=20 \
  --region=europe-west4 \
  --project=vigilant-axis-483119-r8

# Or update in code and redeploy
```

#### Scenario B: Attack/Abuse
```bash
# Block specific user or IP
# Add to blocklist in Firestore or implement IP blocking

# Example: Update firewall rule
gcloud compute firewall-rules create block-abuser \
  --network=default \
  --action=DENY \
  --rules=all \
  --source-ranges=ABUSER_IP \
  --priority=1000 \
  --project=vigilant-axis-483119-r8
```

#### Scenario C: Misconfigured Limits
- Review current limits: 10 uploads per 60 seconds
- Consider tiered limits (free vs paid users)
- Implement user-specific overrides

---

## Monitoring Commands

### Real-time Monitoring
```bash
# Tail application logs
gcloud logging tail \
  'resource.type="cloud_run_revision"' \
  --format=json \
  --project=vigilant-axis-483119-r8

# Watch Redis metrics
watch -n 10 'gcloud redis instances describe allms-redis \
  --region=europe-west4 \
  --format="table(state,currentLocationId,memorySizeGb)"'
```

### Historical Analysis
```bash
# Rate limit events in last 24 hours
gcloud logging read \
  'resource.type="cloud_run_revision"
   jsonPayload.event="rate_limit"
   timestamp>="$(date -u -d "24 hours ago" +%Y-%m-%dT%H:%M:%SZ)"' \
  --format=json \
  --project=vigilant-axis-483119-r8 | jq length

# Redis errors in last 24 hours
gcloud logging read \
  'resource.type="cloud_run_revision"
   severity="ERROR"
   jsonPayload.message=~"Redis"
   timestamp>="$(date -u -d "24 hours ago" +%Y-%m-%dT%H:%M:%SZ)"' \
  --format=json \
  --project=vigilant-axis-483119-r8 | jq length
```

---

## Escalation

### Level 1: On-Call Engineer
- Follow this runbook
- Attempt resolution
- Document actions taken

### Level 2: Platform Lead
- Escalate if:
  - Issue persists >30 minutes
  - Multiple alerts firing
  - Unable to diagnose root cause

### Level 3: GCP Support
- Escalate if:
  - Redis instance unresponsive
  - Suspected GCP infrastructure issue
  - Regional outage suspected

---

## Post-Incident

### Required Actions
1. Document incident in incident log
2. Update runbook if new scenarios discovered
3. Review and improve monitoring
4. Consider preventive measures

### Review Questions
- What was the root cause?
- How can we prevent recurrence?
- Were alerts timely and actionable?
- Do we need additional monitoring?
- Should we adjust rate limits?

---

## Contact Information

- **On-Call:** Check PagerDuty schedule
- **Platform Team:** platform@mgms.eu
- **GCP Support:** https://console.cloud.google.com/support

---

## Related Documentation

- Rate Limiter Service: `app/services/rate_limiter.py`
- Upload Metrics: `app/services/upload_metrics.py`
- Alert Policies: `monitoring/alert-*.yaml`
- Issue #209: Rate Limiter Alerts

