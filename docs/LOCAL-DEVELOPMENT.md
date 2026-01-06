# Local Development Guide

## Overview

This guide explains how to run the LLS Study Portal locally without Google Cloud IAP. The application supports an **auth bypass mode** for local development that uses a mock user instead of requiring IAP infrastructure.

## Quick Start

1. **Set up environment**:
   ```bash
   cp .env.example .env
   ```

2. **Configure auth bypass**:
   ```bash
   # In .env
   AUTH_ENABLED=false
   AUTH_MOCK_USER_EMAIL=dev@mgms.eu
   AUTH_MOCK_USER_IS_ADMIN=true
   ```

3. **Run the application**:
   ```bash
   source .venv/bin/activate
   uvicorn app.main:app --reload --port 8080
   ```

4. **Access the app**:
   ```
   http://localhost:8080
   ```

You're now running with a mock user - no login required!

## Auth Bypass Mode

### How It Works

When `AUTH_ENABLED=false`:

1. **Auth middleware** detects the flag and creates a mock user
2. **Mock user** is attached to all requests automatically
3. **No IAP headers** are required or validated
4. **All endpoints** work as if you're logged in

### Configuration

#### Mock User Settings

Configure the mock user in `.env`:

```bash
# Disable authentication for local development
AUTH_ENABLED=false

# Mock user email (determines access level)
AUTH_MOCK_USER_EMAIL=dev@mgms.eu

# Mock user admin status
AUTH_MOCK_USER_IS_ADMIN=true
```

#### Mock User Profiles

**Admin User (Full Access)**:
```bash
AUTH_MOCK_USER_EMAIL=dev@mgms.eu
AUTH_MOCK_USER_IS_ADMIN=true
```
- Access to all endpoints including `/api/admin/*`
- Can manage users, courses, and view analytics

**Regular User (Limited Access)**:
```bash
AUTH_MOCK_USER_EMAIL=student@university.edu
AUTH_MOCK_USER_IS_ADMIN=false
```
- Access to student-facing features
- Cannot access admin endpoints

**External User (Allow List Testing)**:
```bash
AUTH_MOCK_USER_EMAIL=guest@external.com
AUTH_MOCK_USER_IS_ADMIN=false
```
- Simulates external user on allow list
- Useful for testing allow list functionality

### Mock User Object

The mock user has the following structure:

```python
MockUser(
    email="dev@mgms.eu",
    user_id="mock-user-id",
    is_admin=True,
    is_domain_user=True,  # True if @mgms.eu
    is_allowed=True       # Always True in mock mode
)
```

## Testing Authenticated Endpoints

### Testing Admin Endpoints

With admin mock user (`dev@mgms.eu`):

```bash
# List allowed users
curl http://localhost:8080/api/admin/users/allowed

# Get usage analytics
curl http://localhost:8080/api/admin/usage/summary

# List courses
curl http://localhost:8080/api/admin/courses
```

### Testing Regular User Endpoints

With regular mock user:

```bash
# AI Tutor
curl -X POST http://localhost:8080/api/ai-tutor \
  -H "Content-Type: application/json" \
  -d '{"message": "Explain contract law", "course_id": "test-course"}'

# Assessment
curl -X POST http://localhost:8080/api/assessment \
  -H "Content-Type: application/json" \
  -d '{"question": "What is tort law?", "answer": "...", "course_id": "test-course"}'
```

### Testing Authorization

Test different access levels by changing `AUTH_MOCK_USER_EMAIL`:

1. **Admin access** (`dev@mgms.eu`):
   - ✅ Can access `/api/admin/*`
   - ✅ Can access regular endpoints

2. **Domain user** (`user@mgms.eu`):
   - ❌ Cannot access `/api/admin/*` (403 Forbidden)
   - ✅ Can access regular endpoints

3. **External user** (`guest@external.com`):
   - ❌ Cannot access `/api/admin/*` (403 Forbidden)
   - ✅ Can access regular endpoints (if on allow list)

## Environment Variables

### Required for Local Development

