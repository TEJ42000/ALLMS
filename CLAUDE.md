# Claude Code Review Instructions

## Project Overview

ALLMS (AI-Powered Learning Management System) is a FastAPI-based web application for legal education. It provides:
- AI-powered tutoring using Anthropic Claude
- Interactive quiz system with saved quizzes and history
- Study guide generation with Mermaid diagrams
- Flashcard generation and study
- Multi-course architecture with Firestore backend
- Document processing and text extraction
- Gamification with badge system
- Essay assessment with AI grading

### Planned Features (In Development)
- **Content Upload & Processing Pipeline** - User-facing upload UI with intelligent content analysis
- **Spaced Repetition System** - SM-2 algorithm for flashcard scheduling
- **AI Podcast Generation** - Two-host conversational podcasts from course content

## Technology Stack

### Current Stack
- **Backend**: Python 3.11+, FastAPI, Uvicorn
- **Frontend**: HTML, CSS, JavaScript (vanilla), Jinja2 templates
- **Database**: Google Cloud Firestore
- **AI**: Anthropic Claude API (claude-sonnet-4-20250514)
- **Document Processing**: PyMuPDF, python-docx, pytesseract, BeautifulSoup
- **Authentication**: Google Cloud IAP
- **Testing**: pytest (Python), Playwright (frontend)
- **Deployment**: Google Cloud Run, Docker

### Planned Additions
- **Text-to-Speech**: ElevenLabs API / Google Cloud TTS (for podcasts)
- **Speech-to-Text**: OpenAI Whisper / Google Cloud STT (for podcast Q&A)
- **Audio Processing**: pydub, ffmpeg (for podcast generation)
- **Real-time**: WebSockets (for upload progress, podcast streaming)

---

## Current File Structure

```
ALLMS/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI entry point, router registration
│   ├── middleware.py                # Authentication middleware
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── ai_tutor.py              # AI chat endpoints
│   │   ├── assessment.py            # Essay grading endpoints
│   │   ├── files_content.py         # Quiz, flashcard, study guide generation
│   │   ├── pages.py                 # HTML page serving
│   │   ├── admin_courses.py         # Course management
│   │   ├── admin_users.py           # User management
│   │   ├── admin_usage.py           # Usage tracking
│   │   ├── quiz_management.py       # Saved quiz CRUD
│   │   ├── study_guide_routes.py    # Saved study guide CRUD
│   │   ├── gamification.py          # Badge system
│   │   ├── echr.py                  # ECHR case law
│   │   └── gdpr.py                  # GDPR compliance
│   ├── services/
│   │   ├── __init__.py
│   │   ├── anthropic_client.py      # Claude API wrapper
│   │   ├── files_api_service.py     # ⭐ Core content generation service
│   │   ├── text_extractor.py        # ⭐ Unified text extraction
│   │   ├── slide_archive.py         # ZIP/slide archive handling
│   │   ├── course_service.py        # Firestore course operations
│   │   ├── auth_service.py          # IAP authentication
│   │   ├── gcp_service.py           # GCP clients (Firestore, Secrets)
│   │   └── usage_tracking_service.py # LLM usage tracking
│   ├── models/
│   │   ├── __init__.py
│   │   ├── schemas.py               # General Pydantic models
│   │   ├── course_models.py         # Course, Week, Material models
│   │   └── usage_models.py          # Usage tracking models
│   └── static/
│       ├── css/
│       │   ├── styles.css           # Main styles
│       │   └── quiz-*.css           # Quiz-specific styles
│       └── js/
│           ├── app.js               # Main application logic
│           ├── gamification-ui.js   # Badge display
│           └── quiz-*.js            # Quiz enhancement modules
├── templates/
│   ├── index.html                   # Main SPA template
│   ├── base.html                    # Base template
│   ├── errors/                      # Error pages (401, 403)
│   └── partials/                    # Reusable components
├── Materials/                       # Course materials (local storage)
│   └── {course_id}/
│       ├── Syllabus/
│       ├── Course_Materials/
│       └── Supplementary_Sources/
├── tests/                           # pytest test files
├── e2e/                             # Playwright E2E tests
├── scripts/                         # Utility scripts
├── docs/                            # Documentation
├── requirements.txt
├── Dockerfile
├── deploy.sh
└── CLAUDE.md                        # This file
```

