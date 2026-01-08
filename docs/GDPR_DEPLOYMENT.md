# GDPR Deployment Guide

This guide covers deploying the GDPR compliance features to production.

## Prerequisites

Before deploying GDPR features, ensure you have:

- [ ] Google Cloud Project with Firestore enabled
- [ ] **Redis instance (REQUIRED for multi-instance deployments)** OR single-worker deployment
- [ ] Email service configured (SendGrid, AWS SES, or SMTP)
- [ ] SSL/TLS certificates for HTTPS
- [ ] Domain name configured
- [ ] Google Secret Manager access (for storing secrets)

## ⚠️ IMPORTANT: Rate Limiting Deployment Options

The GDPR implementation includes rate limiting to prevent abuse. You have **two deployment options**:

### Option A: Redis-Based Rate Limiting (RECOMMENDED for Production)

**Use this if:**
- You need to scale to multiple instances
- You want persistent rate limits across restarts
- You need distributed rate limiting

**Requirements:**
- Redis instance (Google Cloud Memorystore or self-hosted)
- Set `RATE_LIMIT_BACKEND=redis`
- Configure Redis connection details

**Pros:**
- ✅ Works with multiple instances
- ✅ Persistent across restarts
- ✅ Distributed and synchronized
- ✅ Production-ready

**Cons:**
- ❌ Requires Redis infrastructure
- ❌ Additional cost

### Option B: In-Memory Rate Limiting (Development/Single-Worker Only)

**Use this if:**
- You're deploying to a single instance only
- You're in development/testing
- You want to avoid Redis setup initially

**Requirements:**
- Set `RATE_LIMIT_BACKEND=memory`
- **CRITICAL:** Deploy with `--max-instances=1` (Cloud Run) or single worker
- Accept that rate limits reset on restart

**Pros:**
- ✅ No additional infrastructure
- ✅ Simple setup
- ✅ No extra cost

**Cons:**
- ❌ Only works with single instance
- ❌ Rate limits reset on restart
- ❌ Not suitable for high-traffic production
- ❌ Cannot scale horizontally

**Single-Worker Deployment Example:**
```bash
# Cloud Run with single instance
gcloud run deploy allms \
    --image gcr.io/YOUR_PROJECT/allms:latest \
    --max-instances=1 \
    --min-instances=1 \
    --set-env-vars RATE_LIMIT_BACKEND=memory

# WARNING: This limits your application to a single instance!
# If the instance crashes, there will be downtime until it restarts.
```

**⚠️ Production Recommendation:**
For production deployments, **always use Redis** (Option A). In-memory rate limiting should only be used for:
- Development environments
- Testing/staging with low traffic
- Temporary deployments while setting up Redis

See [GDPR_RATE_LIMITING.md](GDPR_RATE_LIMITING.md) for detailed information on rate limiting implementation and migration.

## Pre-Deployment Checklist

### 1. Environment Variables

**Critical - Must Set:**
- [ ] `GDPR_TOKEN_SECRET` - Generate and store in Secret Manager
- [ ] `FIRESTORE_PROJECT_ID` - Your GCP project ID
- [ ] `ANTHROPIC_API_KEY` - Your Anthropic API key
- [ ] `RATE_LIMIT_BACKEND=redis` - Use Redis for production
- [ ] `REDIS_HOST` - Redis server hostname
- [ ] `EMAIL_SERVICE_PROVIDER` - Email service (sendgrid/ses/smtp)

**Recommended:**
- [ ] `REDIS_PASSWORD` - Redis authentication
- [ ] `REDIS_SSL=true` - Enable SSL for Redis
- [ ] `SENDGRID_API_KEY` or equivalent email credentials

See [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) for complete list.

### 2. Generate Secrets

```bash
# Generate GDPR token secret
python3 -c "import secrets; print(secrets.token_hex(32))"

# Store in Google Secret Manager
gcloud secrets create gdpr-token-secret \
    --data-file=- \
    --replication-policy="automatic"
```

### 3. Configure Firestore

**Collections:**

