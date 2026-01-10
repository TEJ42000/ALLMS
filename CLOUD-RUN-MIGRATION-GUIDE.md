# 🚀 LLS Study Portal - Google Cloud Run Migration Guide

## 📋 Overview

**From:** Client-side HTML file with direct Anthropic API calls
**To:** Python web application on Google Cloud Run with server-side API management

---

## 🏗️ Architecture

### Current Architecture (Client-Side)
```
Browser
  ├── HTML/CSS/JavaScript
  ├── User's API Key in localStorage
  └── Direct calls to Anthropic API
```

### New Architecture (Server-Side)
```
User's Browser
  ↓
Google Cloud Run (Python Flask/FastAPI)
  ├── Frontend (HTML/CSS/JS served by Python)
  ├── Backend API endpoints
  ├── Session management
  └── Server-side Anthropic API calls
      ↓
Anthropic API (your API key stored securely)
```

---

## 🛠️ Technology Stack

### Backend
- **Framework:** Flask or FastAPI (recommend FastAPI for modern async support)
- **Python Version:** 3.11+
- **API Client:** `anthropic` Python SDK
- **Session Management:** Flask-Session or JWT tokens

### Frontend
- **Keep existing:** HTML/CSS/JavaScript
- **Update:** Remove client-side API calls, use fetch() to your backend

### Deployment
- **Platform:** Google Cloud Run
- **Container:** Docker
- **Secrets:** Google Cloud Secret Manager for API keys

### Optional Enhancements
- **Database:** Google Cloud Firestore or PostgreSQL (Cloud SQL)
- **Authentication:** Google OAuth 2.0 or Firebase Auth
- **Caching:** Redis (Cloud Memorystore)
- **Storage:** Google Cloud Storage for user files

---

## 📁 Project Structure

```
lls-study-portal/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI/Flask app entry point
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── ai_tutor.py        # AI tutor endpoints
│   │   ├── assessment.py      # AI assessment endpoints
│   │   ├── practice.py        # Practice/quiz endpoints
│   │   └── pages.py           # Page rendering endpoints
│   ├── services/
│   │   ├── __init__.py
│   │   ├── anthropic_client.py # Anthropic API wrapper
│   │   └── formatters.py      # Markdown formatting
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py         # Pydantic models for API
│   └── static/
│       ├── css/
│       │   └── styles.css     # Your existing styles
│       ├── js/
│       │   └── app.js         # Frontend JavaScript
│       └── images/
├── templates/
│   ├── base.html              # Base template
│   ├── index.html             # Main portal page
│   └── components/            # Reusable HTML components
├── tests/
│   ├── test_ai_tutor.py
│   └── test_assessment.py
├── .env.example               # Environment variables template
├── .gitignore
├── .dockerignore
├── Dockerfile                 # Container definition
├── requirements.txt           # Python dependencies
├── cloudbuild.yaml           # Cloud Build config (optional)
└── README.md
```

---

## 🔧 Technology Choice: FastAPI vs Flask

### FastAPI (Recommended)
**Pros:**
- Modern async/await support (better for AI API calls)
- Automatic API documentation (Swagger UI)
- Built-in data validation (Pydantic)
- Better performance
- Type hints throughout

**Cons:**
- Slightly steeper learning curve
- More "opinionated" structure

### Flask
**Pros:**
- Simpler, more flexible
- Larger ecosystem
- Easier to learn
- More tutorials available

**Cons:**
- No built-in async support (need extensions)
- Manual validation required
- No automatic API docs

**Recommendation:** Use **FastAPI** for this project - the async support is perfect for AI API calls.

---

## 📝 Migration Steps

### Phase 1: Local Development Setup (Week 1)

#### Step 1.1: Create Project Structure
```bash
mkdir lls-study-portal
cd lls-study-portal

# Create directory structure
mkdir -p app/routes app/services app/models app/static/css app/static/js templates tests

# Initialize git
git init
```

#### Step 1.2: Set Up Python Environment
```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install fastapi uvicorn anthropic python-dotenv pydantic jinja2 python-multipart
pip freeze > requirements.txt
```

#### Step 1.3: Create Basic FastAPI App
See `FASTAPI-STARTER.py` file for complete starter code.

#### Step 1.4: Migrate Frontend
- Copy HTML structure to Jinja2 templates
- Move CSS to static/css/
- Update JavaScript to call your backend API instead of Anthropic directly
- Remove API key input (now server-side)

---

### Phase 2: Backend Development (Week 1-2)

