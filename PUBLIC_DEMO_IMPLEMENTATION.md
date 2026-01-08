# Public Demo Implementation Plan

## Status: IN PROGRESS - Day 1 Complete

**Goal:** Create publicly accessible demo at `demo.allms.app`  
**Timeline:** 2-3 days  
**Current Progress:** 40% complete

---

## ✅ Day 1: Core Integration (COMPLETE)

### Task 1.1: Upload → Quiz/Flashcard Integration ✅
**Status:** COMPLETE  
**Commit:** `a593fd7`  
**Time:** 2 hours

**Implemented:**
- ✅ `generateQuiz()` - Calls existing quiz API with analysis context
- ✅ `generateFlashcards()` - Calls existing flashcard API with analysis context
- ✅ Intelligent difficulty selection based on analysis
- ✅ Optimal flashcard count calculation (2 per concept, max 20)
- ✅ Seamless tab switching
- ✅ Loading and success/error notifications
- ✅ Integration with existing display functions

**Testing Required:**
- [ ] Upload PDF and generate quiz
- [ ] Upload PDF and generate flashcards
- [ ] Verify quiz appears in Quiz tab
- [ ] Verify flashcards appear in Flashcards tab
- [ ] Test error handling

---

## 🔄 Day 1 Remaining: Sample Content (4-6 hours)

### Task 1.2: Create Demo Course

**Objective:** Create "Introduction to Contract Law" demo course with sample materials

#### Step 1: Create Course in Firestore (30 min)

```python
# scripts/create_demo_course.py

from google.cloud import firestore
from datetime import datetime

db = firestore.Client()

demo_course = {
    "id": "DEMO-CONTRACT-LAW-2026",
    "name": "Introduction to Contract Law",
    "description": "A comprehensive introduction to contract law principles, covering formation, performance, and remedies.",
    "instructor": "Demo Instructor",
    "semester": "Demo 2026",
    "active": True,
    "created_at": datetime.utcnow(),
    "weeks": [
        {
            "number": 1,
            "title": "Contract Formation",
            "topics": ["Offer", "Acceptance", "Consideration"]
        },
        {
            "number": 2,
            "title": "Contract Terms",
            "topics": ["Express Terms", "Implied Terms", "Exclusion Clauses"]
        },
        {
            "number": 3,
            "title": "Contract Performance",
            "topics": ["Performance", "Breach", "Remedies"]
        }
    ]
}

db.collection('courses').document(demo_course['id']).set(demo_course)
print(f"Created demo course: {demo_course['id']}")
```

#### Step 2: Find Sample Materials (1 hour)

**Sources for Public Domain Law Content:**
1. **Cornell Law School** - https://www.law.cornell.edu/
2. **Justia** - https://www.justia.com/
3. **Google Scholar** - https://scholar.google.com/
4. **Open Textbook Library** - https://open.umn.edu/opentextbooks/

**Materials Needed:**
- [ ] 3-5 PDFs on contract formation
- [ ] 2-3 PDFs on contract terms
- [ ] 2-3 PDFs on contract performance
- [ ] 1 syllabus document

#### Step 3: Upload Materials via UI (1 hour)

1. Login to application
2. Select demo course
3. Navigate to Upload tab
4. Upload each PDF
5. Wait for analysis to complete
6. Verify analysis results

#### Step 4: Generate Sample Quizzes (1 hour)

For each uploaded material:
1. Click "Generate Quiz"
2. Verify quiz appears
3. Take quiz to completion
4. Save quiz results

**Target:** 5-10 saved quizzes

#### Step 5: Generate Sample Flashcards (1 hour)

For each uploaded material:
1. Click "Generate Flashcards"
2. Verify flashcards appear
3. Study flashcards
4. Mark some as "known"

**Target:** 50-100 flashcards total

#### Step 6: Create Sample User Data (30 min)

