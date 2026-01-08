# GDPR Soft Delete Cleanup Automation

This document describes the automated cleanup process for permanently deleting soft-deleted user data after the retention period.

## Overview

When users request account deletion, ALLMS performs a "soft delete":
1. User account is marked as `deleted: true`
2. Data is retained for 30 days (configurable)
3. After 30 days, data should be permanently deleted

The cleanup service automates step 3.

## Cleanup Service

**File:** `app/services/cleanup_service.py`

**Features:**
- Finds users whose retention period has expired
- Permanently deletes all user data from all collections
- Logs deletion audit trail
- Supports dry-run mode for testing
- Batch processing to avoid timeouts
- Error handling and retry logic

## Deployment Options

### Option 1: Cloud Scheduler + Cloud Functions (Recommended)

**Setup:**

1. **Create Cloud Function**

```bash
# Deploy cleanup function
gcloud functions deploy gdpr-cleanup \
    --runtime python39 \
    --trigger-topic gdpr-cleanup-topic \
    --entry-point scheduled_cleanup_handler \
    --timeout 540s \
    --memory 512MB \
    --set-env-vars ENVIRONMENT=production
```

2. **Create Cloud Scheduler Job**

```bash
# Create Pub/Sub topic
gcloud pubsub topics create gdpr-cleanup-topic

# Create scheduler job (runs daily at 2 AM UTC)
gcloud scheduler jobs create pubsub gdpr-cleanup-job \
    --schedule="0 2 * * *" \
    --topic=gdpr-cleanup-topic \
    --message-body='{"action":"cleanup"}' \
    --time-zone="UTC"
```

**Pros:**
- ✅ Fully managed
- ✅ Automatic scaling
- ✅ No server maintenance
- ✅ Pay per execution

**Cons:**
- ❌ 9-minute timeout limit
- ❌ May need batching for large deletions

---

### Option 2: Cloud Run Scheduled Job

**Setup:**

1. **Create Cloud Run Job**

```bash
# Build container
docker build -t gcr.io/YOUR_PROJECT/gdpr-cleanup:latest -f Dockerfile.cleanup .
docker push gcr.io/YOUR_PROJECT/gdpr-cleanup:latest

# Deploy Cloud Run job
gcloud run jobs create gdpr-cleanup \
    --image gcr.io/YOUR_PROJECT/gdpr-cleanup:latest \
    --region us-central1 \
    --task-timeout 3600s \
    --set-env-vars ENVIRONMENT=production
```

2. **Create Cloud Scheduler**

```bash
# Create scheduler to trigger Cloud Run job
gcloud scheduler jobs create http gdpr-cleanup-scheduler \
    --location us-central1 \
    --schedule="0 2 * * *" \
    --uri="https://us-central1-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/YOUR_PROJECT/jobs/gdpr-cleanup:run" \
    --http-method POST \
    --oauth-service-account-email YOUR_SERVICE_ACCOUNT@YOUR_PROJECT.iam.gserviceaccount.com
```

**Pros:**
- ✅ Longer timeout (1 hour)
- ✅ More resources available
- ✅ Better for large deletions

**Cons:**
- ❌ More complex setup
- ❌ Requires container

---

### Option 3: Manual Cron Job (Development/Testing)

**Setup:**

```bash
# Add to crontab
0 2 * * * cd /path/to/allms && python3 -m app.services.cleanup_service
```

**Pros:**
- ✅ Simple setup
- ✅ Full control

**Cons:**
- ❌ Requires server
- ❌ Manual maintenance
- ❌ Not suitable for production

---

## Running Cleanup Manually

### Dry Run (Test Mode)

```bash
# See what would be deleted without actually deleting
python3 -m app.services.cleanup_service --dry-run
```

**Output:**
```
Running GDPR cleanup (dry_run=True)...

Cleanup Results:
  Users found: 5
  Users deleted: 0
  Users failed: 0
  Duration: 1.2s

Users to delete:
  - user-123
  - user-456
  - user-789
```

### Actual Deletion

```bash
# Permanently delete expired users
python3 -m app.services.cleanup_service
```

**Output:**
```
Running GDPR cleanup (dry_run=False)...

Cleanup Results:
  Users found: 5
  Users deleted: 5
  Users failed: 0
  Duration: 45.3s
```

---

## Monitoring

### Cloud Logging

View cleanup logs:

```bash
# View all cleanup logs
gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=gdpr-cleanup" \
    --limit 50 \
    --format json

# View errors only
gcloud logging read "resource.type=cloud_function AND resource.labels.function_name=gdpr-cleanup AND severity>=ERROR" \
    --limit 50
```