#### Step 2.1: Implement AI Tutor Endpoints
```python
# app/routes/ai_tutor.py

from fastapi import APIRouter, HTTPException
from app.services.anthropic_client import get_ai_response
from app.models.schemas import ChatMessage, ChatResponse

router = APIRouter(prefix="/api/tutor", tags=["AI Tutor"])

@router.post("/chat", response_model=ChatResponse)
async def chat_with_tutor(message: ChatMessage):
    """Send message to AI tutor and get formatted response"""
    try:
        response = await get_ai_response(
            message.content,
            context=message.context,
            conversation_history=message.history
        )
        return ChatResponse(
            content=response,
            status="success"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

#### Step 2.2: Implement Assessment Endpoints
```python
# app/routes/assessment.py

@router.post("/assess", response_model=AssessmentResponse)
async def assess_answer(submission: AssessmentSubmission):
    """Grade student answer with AI"""
    prompt = build_assessment_prompt(
        topic=submission.topic,
        question=submission.question,
        answer=submission.answer
    )
    
    response = await get_ai_response(prompt)
    
    return AssessmentResponse(
        grade=extract_grade(response),
        feedback=response,
        status="success"
    )
```

#### Step 2.3: Create Anthropic Service
See `ANTHROPIC-SERVICE.py` for complete implementation.

---

### Phase 3: Containerization (Week 2)

#### Step 3.1: Create Dockerfile
See `DOCKERFILE` template below.

#### Step 3.2: Create .dockerignore
```
__pycache__
*.pyc
*.pyo
*.pyd
.Python
venv/
.env
.git
.gitignore
*.md
tests/
.pytest_cache
.coverage
```

#### Step 3.3: Test Locally with Docker
```bash
# Build image
docker build -t lls-study-portal .

# Run container locally
docker run -p 8080:8080 \
  -e ANTHROPIC_API_KEY="your-key-here" \
  lls-study-portal

# Visit http://localhost:8080
```

---

### Phase 4: Google Cloud Setup (Week 2-3)

#### Step 4.1: Install Google Cloud CLI
```bash
# Install gcloud CLI
# Visit: https://cloud.google.com/sdk/docs/install

# Login
gcloud auth login

# Set project
gcloud config set project YOUR_PROJECT_ID
```

#### Step 4.2: Enable Required APIs
```bash
gcloud services enable run.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable cloudbuild.googleapis.com
```

#### Step 4.3: Store API Key in Secret Manager
```bash
# Create secret
echo -n "your-anthropic-api-key" | \
  gcloud secrets create anthropic-api-key \
  --data-file=-

# Verify
gcloud secrets versions access latest --secret=anthropic-api-key
```

---

### Phase 5: Deployment to Cloud Run (Week 3)

#### Step 5.1: Build and Deploy
```bash
# Option A: Using Cloud Build (recommended)
# NOTE: This deploy is private by default. Add --allow-unauthenticated only if you intentionally want public access.
gcloud run deploy lls-study-portal \
  --source . \
  --region us-central1 \
  --platform managed \
  --no-allow-unauthenticated \
  --set-secrets=ANTHROPIC_API_KEY=anthropic-api-key:latest \
  --memory 1Gi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10

# Option B: Build locally and push
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/lls-study-portal

gcloud run deploy lls-study-portal \
  --image gcr.io/YOUR_PROJECT_ID/lls-study-portal \
  --region us-central1 \
  --platform managed
```

#### Step 5.2: Configure Custom Domain (Optional)
```bash
# Map custom domain
gcloud run domain-mappings create \
  --service lls-study-portal \
  --domain lls.yourdomain.com \
  --region us-central1
```

---

### Phase 6: Optional Enhancements (Week 3+)

#### 6.1: Add Database (Firestore)
```python
from google.cloud import firestore

db = firestore.Client()

# Save user progress
def save_progress(user_id: str, data: dict):
    db.collection('users').document(user_id).set(data, merge=True)
```

#### 6.2: Add Authentication
```python
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    # Verify token
    return user
```

#### 6.3: Add Caching
```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_cached_article(article_number: str):
    # Cache frequently accessed articles
    return article_data
```

---

## 💰 Cost Estimation

### Cloud Run Costs (Approximate)
- **Free tier:** 2 million requests/month
- **After free tier:** ~$0.40 per million requests
- **Memory:** ~$0.0000025 per GB-second
- **CPU:** ~$0.00002400 per vCPU-second

### Typical Usage Cost
- **Low usage** (100 requests/day): FREE
- **Medium usage** (1000 requests/day): ~$5-10/month
- **High usage** (10000 requests/day): ~$30-50/month

### Additional Costs
- **Anthropic API:** Based on your usage
- **Secret Manager:** First 6 secrets free, then $0.06/secret/month
- **Firestore** (if used): Free tier: 1GB storage, 50K reads/day
- **Container Registry:** $0.026 per GB/month

**Total estimated cost for moderate usage: $10-30/month** (excluding Anthropic API costs)

---

## 🔒 Security Best Practices

### 1. API Key Management
```python
# ❌ NEVER do this
API_KEY = "sk-ant-1234567890"