---

## Existing Services Reference

### FilesAPIService (`app/services/files_api_service.py`)

This is the core service for AI-powered content generation. Key methods:

```python
# Get course materials from Firestore
def get_course_materials(course_id, week_number=None, tier=None) -> List[CourseMaterial]

# Get materials with extracted text content
async def get_course_materials_with_text(course_id, week_number=None) -> List[Tuple[CourseMaterial, str]]

# Generate quiz from course materials
async def generate_quiz_from_course(course_id, topic, num_questions, difficulty, week_number=None) -> Dict

# Generate study guide with Mermaid diagrams
async def generate_study_guide_from_course(course_id, topic, week_numbers=None) -> str

# Generate flashcards from course materials  
async def generate_flashcards_from_course(course_id, topic, num_cards, week_number=None) -> List[Dict]
```

**Important patterns used:**
- Prompt caching with `cache_control: {"type": "ephemeral"}`
- Extended thinking for study guides
- Rate limit handling with exponential backoff
- Input sanitization via `_sanitize_topic()` method

### TextExtractor (`app/services/text_extractor.py`)

Unified text extraction supporting multiple file types:

```python
# Main entry point
def extract_text(file_path: Path) -> ExtractionResult

# File type detection (handles slide archives disguised as PDFs)
def detect_file_type(file_path: Path) -> str  # 'pdf', 'slide_archive', 'image', 'docx', etc.

# Individual extractors
def extract_from_pdf(file_path) -> ExtractionResult
def extract_from_slide_archive(file_path) -> ExtractionResult
def extract_from_image(file_path) -> ExtractionResult  # Uses pytesseract OCR
def extract_from_docx(file_path) -> ExtractionResult
def extract_from_text(file_path) -> ExtractionResult
def extract_from_html(file_path) -> ExtractionResult
```

### CourseMaterial Model (`app/models/course_models.py`)

```python
class CourseMaterial(BaseModel):
    id: str
    filename: str
    title: Optional[str]
    storagePath: str          # Relative path in Materials/
    weekNumber: Optional[int]
    tier: str                 # 'syllabus', 'course_materials', 'supplementary'
    category: Optional[str]
    # ... other fields
```

---

## Feature Development Workflow

### 1. Issue Creation
- Create comprehensive GitHub issue for each phase
- Include tasks, deliverables, and acceptance criteria
- Reference parent issues for multi-phase features
- Use labels: `enhancement`, `bug`, `documentation`, `phase-1`, etc.

### 2. Development
- Create feature branch from `main`: `feature/{feature-name}-phase-{n}`
- Commit messages must reference issue: `feat: Add upload endpoint (#150)`
- Follow conventional commits: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`

### 3. Testing
- Unit tests for all new functions (>80% coverage)
- Integration tests for API endpoints
- E2E tests for user-facing features
- Mock external services (Firestore, Anthropic API)

### 4. Pull Request
- Comprehensive description with overview, related issues, changes
- Link all related issues
- Title format: `Phase X: Feature Name`

### 5. Code Review Process

#### Trigger Review
Comment `@claude review` on the PR

#### Priority Levels
- **CRITICAL**: Security vulnerabilities, data loss, breaking changes → Must fix immediately
- **HIGH**: Bugs, performance issues, missing validation → Must fix before merge
- **MEDIUM**: Code quality, missing tests, documentation → Should fix before merge
- **LOW**: Style, minor refactoring → Create issue for future work

#### Iteration
1. Fix CRITICAL and HIGH issues
2. Fix MEDIUM issues unless good reason to defer
3. For LOW issues: create GitHub issue, reference in PR comment
4. Re-trigger review with `@claude review`
5. Continue until no CRITICAL/HIGH/MEDIUM issues remain

### 6. Merge and Release
- Squash and merge
- Tag with semantic version: `v{major}.{minor}.{patch}`
- Create GitHub release with notes
- Automated deployment via GitHub Actions

---

## Code Review Focus Areas

### Security (CRITICAL)
- XSS prevention: Always use `escapeHtml()` for user content in JS
- Input validation on all API endpoints (Pydantic validators)
- File upload validation: type, size, content scanning
- No secrets in code - use Google Secret Manager
- Sanitize extracted content before storage/display
- Check `_sanitize_topic()` pattern for prompt injection prevention

### Python Best Practices
- Type hints on all function signatures
- Async/await for I/O operations
- Specific exception types (not bare `except:`)
- Follow existing patterns in `files_api_service.py`
- Use Pydantic validators for request validation
- PEP 8 style (enforced by flake8)

### JavaScript Best Practices
- Event delegation (no inline `onclick`)
- Validate array indices before access
- Try/catch for async operations
- No memory leaks from event listeners
- Follow patterns in `app.js`

### Testing Requirements
- Mock Anthropic API calls
- Mock Firestore operations
- Test error handling paths
- Test input validation (valid and invalid)
- Test edge cases (empty files, large files, malformed content)

---

## Implementation Guide: Content Upload Pipeline

### Phase 1: User Upload Interface

**Priority: HIGH | Effort: Medium | Dependencies: None**

This phase adds user-facing file upload capability. The backend text extraction already exists in `text_extractor.py`.

#### Files to Create

```
app/routes/upload.py                    # Upload API endpoints
app/services/upload_service.py          # Upload business logic
app/models/upload_models.py             # Pydantic request/response models
app/static/js/upload.js                 # Frontend upload logic
app/static/css/upload.css               # Upload UI styles
templates/partials/upload_dropzone.html # Reusable dropzone component
```

#### Files to Modify

```
app/main.py                             # Register upload router
templates/index.html                    # Add Upload tab to nav
```

#### API Endpoints to Implement

```python
# app/routes/upload.py