```python
# scripts/create_demo_user_data.py

demo_user_stats = {
    "user_id": "demo_user",
    "email": "demo@allms.app",
    "name": "Demo User",
    "stats": {
        "total_quizzes": 8,
        "total_questions": 80,
        "correct_answers": 64,
        "accuracy": 0.80,
        "study_time_minutes": 120,
        "flashcards_studied": 75,
        "flashcards_mastered": 45,
        "uploads": 10,
        "xp": 1250,
        "level": 5
    },
    "badges": [
        {"id": "first_upload", "earned_at": "2026-01-01"},
        {"id": "quiz_master", "earned_at": "2026-01-05"},
        {"id": "flashcard_fan", "earned_at": "2026-01-07"}
    ]
}
```

---

## 📅 Day 2: Demo Mode & Public Access (8 hours)

### Task 2.1: Implement Demo Mode (4 hours)

#### Option A: Demo User Bypass (Simpler)

```python
# app/middleware.py

DEMO_USER = {
    'user_id': 'demo_user',
    'email': 'demo@allms.app',
    'name': 'Demo User',
    'is_demo': True
}

@app.middleware("http")
async def demo_mode_middleware(request: Request, call_next):
    # Check if demo mode path
    if request.url.path.startswith('/demo'):
        request.state.user = DEMO_user
        request.state.is_demo = True
    else:
        # Normal IAP authentication
        # ... existing auth logic
    
    response = await call_next(request)
    return response
```

#### Option B: Separate Demo Instance (Better)

**Deploy Configuration:**
```yaml
# demo-service.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: allms-demo
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: '5'
    spec:
      containers:
      - image: gcr.io/vigilant-axis-483119-r8/allms:latest
        env:
        - name: DEMO_MODE
          value: "true"
        - name: AUTH_ENABLED
          value: "false"
        - name: READ_ONLY_MODE
          value: "true"
```

### Task 2.2: Read-Only Mode (2 hours)

```python
# app/middleware.py

@app.middleware("http")
async def read_only_middleware(request: Request, call_next):
    if os.getenv('READ_ONLY_MODE') == 'true':
        # Allow GET requests
        if request.method == 'GET':
            return await call_next(request)
        
        # Allow specific demo actions
        allowed_paths = [
            '/api/tutor/chat',  # AI tutor
            '/api/assessment/assess',  # Essay grading
            '/api/files/generate-quiz',  # Quiz generation
            '/api/files-content/flashcards',  # Flashcard generation
        ]
        
        if any(request.url.path.startswith(path) for path in allowed_paths):
            return await call_next(request)
        
        # Block all other POST/PUT/DELETE
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            return JSONResponse(
                status_code=403,
                content={"detail": "Demo mode is read-only. Sign up for full access."}
            )
    
    return await call_next(request)
```

### Task 2.3: Auto-Reset Daily (1 hour)

```python
# scripts/reset_demo_data.py

import schedule
import time
from google.cloud import firestore

def reset_demo_data():
    """Reset demo data to initial state."""
    db = firestore.Client()
    
    # Reset demo user stats
    db.collection('users').document('demo_user').set(INITIAL_DEMO_STATS)
    
    # Reset quiz results
    db.collection('quiz_results').where('user_id', '==', 'demo_user').stream()
    # ... delete all
    
    print("Demo data reset complete")

# Run daily at 3 AM UTC
schedule.every().day.at("03:00").do(reset_demo_data)

while True:
    schedule.run_pending()
    time.sleep(60)
```

### Task 2.4: Deploy Demo Instance (1 hour)

```bash
# Deploy to Cloud Run
gcloud run deploy allms-demo \
  --image gcr.io/vigilant-axis-483119-r8/allms:latest \
  --region europe-west4 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars DEMO_MODE=true,AUTH_ENABLED=false,READ_ONLY_MODE=true

# Map custom domain
gcloud run domain-mappings create \
  --service allms-demo \
  --domain demo.allms.app \
  --region europe-west4
```

---

## 📅 Day 3: Landing Page & Polish (4-6 hours)

### Task 3.1: Create Landing Page (3 hours)