# ✅ Always do this
import os
API_KEY = os.getenv("ANTHROPIC_API_KEY")
```

### 2. Use Secret Manager
```python
from google.cloud import secretmanager

def get_secret(secret_id: str) -> str:
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")
```

### 3. Rate Limiting
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/tutor/chat")
@limiter.limit("10/minute")
async def chat_endpoint():
    pass
```

### 4. Input Validation
```python
from pydantic import BaseModel, validator

class ChatMessage(BaseModel):
    content: str
    
    @validator('content')
    def content_length(cls, v):
        if len(v) > 5000:
            raise ValueError('Message too long')
        return v
```

---

## 🧪 Testing Strategy

### Unit Tests
```python
# tests/test_ai_tutor.py
import pytest
from app.services.anthropic_client import get_ai_response

@pytest.mark.asyncio
async def test_ai_response():
    response = await get_ai_response("Explain Art. 6:74 DCC")
    assert len(response) > 0
    assert "Art. 6:74" in response
```

### Integration Tests
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_chat_endpoint():
    response = client.post("/api/tutor/chat", json={
        "content": "What is consensus?",
        "context": "Private Law"
    })
    assert response.status_code == 200
    assert "consensus" in response.json()["content"].lower()
```

---

## 📚 Next Steps for Development

### Immediate (Use with Augment Code)
1. **Copy starter templates** (provided in next files)
2. **Set up local development** environment
3. **Create basic FastAPI app** with one endpoint
4. **Test locally** with Docker
5. **Deploy to Cloud Run** for first time

### Short-term (Week 1-2)
1. Migrate all AI endpoints
2. Convert frontend to use new API
3. Add error handling
4. Implement logging
5. Write tests

### Medium-term (Week 2-4)
1. Add user authentication
2. Implement database for progress tracking
3. Add caching layer
4. Set up CI/CD pipeline
5. Custom domain configuration

### Long-term (Month 2+)
1. Advanced analytics
2. Multi-language support
3. Mobile app (React Native/Flutter)
4. Admin dashboard
5. A/B testing framework

---

## 🎯 Development Workflow with Augment Code

### 1. Initial Setup Prompts for Augment
```
"Create a FastAPI application structure for an educational law study portal 
with AI tutoring capabilities. Include routes for AI chat, assessment grading, 
and practice questions. Set up proper async handling for Anthropic API calls."
```

### 2. Endpoint Development Prompts
```
"Create a POST endpoint /api/tutor/chat that accepts a message and context, 
calls the Anthropic API with Claude Sonnet 4, and returns a formatted response. 
Include proper error handling and rate limiting."
```

### 3. Frontend Migration Prompts
```
"Convert this HTML page to a Jinja2 template that works with FastAPI. 
Update the JavaScript to call backend API endpoints instead of direct 
Anthropic API calls. Maintain all existing visual formatting."
```

---

## 📋 Checklist for Migration

### Pre-Development
- [ ] Set up Google Cloud account
- [ ] Create new project in GCP
- [ ] Enable billing
- [ ] Install gcloud CLI
- [ ] Get Anthropic API key ready

### Development
- [ ] Create project structure
- [ ] Set up Python virtual environment
- [ ] Install dependencies
- [ ] Create FastAPI app skeleton
- [ ] Implement AI tutor endpoint
- [ ] Implement assessment endpoint
- [ ] Migrate frontend to Jinja2
- [ ] Update JavaScript for backend API calls
- [ ] Add error handling
- [ ] Write basic tests

### Containerization
- [ ] Create Dockerfile
- [ ] Create .dockerignore
- [ ] Build Docker image locally
- [ ] Test container locally
- [ ] Verify all features work in container

### Deployment
- [ ] Enable Cloud Run API
- [ ] Enable Secret Manager API
- [ ] Store API key in Secret Manager
- [ ] Deploy to Cloud Run
- [ ] Test deployed application
- [ ] Set up custom domain (optional)
- [ ] Configure monitoring

### Post-Deployment
- [ ] Set up logging
- [ ] Configure alerts
- [ ] Document API endpoints
- [ ] Create user guide
- [ ] Plan for scaling

---

## 🚀 Ready to Start?

I'll provide you with:
1. **Complete starter code** for FastAPI app
2. **Dockerfile** template
3. **Frontend migration** example
4. **Anthropic service** implementation
5. **Deployment scripts**

These will be perfect for use with Augment Code and Claude Sonnet 4!

Would you like me to generate all the starter code files now?