@router.post("/api/upload")
async def upload_material(
    file: UploadFile,
    course_id: str = Form(...),
    week_number: Optional[int] = Form(None),
    title: Optional[str] = Form(None)
) -> UploadResponse:
    """
    Upload a course material file.
    
    1. Validate file type and size
    2. Save to Materials/{course_id}/
    3. Create Firestore document in courses/{course_id}/materials
    4. Trigger text extraction (async background task)
    5. Return material_id and status
    """
    pass

@router.get("/api/upload/{material_id}/status")
async def get_upload_status(material_id: str) -> StatusResponse:
    """Get processing status for an uploaded material."""
    pass

@router.post("/api/upload/batch")
async def upload_batch(
    files: List[UploadFile],
    course_id: str = Form(...)
) -> BatchUploadResponse:
    """Upload multiple files at once."""
    pass
```

#### Pydantic Models

```python
# app/models/upload_models.py

class UploadResponse(BaseModel):
    status: Literal["success", "error"]
    material_id: str
    filename: str
    processing_status: Literal["pending", "processing", "complete", "error"]
    message: Optional[str] = None

class StatusResponse(BaseModel):
    material_id: str
    status: Literal["pending", "processing", "complete", "error"]
    progress: Optional[float] = None  # 0.0 - 1.0
    extracted_text_preview: Optional[str] = None
    error: Optional[str] = None

class BatchUploadResponse(BaseModel):
    status: Literal["success", "partial", "error"]
    uploads: List[UploadResponse]
    failed_count: int
```

#### Frontend Implementation

```javascript
// app/static/js/upload.js

class UploadManager {
    constructor(courseId) {
        this.courseId = courseId;
        this.dropzone = document.getElementById('upload-dropzone');
        this.initDragDrop();
    }
    
