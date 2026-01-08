# Deploy to Production - Public Access

**Goal:** Deploy fully operational website accessible to anyone  
**Time:** 30-40 minutes  
**Result:** Live website at Cloud Run URL

---

## 🚀 Deployment Steps

### Step 1: Authenticate with Google Cloud (2 min)

```bash
# Login to Google Cloud
gcloud auth login

# Set the project
gcloud config set project vigilant-axis-483119-r8

# Verify authentication
gcloud config list
```

**Expected Output:**
```
[core]
account = your-email@mgms.eu
project = vigilant-axis-483119-r8
```

---

### Step 2: Verify Anthropic API Key (2 min)

```bash
# Check if secret exists
gcloud secrets describe anthropic-api-key
```

**If secret exists:** ✅ Continue to Step 3

**If secret doesn't exist:** Create it:
```bash
# You'll be prompted to enter your API key
echo -n "YOUR_ANTHROPIC_API_KEY" | gcloud secrets create anthropic-api-key --data-file=-
```

---

### Step 3: Deploy to Cloud Run (20-25 min)

```bash
# Navigate to project directory
cd /Users/matejmonteleone/PycharmProjects/LLMRMS

# Deploy with public access (no authentication required)
./deploy.sh
```

**What happens:**
1. Enables required GCP APIs (Cloud Run, Secret Manager, Cloud Build)
2. Builds Docker container from source
3. Deploys to Cloud Run in europe-west4
4. Configures auto-scaling (0-10 instances)
5. Sets environment variables (AUTH_ENABLED=false)
6. Makes service publicly accessible

**Expected Output:**
```
========================================
Deployment Complete!
========================================

Service URL: https://lls-study-portal-xxxxx-ew.a.run.app

Next steps:
  1. Visit your app at: https://lls-study-portal-xxxxx-ew.a.run.app
  2. Test the API docs: https://lls-study-portal-xxxxx-ew.a.run.app/api/docs
  📊 Monitor logs: gcloud run services logs read lls-study-portal --region europe-west4
```

---

### Step 4: Test the Deployment (5-10 min)

#### 4.1: Visit the Website

Open the Service URL in your browser:
```
https://lls-study-portal-xxxxx-ew.a.run.app
```

**Expected:** Homepage loads with navigation tabs

#### 4.2: Test Upload Flow

1. **Click "Upload" tab**
   - Should see upload interface

2. **Upload a PDF file**
   - Drag & drop or click to browse
   - Any PDF with text content
   - Wait for upload to complete

3. **Wait for Analysis**
   - Should see "Analyzing..." message
   - Wait 20-30 seconds
   - Should see analysis results:
     - Main topics
     - Key concepts
     - Difficulty score
     - Recommended study methods

4. **Generate Quiz**
   - Click "Generate Quiz" button
   - Wait 10-20 seconds
   - Should automatically switch to Quiz tab
   - Should see 10 questions

5. **Generate Flashcards**
   - Return to Upload tab
   - Click "Generate Flashcards" button
   - Wait 10-20 seconds
   - Should automatically switch to Flashcards tab
   - Should see 10-20 flashcards

#### 4.3: Test Other Features

- **AI Tutor:** Click "AI Tutor" tab, ask a question
- **Dashboard:** Click "Dashboard" tab, view stats
- **Badges:** Click "Badges" tab, see achievements

---

### Step 5: Configure Custom Domain (Optional - 10 min)

If you want to use `allms.app` instead of the Cloud Run URL:

```bash
# Map custom domain
gcloud run domain-mappings create \
  --service lls-study-portal \
  --domain allms.app \
  --region europe-west4
```

**Then update DNS:**
- Add CNAME record: `allms.app` → `ghs.googlehosted.com`
- Wait for DNS propagation (5-60 minutes)

---

## 🔧 Troubleshooting

### Issue: "gcloud: command not found"

**Solution:** Install Google Cloud SDK
```bash
# macOS
brew install google-cloud-sdk

# Or download from:
# https://cloud.google.com/sdk/docs/install
```

### Issue: "Permission denied" during deployment

**Solution:** Grant necessary permissions
```bash
# Add Cloud Run Admin role
gcloud projects add-iam-policy-binding vigilant-axis-483119-r8 \
  --member="user:YOUR_EMAIL@mgms.eu" \
  --role="roles/run.admin"

# Add Service Account User role
gcloud projects add-iam-policy-binding vigilant-axis-483119-r8 \
  --member="user:YOUR_EMAIL@mgms.eu" \
  --role="roles/iam.serviceAccountUser"
```