Firestore collections will be auto-created on first use:
- `consent_records` - User consent history
- `audit_logs` - GDPR action audit trail
- `privacy_settings` - User privacy preferences
- `data_subject_requests` - GDPR request tracking
- `rate_limits` - Rate limiting (if using database backend)

**Indexes (REQUIRED):**

Firestore requires composite indexes for GDPR queries. Create indexes **before** deploying:

**Option A: Using firestore.indexes.json (Recommended)**
```bash
# Copy firestore.indexes.json to project root
# See docs/FIRESTORE_INDEXES.md for complete file

firebase deploy --only firestore:indexes
```

**Option B: Using gcloud CLI**
```bash
# Consent records - user history
gcloud firestore indexes composite create \
    --collection-group=consent_records \
    --field-config field-path=user_id,order=ascending \
    --field-config field-path=timestamp,order=descending

# Audit logs - user history
gcloud firestore indexes composite create \
    --collection-group=audit_logs \
    --field-config field-path=user_id,order=ascending \
    --field-config field-path=timestamp,order=descending

# Data subject requests - user requests
gcloud firestore indexes composite create \
    --collection-group=data_subject_requests \
    --field-config field-path=user_id,order=ascending \
    --field-config field-path=created_at,order=descending

# See docs/FIRESTORE_INDEXES.md for complete list (10 indexes total)
```

**Option C: Firebase Console**
1. Go to Firebase Console → Firestore Database → Indexes
2. Create indexes manually
3. See docs/FIRESTORE_INDEXES.md for required indexes

**⚠️ Important:**
- Indexes can take hours to build for large collections
- Queries will fail until indexes are READY
- Create indexes before deploying to production
- See [FIRESTORE_INDEXES.md](FIRESTORE_INDEXES.md) for complete documentation

### 4. Set Up Redis

**Option A: Google Cloud Memorystore**
```bash
gcloud redis instances create gdpr-rate-limit \
    --size=1 \
    --region=us-central1 \
    --redis-version=redis_6_x \
    --tier=basic
```

**Option B: Self-Hosted Redis**
```bash
# Docker Compose
services:
  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
```

### 5. Configure Email Service

**SendGrid:**
```bash
# Create API key in SendGrid dashboard
# Store in Secret Manager
gcloud secrets create sendgrid-api-key \
    --data-file=- \
    --replication-policy="automatic"
```

**AWS SES:**
```bash
# Verify domain in AWS SES
aws ses verify-domain-identity --domain yourdomain.com

# Create SMTP credentials
aws iam create-access-key --user-name ses-smtp-user
```

## Deployment Steps

### Step 1: Deploy Application

**Option A: Production Deployment with Redis (Recommended)**

```bash
# Build Docker image
docker build -t gcr.io/YOUR_PROJECT/allms:gdpr-v1 .

# Push to Container Registry
docker push gcr.io/YOUR_PROJECT/allms:gdpr-v1

# Deploy to Cloud Run with Redis rate limiting
gcloud run deploy allms \
    --image gcr.io/YOUR_PROJECT/allms:gdpr-v1 \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --min-instances=1 \
    --max-instances=10 \
    --set-env-vars ENVIRONMENT=production \
    --set-env-vars GDPR_TOKEN_SECRET=projects/YOUR_PROJECT/secrets/gdpr-token-secret/versions/latest \
    --set-env-vars RATE_LIMIT_BACKEND=redis \
    --set-env-vars REDIS_HOST=YOUR_REDIS_HOST \
    --set-env-vars REDIS_PORT=6379 \
    --set-env-vars REDIS_PASSWORD=YOUR_REDIS_PASSWORD \
    --set-env-vars REDIS_SSL=true \
    --set-env-vars EMAIL_SERVICE_PROVIDER=sendgrid \
    --set-env-vars SENDGRID_API_KEY=projects/YOUR_PROJECT/secrets/sendgrid-api-key/versions/latest \
    --set-env-vars EMAIL_FROM_ADDRESS=noreply@yourdomain.com
```

**Option B: Single-Worker Deployment with In-Memory Rate Limiting (Not Recommended for Production)**