    initDragDrop() {
        this.dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.dropzone.classList.add('dragover');
        });
        
        this.dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            this.dropzone.classList.remove('dragover');
            this.handleFiles(e.dataTransfer.files);
        });
    }
    
    async handleFiles(files) {
        for (const file of files) {
            await this.uploadFile(file);
        }
    }
    
    async uploadFile(file) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('course_id', this.courseId);
        
        // Show progress UI
        const progressId = this.showUploadProgress(file.name);
        
        try {
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (result.status === 'success') {
                this.pollStatus(result.material_id, progressId);
            } else {
                this.showError(progressId, result.message);
            }
        } catch (error) {
            this.showError(progressId, error.message);
        }
    }
    
    async pollStatus(materialId, progressId) {
        // Poll every 2 seconds until complete
        const poll = async () => {
            const response = await fetch(`/api/upload/${materialId}/status`);
            const status = await response.json();
            
            this.updateProgress(progressId, status.progress);
            
            if (status.status === 'complete') {
                this.showComplete(progressId);
            } else if (status.status === 'error') {
                this.showError(progressId, status.error);
            } else {
                setTimeout(poll, 2000);
            }
        };
        
        poll();
    }
}
```

#### Code Review Checklist for Phase 1

- [ ] File type validation (whitelist: pdf, docx, pptx, txt, md, html, png, jpg)
- [ ] File size limit enforced (e.g., 50MB max)
- [ ] Filename sanitization (no path traversal)
- [ ] Firestore document created with correct schema
- [ ] Text extraction uses existing `text_extractor.py`
- [ ] Error handling for extraction failures
- [ ] Progress tracking updates Firestore
- [ ] Frontend shows upload progress
- [ ] Frontend handles errors gracefully
- [ ] Tests for valid uploads, invalid types, oversized files
- [ ] CSRF protection on upload endpoint

---

### Phase 2: Intelligent Content Analysis

**Priority: HIGH | Effort: Medium | Dependencies: Phase 1**

Add Claude-powered content analysis that categorizes uploaded materials and recommends study methods.

#### Files to Create

```
app/services/content_analyzer.py        # Content analysis service
```

#### Files to Modify

```
app/services/files_api_service.py       # Add analyze_material method
app/routes/upload.py                    # Trigger analysis after extraction
app/models/upload_models.py             # Add analysis response models
```

#### Content Analysis Service

```python
# app/services/content_analyzer.py

from typing import Dict, List, Optional
from anthropic import AsyncAnthropic
from app.services.gcp_service import get_anthropic_api_key

ANALYSIS_SYSTEM_PROMPT = """You are an expert educational content analyst for law courses.
Analyze the provided course material and extract structured information.

You must identify:
1. Content type (lecture_notes, syllabus, case_law, textbook, practice_problems, etc.)
2. Main topics covered
3. Key concepts with brief definitions
4. Difficulty level (1-10)
5. Recommended revision methods based on content type

Respond ONLY with valid JSON matching the specified schema."""

class ContentAnalyzer:
    def __init__(self):
        self.client = AsyncAnthropic(api_key=get_anthropic_api_key())
    
    async def analyze_material(
        self,
        text_content: str,
        filename: str,
        course_context: Optional[Dict] = None
    ) -> Dict:
        """
        Analyze extracted text content and return structured analysis.
        
        Args:
            text_content: Extracted text from the material
            filename: Original filename for context
            course_context: Optional course metadata
            
        Returns:
            Analysis dict with topics, concepts, recommendations
        """
        # Truncate if too long
        max_chars = 50000
        if len(text_content) > max_chars:
            text_content = text_content[:max_chars] + "\n[...truncated...]"
        
        prompt = f"""Analyze this course material:

FILENAME: {filename}
{f"COURSE CONTEXT: {course_context}" if course_context else ""}

CONTENT:
{text_content}

Return JSON:
{{
    "content_type": "lecture_notes|syllabus|case_law|textbook|practice_problems|other",
    "topics": ["topic1", "topic2"],
    "key_concepts": [
        {{"term": "...", "definition": "...", "importance": "high|medium|low"}}
    ],
    "difficulty_score": 1-10,
    "estimated_study_time_minutes": int,
    "recommended_revision_methods": [
        {{"method": "flashcards|quiz|spaced_repetition|practice_questions|summary", 
          "reason": "why this method suits this content",
          "priority": 1-5}}
    ],
    "prerequisites": ["topic that should be studied first"],
    "learning_objectives": ["what student should learn from this"]
}}"""

        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2000,
            system=ANALYSIS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}]
        )
        
        # Parse JSON response
        import json
        import re
        
        text = response.content[0].text
        # Handle markdown code blocks
        if "```json" in text:
            match = re.search(r'```json\n(.*?)\n```', text, re.DOTALL)
            if match:
                text = match.group(1)
        
        return json.loads(text)

# Singleton
_analyzer = None

def get_content_analyzer() -> ContentAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = ContentAnalyzer()
    return _analyzer
```

#### Integration with Upload Flow

```python
# In app/routes/upload.py, after text extraction succeeds:

from app.services.content_analyzer import get_content_analyzer

