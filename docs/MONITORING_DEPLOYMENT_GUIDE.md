# Monitoring Deployment Guide - Streak Maintenance Job

**Date:** 2026-01-08  
**Component:** Streak Maintenance Job  
**Priority:** CRITICAL

---

## Overview

This guide covers deploying monitoring and alerting for the streak maintenance job to ensure production reliability.

---

## Prerequisites

- Google Cloud Project with billing enabled
- `gcloud` CLI installed and authenticated
- Cloud Monitoring API enabled
- Notification channels configured (Slack, Email, PagerDuty)

---

## Step 1: Enable Required APIs

```bash
# Enable Cloud Monitoring API
gcloud services enable monitoring.googleapis.com

# Enable Cloud Logging API
gcloud services enable logging.googleapis.com

# Enable Cloud Functions API (if not already enabled)
gcloud services enable cloudfunctions.googleapis.com
```

---

## Step 2: Create Notification Channels

### Slack Channel

```bash
# Create Slack notification channel
gcloud alpha monitoring channels create \
  --display-name="Gamification Alerts Slack" \
  --type=slack \
  --channel-labels=url=YOUR_SLACK_WEBHOOK_URL
```

### Email Channel

```bash
# Create email notification channel
gcloud alpha monitoring channels create \
  --display-name="Gamification Alerts Email" \
  --type=email \
  --channel-labels=email_address=alerts@yourcompany.com
```

### PagerDuty Channel (for critical alerts)

```bash
# Create PagerDuty notification channel
gcloud alpha monitoring channels create \
  --display-name="Gamification PagerDuty" \
  --type=pagerduty \
  --channel-labels=service_key=YOUR_PAGERDUTY_SERVICE_KEY
```

### List Notification Channels

```bash
# Get channel IDs for alert policies
gcloud alpha monitoring channels list
```

---

## Step 3: Update Alert Policy Configuration

Edit `monitoring/streak_maintenance_alerts.yaml` and replace placeholders:

```yaml
# Replace PROJECT_ID with your GCP project ID
# Replace SLACK_CHANNEL_ID with ID from Step 2
# Replace EMAIL_CHANNEL_ID with ID from Step 2
# Replace PAGERDUTY_CHANNEL_ID with ID from Step 2

notificationChannels:
  - projects/YOUR_PROJECT_ID/notificationChannels/SLACK_CHANNEL_ID
  - projects/YOUR_PROJECT_ID/notificationChannels/EMAIL_CHANNEL_ID
  - projects/YOUR_PROJECT_ID/notificationChannels/PAGERDUTY_CHANNEL_ID
```

---

## Step 4: Deploy Alert Policies

```bash
# Navigate to monitoring directory
cd monitoring

# Deploy alert policies
gcloud alpha monitoring policies create \
  --policy-from-file=streak_maintenance_alerts.yaml

# Verify policies created
gcloud alpha monitoring policies list
```

---

## Step 5: Create Monitoring Dashboard

```bash
# Update dashboard configuration with your project ID
sed -i 's/PROJECT_ID/YOUR_PROJECT_ID/g' streak_maintenance_dashboard.json

# Create dashboard
gcloud monitoring dashboards create \
  --config-from-file=streak_maintenance_dashboard.json

# Get dashboard URL
gcloud monitoring dashboards list
```

---

## Step 6: Configure Log-Based Metrics

Create custom metrics for better monitoring:

```bash
# Create metric for job failures
gcloud logging metrics create streak_maintenance_failures \
  --description="Count of streak maintenance job failures" \
  --log-filter='resource.type="cloud_function"
    AND resource.labels.function_name="streak-maintenance"
    AND jsonPayload.status="error"'

# Create metric for high error rate
gcloud logging metrics create streak_maintenance_error_rate \
  --description="Error rate in streak maintenance job" \
  --log-filter='resource.type="cloud_function"
    AND resource.labels.function_name="streak-maintenance"
    AND jsonPayload.errors>10' \
  --value-extractor='EXTRACT(jsonPayload.errors)'

# Create metric for job duration
gcloud logging metrics create streak_maintenance_duration \
  --description="Duration of streak maintenance job" \
  --log-filter='resource.type="cloud_function"
    AND resource.labels.function_name="streak-maintenance"
    AND jsonPayload.duration_seconds>0' \
  --value-extractor='EXTRACT(jsonPayload.duration_seconds)'

# Create metric for users processed
gcloud logging metrics create streak_maintenance_users_processed \
  --description="Number of users processed by maintenance job" \
  --log-filter='resource.type="cloud_function"
    AND resource.labels.function_name="streak-maintenance"
    AND jsonPayload.users_processed>0' \
  --value-extractor='EXTRACT(jsonPayload.users_processed)'
```

---

## Step 7: Set Up Uptime Checks

```bash
# Create uptime check for maintenance job endpoint
gcloud monitoring uptime create streak-maintenance-check \
  --display-name="Streak Maintenance Job Health" \
  --resource-type=uptime-url \
  --monitored-resource=YOUR_CLOUD_FUNCTION_URL \
  --check-interval=3600s \
  --timeout=60s
```

---

## Step 8: Configure Cloud Scheduler Monitoring

```bash
# Add monitoring to Cloud Scheduler job
gcloud scheduler jobs update http streak-maintenance-job \
  --attempt-deadline=540s \
  --max-retry-attempts=3 \
  --max-backoff=3600s \
  --min-backoff=60s

# Enable job failure notifications
gcloud scheduler jobs update http streak-maintenance-job \
  --pubsub-topic=projects/YOUR_PROJECT_ID/topics/scheduler-failures
```

