# Claude Code Review Instructions

## Project Overview

ALLMS (AI-Powered Learning Management System) is a FastAPI-based web application for legal education. It provides:
- AI-powered tutoring using Anthropic Claude
- Interactive quiz system
- Study guide generation
- Multi-course architecture with Firestore backend
- Document processing and text extraction

## Technology Stack

- **Backend**: Python 3.11+, FastAPI, Uvicorn
- **Frontend**: HTML, CSS, JavaScript (vanilla)
- **Database**: Google Cloud Firestore
- **AI**: Anthropic Claude API
- **Testing**: pytest (Python), Playwright (frontend)
- **Deployment**: Google Cloud Run, Docker

## Deployment Process

**Automated Production Deployment:**
- Deployment to production is automatically handled by a GitHub Action
- Any commit tagged with a semantic version (e.g., `v2.9.0`, `v1.2.3`) triggers the deployment
- The GitHub Action automatically deploys to Google Cloud Run
- See `.github/` folder for workflow configuration and deployment scripts
- **Do NOT manually deploy to production** - always use version tags to trigger automated deployment

## Code Review Focus Areas

### Security (CRITICAL)
- XSS vulnerabilities in JavaScript (always use `escapeHtml()` for user content)
- SQL/NoSQL injection in database queries
- Input validation on all API endpoints
- Proper authentication/authorization checks
- No secrets or API keys in code

### JavaScript Best Practices
- Use event delegation instead of inline `onclick` handlers (CSP compliance)
- Always validate array indices before access
- Proper error handling with try/catch
- No memory leaks from event listeners

### Python Best Practices
- Type hints on all function signatures
- Proper exception handling with specific exception types
- Use of async/await for I/O operations
- Follow PEP 8 style guidelines

### Testing
- All new features should have corresponding tests
- Mock external services (Firestore, Anthropic API)
- Test error handling paths
- Maintain backward compatibility

## File Structure

```
app/
├── main.py              # FastAPI application entry point
├── routes/              # API route handlers
├── services/            # Business logic services
├── models/              # Pydantic schemas
└── static/              # CSS and JavaScript files
templates/               # Jinja2 HTML templates
tests/                   # pytest test files
e2e/                     # Playwright frontend tests
```

## Review Guidelines

1. **Must Fix**: Security vulnerabilities, data loss risks, breaking changes
2. **Should Fix**: Performance issues, code quality, missing tests
3. **Consider**: Style improvements, documentation, refactoring suggestions

## Common Patterns

### API Response Format
```python
{"status": "success", "data": {...}}
{"status": "error", "message": "..."}
```

### Quiz Data Format
```json
{"quiz": {"questions": [{"question": "...", "options": [...], "correct_index": 0}]}}
```

### Course Context
The application supports multi-course mode with `course_id` parameter for filtering content.