async def process_uploaded_material(material_id: str, course_id: str):
    """Background task to extract text and analyze content."""
    
    # 1. Get material from Firestore
    material = get_material(course_id, material_id)
    
    # 2. Extract text (existing service)
    from app.services.text_extractor import extract_text
    result = extract_text(Path(f"Materials/{material.storagePath}"))
    
    if not result.success:
        update_material_status(material_id, "error", error=result.error)
        return
    
    # 3. Analyze content with Claude
    analyzer = get_content_analyzer()
    try:
        analysis = await analyzer.analyze_material(
            text_content=result.text,
            filename=material.filename,
            course_context={"course_id": course_id}
        )
        
        # 4. Update Firestore with analysis results
        update_material_analysis(material_id, analysis)
        update_material_status(material_id, "complete")
        
    except Exception as e:
        update_material_status(material_id, "error", error=str(e))
```

#### Code Review Checklist for Phase 2

- [ ] Analysis prompt prevents hallucination (instructs to use only provided content)
- [ ] JSON parsing handles malformed responses gracefully
- [ ] Token limits respected (truncate long content)
- [ ] Analysis results stored in Firestore
- [ ] Error handling for API failures
- [ ] Rate limiting considered (reuse existing patterns)
- [ ] Tests with mock Anthropic responses
- [ ] Analysis results displayed in UI

---

### Phase 3: Spaced Repetition System

**Priority: MEDIUM | Effort: Medium | Dependencies: None (can parallel Phase 1-2)**

Implement SM-2 algorithm for flashcard scheduling.

#### Files to Create

```
app/services/spaced_repetition.py       # SM-2 algorithm
app/routes/flashcard_review.py          # Review session endpoints
app/models/flashcard_models.py          # SR data models
```

#### Files to Modify

```
app/routes/files_content.py             # Add SR data to flashcard responses
templates/index.html                    # Update flashcard UI for SR
app/static/js/app.js                    # Add SR review logic
```

#### SM-2 Algorithm Implementation

```python
# app/services/spaced_repetition.py

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