```bash
# Build Docker image
docker build -t gcr.io/YOUR_PROJECT/allms:gdpr-v1 .

# Push to Container Registry
docker push gcr.io/YOUR_PROJECT/allms:gdpr-v1

# Deploy to Cloud Run with SINGLE INSTANCE ONLY
gcloud run deploy allms \
    --image gcr.io/YOUR_PROJECT/allms:gdpr-v1 \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --min-instances=1 \
    --max-instances=1 \
    --set-env-vars ENVIRONMENT=production \
    --set-env-vars GDPR_TOKEN_SECRET=projects/YOUR_PROJECT/secrets/gdpr-token-secret/versions/latest \
    --set-env-vars RATE_LIMIT_BACKEND=memory \
    --set-env-vars EMAIL_SERVICE_PROVIDER=sendgrid \
    --set-env-vars SENDGRID_API_KEY=projects/YOUR_PROJECT/secrets/sendgrid-api-key/versions/latest \
    --set-env-vars EMAIL_FROM_ADDRESS=noreply@yourdomain.com

# ⚠️ WARNING: This deployment is limited to a single instance!
# - Cannot scale horizontally
# - Rate limits reset on restart
# - Single point of failure
# - Only suitable for low-traffic deployments
```

### Step 2: Verify Deployment

```bash
# Test health endpoint
curl https://your-domain.com/health

# Test GDPR endpoints (requires authentication)
curl -X POST https://your-domain.com/api/gdpr/consent \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -d '{"consent_type": "analytics", "status": "granted"}'
```

### Step 3: Configure DNS

```bash
# Point domain to Cloud Run service
gcloud run services describe allms --region us-central1 --format 'value(status.url)'

# Add custom domain
gcloud run domain-mappings create \
    --service allms \
    --domain your-domain.com \
    --region us-central1
```

### Step 4: Enable HTTPS

```bash
# Cloud Run automatically provisions SSL certificates
# Verify HTTPS is working
curl -I https://your-domain.com
```

## Post-Deployment Verification

### 1. Test GDPR Features

**Cookie Consent:**
- [ ] Visit homepage - cookie banner appears
- [ ] Accept all cookies - preferences saved
- [ ] Reject optional cookies - only essential cookies set
- [ ] Customize cookies - granular control works

**Privacy Dashboard:**
- [ ] Login and visit `/privacy-dashboard`
- [ ] View data summary (quiz results, conversations, etc.)
- [ ] Toggle privacy settings
- [ ] Export data - JSON file downloads
- [ ] Request account deletion - email sent

**Account Deletion:**
- [ ] Request deletion - receive email with token
- [ ] Submit token - account marked for deletion
- [ ] Verify soft delete (30-day retention)

**Rate Limiting:**
- [ ] Make 6 export requests - 6th should be rate limited (429)
- [ ] Make 4 deletion requests - 4th should be rate limited (429)
- [ ] Verify rate limits reset after window

### 2. Monitor Logs

```bash
# View application logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=allms" \
    --limit 50 \
    --format json

# Filter for GDPR operations
gcloud logging read "resource.type=cloud_run_revision AND jsonPayload.message=~'GDPR'" \
    --limit 50

# Check for errors
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" \
    --limit 50
```

### 3. Verify Audit Logs

```bash
# Check Firestore audit_logs collection
# Should contain entries for:
# - consent_granted
# - consent_revoked
# - data_export
# - account_deleted
```

### 4. Test Email Delivery

```bash
# Request account deletion
# Verify email is received
# Check email content and token format
# Verify token expiration (30 minutes)
```

## Monitoring & Alerting

### Set Up Monitoring

```bash
# Create uptime check
gcloud monitoring uptime-checks create https-check \
    --display-name="ALLMS GDPR Endpoints" \
    --resource-type=uptime-url \
    --host=your-domain.com \
    --path=/health

# Create alert policy for rate limit errors
gcloud alpha monitoring policies create \
    --notification-channels=YOUR_CHANNEL_ID \
    --display-name="High Rate Limit Errors" \
    --condition-display-name="Rate limit 429 errors" \
    --condition-threshold-value=10 \
    --condition-threshold-duration=300s
```