```bash
# Core settings
ANTHROPIC_API_KEY=your-api-key-here
GCP_PROJECT_ID=vigilant-axis-483119-r8

# Auth settings (local dev)
AUTH_ENABLED=false
AUTH_DOMAIN=mgms.eu
AUTH_MOCK_USER_EMAIL=dev@mgms.eu
AUTH_MOCK_USER_IS_ADMIN=true

# Optional
DEBUG=True
LOG_LEVEL=DEBUG
PORT=8080
```

### Not Required for Local Development

These are only needed in production with IAP:

```bash
# ❌ Not needed locally
GOOGLE_CLIENT_ID=...
IAP_AUDIENCE=...
```

## Running Tests

### Unit Tests

Run tests with mock authentication:

```bash
# Run all tests
pytest

# Run auth tests specifically
pytest tests/test_auth.py -v

# Run with coverage
pytest --cov=app tests/
```

### Integration Tests

Test with different mock users:

```bash
# Test as admin
AUTH_MOCK_USER_EMAIL=dev@mgms.eu pytest tests/integration/

# Test as regular user
AUTH_MOCK_USER_EMAIL=student@university.edu pytest tests/integration/

# Test as external user
AUTH_MOCK_USER_EMAIL=guest@external.com pytest tests/integration/
```

## Debugging

### Enable Debug Logging

```bash
# In .env
LOG_LEVEL=DEBUG
DEBUG=True
```

### Check Auth Status

The application logs auth status on startup:

```
INFO:     ⚠️  Authentication is DISABLED (development mode)
INFO:     Mock user: dev@mgms.eu (admin=True)
```

### Verify Mock User

Check request state in route handlers:

```python
from fastapi import Request

@router.get("/debug/user")
async def debug_user(request: Request):
    user = getattr(request.state, 'user', None)
    return {
        "user": user.model_dump() if user else None,
        "auth_enabled": get_auth_config().auth_enabled
    }
```

## Common Issues

### Issue: "401 Unauthorized" even with AUTH_ENABLED=false

**Cause**: Environment variable not loaded  
**Solution**:
```bash
# Verify .env is loaded
python -c "from app.services.auth_service import get_auth_config; print(get_auth_config())"

# Restart the server
uvicorn app.main:app --reload
```

### Issue: "403 Forbidden" on admin endpoints

**Cause**: Mock user doesn't have admin privileges  
**Solution**:
```bash
# In .env
AUTH_MOCK_USER_EMAIL=dev@mgms.eu  # Must be @mgms.eu for admin
AUTH_MOCK_USER_IS_ADMIN=true
```

### Issue: Changes to .env not taking effect

**Cause**: Server not restarted or .env not reloaded  
**Solution**:
```bash
# Stop server (Ctrl+C)
# Restart with --reload flag
uvicorn app.main:app --reload --port 8080
```

## Switching Between Local and Production

### Local Development → Production

1. Update `.env`:
   ```bash
   AUTH_ENABLED=true
   GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
   ```

2. Deploy to Cloud Run:
   ```bash
   ./deploy.sh
   ```

3. Configure IAP (see [IAP-SETUP.md](IAP-SETUP.md))

### Production → Local Development

1. Update `.env`:
   ```bash
   AUTH_ENABLED=false
   AUTH_MOCK_USER_EMAIL=dev@mgms.eu
   AUTH_MOCK_USER_IS_ADMIN=true
   ```

2. Restart server:
   ```bash
   uvicorn app.main:app --reload
   ```

## Best Practices

### ✅ Do

- Use `AUTH_ENABLED=false` for local development
- Configure mock user to match your testing needs
- Test with different mock user profiles
- Enable debug logging when troubleshooting
- Keep `.env` out of version control

### ❌ Don't

- Deploy to production with `AUTH_ENABLED=false`
- Commit `.env` file to git
- Use production credentials locally
- Skip testing authorization logic

## Related Documentation

- [Authentication System](AUTHENTICATION.md) - Architecture overview
- [IAP Setup Guide](IAP-SETUP.md) - Production configuration
- [Allow List Management](ALLOW-LIST-MANAGEMENT.md) - Managing external users

## References

- [FastAPI Development](https://fastapi.tiangolo.com/tutorial/)
- [Python-dotenv](https://github.com/theskumar/python-dotenv)
- [Uvicorn](https://www.uvicorn.org/)

