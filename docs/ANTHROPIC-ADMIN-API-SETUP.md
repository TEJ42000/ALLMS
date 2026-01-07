# Anthropic Admin API Setup Guide

This guide explains how to set up the Anthropic Admin API for cost reconciliation in the ALLMS LLS Study Portal.

## Overview

The **Anthropic Admin API** provides official usage and cost data directly from Anthropic's billing system. This allows you to:

- ✅ **Validate** internal tracking accuracy
- ✅ **Reconcile** costs with Anthropic invoices
- ✅ **Audit** LLM usage for compliance
- ✅ **Cross-reference** token counts and costs

## Prerequisites

- **Organization Admin Role** in Anthropic Console
- **Access to Google Cloud Secret Manager** (for storing the API key)
- **Existing ALLMS deployment** with v2.8.0 or later

## Step 1: Create Admin API Key

### 1.1 Log into Anthropic Console

1. Go to [https://console.anthropic.com/](https://console.anthropic.com/)
2. Sign in with your Anthropic account
3. Ensure you have **Admin** role in your organization

### 1.2 Generate Admin API Key

1. Navigate to **Settings** → **API Keys**
2. Click **"Create Key"**
3. Select **"Admin API Key"** (not regular API key)
4. Give it a descriptive name: `ALLMS-Admin-API-Key`
5. Copy the key immediately (starts with `sk-ant-admin...`)

⚠️ **Important**: Admin API keys are different from regular API keys:
- Regular API keys: `sk-ant-api...` (for making Claude API calls)
- Admin API keys: `sk-ant-admin...` (for usage/cost reporting)

## Step 2: Store Key in Secret Manager

### Option A: Using gcloud CLI (Recommended)

```bash
# Set your project ID
export PROJECT_ID=vigilant-axis-483119-r8

# Create the secret
echo -n "sk-ant-admin-YOUR-KEY-HERE" | gcloud secrets create anthropic-admin-api-key \
    --project=$PROJECT_ID \
    --data-file=-

# Verify the secret was created
gcloud secrets describe anthropic-admin-api-key --project=$PROJECT_ID
```

### Option B: Using Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select project: `vigilant-axis-483119-r8`
3. Navigate to **Security** → **Secret Manager**
4. Click **"Create Secret"**
5. Name: `anthropic-admin-api-key`
6. Secret value: Paste your Admin API key
7. Click **"Create"**

### Option C: Local Development (.env file)

For local development only:

```bash
# Add to .env file
ANTHROPIC_ADMIN_API_KEY=sk-ant-admin-YOUR-KEY-HERE
```

## Step 3: Grant Access to Cloud Run Service

The Cloud Run service account needs permission to access the secret:

```bash
# Get the service account email
SERVICE_ACCOUNT=$(gcloud run services describe lls-study-portal \
    --region=europe-west4 \
    --project=$PROJECT_ID \
    --format='value(spec.template.spec.serviceAccountName)')

# Grant access to the secret
gcloud secrets add-iam-policy-binding anthropic-admin-api-key \
    --project=$PROJECT_ID \
    --member="serviceAccount:${SERVICE_ACCOUNT}" \
    --role="roles/secretmanager.secretAccessor"
```

## Step 4: Verify Setup

### 4.1 Check API Endpoint

Once deployed, test the reconciliation endpoint:

```bash
# Get your deployment URL
DEPLOYMENT_URL=$(gcloud run services describe lls-study-portal \
    --region=europe-west4 \
    --project=$PROJECT_ID \
    --format='value(status.url)')

# Test the endpoint (requires @mgms.eu authentication)
curl "${DEPLOYMENT_URL}/api/admin/usage/reconciliation?days=7"
```

### 4.2 Check Dashboard

1. Navigate to `/admin/usage` in your browser
2. Scroll to **"🔄 Anthropic Cross-Reference"** section
3. Verify data is loading correctly
4. Check that variance is within acceptable range (<1%)

## Troubleshooting

### Error: "Anthropic Admin API not configured"

**Cause**: Admin API key not found in Secret Manager

**Solution**:
1. Verify secret exists: `gcloud secrets list --project=$PROJECT_ID | grep anthropic-admin`
2. Check secret name is exactly: `anthropic-admin-api-key`
3. Verify service account has access (see Step 3)

### Error: "API key does not start with 'sk-ant-admin'"

**Cause**: Using regular API key instead of Admin API key

**Solution**:
1. Go back to Anthropic Console
2. Create a new **Admin API Key** (not regular API key)
3. Update the secret with the new key

### Error: "403 Forbidden" from Anthropic API

**Cause**: API key doesn't have admin permissions

**Solution**:
1. Verify your Anthropic account has **Admin** role
2. Regenerate the Admin API key
3. Update Secret Manager with new key

### High Variance Between Internal and Anthropic Data

**Cause**: Possible tracking issues or timing differences

**Investigation Steps**:
1. Check if variance is consistent or sporadic
2. Compare token counts by type (input, output, cache)
3. Verify all API calls are being tracked
4. Check for any failed requests not logged

**Acceptable Variance**:
- **< 0.01%**: Exact match ✅
- **< 1%**: Close match (acceptable) ⚠️
- **> 1%**: Investigate further ❌

## API Endpoints

The following endpoints are available (requires @mgms.eu authentication):

### GET `/api/admin/usage/anthropic/usage`

Fetch token usage from Anthropic.

**Query Parameters**:
- `days` (int): Number of days to query (default: 7, max: 365)

**Response**:
```json
{
  "total_input_tokens": 125000,
  "total_output_tokens": 45000,
  "total_cache_creation_tokens": 30000,
  "total_cache_read_tokens": 50000,
  "total_requests": 150,
  "start_date": "2026-01-01T00:00:00Z",
  "end_date": "2026-01-08T00:00:00Z"
}
```

### GET `/api/admin/usage/anthropic/cost`

Fetch actual costs from Anthropic.

**Query Parameters**:
- `days` (int): Number of days to query (default: 7, max: 365)

**Response**:
```json
{
  "total_cost_usd": 12.345678,
  "start_date": "2026-01-01T00:00:00Z",
  "end_date": "2026-01-08T00:00:00Z"
}
```

### GET `/api/admin/usage/reconciliation`

Compare internal tracking with Anthropic data.

**Query Parameters**:
- `days` (int): Number of days to query (default: 7, max: 365)

**Response**: See ReconciliationReport model in code

## Security Considerations

1. **Admin API keys are sensitive** - They provide access to billing data
2. **Never commit keys to git** - Always use Secret Manager
3. **Rotate keys periodically** - Update every 90 days
4. **Monitor access logs** - Check who's accessing reconciliation endpoints
5. **Restrict to @mgms.eu domain** - Only admins should see cost data

## Cost Implications

- **Usage API calls**: Free (no cost)
- **Cost API calls**: Free (no cost)
- **Recommended polling**: Once per minute maximum
- **Dashboard refresh**: Only on page load (not continuous polling)

## References

- [Anthropic Admin API Documentation](https://docs.anthropic.com/en/api/admin-api)
- [Google Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [ALLMS Authentication Guide](./AUTHENTICATION.md)

