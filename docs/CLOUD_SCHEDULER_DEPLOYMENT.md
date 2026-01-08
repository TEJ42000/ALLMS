# Cloud Scheduler Deployment Guide

**Component:** Daily Streak Maintenance Job  
**Schedule:** Every day at 4:00 AM UTC  
**Endpoint:** `POST /api/gamification/streak/maintenance`  
**Related:** PR #153 - Phase 3: Streak System

---

## Overview

This guide provides step-by-step instructions for deploying the Cloud Scheduler job that runs daily streak maintenance.

---

## Prerequisites

- Google Cloud Project with billing enabled
- Cloud Scheduler API enabled
- Service account with appropriate permissions
- Application deployed to Cloud Run
- `ADMIN_EMAILS` environment variable configured

---

## Step 1: Enable Cloud Scheduler API

```bash
# Enable the API
gcloud services enable cloudscheduler.googleapis.com

# Verify it's enabled
gcloud services list --enabled | grep cloudscheduler
```

---

## Step 2: Create Service Account

Create a dedicated service account for the scheduler job:

```bash
# Create service account
gcloud iam service-accounts create streak-maintenance-scheduler \
    --display-name="Streak Maintenance Scheduler" \
    --description="Service account for daily streak maintenance job"

# Get the service account email
export SA_EMAIL="streak-maintenance-scheduler@${PROJECT_ID}.iam.gserviceaccount.com"

# Grant Cloud Run Invoker role
gcloud run services add-iam-policy-binding allms-backend \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/run.invoker" \
    --region=us-central1
```

---

## Step 3: Create Admin User for Scheduler

The maintenance endpoint requires admin authorization. Add the service account to `ADMIN_EMAILS`:

```bash
# Update Cloud Run service with admin email
gcloud run services update allms-backend \
    --update-env-vars ADMIN_EMAILS="admin@example.com,${SA_EMAIL}" \
    --region=us-central1
```

**Note:** Replace `admin@example.com` with your actual admin email(s).

---

## Step 4: Create Cloud Scheduler Job

```bash
# Set variables
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export SERVICE_URL="https://allms-backend-xxxxx-uc.a.run.app"  # Your Cloud Run URL

# Create the scheduler job
gcloud scheduler jobs create http streak-maintenance-daily \
    --location=${REGION} \
    --schedule="0 4 * * *" \
    --time-zone="UTC" \
    --uri="${SERVICE_URL}/api/gamification/streak/maintenance" \
    --http-method=POST \
    --oidc-service-account-email=${SA_EMAIL} \
    --oidc-token-audience=${SERVICE_URL} \
    --attempt-deadline=600s \
    --max-retry-attempts=3 \
    --max-backoff=3600s \
    --min-backoff=60s \
    --description="Daily streak maintenance job - runs at 4:00 AM UTC"
```

### Schedule Explanation

- `0 4 * * *` - Cron expression for 4:00 AM UTC daily
- `--time-zone="UTC"` - Ensures consistent timing
- `--attempt-deadline=600s` - 10 minute timeout
- `--max-retry-attempts=3` - Retry up to 3 times on failure
- `--max-backoff=3600s` - Max 1 hour between retries
- `--min-backoff=60s` - Min 1 minute between retries

---

## Step 5: Verify Job Creation

```bash
# List all scheduler jobs
gcloud scheduler jobs list --location=${REGION}

# Describe the specific job
gcloud scheduler jobs describe streak-maintenance-daily \
    --location=${REGION}
```

Expected output:
```
name: projects/PROJECT_ID/locations/REGION/jobs/streak-maintenance-daily
schedule: 0 4 * * *
timeZone: UTC
httpTarget:
  uri: https://allms-backend-xxxxx-uc.a.run.app/api/gamification/streak/maintenance
  httpMethod: POST
  oidcToken:
    serviceAccountEmail: streak-maintenance-scheduler@PROJECT_ID.iam.gserviceaccount.com
state: ENABLED
```

---

## Step 6: Test the Job Manually

Before waiting for the scheduled run, test the job manually:

```bash
# Trigger the job immediately
gcloud scheduler jobs run streak-maintenance-daily \
    --location=${REGION}

# Check the execution logs
gcloud scheduler jobs describe streak-maintenance-daily \
    --location=${REGION} \
    | grep -A 5 "lastAttemptTime"
```

### Verify in Cloud Run Logs

```bash
# View Cloud Run logs
gcloud run services logs read allms-backend \
    --region=${REGION} \
    --limit=50 \
    | grep "streak maintenance"
```

Expected log output:
```
Starting daily streak maintenance
Processed batch 1: 100 users
Processed batch 2: 100 users
...
Daily streak maintenance completed: 1000 users processed, 20 freezes applied, 5 streaks broken
```

---

## Step 7: Set Up Monitoring Alerts

Deploy the monitoring alerts from the configuration file:

