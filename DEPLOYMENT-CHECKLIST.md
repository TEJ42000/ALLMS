# 🚀 Deployment Checklist for LLS Study Portal

## ✅ Pre-Deployment Checklist

### 1. Authentication & Setup
- [ ] Authenticate with Google Cloud
  ```bash
  gcloud auth login
  ```
- [ ] Set the correct project
  ```bash
  gcloud config set project vigilant-axis-483119-r8
  ```
- [ ] Verify project is set
  ```bash
  gcloud config get-value project
  ```

### 2. API Keys & Secrets
- [ ] Get Anthropic API key from Secret Manager
  ```bash
  gcloud secrets versions access latest --secret=anthropic-api-key --project=vigilant-axis-483119-r8
  ```
- [ ] Update `.env` file with the API key (for local testing)
- [ ] Verify secret exists in Secret Manager
  ```bash
  gcloud secrets describe anthropic-api-key
  ```

### 3. Enable Required APIs
- [ ] Enable Cloud Run API
  ```bash
  gcloud services enable run.googleapis.com
  ```
- [ ] Enable Secret Manager API
  ```bash
  gcloud services enable secretmanager.googleapis.com
  ```
- [ ] Enable Cloud Build API
  ```bash
  gcloud services enable cloudbuild.googleapis.com
  ```

### 4. Local Testing (Optional but Recommended)
- [ ] Install dependencies
  ```bash
  source .venv/bin/activate
  pip install -r requirements.txt
  ```
- [ ] Run locally
  ```bash
  uvicorn app.main:app --reload --port 8080
  ```
- [ ] Test endpoints:
  - [ ] http://localhost:8080 (main page)
  - [ ] http://localhost:8080/health (health check)
  - [ ] http://localhost:8080/api/docs (API documentation)
- [ ] Test AI Tutor functionality
- [ ] Test Assessment functionality

### 5. Commit & Push Changes
- [ ] Commit all changes
  ```bash
  git add -A
  git commit -m "Ready for deployment"
  ```
- [ ] Push to GitHub
  ```bash
  git push origin main
  ```

## 🚀 Deployment Steps

### Option A: Automated Deployment (Recommended)

```bash
chmod +x deploy.sh
./deploy.sh
```

### Option B: Manual Deployment

1. **Deploy to Cloud Run**
   ```bash
   # NOTE: This deploy is private by default. Add --allow-unauthenticated only if you intentionally want public access.
   gcloud run deploy lls-study-portal \
     --source . \
     --region europe-west4 \
     --platform managed \
     --no-allow-unauthenticated \
     --set-secrets=ANTHROPIC_API_KEY=anthropic-api-key:latest \
     --memory 1Gi \
     --cpu 1 \
     --min-instances 0 \
     --max-instances 10 \
     --timeout 300 \
     --port 8080
   ```

2. **Wait for deployment** (this may take 5-10 minutes)

3. **Get service URL**
   ```bash
   gcloud run services describe lls-study-portal \
     --region europe-west4 \
     --format 'value(status.url)'
   ```

## ✅ Post-Deployment Verification

### 1. Test the Deployed Service
- [ ] Visit the service URL
- [ ] Check health endpoint: `https://your-service-url/health`
- [ ] Test API docs: `https://your-service-url/api/docs`
- [ ] Test AI Tutor chat
- [ ] Test Assessment grading

### 2. Monitor Logs
```bash
gcloud run services logs read lls-study-portal \
  --region europe-west4 \
  --limit 50
```

### 3. Check Service Status
```bash
gcloud run services describe lls-study-portal \
  --region europe-west4
```

### 4. Test Performance
- [ ] Check response times
- [ ] Verify cold start time (first request)
- [ ] Test concurrent requests

## 🔧 Troubleshooting

### If deployment fails:

1. **Check build logs**
   ```bash
   gcloud builds list --limit 5
   gcloud builds log [BUILD_ID]
   ```

2. **Check service logs**
   ```bash
   gcloud run services logs read lls-study-portal --region europe-west4 --limit 100
   ```

3. **Verify secret access**
   ```bash
   gcloud secrets describe anthropic-api-key
   gcloud secrets get-iam-policy anthropic-api-key
   ```

4. **Common issues:**
   - **Secret not found**: Create the secret first
   - **Permission denied**: Grant Cloud Run service account access to secrets
   - **Build timeout**: Increase timeout or optimize Dockerfile
   - **Import errors**: Check all imports use `app.` prefix

### Grant Secret Access to Cloud Run

If you get permission errors:

```bash
# Get the service account email
SERVICE_ACCOUNT=$(gcloud run services describe lls-study-portal \
  --region europe-west4 \
  --format 'value(spec.template.spec.serviceAccountName)')

# Grant access to the secret
gcloud secrets add-iam-policy-binding anthropic-api-key \
  --member="serviceAccount:${SERVICE_ACCOUNT}" \
  --role="roles/secretmanager.secretAccessor"
```

## 📊 Monitoring & Maintenance

### View Metrics
```bash
# Open Cloud Console
gcloud run services describe lls-study-portal --region europe-west4
```

### Update Service
```bash
# Redeploy with changes
gcloud run deploy lls-study-portal \
  --source . \
  --region europe-west4
```

### Scale Configuration
```bash
# Update scaling
gcloud run services update lls-study-portal \
  --region europe-west4 \
  --min-instances 1 \
  --max-instances 20
```

## 🎉 Success Criteria

- [ ] Service is deployed and accessible
- [ ] Health check returns `{"status": "healthy"}`
- [ ] Main page loads correctly
- [ ] AI Tutor responds to questions
- [ ] Assessment grading works
- [ ] No errors in logs
- [ ] Response time < 2 seconds (after cold start)

## 📝 Notes

- **Cold Start**: First request may take 10-30 seconds
- **Region**: europe-west4 (Netherlands) for EU data residency
- **Costs**: Pay-per-use, ~$0.00002400 per request
- **Scaling**: Auto-scales from 0 to 10 instances
- **Timeout**: 300 seconds (5 minutes) for long-running requests

## 🔗 Useful Links

- [Cloud Run Console](https://console.cloud.google.com/run?project=vigilant-axis-483119-r8)
- [Secret Manager Console](https://console.cloud.google.com/security/secret-manager?project=vigilant-axis-483119-r8)
- [Cloud Build History](https://console.cloud.google.com/cloud-build/builds?project=vigilant-axis-483119-r8)
- [Logs Explorer](https://console.cloud.google.com/logs?project=vigilant-axis-483119-r8)

