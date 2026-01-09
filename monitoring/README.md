# Cloud Monitoring Alert Policies

This directory contains Cloud Monitoring alert policies for the ALLMS rate limiter system.

## Overview

The rate limiter uses Redis for distributed rate limiting in production. These alert policies monitor the health and performance of the rate limiting system.

### Alert Policies

1. **alert-redis-connection.yaml** (CRITICAL)
   - Triggers when Redis connection fails
   - Impact: Rate limiting degraded
   - Action: Immediate investigation required

2. **alert-rate-limiter-failure.yaml** (HIGH)
   - Triggers when rate limiter backend fails
   - Impact: Inconsistent rate limiting
   - Action: Check Redis health and connectivity

3. **alert-rate-limit-capacity.yaml** (MEDIUM)
   - Triggers when many users hit rate limits
   - Impact: Legitimate users may be blocked
   - Action: Investigate traffic patterns, consider capacity increase

## Deployment

### Prerequisites

- gcloud CLI installed and authenticated
- Project: `vigilant-axis-483119-r8`
- Permissions: `monitoring.alertPolicies.create`, `monitoring.notificationChannels.create`

### Quick Start

```bash
# Deploy all alert policies with default email
./monitoring/deploy-alerts.sh

# Deploy with custom email
./monitoring/deploy-alerts.sh --email your-email@example.com

# Dry run (show what would be deployed)
./monitoring/deploy-alerts.sh --dry-run
```

### Manual Deployment

If you prefer to deploy manually:

```bash
# 1. Create notification channel
gcloud alpha monitoring channels create \
  --display-name="Ops Team Email" \
  --type=email \
  --channel-labels=email_address=ops@mgms.eu \
  --project=vigilant-axis-483119-r8

# 2. Get channel ID
CHANNEL_ID=$(gcloud alpha monitoring channels list \
  --filter="displayName='Ops Team Email'" \
  --format="value(name)" \
  --project=vigilant-axis-483119-r8)

# 3. Deploy alert policies
gcloud alpha monitoring policies create \
  --notification-channels=$CHANNEL_ID \
  --policy-from-file=monitoring/alert-redis-connection.yaml \
  --project=vigilant-axis-483119-r8

gcloud alpha monitoring policies create \
  --notification-channels=$CHANNEL_ID \
  --policy-from-file=monitoring/alert-rate-limiter-failure.yaml \
  --project=vigilant-axis-483119-r8

gcloud alpha monitoring policies create \
  --notification-channels=$CHANNEL_ID \
  --policy-from-file=monitoring/alert-rate-limit-capacity.yaml \
  --project=vigilant-axis-483119-r8
```

## Alert Details

### Redis Connection Failure (CRITICAL)

**Trigger Condition:**
- 3+ "Failed to connect to Redis" errors in 3 minutes

**Symptoms:**
- Cannot connect to Redis instance
- Application falling back to in-memory rate limiter
- Rate limiting not working across instances

**Immediate Actions:**
1. Check Redis instance status
2. Verify network connectivity
3. Check authentication
4. Restart Redis if needed

**Runbook:** [docs/runbooks/rate-limiter-alerts.md](../docs/runbooks/rate-limiter-alerts.md)

---

### Rate Limiter Backend Failure (HIGH)

**Trigger Condition:**
- 5+ "Redis rate limit check failed" errors in 5 minutes

**Symptoms:**
- Intermittent Redis failures
- Some requests succeed, others fail
- Inconsistent rate limiting

**Immediate Actions:**
1. Check Redis performance metrics
2. Review error logs
3. Check for connection pool exhaustion
4. Consider scaling Redis

**Runbook:** [docs/runbooks/rate-limiter-alerts.md](../docs/runbooks/rate-limiter-alerts.md)

---

### High Rate Limit Hits (MEDIUM)

**Trigger Condition:**
- 100+ "Rate limit exceeded" events in 5 minutes

**Symptoms:**
- Many users hitting rate limits
- High volume of 429 responses
- Increased rate limit log entries

**Immediate Actions:**
1. Identify top users hitting limits
2. Check for attack vs legitimate spike
3. Review rate limit configuration
4. Consider temporary limit increase

**Runbook:** [docs/runbooks/rate-limiter-alerts.md](../docs/runbooks/rate-limiter-alerts.md)

---

## Testing Alerts

### Test Redis Connection Failure