### Key Metrics to Monitor

1. **Rate Limit Hits**
   - Metric: HTTP 429 responses
   - Alert: > 100 per hour
   - Action: Investigate potential abuse

2. **Data Export Requests**
   - Metric: `/api/gdpr/export` requests
   - Alert: > 1000 per day
   - Action: Check for unusual patterns

3. **Account Deletions**
   - Metric: `/api/gdpr/delete` requests
   - Alert: > 50 per day
   - Action: Investigate spike

4. **Token Validation Failures**
   - Metric: Invalid token errors
   - Alert: > 20 per hour
   - Action: Check for attack attempts

5. **Redis Connection Errors**
   - Metric: Redis connection failures
   - Alert: Any failure
   - Action: Check Redis health

## Rollback Plan

If issues are detected:

### Quick Rollback

```bash
# Rollback to previous revision
gcloud run services update-traffic allms \
    --to-revisions=PREVIOUS_REVISION=100 \
    --region us-central1
```

### Disable GDPR Features

```bash
# Set environment variable to disable GDPR
gcloud run services update allms \
    --set-env-vars GDPR_ENABLED=false \
    --region us-central1
```

### Emergency Fixes

1. **Rate limiting not working:**
   - Switch to in-memory: `RATE_LIMIT_BACKEND=memory`
   - Fix Redis connection
   - Redeploy with Redis

2. **Email not sending:**
   - Switch to console: `EMAIL_SERVICE_PROVIDER=console`
   - Check logs for email content
   - Fix email service configuration

3. **Token validation failing:**
   - Check `GDPR_TOKEN_SECRET` is set correctly
   - Verify secret hasn't changed
   - Check token expiration times

## Maintenance

### Regular Tasks

**Daily:**
- [ ] Check error logs
- [ ] Monitor rate limit hits
- [ ] Review deletion requests

**Weekly:**
- [ ] Review audit logs
- [ ] Check Redis memory usage
- [ ] Verify email delivery

**Monthly:**
- [ ] Review GDPR metrics
- [ ] Update documentation
- [ ] Test disaster recovery

**Quarterly:**
- [ ] Rotate `GDPR_TOKEN_SECRET`
- [ ] Review and update privacy policy
- [ ] Audit GDPR compliance

### Secret Rotation

```bash
# Generate new secret
NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Create new version in Secret Manager
echo -n "$NEW_SECRET" | gcloud secrets versions add gdpr-token-secret --data-file=-

# Update Cloud Run to use new version
gcloud run services update allms \
    --update-secrets GDPR_TOKEN_SECRET=gdpr-token-secret:latest \
    --region us-central1

# Keep old version for 30 minutes grace period
# Then delete old version
gcloud secrets versions destroy OLD_VERSION --secret gdpr-token-secret
```

## Troubleshooting

### Common Issues

**Issue: Cookie consent banner not appearing**
- Check: `/static/js/cookie-consent.js` is loaded
- Check: No JavaScript errors in console
- Check: localStorage is enabled

**Issue: Rate limiting not working**
- Check: `RATE_LIMIT_BACKEND` is set to `redis`
- Check: Redis connection is working
- Check: Redis credentials are correct

**Issue: Email not sending**
- Check: `EMAIL_SERVICE_PROVIDER` is configured
- Check: Email service credentials are correct
- Check: Email service is not rate limiting

**Issue: Token validation failing**
- Check: `GDPR_TOKEN_SECRET` is set
- Check: Token hasn't expired (30 minutes)
- Check: Token format is correct

## Support

For issues or questions:
- **Technical:** dev@allms.example.com
- **Security:** security@allms.example.com
- **Privacy:** privacy@allms.example.com
- **DPO:** dpo@allms.example.com

## Related Documentation

- [GDPR Implementation Guide](GDPR_IMPLEMENTATION.md)
- [Environment Variables](ENVIRONMENT_VARIABLES.md)
- [Rate Limiting Guide](GDPR_RATE_LIMITING.md)