### Metrics to Track

1. **Users Deleted**
   - Number of users permanently deleted per run
   - Alert if > 100 per day (potential issue)

2. **Deletion Failures**
   - Number of failed deletions
   - Alert if > 0

3. **Execution Time**
   - Duration of cleanup job
   - Alert if > 5 minutes (may need optimization)

4. **Documents Deleted**
   - Total documents deleted per user
   - Track for capacity planning

### Alerting

Set up alerts for:

```bash
# Alert on cleanup failures
gcloud alpha monitoring policies create \
    --notification-channels=YOUR_CHANNEL_ID \
    --display-name="GDPR Cleanup Failures" \
    --condition-display-name="Cleanup job failed" \
    --condition-threshold-value=1 \
    --condition-threshold-duration=60s
```

---

## Audit Trail

All permanent deletions are logged to `deletion_audit_logs` collection:

```json
{
  "user_id": "user-123",
  "deletion_timestamp": "2026-01-08T02:00:00Z",
  "deleted_collections": {
    "users": 1,
    "quiz_results": 45,
    "conversations": 12,
    "study_materials": 8,
    "consent_records": 3,
    "privacy_settings": 1,
    "data_subject_requests": 2,
    "audit_logs": 67
  },
  "total_documents_deleted": 139
}
```

**Retention:** Keep audit logs for 7 years (legal requirement)

---

## Troubleshooting

### Issue: Cleanup job times out

**Solution:**
- Switch to Cloud Run Jobs (longer timeout)
- Implement batching (process N users per run)
- Optimize Firestore queries

### Issue: Some users not deleted

**Check:**
1. Firestore indexes are created
2. `permanent_deletion_date` field exists
3. Date comparison is correct (UTC)

**Debug:**
```python
# Check users marked for deletion
users_ref = db.collection('users')
query = users_ref.where('deleted', '==', True)
for doc in query.stream():
    print(doc.id, doc.to_dict())
```

### Issue: Deletion fails for specific user

**Check:**
1. User exists in database
2. User has documents in collections
3. Firestore permissions are correct

**Manual deletion:**
```python
from app.services.cleanup_service import CleanupService
from app.services.gcp_service import get_firestore_client

db = get_firestore_client()
cleanup = CleanupService(db)
await cleanup.permanently_delete_user('user-123')
```

---

## Testing

### Unit Tests

```python
# tests/test_cleanup_service.py
import pytest
from app.services.cleanup_service import CleanupService

@pytest.mark.asyncio
async def test_find_users_for_deletion(mock_firestore):
    cleanup = CleanupService(mock_firestore)
    users = await cleanup.find_users_for_permanent_deletion()
    assert len(users) >= 0

@pytest.mark.asyncio
async def test_dry_run(mock_firestore):
    cleanup = CleanupService(mock_firestore)
    results = await cleanup.run_cleanup(dry_run=True)
    assert results['users_deleted'] == 0
```

### Integration Tests

```bash
# Create test user with expired deletion date
# Run cleanup
# Verify user is deleted
```

---

## Security Considerations

1. **Access Control**
   - Only cleanup service should have delete permissions
   - Use dedicated service account
   - Audit all deletions

2. **Data Verification**
   - Verify user consent before deletion
   - Check retention period is expired
   - Log all deletions

3. **Backup**
   - Consider backup before deletion (optional)
   - Keep audit logs for 7 years
   - Document deletion process

---

## Compliance

### GDPR Requirements

- ✅ Delete data within 30 days of request
- ✅ Permanent deletion (not just soft delete)
- ✅ Delete from all systems
- ✅ Audit trail of deletions
- ✅ Automated process (no manual intervention)

### Retention Policy

**User Data:** 30 days after deletion request
**Audit Logs:** 7 years (legal requirement)
**Deletion Logs:** 7 years (legal requirement)

---

## Maintenance

### Weekly Tasks
- [ ] Review cleanup logs
- [ ] Check for failed deletions
- [ ] Verify job is running

### Monthly Tasks
- [ ] Review deletion metrics
- [ ] Optimize if needed
- [ ] Update documentation

### Quarterly Tasks
- [ ] Audit deletion process
- [ ] Review retention policies
- [ ] Test disaster recovery

---

## Related Documentation

- [GDPR Implementation Guide](GDPR_IMPLEMENTATION.md)
- [Deployment Guide](GDPR_DEPLOYMENT.md)
- [Firestore Indexes](FIRESTORE_INDEXES.md)