@dataclass
class SpacedRepetitionData:
    """SM-2 algorithm data for a flashcard."""
    ease_factor: float = 2.5      # E-Factor (1.3 - 2.5)
    interval_days: int = 1        # Current interval
    repetitions: int = 0          # Successful repetitions in a row
    next_review: Optional[datetime] = None
    last_review: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        return {
            "ease_factor": self.ease_factor,
            "interval_days": self.interval_days,
            "repetitions": self.repetitions,
            "next_review": self.next_review.isoformat() if self.next_review else None,
            "last_review": self.last_review.isoformat() if self.last_review else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "SpacedRepetitionData":
        return cls(
            ease_factor=data.get("ease_factor", 2.5),
            interval_days=data.get("interval_days", 1),
            repetitions=data.get("repetitions", 0),
            next_review=datetime.fromisoformat(data["next_review"]) if data.get("next_review") else None,
            last_review=datetime.fromisoformat(data["last_review"]) if data.get("last_review") else None
        )


def calculate_next_review(
    quality: int,  # 0-5 (0-2 = fail, 3-5 = pass)
    current_data: SpacedRepetitionData
) -> SpacedRepetitionData:
    """
    SM-2 Algorithm implementation.
    
    Args:
        quality: User's self-assessment (0-5)
            0 - Complete blackout
            1 - Incorrect, but remembered upon seeing answer
            2 - Incorrect, but answer seemed easy to recall
            3 - Correct with serious difficulty
            4 - Correct after hesitation
            5 - Perfect response
        current_data: Current SR data for the card
        
    Returns:
        Updated SR data with new interval and next review date
    """
    data = SpacedRepetitionData(
        ease_factor=current_data.ease_factor,
        interval_days=current_data.interval_days,
        repetitions=current_data.repetitions,
        last_review=datetime.utcnow()
    )
    
    # Failed response (quality < 3)
    if quality < 3:
        data.repetitions = 0
        data.interval_days = 1
    else:
        # Successful response
        if data.repetitions == 0:
            data.interval_days = 1
        elif data.repetitions == 1:
            data.interval_days = 6
        else:
            data.interval_days = round(data.interval_days * data.ease_factor)
        
        data.repetitions += 1
    
    # Update ease factor
    # EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    data.ease_factor = data.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
    
    # EF must be at least 1.3
    if data.ease_factor < 1.3:
        data.ease_factor = 1.3
    
    # Calculate next review date
    data.next_review = datetime.utcnow() + timedelta(days=data.interval_days)
    
    return data


def get_cards_due_for_review(
    flashcards: list,
    max_cards: int = 20
) -> list:
    """
    Get flashcards that are due for review.
    
    Args:
        flashcards: List of flashcard dicts with 'sr_data' field
        max_cards: Maximum number of cards to return
        
    Returns:
        List of flashcards due for review, sorted by urgency
    """
    now = datetime.utcnow()
    due_cards = []
    
    for card in flashcards:
        sr_data = card.get("sr_data")
        
        # New card (no SR data yet)
        if not sr_data:
            due_cards.append((card, now))  # Due immediately
            continue
        
        sr = SpacedRepetitionData.from_dict(sr_data)
        
        # Card is due
        if sr.next_review is None or sr.next_review <= now:
            due_cards.append((card, sr.next_review or now))
    
    # Sort by due date (most overdue first)
    due_cards.sort(key=lambda x: x[1])
    
    return [card for card, _ in due_cards[:max_cards]]
```

#### API Endpoints for SR

```python
# app/routes/flashcard_review.py

from fastapi import APIRouter, HTTPException
from app.services.spaced_repetition import calculate_next_review, get_cards_due_for_review

router = APIRouter(prefix="/api/flashcards", tags=["Flashcard Review"])

@router.get("/due/{course_id}")
async def get_due_flashcards(course_id: str, max_cards: int = 20):
    """Get flashcards due for review."""
    # Fetch user's flashcards from Firestore
    # Filter using get_cards_due_for_review()
    # Return cards
    pass

@router.post("/review/{card_id}")
async def submit_review(card_id: str, quality: int):
    """
    Submit a flashcard review result.
    
    quality: 0-5 (0-2 = failed, 3-5 = passed)
    """
    if not 0 <= quality <= 5:
        raise HTTPException(400, "Quality must be 0-5")
    
    # Get card from Firestore
    # Calculate new SR data
    # Update Firestore
    # Return updated card with next review date
    pass
```

#### Code Review Checklist for Phase 3

- [ ] SM-2 algorithm correctly implemented
- [ ] Edge cases handled (new cards, first review, etc.)
- [ ] Ease factor bounded (min 1.3)
- [ ] Next review date calculated correctly
- [ ] SR data persisted to Firestore
- [ ] Due cards query is efficient (consider Firestore indexing)
- [ ] UI shows next review date
- [ ] Quality rating UI is intuitive (e.g., 1-5 buttons)
- [ ] Tests for algorithm correctness

---

### Phase 4: AI Podcast Generation (Future)

**Priority: LOW | Effort: Very High | Dependencies: Phases 1-3 complete**

This is a complex feature requiring TTS integration, audio processing, and real-time streaming. Defer until core features are stable.

#### High-Level Architecture

```
User Request → Script Generation (Claude) → TTS (ElevenLabs) → Audio Storage (GCS)
                                                    ↓
                                           WebSocket Streaming → User Playback
                                                    ↓
                                           User Question (STT) → Context-Aware Response → Resume
```

#### Key Components Needed

1. **Script Generator**: Extend `files_api_service.py` with podcast script generation
2. **TTS Service**: New service wrapping ElevenLabs or Google Cloud TTS API
3. **Audio Processor**: Combine multiple TTS outputs, add transitions
4. **Streaming Server**: WebSocket endpoint for real-time audio delivery
5. **STT Service**: Transcribe user questions during playback
6. **Q&A Handler**: Context-aware responses using course materials

#### Dependencies to Add

```
# requirements.txt additions for podcast feature
elevenlabs>=0.2.0           # Or google-cloud-texttospeech
openai>=1.0.0               # For Whisper STT
pydub>=0.25.0               # Audio processing
ffmpeg-python>=0.2.0        # Audio manipulation
websockets>=12.0            # Real-time streaming
```

This phase should be broken into sub-phases:
- 4a: Script generation only (text output)
- 4b: TTS integration (audio file generation)
- 4c: Streaming playback
- 4d: Interactive Q&A

---

## API Response Patterns

### Success Response
```python
{"status": "success", "data": {...}}
```

### Error Response
```python
{"status": "error", "message": "Human-readable error", "detail": "Technical detail"}
```

### Quiz Response
```json
{
    "quiz": {
        "questions": [
            {
                "question": "What are the requirements for...",
                "options": ["A", "B", "C", "D"],
                "correct_index": 0,
                "explanation": "Under Dutch law...",
                "difficulty": "medium",
                "articles": ["Art. 3:32 DCC"],
                "topic": "Contract Law"
            }
        ]
    },
    "course_id": "LLS-2025-2026",
    "week": 3
}
```

### Flashcard Response
```json
{
    "flashcards": [
        {
            "id": "card_123",
            "front": "What is consensus?",
            "back": "Meeting of the minds between parties (Art. 3:33 DCC)...",
            "sr_data": {
                "ease_factor": 2.5,
                "interval_days": 6,
                "next_review": "2026-01-15T00:00:00Z"
            }
        }
    ],
    "count": 20,
    "due_count": 5
}
```

---

## Common Validation Patterns

### Topic Sanitization (Prompt Injection Prevention)

Follow the pattern in `files_api_service.py`:

```python
def _sanitize_topic(self, topic: str | None, default: str = "Course Materials") -> str:
    """Sanitize topic parameter to prevent prompt injection."""
    if topic is None or topic == '':
        return default
    
    topic = topic.strip()
    if not topic:
        return default
    
    # Length validation
    if len(topic) > 200:
        raise ValueError("topic must not exceed 200 characters")
    
    # Unicode normalization
    topic = unicodedata.normalize('NFKC', topic)
    
    # Remove zero-width characters
    for char in ['\u200b', '\u200c', '\u200d', '\ufeff']:
        topic = topic.replace(char, '')
    
    # Check for prompt injection patterns
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(topic):
            raise ValueError("topic contains suspicious content")
    
    # Escape special characters
    topic = topic.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
    
    return topic
```

### File Upload Validation

```python
ALLOWED_EXTENSIONS = {'pdf', 'docx', 'pptx', 'txt', 'md', 'html', 'png', 'jpg', 'jpeg'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

def validate_upload(file: UploadFile) -> None:
    """Validate uploaded file."""
    # Check extension
    ext = file.filename.split('.')[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type .{ext} not allowed")
    
    # Check size (read in chunks to avoid memory issues)
    file.file.seek(0, 2)  # Seek to end
    size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if size > MAX_FILE_SIZE:
        raise HTTPException(400, f"File too large. Max size: {MAX_FILE_SIZE // 1024 // 1024}MB")
    
    # Sanitize filename
    safe_filename = secure_filename(file.filename)
    if not safe_filename:
        raise HTTPException(400, "Invalid filename")
```

---

## Deployment

### Automated Production Deployment

- GitHub Action triggers on semantic version tags (`v2.9.0`, `v3.0.0`)
- Deploys to Google Cloud Run (europe-west4)
- See `.github/workflows/` for configuration

### Manual Deployment (NOT RECOMMENDED)

```bash
./deploy.sh
```

### Environment Variables

Required in production:
- `ANTHROPIC_API_KEY` (via Secret Manager)
- `AUTH_ENABLED=true`
- `AUTH_DOMAIN=mgms.eu`
- `GOOGLE_CLIENT_ID`
- `GCP_PROJECT_ID`

---

## Testing Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_upload.py -v

# Run E2E tests
npx playwright test

# Type checking
mypy app/
```

---

## Version History

- **v2.10.0** - Badge System with Tier Progression
- **v2.9.x** - Quiz management, study guide saving
- **v2.8.x** - Gamification foundation
- **v2.7.x** - Text extraction service
- **v2.6.x** - Course-aware content generation

---

## Implementation Phases Summary

| Phase | Feature | Priority | Effort | Status |
|-------|---------|----------|--------|--------|
| 1 | User Upload Interface | HIGH | Medium | 🔴 Not Started |
| 2 | Content Analysis | HIGH | Medium | 🔴 Not Started |
| 3 | Spaced Repetition | MEDIUM | Medium | 🔴 Not Started |
| 4a | Podcast Scripts | LOW | Medium | 🔴 Not Started |
| 4b | TTS Integration | LOW | High | 🔴 Not Started |
| 4c | Audio Streaming | LOW | High | 🔴 Not Started |
| 4d | Interactive Q&A | LOW | Very High | 🔴 Not Started |

**Recommended order**: Phase 1 → Phase 2 → Phase 3 → Phase 4a → 4b → 4c → 4d