---

## Step 9: Test Alerts

### Test Failure Alert

```bash
# Trigger a test failure
gcloud functions call streak-maintenance \
  --data='{"test_mode": true, "force_error": true}'

# Check if alert fired
gcloud alpha monitoring policies list --filter="displayName:Streak Maintenance Job Failure"
```

### Test Memory Alert

```bash
# Monitor memory usage
gcloud logging read 'resource.type="cloud_function" 
  AND resource.labels.function_name="streak-maintenance"
  AND metric.type="cloudfunctions.googleapis.com/function/user_memory_bytes"' \
  --limit=10 \
  --format=json
```

---

## Step 10: Set Up Incident Response

### Create Runbook

Document in your incident management system:

1. **Alert: Maintenance Job Failed**
   - Check Cloud Scheduler logs
   - Verify Firestore connectivity
   - Review error logs
   - Manually trigger job if needed
   - Escalate if failure persists > 1 hour

2. **Alert: High Error Rate**
   - Review error logs for patterns
   - Check for data integrity issues
   - Verify transaction conflicts
   - Consider reducing batch size

3. **Alert: Memory Leak**
   - Review batch processing logic
   - Check for unreleased resources
   - Restart function if needed
   - Deploy fix if confirmed

### Configure On-Call Rotation

```bash
# Set up PagerDuty escalation policy
# Configure on-call schedule
# Test paging workflow
```

---

## Step 11: Verify Monitoring

### Checklist

- [ ] All alert policies created and enabled
- [ ] Notification channels configured and tested
- [ ] Dashboard accessible and displaying data
- [ ] Log-based metrics collecting data
- [ ] Uptime checks running
- [ ] Cloud Scheduler monitoring enabled
- [ ] Incident response runbook documented
- [ ] On-call rotation configured
- [ ] Test alerts verified

### Verification Commands

```bash
# List all alert policies
gcloud alpha monitoring policies list

# List all notification channels
gcloud alpha monitoring channels list

# List all dashboards
gcloud monitoring dashboards list

# List all log-based metrics
gcloud logging metrics list

# Check recent logs
gcloud logging read 'resource.type="cloud_function" 
  AND resource.labels.function_name="streak-maintenance"' \
  --limit=50 \
  --format=json
```

---

## Monitoring Best Practices

### 1. Alert Fatigue Prevention
- Set appropriate thresholds
- Use notification rate limiting
- Implement auto-close for resolved issues
- Review and tune alerts monthly

### 2. Dashboard Organization
- Group related metrics
- Use consistent time ranges
- Add threshold lines for SLOs
- Include recent error logs

### 3. Log Management
- Use structured logging
- Include correlation IDs
- Set appropriate retention periods
- Archive old logs to Cloud Storage

### 4. Incident Response
- Document all incidents
- Conduct post-mortems
- Update runbooks regularly
- Share learnings with team

---

## Troubleshooting

### Alert Not Firing

```bash
# Check alert policy status
gcloud alpha monitoring policies describe POLICY_ID

# Verify notification channels
gcloud alpha monitoring channels describe CHANNEL_ID

# Check logs for matching entries
gcloud logging read 'FILTER_FROM_ALERT_POLICY' --limit=10
```

### Dashboard Not Showing Data

```bash
# Verify metrics exist
gcloud logging metrics list

# Check metric data
gcloud logging read 'metric.type="logging.googleapis.com/user/METRIC_NAME"' --limit=10

# Verify time range in dashboard
```

### High Alert Volume

```bash
# Review alert frequency
gcloud alpha monitoring policies list --format=json | jq '.[] | {name, enabled}'

# Adjust thresholds or add rate limiting
gcloud alpha monitoring policies update POLICY_ID \
  --notification-rate-limit=3600s
```

---

## Maintenance

### Weekly
- Review dashboard for anomalies
- Check alert firing frequency
- Verify notification delivery

### Monthly
- Review and tune alert thresholds
- Update runbooks with new learnings
- Archive old logs
- Review monitoring costs

### Quarterly
- Conduct monitoring effectiveness review
- Update dashboards with new metrics
- Review incident response times
- Optimize log retention policies

---

## Cost Optimization

### Monitoring Costs

```bash
# Check monitoring usage
gcloud monitoring time-series list \
  --filter='metric.type="monitoring.googleapis.com/billing/bytes_ingested"'

# Optimize log ingestion
gcloud logging sinks create archive-old-logs \
  storage.googleapis.com/YOUR_ARCHIVE_BUCKET \
  --log-filter='timestamp<"2024-01-01"'
```

### Estimated Costs
- Alert policies: $0.15/policy/month
- Log-based metrics: $0.50/metric/month
- Dashboard: Free
- Log ingestion: $0.50/GB
- Log storage: $0.01/GB/month

---

## Support

### Resources
- [Cloud Monitoring Documentation](https://cloud.google.com/monitoring/docs)
- [Alert Policy Reference](https://cloud.google.com/monitoring/api/ref_v3/rest/v3/projects.alertPolicies)
- [Dashboard Configuration](https://cloud.google.com/monitoring/dashboards)

### Contact
- Team: #gamification-team
- On-call: PagerDuty escalation
- Email: devops@yourcompany.com

---

**Last Updated:** 2026-01-08  
**Status:** Ready for deployment

