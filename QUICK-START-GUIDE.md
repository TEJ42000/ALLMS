# 🚀 Quick Start Guide - LLS Study Portal on Google Cloud Run

## 📋 Prerequisites

- [ ] Google Cloud account with billing enabled
- [ ] Anthropic API key
- [ ] Python 3.11+ installed locally
- [ ] Docker installed (for local testing)
- [ ] gcloud CLI installed
- [ ] Augment Code installed
- [ ] Git installed

---

## ⚡ 5-Minute Setup (Local Development)

### Step 1: Create Project
```bash
mkdir lls-study-portal
cd lls-study-portal
git init
```

### Step 2: Copy Starter Files

Copy all files from `starter-code/` directory:
- `app_main.py` → `app/main.py`
- `anthropic_client.py` → `app/services/anthropic_client.py`
- `schemas.py` → `app/models/schemas.py`
- `ai_tutor_routes.py` → `app/routes/ai_tutor.py`
- `assessment_routes.py` → `app/routes/assessment.py`
- `requirements.txt` → root directory
- `Dockerfile` → root directory
- `env.example` → `.env` (and fill in your API key)

### Step 3: Set Up Python Environment
```bash
python3.11 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 4: Configure Environment
```bash
cp env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Step 5: Run Locally
```bash
python -m app.main
# Visit http://localhost:8080/api/docs
```

---

## 🤖 Using Augment Code for Development

### Initial Project Setup with Augment

**Prompt 1: Project Structure**
```
Create a FastAPI project structure for a law study portal with these components:
- app/main.py (FastAPI entry point)
- app/routes/ (AI tutor, assessment, pages)
- app/services/ (Anthropic API client)
- app/models/ (Pydantic schemas)
- templates/ (Jinja2 HTML templates)
- app/static/ (CSS, JS, images)
- tests/ (pytest test files)
- Dockerfile and requirements.txt

Use Python 3.11 and include proper async/await handling.
```

**Prompt 2: Create AI Tutor Endpoint**
```
Create a FastAPI POST endpoint at /api/tutor/chat that:
1. Accepts: { "message": str, "context": str, "conversation_history": list }
2. Calls Anthropic Claude Sonnet 4 API with system prompt for legal tutoring
3. Returns formatted response with visual markdown elements
4. Includes error handling and logging
5. Uses Pydantic models for validation

The system prompt should instruct Claude to use visual formatting like:
- ## headers for sections
- ✅ checkmarks for correct info
- ❌ X marks for errors
- ⚠️ warnings
- Article citations like Art. 6:74 DCC
```

**Prompt 3: Create Assessment Endpoint**
```
Create a FastAPI POST endpoint at /api/assessment/assess that:
1. Accepts: { "topic": str, "question": str (optional), "answer": str }
2. Calls Anthropic API to grade answer out of 10
3. Returns structured feedback with:
   - Grade (0-10)
   - Strengths (✅)
   - Weaknesses (⚠️)
   - Corrections (❌)
   - Improvement steps (STEP 1:, STEP 2:)
4. Extract grade from AI response using regex
5. Include grading rubric in system prompt
```

**Prompt 4: Migrate Frontend**
```
Convert this HTML study portal to use:
1. Jinja2 templates served by FastAPI
2. JavaScript fetch() calls to backend API endpoints instead of direct Anthropic API
3. Keep all existing visual styling and features
4. Remove client-side API key input
5. Add loading states for async API calls

Here's the current HTML: [paste your HTML]
```

**Prompt 5: Create Dockerfile**
```
Create a production-ready Dockerfile for FastAPI app that:
1. Uses Python 3.11-slim base image
2. Installs dependencies from requirements.txt
3. Runs as non-root user
4. Exposes port 8080
5. Uses uvicorn with proper Cloud Run settings
6. Includes health check endpoint
```

---

## 🔧 Development Workflow

### 1. Create New Feature with Augment
```
Example: "Add practice quiz endpoint"

Prompt:
"Create a GET endpoint /api/practice/quiz that returns random law questions
based on topic. Include:
- Question text
- 4 multiple choice options
- Correct answer index
- Explanation
Use Pydantic models and include 10 questions per topic."
```

### 2. Test with Augment
```
Prompt:
"Create pytest tests for the /api/tutor/chat endpoint that:
1. Test successful response
2. Test with invalid input
3. Test with long conversation history
4. Mock the Anthropic API call
Use pytest-asyncio for async tests."
```

### 3. Refactor with Augment
```
Prompt:
"Refactor anthropic_client.py to:
1. Add retry logic with exponential backoff
2. Add caching for repeated questions
3. Add token counting and cost tracking
4. Improve error messages
Keep async/await pattern."
```

---

## 📦 Deployment Workflow

### Option A: Automated Deployment (Recommended)
```bash
# Make script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh
```