```bash
# Deploy alerts
gcloud alpha monitoring policies create \
    --policy-from-file=monitoring/streak_maintenance_alerts.yaml
```

### Key Alerts

1. **Job Failure Alert**
   - Triggers if job fails 2+ times in 1 hour
   - Sends email/SMS to admins

2. **High Error Rate Alert**
   - Triggers if error rate > 5%
   - Indicates potential system issues

3. **Long Execution Time Alert**
   - Triggers if execution > 10 minutes
   - May indicate performance degradation

---

## Step 8: Configure Logging

Ensure proper logging is configured:

```bash
# Create log sink for streak maintenance
gcloud logging sinks create streak-maintenance-sink \
    bigquery.googleapis.com/projects/${PROJECT_ID}/datasets/streak_logs \
    --log-filter='resource.type="cloud_run_revision"
                  AND resource.labels.service_name="allms-backend"
                  AND textPayload=~"streak maintenance"'
```

---

## Maintenance and Monitoring

### Daily Checks

1. **Verify Job Execution**
   ```bash
   gcloud scheduler jobs describe streak-maintenance-daily \
       --location=${REGION} \
       | grep -A 10 "lastAttemptTime"
   ```

2. **Check Success Rate**
   ```bash
   gcloud logging read \
       'resource.type="cloud_scheduler_job"
        AND resource.labels.job_id="streak-maintenance-daily"' \
       --limit=7 \
       --format="table(timestamp,jsonPayload.status)"
   ```

3. **Review Metrics**
   - Users processed
   - Freezes applied
   - Streaks broken
   - Execution time
   - Error count

### Weekly Reviews

- Analyze trends in streak breaks
- Review freeze usage patterns
- Check for performance degradation
- Verify alert configurations

### Monthly Audits

- Review service account permissions
- Update admin email list if needed
- Optimize batch size if necessary
- Review and update monitoring thresholds

---

## Troubleshooting

### Job Not Running

**Check job status:**
```bash
gcloud scheduler jobs describe streak-maintenance-daily \
    --location=${REGION}
```

**Common issues:**
- Job is paused: `gcloud scheduler jobs resume ...`
- Wrong timezone: Update with `--time-zone=UTC`
- Service account lacks permissions

### Authentication Errors

**Error:** `403 Forbidden` or `401 Unauthorized`

**Solutions:**
1. Verify service account has Cloud Run Invoker role
2. Check ADMIN_EMAILS includes service account
3. Verify OIDC token configuration

```bash
# Re-grant permissions
gcloud run services add-iam-policy-binding allms-backend \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/run.invoker" \
    --region=${REGION}
```

### Timeout Errors

**Error:** `504 Gateway Timeout`

**Solutions:**
1. Increase attempt deadline:
   ```bash
   gcloud scheduler jobs update http streak-maintenance-daily \
       --location=${REGION} \
       --attempt-deadline=900s  # 15 minutes
   ```

2. Optimize batch processing in code
3. Check database performance

### High Error Rate

**Check logs for errors:**
```bash
gcloud run services logs read allms-backend \
    --region=${REGION} \
    --limit=100 \
    | grep -i error
```

**Common causes:**
- Firestore connection issues
- Invalid user data
- Memory limits exceeded

---

## Updating the Job

### Change Schedule

```bash
# Update to run at 3:00 AM instead
gcloud scheduler jobs update http streak-maintenance-daily \
    --location=${REGION} \
    --schedule="0 3 * * *"
```

### Change Timeout

```bash
gcloud scheduler jobs update http streak-maintenance-daily \
    --location=${REGION} \
    --attempt-deadline=900s
```

### Pause/Resume Job

```bash
# Pause (disable)
gcloud scheduler jobs pause streak-maintenance-daily \
    --location=${REGION}

# Resume (enable)
gcloud scheduler jobs resume streak-maintenance-daily \
    --location=${REGION}
```

---

## Cleanup (If Needed)

To remove the scheduler job:

```bash
# Delete the job
gcloud scheduler jobs delete streak-maintenance-daily \
    --location=${REGION}

# Delete the service account
gcloud iam service-accounts delete ${SA_EMAIL}
```

---

## Best Practices

1. **Always test manually** before relying on scheduled runs
2. **Monitor execution logs** daily for the first week
3. **Set up alerts** for failures and anomalies
4. **Document any changes** to schedule or configuration
5. **Review permissions** quarterly
6. **Keep backup** of job configuration
7. **Test disaster recovery** procedures

---

## Related Documentation

- [Monitoring Deployment Guide](MONITORING_DEPLOYMENT_GUIDE.md)
- [Phase 3 Streak System](PHASE3_STREAK_SYSTEM.md)
- [Google Cloud Scheduler Documentation](https://cloud.google.com/scheduler/docs)

---

**Deployment Status:** Ready for production  
**Last Updated:** 2026-01-08  
**Maintained By:** DevOps Team

