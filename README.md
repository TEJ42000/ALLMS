# LLS Study Portal

AI-Powered Learning System for Law & Legal Skills using Anthropic Claude and Google Cloud Run.

## 🎯 Features

- **AI Tutor**: Interactive chat for legal questions across multiple subjects
- **Assessment Grading**: Automated feedback on student answers
- **Quiz Generator**: Generate practice quizzes from course materials using Files API
- **Study Guide Generator**: Create comprehensive study guides from uploaded materials
- **Case Analysis**: Analyze legal cases with AI assistance
- **Article Explanations**: Get detailed explanations of legal articles

## 🏗️ Architecture

- **Backend**: FastAPI (Python 3.11+)
- **AI**: Anthropic Claude 3.5 Sonnet with Files API
- **Deployment**: Google Cloud Run (europe-west4)
- **Authentication**: Google Cloud Identity-Aware Proxy (IAP)
- **Storage**: Google Secret Manager for API keys, Firestore for data
- **Frontend**: Vanilla JavaScript with modern CSS

## 📁 Project Structure

```
LLMRMS/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── ai_tutor.py         # AI tutor endpoints
│   │   ├── assessment.py       # Assessment grading endpoints
│   │   ├── files_content.py    # Files API endpoints (quiz, study guides)
│   │   └── pages.py            # HTML page serving
│   ├── services/
│   │   ├── __init__.py
│   │   ├── anthropic_client.py  # Anthropic API integration
│   │   ├── files_api_service.py # Files API service
│   │   ├── text_extractor.py    # Unified text extraction (see TEXT-EXTRACTION-SERVICE.md)
│   │   ├── slide_archive.py     # Slide archive viewer (ZIP-based PDFs)
│   │   └── materials_scanner.py # Course materials folder scanner
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic models
│   └── static/
│       ├── css/
│       │   └── styles.css      # Application styles
│       └── js/
│           └── app.js          # Frontend JavaScript
├── templates/
│   ├── base.html               # Base template
│   └── index.html              # Main page
├── Materials/                  # Course materials (PDFs, DOCX, etc.)
├── scripts/
│   └── upload_files_script.py  # Upload materials to Anthropic Files API
├── Dockerfile                  # Container configuration
├── requirements.txt            # Python dependencies
├── deploy.sh                   # Deployment script
└── .env.example                # Environment variables template

```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Google Cloud SDK (`gcloud`)
- Anthropic API key
- Google Cloud Project with billing enabled

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/TEJ42000/ALLMS.git
   cd ALLMS
   ```

2. **Set up Python environment**
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and configure:
   # - ANTHROPIC_API_KEY (required)
   # - AUTH_ENABLED=false (for local development)
   # - AUTH_MOCK_USER_EMAIL=dev@mgms.eu (mock user)
   ```

4. **Get API key from Google Secret Manager** (if already stored)
   ```bash
   gcloud auth login
   gcloud secrets versions access latest --secret=anthropic-api-key --project=vigilant-axis-483119-r8
   ```

5. **Run locally**
   ```bash
   uvicorn app.main:app --reload --port 8080
   ```

6. **Visit the application**
   - Main app: http://localhost:8080
   - API docs: http://localhost:8080/api/docs
   - Health check: http://localhost:8080/health

> **Note**: Authentication is disabled by default for local development. See [Local Development Guide](docs/LOCAL-DEVELOPMENT.md) for details.

### Upload Course Materials (Optional)

If you want to use the Files API features (quiz generation, study guides):

```bash
python scripts/upload_files_script.py
```

This will automatically discover and upload all materials from the three-tier `Materials/` structure to Anthropic's Files API and generate `file_ids.json` with tier metadata.

**Materials Structure:**
- **Tier 1: `Syllabus/`** - Official course syllabi (highest priority)
- **Tier 2: `Course_Materials/`** - Primary learning materials
- **Tier 3: `Supplementary_Sources/`** - External and supplementary resources

See `Materials/README.md` for detailed information about the three-tier organization system.

## 🔐 Authentication

The application uses **Google Cloud Identity-Aware Proxy (IAP)** for authentication and authorization.

### Access Control

