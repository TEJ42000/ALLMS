# 📂 Complete File Structure & Setup Checklist

## ✅ Step-by-Step File Organization

### 1. Create Directory Structure
```bash
mkdir -p lls-study-portal/{app/{routes,services,models,static/{css,js,images}},templates,tests}
cd lls-study-portal
```

### 2. Copy Starter Code Files

#### Root Directory Files
```
lls-study-portal/
├── requirements.txt          ← Copy from starter-code/requirements.txt
├── Dockerfile               ← Copy from starter-code/Dockerfile
├── .env                     ← Copy env.example, rename to .env, fill in API key
├── .gitignore              ← Create (see template below)
├── deploy.sh               ← Copy from starter-code/deploy.sh
└── README.md               ← Create your own or copy QUICK-START-GUIDE.md
```

#### App Directory Files
```
app/
├── __init__.py             ← Create empty file
├── main.py                 ← Copy from starter-code/app_main.py
├── routes/
│   ├── __init__.py        ← Create empty file
│   ├── ai_tutor.py        ← Copy from starter-code/ai_tutor_routes.py
│   ├── assessment.py      ← Copy from starter-code/assessment_routes.py
│   └── pages.py           ← Copy from starter-code/pages_routes.py
├── services/
│   ├── __init__.py        ← Create empty file
│   └── anthropic_client.py ← Copy from starter-code/anthropic_client.py
├── models/
│   ├── __init__.py        ← Create empty file
│   └── schemas.py         ← Copy from starter-code/schemas.py
└── static/
    ├── css/
    │   └── styles.css     ← Copy your CSS from original HTML
    └── js/
        └── app.js         ← Create new (see template below)
```

#### Templates Directory
```
templates/
├── base.html              ← Create (see template below)
└── index.html             ← Migrate from your original HTML
```

---

## 📋 File Templates

### .gitignore
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
.venv

# Environment
.env
.env.local
.env.*.local

# IDEs
.vscode/
.idea/
*.swp
*.swo
.DS_Store

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/

# Build
dist/
build/
*.egg-info/

# Logs
*.log
logs/

# Docker
docker-compose.override.yml

# Cloud
.gcloud/
cloudbuild.yaml.backup
```

### app/__init__.py
```python
# app/__init__.py
"""LLS Study Portal Application"""

__version__ = "2.0.0"
```

### app/routes/__init__.py
```python
# app/routes/__init__.py
"""API Routes"""

from . import ai_tutor, assessment, pages

__all__ = ["ai_tutor", "assessment", "pages"]
```

### app/services/__init__.py
```python
# app/services/__init__.py
"""Application Services"""

from .anthropic_client import (
    get_ai_tutor_response,
    get_assessment_response,
    get_simple_response
)

__all__ = [
    "get_ai_tutor_response",
    "get_assessment_response",
    "get_simple_response"
]
```

### app/models/__init__.py
```python
# app/models/__init__.py
"""Data Models"""

from .schemas import (
    ChatRequest,
    ChatResponse,
    AssessmentRequest,
    AssessmentResponse,
    ConversationMessage
)

