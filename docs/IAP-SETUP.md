# Google Cloud IAP Setup Guide

This guide walks you through configuring Google Cloud Identity-Aware Proxy (IAP) for the LLS Study Portal.

## Prerequisites

- Google Cloud project with billing enabled
- Cloud Run service deployed (`deploy.sh`)
- gcloud CLI installed and authenticated
- Access to Google Workspace admin (for internal user type)

## Overview

IAP provides enterprise-grade security by:
1. Handling OAuth authentication at the infrastructure level
2. Verifying user identity before requests reach your application
3. Forwarding user information via secure headers

## Architecture

```
User → Load Balancer → IAP → Cloud Run → Application
                        ↓
              Google OAuth Login
              Domain Verification
```

## Quick Start

Run the automated setup script:

```bash
./scripts/setup-iap.sh
```

For manual setup, follow the sections below.

---

## Step 1: Configure OAuth Consent Screen

1. Go to [Google Cloud Console > APIs & Services > OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent)

2. Select **Internal** as User Type
   - This restricts access to Google Workspace users only
   - Requires your domain to be a Workspace domain

3. Fill in the app information:
   | Field | Value |
   |-------|-------|
   | App name | LLS Study Portal |
   | User support email | admin@mgms.eu |
   | App logo | (optional) |
   | Application home page | https://your-cloud-run-url |
   | Developer contact email | admin@mgms.eu |

4. Add scopes:
   - `email`
   - `profile`
   - `openid`

5. Save and continue

## Step 2: Create OAuth 2.0 Client ID

1. Go to [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials)

2. Click **+ CREATE CREDENTIALS** > **OAuth client ID**

3. Configure:
   | Field | Value |
   |-------|-------|
   | Application type | Web application |
   | Name | LLS Study Portal IAP |
   | Authorized redirect URIs | (auto-configured by IAP) |

4. Click **Create** and save the Client ID and Secret

5. Store in Secret Manager:
   ```bash
   echo -n "YOUR_CLIENT_ID" | gcloud secrets create oauth-client-id --data-file=-
   echo -n "YOUR_CLIENT_SECRET" | gcloud secrets create oauth-client-secret --data-file=-
   ```

## Step 3: Enable IAP API

```bash
gcloud services enable iap.googleapis.com
```

## Step 4: Set Up Load Balancer (Required for IAP)

IAP requires a Load Balancer in front of Cloud Run. Create a serverless Network Endpoint Group (NEG):

```bash
# Create serverless NEG for Cloud Run
gcloud compute network-endpoint-groups create lls-portal-neg \
    --region=europe-west4 \
    --network-endpoint-type=serverless \
    --cloud-run-service=lls-study-portal

# Create backend service
gcloud compute backend-services create lls-portal-backend \
    --global \
    --load-balancing-scheme=EXTERNAL_MANAGED

# Add NEG to backend
gcloud compute backend-services add-backend lls-portal-backend \
    --global \
    --network-endpoint-group=lls-portal-neg \
    --network-endpoint-group-region=europe-west4

# Create URL map
gcloud compute url-maps create lls-portal-urlmap \
    --default-service=lls-portal-backend

# Create SSL certificate (or use existing)
gcloud compute ssl-certificates create lls-portal-cert \
    --domains=your-domain.com

# Create HTTPS proxy
gcloud compute target-https-proxies create lls-portal-https-proxy \
    --ssl-certificates=lls-portal-cert \
    --url-map=lls-portal-urlmap

# Create forwarding rule
gcloud compute forwarding-rules create lls-portal-forwarding \
    --global \
    --target-https-proxy=lls-portal-https-proxy \
    --ports=443
```

## Step 5: Enable IAP on Backend Service

```bash
gcloud iap web enable \
    --resource-type=backend-services \
    --service=lls-portal-backend
```

## Step 6: Configure Domain Access

Grant access to @mgms.eu domain users:

```bash
gcloud iap web add-iam-policy-binding \
    --resource-type=backend-services \
    --service=lls-portal-backend \
    --member="domain:mgms.eu" \
    --role="roles/iap.httpsResourceAccessor"
```

For individual users (e.g., external guests on allow list):
```bash
gcloud iap web add-iam-policy-binding \
    --resource-type=backend-services \
    --service=lls-portal-backend \
    --member="user:guest@university.edu" \
    --role="roles/iap.httpsResourceAccessor"
```

## Step 7: Update Application Configuration

Set environment variables in Cloud Run:

```bash
gcloud run services update lls-study-portal \
    --region=europe-west4 \
    --set-env-vars="AUTH_ENABLED=true,AUTH_DOMAIN=mgms.eu"
```

---

## Verification

### Check IAP Status

```bash
gcloud iap web get-iam-policy \
    --resource-type=backend-services \
    --service=lls-portal-backend
```

### Test Access

1. Visit your Load Balancer URL (not Cloud Run URL directly)
2. You should see a Google login page
3. Login with @mgms.eu account → Access granted
4. Login with other account → Access denied

### Verify Headers

When IAP is working, your app receives these headers:

| Header | Example |
|--------|---------|
| `X-Goog-Authenticated-User-Email` | `accounts.google.com:user@mgms.eu` |
| `X-Goog-Authenticated-User-Id` | `accounts.google.com:123456789` |
| `X-Goog-IAP-JWT-Assertion` | `<JWT token>` |

---

## Troubleshooting

### "Access Denied" after successful login

- Verify the user's domain is in the IAM policy
- Check if user is part of Google Workspace
- Ensure IAP is using correct OAuth client

### "Invalid Client" error

- Verify OAuth client ID in IAP settings
- Check OAuth consent screen is configured
- Ensure redirect URIs are correct

### Headers not received by application

- Access via Load Balancer URL, not Cloud Run URL
- Check Cloud Run ingress settings
- Verify IAP is the entry point

### 403 Forbidden with correct domain

- Check IAP policy bindings
- Verify user's Workspace status
- Check for typos in domain name

---

## Alternative: Cloud Run Built-in Auth

For simpler setups without Load Balancer, use Cloud Run's built-in auth:

1. Remove `--allow-unauthenticated` from deploy.sh
2. Add IAM bindings directly to Cloud Run:
   ```bash
   gcloud run services add-iam-policy-binding lls-study-portal \
       --region=europe-west4 \
       --member="domain:mgms.eu" \
       --role="roles/run.invoker"
   ```

Note: This doesn't provide user identity headers - only controls access.

---

## Required IAM Roles

The deploying user/service account needs:

| Role | Purpose |
|------|---------|
| `roles/iap.admin` | Configure IAP settings |
| `roles/run.admin` | Manage Cloud Run |
| `roles/compute.admin` | Create Load Balancer |
| `roles/iam.serviceAccountUser` | Act as service account |

---

## References

- [IAP for Cloud Run](https://cloud.google.com/iap/docs/enabling-cloud-run)
- [Serverless NEGs](https://cloud.google.com/load-balancing/docs/negs/serverless-neg-concepts)
- [IAP Signed Headers](https://cloud.google.com/iap/docs/signed-headers-howto)