- **`@mgms.eu` domain users**: Full access to all features including admin endpoints
- **External users**: Can be granted access via admin-managed allow list
- **Local development**: Authentication disabled by default (mock user mode)

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AUTH_ENABLED` | No | `true` | Enable/disable authentication |
| `AUTH_DOMAIN` | Yes | `mgms.eu` | Primary allowed domain |
| `GOOGLE_CLIENT_ID` | Yes* | - | OAuth client ID for JWT verification |
| `AUTH_MOCK_USER_EMAIL` | No** | `dev@mgms.eu` | Mock user email (local dev) |
| `AUTH_MOCK_USER_IS_ADMIN` | No** | `true` | Mock user admin status (local dev) |

\* Required in production when `AUTH_ENABLED=true`
\*\* Only used when `AUTH_ENABLED=false`

### Quick Start

**Local Development** (no IAP required):
```bash
# In .env
AUTH_ENABLED=false
AUTH_MOCK_USER_EMAIL=dev@mgms.eu
AUTH_MOCK_USER_IS_ADMIN=true
```

**Production** (with IAP):
```bash
# In .env or Cloud Run environment
AUTH_ENABLED=true
AUTH_DOMAIN=mgms.eu
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

### Documentation

- **[Authentication System](docs/AUTHENTICATION.md)** - Architecture and security model
- **[IAP Setup Guide](docs/IAP-SETUP.md)** - Configure Google Cloud IAP
- **[Local Development](docs/LOCAL-DEVELOPMENT.md)** - Run locally without IAP
- **[Allow List Management](docs/ALLOW-LIST-MANAGEMENT.md)** - Manage external user access

## ☁️ Deploy to Google Cloud Run

### Option 1: Using the deployment script

```bash
chmod +x deploy.sh
./deploy.sh
```

### Option 2: Manual deployment

1. **Authenticate with Google Cloud**
   ```bash
   gcloud auth login
   gcloud config set project vigilant-axis-483119-r8
   ```

2. **Enable required APIs**
   ```bash
   gcloud services enable run.googleapis.com
   gcloud services enable secretmanager.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   ```

3. **Store API key in Secret Manager** (if not already done)
   ```bash
   echo -n "your-anthropic-api-key" | gcloud secrets create anthropic-api-key --data-file=-
   ```

4. **Deploy to Cloud Run**
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

5. **Get the service URL**
   ```bash
   gcloud run services describe lls-study-portal --region europe-west4 --format 'value(status.url)'
   ```

## 📚 API Endpoints

### Pages
- `GET /` - Main study portal interface
- `GET /health` - Health check endpoint

### AI Tutor
- `POST /api/tutor/chat` - Chat with AI tutor
- `POST /api/tutor/simple` - Simple question/answer

### Assessment
- `POST /api/assessment/assess` - Grade student answers

### Files Content (requires uploaded materials)
- `POST /api/files-content/quiz` - Generate quiz from materials
- `POST /api/files-content/study-guide` - Generate study guide
- `POST /api/files-content/case-analysis` - Analyze legal cases
- `POST /api/files-content/article-explanation` - Explain legal articles
- `POST /api/files-content/flashcards` - Generate flashcards

## 🔧 Configuration

### Environment Variables

See `.env.example` for all available configuration options:

- `ANTHROPIC_API_KEY` - Your Anthropic API key (required)
- `GCP_PROJECT_ID` - Google Cloud project ID
- `GCP_REGION` - Deployment region (default: europe-west4)
- `PORT` - Application port (default: 8080)
- `ECHR_CACHE_DIR` - Directory for ECHR case law cache (default: data/echr_cache)

### Google Cloud Settings

- **Project**: vigilant-axis-483119-r8
- **Region**: europe-west4
- **Service**: lls-study-portal

## 📖 Course Materials

The `Materials/` folder contains Criminal Law course materials organized into:

1. Course Outlines and Syllabi
2. Part A - Substantive Law
3. Part B - Procedural Law
4. Case Law (ECHR cases)
5. Working Group Materials
6. Study Summaries and Notes
7. Exam Materials
8. Study Guides

## 🧪 Testing

Run tests with pytest:

```bash
pytest
```

## 📝 License

Proprietary

## 👥 Contributors
- Matej G. Monteleone (@TEJ42000)
- Matthew G. Monteleone (@mgmonteleone)

## 🆘 Support

For issues or questions, please open an issue on GitHub.