```bash
# Temporarily stop Redis (in test environment only!)
gcloud redis instances update allms-redis-test \
  --maintenance-policy=DENY \
  --region=europe-west4 \
  --project=vigilant-axis-483119-r8

# Wait for alert to trigger (3-5 minutes)

# Restore Redis
gcloud redis instances update allms-redis-test \
  --maintenance-policy=ALLOW \
  --region=europe-west4 \
  --project=vigilant-axis-483119-r8
```

### Test Rate Limit Capacity

```bash
# Generate high volume of uploads (test environment only!)
for i in {1..150}; do
  curl -X POST https://allms-test.mgms.eu/api/upload \
    -H "Authorization: Bearer $TOKEN" \
    -F "file=@test.pdf" \
    -F "course_id=test" &
done

# Wait for alert to trigger (5-10 minutes)
```

## Monitoring Dashboard

View alerts in Cloud Console:
- **Alert Policies:** https://console.cloud.google.com/monitoring/alerting/policies?project=vigilant-axis-483119-r8
- **Incidents:** https://console.cloud.google.com/monitoring/alerting/incidents?project=vigilant-axis-483119-r8
- **Logs:** https://console.cloud.google.com/logs?project=vigilant-axis-483119-r8

## Notification Channels

### Email

Default channel created by deployment script:
- **Name:** Ops Team Email
- **Type:** Email
- **Address:** ops@mgms.eu (or custom via --email flag)

### Additional Channels (Optional)

#### Slack

```bash
# Create Slack notification channel
gcloud alpha monitoring channels create \
  --display-name="Slack Alerts" \
  --type=slack \
  --channel-labels=url=https://hooks.slack.com/services/YOUR/WEBHOOK/URL \
  --project=vigilant-axis-483119-r8
```

#### PagerDuty (for CRITICAL alerts)

```bash
# Create PagerDuty notification channel
gcloud alpha monitoring channels create \
  --display-name="PagerDuty Critical" \
  --type=pagerduty \
  --channel-labels=service_key=YOUR_PAGERDUTY_KEY \
  --project=vigilant-axis-483119-r8
```

## Maintenance

### Updating Alert Policies

1. Edit the YAML file
2. Redeploy using the script:
   ```bash
   ./monitoring/deploy-alerts.sh
   ```
3. Confirm update when prompted

### Deleting Alert Policies

```bash
# List policies
gcloud alpha monitoring policies list \
  --project=vigilant-axis-483119-r8

# Delete specific policy
gcloud alpha monitoring policies delete POLICY_NAME \
  --project=vigilant-axis-483119-r8
```

### Viewing Alert History

```bash
# List recent incidents
gcloud alpha monitoring incidents list \
  --project=vigilant-axis-483119-r8 \
  --limit=10

# Get incident details
gcloud alpha monitoring incidents describe INCIDENT_ID \
  --project=vigilant-axis-483119-r8
```

## Troubleshooting

### Alert Not Triggering

1. **Check log filter:**
   ```bash
   gcloud logging read \
     'resource.type="cloud_run_revision"
      severity="ERROR"
      jsonPayload.message=~"Redis"' \
     --limit=10 \
     --project=vigilant-axis-483119-r8
   ```

2. **Verify alert policy is active:**
   ```bash
   gcloud alpha monitoring policies list \
     --filter="enabled=true" \
     --project=vigilant-axis-483119-r8
   ```

3. **Check notification channel:**
   ```bash
   gcloud alpha monitoring channels list \
     --project=vigilant-axis-483119-r8
   ```

### Too Many Alerts

1. **Adjust thresholds** in YAML files
2. **Increase duration** before triggering
3. **Add notification rate limits**

### False Positives

1. **Review log filters** - may be too broad
2. **Adjust threshold values** - may be too sensitive
3. **Add exclusion filters** - filter out known noise

## Related Documentation

- **Runbook:** [docs/runbooks/rate-limiter-alerts.md](../docs/runbooks/rate-limiter-alerts.md)
- **Rate Limiter Service:** [app/services/rate_limiter.py](../app/services/rate_limiter.py)
- **Upload Metrics:** [app/services/upload_metrics.py](../app/services/upload_metrics.py)
- **Issue #209:** Rate Limiter Alerts

## Support

- **On-Call:** Check PagerDuty schedule
- **Platform Team:** platform@mgms.eu
- **GCP Support:** https://console.cloud.google.com/support