### Issue: "Secret not found"

**Solution:** Create the Anthropic API key secret
```bash
echo -n "YOUR_ANTHROPIC_API_KEY" | gcloud secrets create anthropic-api-key --data-file=-
```

### Issue: Upload fails with "CSRF error"

**Solution:** Update ALLOWED_ORIGINS
```bash
# Get your Cloud Run URL
SERVICE_URL=$(gcloud run services describe lls-study-portal --region europe-west4 --format 'value(status.url)')

# Redeploy with correct origin
gcloud run services update lls-study-portal \
  --region europe-west4 \
  --set-env-vars="ALLOWED_ORIGINS=${SERVICE_URL}"
```

### Issue: "Analysis failed"

**Possible causes:**
1. Anthropic API key not set correctly
2. File too large (>25MB)
3. File format not supported

**Check logs:**
```bash
gcloud run services logs read lls-study-portal --region europe-west4 --limit 50
```

---

## 📊 Post-Deployment Checklist

### Immediate Testing
- [ ] Website loads
- [ ] Upload works
- [ ] Analysis completes
- [ ] Quiz generation works
- [ ] Flashcard generation works
- [ ] AI Tutor works
- [ ] No errors in browser console

### Configuration
- [ ] Custom domain configured (optional)
- [ ] ALLOWED_ORIGINS set correctly
- [ ] Monitoring enabled
- [ ] Logs accessible

### Share with Users
- [ ] Share Cloud Run URL
- [ ] Provide usage instructions
- [ ] Set up support channel

---

## 🎯 What Users Can Do

Once deployed, users can:

1. **Visit the website** (no login required)
2. **Upload course materials** (PDF, DOCX, TXT, etc.)
3. **Get AI analysis** (topics, concepts, difficulty)
4. **Generate quizzes** (10 questions, auto-graded)
5. **Generate flashcards** (10-20 cards, study mode)
6. **Use AI tutor** (chat with Claude about materials)
7. **Submit essays** (get AI grading and feedback)
8. **Track progress** (dashboard with stats)
9. **Earn badges** (gamification system)

**No account required!** Everything works immediately.

---

## 📈 Monitoring

### View Logs
```bash
# Real-time logs
gcloud run services logs tail lls-study-portal --region europe-west4

# Recent logs
gcloud run services logs read lls-study-portal --region europe-west4 --limit 100
```

### View Metrics
```bash
# Open Cloud Console
gcloud run services describe lls-study-portal --region europe-west4
```

Or visit: https://console.cloud.google.com/run?project=vigilant-axis-483119-r8

### Monitor Usage
- **Requests:** Cloud Run metrics
- **Errors:** Cloud Logging
- **Costs:** Cloud Billing

---

## 💰 Cost Estimate

**Cloud Run Pricing (europe-west4):**
- First 2 million requests/month: FREE
- CPU: $0.00002400 per vCPU-second
- Memory: $0.00000250 per GiB-second
- Requests: $0.40 per million requests

**Estimated Monthly Cost:**
- **Low usage** (100 users, 1000 requests/day): ~$5-10/month
- **Medium usage** (500 users, 5000 requests/day): ~$20-30/month
- **High usage** (2000 users, 20000 requests/day): ~$50-100/month

**Anthropic API:**
- Claude Sonnet: $3 per million input tokens, $15 per million output tokens
- Estimated: $10-50/month depending on usage

**Total:** ~$15-150/month depending on usage

---

## 🚀 Ready to Deploy?

### Quick Start (Copy & Paste)

```bash
# 1. Authenticate
gcloud auth login
gcloud config set project vigilant-axis-483119-r8

# 2. Navigate to project
cd /Users/matejmonteleone/PycharmProjects/LLMRMS

# 3. Deploy
./deploy.sh

# 4. Wait for deployment (20-25 minutes)

# 5. Visit the URL shown in output
```

---

## ✅ Success Criteria

**Deployment successful if:**
- ✅ Cloud Run service shows "Serving"
- ✅ Service URL is accessible
- ✅ Homepage loads without errors
- ✅ Upload works
- ✅ Quiz generation works
- ✅ Flashcard generation works

**You're live!** 🎉

---

## 📞 Need Help?

**Check logs:**
```bash
gcloud run services logs read lls-study-portal --region europe-west4 --limit 50
```

**Check service status:**
```bash
gcloud run services describe lls-study-portal --region europe-west4
```

**Redeploy if needed:**
```bash
./deploy.sh
```

---

**Ready?** Run the commands in "Quick Start" above and you'll have a live website in 30 minutes!