### Option B: Manual Deployment
```bash
# 1. Set project
gcloud config set project YOUR_PROJECT_ID

# 2. Enable APIs
gcloud services enable run.googleapis.com
gcloud services enable secretmanager.googleapis.com

# 3. Create secret
echo -n "your-api-key" | \
  gcloud secrets create anthropic-api-key --data-file=-

# 4. Deploy
# NOTE: This deploy is private by default. Add --allow-unauthenticated only if you intentionally want public access.
gcloud run deploy lls-study-portal \
  --source . \
  --region us-central1 \
  --no-allow-unauthenticated \
  --set-secrets=ANTHROPIC_API_KEY=anthropic-api-key:latest
```

---

## 🧪 Testing

### Test Locally with Docker
```bash
# Build
docker build -t lls-portal .

# Run
docker run -p 8080:8080 \
  -e ANTHROPIC_API_KEY="your-key" \
  lls-portal

# Test
curl http://localhost:8080/health
```

### Test Endpoints
```bash
# Health check
curl http://localhost:8080/health

# AI Tutor
curl -X POST http://localhost:8080/api/tutor/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain Art. 6:74 DCC", "context": "Private Law"}'

# Assessment
curl -X POST http://localhost:8080/api/assessment/assess \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "Private Law",
    "answer": "A contract needs consensus."
  }'

# API Docs
open http://localhost:8080/api/docs
```

---

## 📊 Common Augment Prompts

### Database Integration
```
"Add Firestore integration to track user progress:
- Store: questions completed, mock exams taken, average score
- Create UserProgress model
- Add endpoints: GET /api/progress, POST /api/progress
- Use google-cloud-firestore library"
```

### Authentication
```
"Add Google OAuth 2.0 authentication:
- Use FastAPI OAuth2 with JWT tokens
- Protect all /api/* endpoints except /health
- Add user session management
- Create login/logout endpoints"
```

### Caching
```
"Add Redis caching layer:
- Cache AI responses for 1 hour
- Use response message as cache key
- Add cache hit/miss metrics
- Implement cache invalidation strategy"
```

### Rate Limiting
```
"Add rate limiting using slowapi:
- Limit /api/tutor/chat to 10 requests/minute
- Limit /api/assessment/assess to 5 requests/minute
- Return 429 with retry-after header
- Track by IP address"
```

---

## 🎯 Project Milestones

### Week 1: Core Backend
- [x] Set up FastAPI project
- [x] Implement AI tutor endpoint
- [x] Implement assessment endpoint
- [ ] Create basic frontend templates
- [ ] Write unit tests
- [ ] Test locally with Docker

### Week 2: Frontend & Deploy
- [ ] Migrate all HTML to Jinja2
- [ ] Update JavaScript for API calls
- [ ] Add loading states
- [ ] Deploy to Cloud Run
- [ ] Set up custom domain

### Week 3: Enhancements
- [ ] Add user authentication
- [ ] Implement progress tracking (Firestore)
- [ ] Add caching layer
- [ ] Set up monitoring
- [ ] Create admin dashboard

### Week 4: Polish
- [ ] Add analytics
- [ ] Optimize performance
- [ ] Write documentation
- [ ] Create user guide
- [ ] Launch! 🚀

---

## 💡 Tips for Success

### With Augment Code
1. **Be specific**: "Create POST endpoint for X" is better than "Add feature X"
2. **Show examples**: Paste existing code when asking for similar functionality
3. **Iterate**: Start simple, then ask Augment to enhance
4. **Test prompts**: If output isn't right, refine your prompt and try again
5. **Use context**: Reference existing files: "Update ai_tutor.py to add caching"

### With Cloud Run
1. **Start small**: Deploy early, iterate often
2. **Monitor costs**: Check Cloud Run billing dashboard regularly
3. **Use secrets**: Never hardcode API keys
4. **Set limits**: Use min/max instances to control costs
5. **Watch logs**: `gcloud run services logs tail SERVICE_NAME --region REGION`

---

## 🆘 Troubleshooting

### "Module not found" error
```bash
# Make sure you're in venv
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### "API key not set" error
```bash
# Check .env file exists
ls -la .env

# Verify API key is set
cat .env | grep ANTHROPIC_API_KEY
```

### Docker build fails
```bash
# Clear Docker cache
docker system prune -a

# Rebuild
docker build --no-cache -t lls-portal .
```

### Cloud Run deployment fails
```bash
# Check logs
gcloud run services logs read lls-study-portal --region us-central1

# Verify secret exists
gcloud secrets versions access latest --secret=anthropic-api-key
```

---

## 🎉 You're Ready!

You now have everything you need to:
1. ✅ Develop locally with Python/FastAPI
2. ✅ Use Augment Code for AI-assisted development
3. ✅ Test with Docker
4. ✅ Deploy to Google Cloud Run
5. ✅ Scale to thousands of users

**Start with the 5-minute local setup above, then use Augment to build features!**

Questions? Check the full migration guide: `CLOUD-RUN-MIGRATION-GUIDE.md`