__all__ = [
    "ChatRequest",
    "ChatResponse",
    "AssessmentRequest",
    "AssessmentResponse",
    "ConversationMessage"
]
```

### templates/base.html
```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}LLS Study Portal{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', path='/css/styles.css') }}">
    {% block extra_css %}{% endblock %}
</head>
<body>
    <header>
        <nav>
            <h1>LLS Study Portal</h1>
            <!-- Navigation links -->
        </nav>
    </header>
    
    <main>
        {% block content %}{% endblock %}
    </main>
    
    <footer>
        <p>&copy; 2026 LLS Study Portal</p>
    </footer>
    
    <script src="{{ url_for('static', path='/js/app.js') }}"></script>
    {% block extra_js %}{% endblock %}
</body>
</html>
```

### app/static/js/app.js (Basic Frontend)
```javascript
// app.js - Frontend JavaScript for API calls

const API_BASE = '';  // Empty for same origin

// Format markdown response
function formatMarkdown(text) {
    // Your formatting logic from original HTML
    // ... (copy formatMarkdown function)
    return text;
}

// Call AI Tutor API
async function askAITutor(message, context = 'Law & Legal Skills') {
    try {
        const response = await fetch(`${API_BASE}/api/tutor/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                context: context
            })
        });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const data = await response.json();
        return formatMarkdown(data.content);
        
    } catch (error) {
        console.error('Error calling AI tutor:', error);
        throw error;
    }
}

// Call Assessment API
async function submitAssessment(topic, question, answer) {
    try {
        const response = await fetch(`${API_BASE}/api/assessment/assess`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                topic: topic,
                question: question,
                answer: answer
            })
        });
        
        if (!response.ok) {
            throw new Error(`API error: ${response.status}`);
        }
        
        const data = await response.json();
        return {
            feedback: formatMarkdown(data.feedback),
            grade: data.grade
        };
        
    } catch (error) {
        console.error('Error calling assessment API:', error);
        throw error;
    }
}

// Export functions
window.askAITutor = askAITutor;
window.submitAssessment = submitAssessment;
```

---

## ✅ Setup Checklist

### Prerequisites
- [ ] Python 3.11+ installed
- [ ] Google Cloud account created
- [ ] gcloud CLI installed
- [ ] Anthropic API key obtained
- [ ] Git installed
- [ ] Docker installed (optional, for local testing)

### Local Setup
- [ ] Created directory structure
- [ ] Copied all starter code files
- [ ] Created __init__.py files
- [ ] Created .env with API key
- [ ] Created .gitignore
- [ ] Created virtual environment
- [ ] Installed dependencies (`pip install -r requirements.txt`)
- [ ] Ran app locally (`python -m app.main`)
- [ ] Tested at http://localhost:8080/api/docs

### Frontend Migration
- [ ] Copied CSS to app/static/css/styles.css
- [ ] Created base.html template
- [ ] Migrated HTML to templates/index.html
- [ ] Created app.js with API calls
- [ ] Updated JavaScript to use backend API
- [ ] Removed client-side API key code
- [ ] Tested frontend locally

### Docker Testing
- [ ] Built Docker image
- [ ] Ran container locally
- [ ] Tested all endpoints
- [ ] Verified health check
- [ ] Checked logs

### Google Cloud Setup
- [ ] Created GCP project
- [ ] Enabled billing
- [ ] Enabled Cloud Run API
- [ ] Enabled Secret Manager API
- [ ] Created anthropic-api-key secret
- [ ] Configured gcloud CLI

### Deployment
- [ ] Made deploy.sh executable
- [ ] Ran deployment script
- [ ] Verified deployment successful
- [ ] Tested deployed application
- [ ] Checked Cloud Run logs
- [ ] Set up custom domain (optional)

### Post-Deployment
- [ ] Tested all features in production
- [ ] Set up monitoring
- [ ] Configured logging
- [ ] Documented API
- [ ] Created user guide

---

## 🎯 Quick Command Reference

```bash
# Create project structure
mkdir -p lls-study-portal/app/{routes,services,models,static/{css,js},templates,tests}

# Set up Python
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run locally
python -m app.main

# Test Docker
docker build -t lls-portal .
docker run -p 8080:8080 -e ANTHROPIC_API_KEY="..." lls-portal

# Deploy to Cloud Run
chmod +x deploy.sh
./deploy.sh

# View logs
gcloud run services logs tail lls-study-portal --region us-central1

# Update deployment
gcloud run deploy lls-study-portal --source . --region us-central1
```

---

## 📚 Next Steps

1. **Complete setup checklist above**
2. **Follow QUICK-START-GUIDE.md for detailed walkthrough**
3. **Use Augment Code prompts from guide**
4. **Read CLOUD-RUN-MIGRATION-GUIDE.md for full details**
5. **Test locally before deploying**
6. **Deploy to Cloud Run**
7. **Iterate and enhance!**

---

## 💡 Pro Tips

1. **Start simple**: Get basic app working first, then add features
2. **Test locally**: Always test with `python -m app.main` before deploying
3. **Use API docs**: FastAPI auto-generates docs at /api/docs
4. **Check logs**: Use `gcloud run services logs` to debug issues
5. **Version control**: Commit often to git
6. **Environment vars**: Never commit .env file
7. **Augment prompts**: Be specific and show examples

You're ready to build! 🚀