```html
<!-- templates/landing.html -->
<!DOCTYPE html>
<html>
<head>
    <title>ALLMS - AI-Powered Learning Management System</title>
    <style>
        /* Modern landing page styles */
    </style>
</head>
<body>
    <header>
        <h1>ALLMS</h1>
        <p>AI-Powered Learning Management System for Legal Education</p>
    </header>
    
    <section class="hero">
        <h2>Transform Your Study Experience</h2>
        <p>Upload course materials, get AI-powered analysis, generate quizzes and flashcards automatically.</p>
        <a href="/demo" class="cta-button">Try Demo</a>
        <a href="/signup" class="cta-button secondary">Sign Up</a>
    </section>
    
    <section class="features">
        <div class="feature">
            <h3>📤 Smart Upload</h3>
            <p>Upload PDFs, DOCX, and more. AI extracts and analyzes content automatically.</p>
        </div>
        <div class="feature">
            <h3>🧠 AI Tutor</h3>
            <p>Chat with Claude AI about your course materials. Get instant answers.</p>
        </div>
        <div class="feature">
            <h3>📝 Auto-Generate Quizzes</h3>
            <p>Generate practice quizzes from your materials with one click.</p>
        </div>
        <div class="feature">
            <h3>🎴 Smart Flashcards</h3>
            <p>Create flashcards automatically from key concepts in your materials.</p>
        </div>
        <div class="feature">
            <h3>📊 Track Progress</h3>
            <p>Monitor your learning with detailed stats and gamification.</p>
        </div>
        <div class="feature">
            <h3>🏆 Earn Badges</h3>
            <p>Stay motivated with achievements and level progression.</p>
        </div>
    </section>
    
    <section class="demo-cta">
        <h2>See It In Action</h2>
        <p>Try our demo with sample contract law materials</p>
        <a href="/demo" class="cta-button large">Launch Demo</a>
    </section>
</body>
</html>
```

### Task 3.2: Polish Demo Experience (2 hours)

- [ ] Add "Demo Mode" banner at top
- [ ] Add "Sign up for full access" prompts
- [ ] Improve loading states
- [ ] Add tooltips and help text
- [ ] Test all features work in demo mode

### Task 3.3: Create Demo Video (1 hour - Optional)

- [ ] Record 2-3 minute walkthrough
- [ ] Upload file → analyze → generate quiz → take quiz
- [ ] Show AI tutor, flashcards, badges
- [ ] Embed on landing page

---

## 📊 Progress Tracking

### Day 1: Core Integration
- [x] Upload → Quiz integration (2 hours)
- [x] Upload → Flashcard integration (included above)
- [ ] Create demo course (30 min)
- [ ] Find sample materials (1 hour)
- [ ] Upload materials (1 hour)
- [ ] Generate sample quizzes (1 hour)
- [ ] Generate sample flashcards (1 hour)
- [ ] Create sample user data (30 min)

**Day 1 Progress:** 40% complete (4/10 tasks)

### Day 2: Demo Mode
- [ ] Implement demo mode (4 hours)
- [ ] Read-only mode (2 hours)
- [ ] Auto-reset (1 hour)
- [ ] Deploy demo instance (1 hour)

**Day 2 Progress:** 0% complete (0/4 tasks)

### Day 3: Landing Page
- [ ] Create landing page (3 hours)
- [ ] Polish demo experience (2 hours)
- [ ] Create demo video (1 hour - optional)

**Day 3 Progress:** 0% complete (0/3 tasks)

---

## 🎯 Next Steps

**Immediate (Next 4-6 hours):**
1. Create demo course in Firestore
2. Find and upload sample materials
3. Generate sample quizzes and flashcards
4. Test upload → quiz/flashcard integration

**Tomorrow (Day 2):**
5. Implement demo mode
6. Deploy demo instance
7. Test public access

**Day After (Day 3):**
8. Create landing page
9. Polish and test
10. Launch! 🚀

---

**Current Status:** Day 1 - 40% complete  
**Next Task:** Create demo course and upload sample materials  
**Estimated Time to Public Demo:** 1.5-2 days

