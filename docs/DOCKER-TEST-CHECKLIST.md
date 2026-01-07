# Docker Build and Container Testing Checklist

This checklist corresponds to Issue #8: 🐳 Test Docker build and local container

## Prerequisites

- [ ] Docker installed and running
- [ ] Docker daemon accessible (`docker ps` works)
- [ ] At least 2GB free disk space
- [ ] Port 8080 available
- [ ] Anthropic API key available (or test key for basic testing)

> ⚠️ **Security Warning:** Never use production API keys for local testing. Use a dedicated test key with rate limits or a dummy key for basic endpoint testing. Real API keys should only be stored in Secret Manager for production deployments.

---

## Automated Testing (Recommended)

### Quick Test

```bash
# Run the automated test script
./scripts/test-docker.sh
```

**Expected Result:** All tests pass with green checkmarks ✓

---

## Manual Testing Checklist

### Task 1: Build Docker Image

- [ ] Run build command:
  ```bash
  docker build -t lls-study-portal .
  ```

- [ ] Verify build completes without errors
- [ ] Check build output for warnings
- [ ] Verify image exists:
  ```bash
  docker images | grep lls-study-portal
  ```

**Expected Output:**
```
lls-study-portal   latest   <image-id>   <time>   <size>
```

**Potential Issues:**
- ✅ All dependencies in requirements.txt
- ✅ Static files path correct in Dockerfile
- ✅ Templates directory copied correctly
- ✅ gcc installed for Python package compilation

---

### Task 2: Run Container Locally

- [ ] Start container with environment variables:
  ```bash
  docker run -p 8080:8080 \
    -e ANTHROPIC_API_KEY="your-key" \
    -e AUTH_ENABLED=false \
    -e ENV=development \
    lls-study-portal
  ```

- [ ] Verify container starts without errors
- [ ] Check startup logs show:
  - [ ] "🚀 LLS Study Portal starting up..."
  - [ ] "✅ Anthropic API key loaded"
  - [ ] "✅ Application ready!"
  - [ ] "Uvicorn running on http://0.0.0.0:8080"

- [ ] Verify container is running:
  ```bash
  docker ps
  ```

**Potential Issues:**
- ✅ Environment variables passed correctly
- ✅ Port 8080 not already in use
- ✅ Application starts successfully

---

### Task 3: Test All Endpoints in Container

#### 3.1: Health Check Endpoint

- [ ] Test health endpoint:
  ```bash
  curl http://localhost:8080/health
  ```

- [ ] Verify response:
  ```json
  {
    "status": "healthy",
    "service": "lls-study-portal",
    "version": "2.0.0"
  }
  ```

- [ ] Verify HTTP status code is 200

**Status:** ✅ Returns healthy status

---

#### 3.2: Main Page Loads

- [ ] Test main page:
  ```bash
  curl -I http://localhost:8080/
  ```

- [ ] Verify HTTP status code is 200
- [ ] Verify content-type is `text/html`

- [ ] Open in browser: http://localhost:8080/
- [ ] Verify page loads correctly
- [ ] Check for "LLS Study Portal" or "Select Your Course"

**Status:** ✅ Main page loads

---

#### 3.3: Swagger UI Loads

- [ ] Test API docs endpoint:
  ```bash
  curl -I http://localhost:8080/api/docs
  ```

- [ ] Verify HTTP status code is 200

- [ ] Open in browser: http://localhost:8080/api/docs
- [ ] Verify Swagger UI loads
- [ ] Check all API endpoints are listed

**Status:** ✅ Swagger UI loads

---

#### 3.4: AI Tutor Works

- [ ] Test AI Tutor endpoint:
  ```bash
  curl -X POST http://localhost:8080/api/tutor/chat \
    -H "Content-Type: application/json" \
    -d '{
      "message": "What is constitutional law?",
      "conversation_history": []
    }'
  ```

- [ ] Verify response contains:
  - [ ] `response` field with AI-generated text
  - [ ] `conversation_history` array

- [ ] Verify HTTP status code is 200

**Status:** ✅ AI Tutor works

---

#### 3.5: Assessment Works

- [ ] Test Assessment endpoint:
  ```bash
  curl -X POST http://localhost:8080/api/assessment/assess \
    -H "Content-Type: application/json" \
    -d '{
      "essay": "This is a test essay about constitutional law principles.",
      "topic": "Constitutional Law"
    }'
  ```

- [ ] Verify response contains:
  - [ ] `grade` field (number 1-10)
  - [ ] `feedback` field (string)
  - [ ] `strengths` array
  - [ ] `improvements` array

- [ ] Verify HTTP status code is 200

**Status:** ✅ Assessment works

---

### Task 4: Verify Static Files Are Served Correctly

- [ ] Test CSS file:
  ```bash
  curl -I http://localhost:8080/static/css/styles.css
  ```
  - [ ] HTTP status code is 200
  - [ ] Content-Type is `text/css`

- [ ] Test JavaScript file:
  ```bash
  curl -I http://localhost:8080/static/js/app.js
  ```
  - [ ] HTTP status code is 200
  - [ ] Content-Type is `application/javascript`

- [ ] Open main page in browser
- [ ] Open browser developer console
- [ ] Check Network tab for any 404 errors on static files

**Status:** ✅ Static files served correctly

---

### Task 5: Check Container Logs for Errors

- [ ] View container logs:
  ```bash
  docker logs <container-id>
  ```

- [ ] Check for:
  - [ ] No ERROR level messages (except expected ones)
  - [ ] No unhandled exceptions
  - [ ] No "Failed to..." messages
  - [ ] Application started successfully

- [ ] Verify startup sequence:
  1. [ ] Authentication status logged
  2. [ ] API key status logged
  3. [ ] "Application ready!" message
  4. [ ] Uvicorn started

**Status:** ✅ No critical errors in logs

---

### Task 6: Verify Container Stops Cleanly

- [ ] Stop the container:
  ```bash
  docker stop <container-id>
  ```

- [ ] Verify container stops within 10 seconds
- [ ] Check final logs:
  ```bash
  docker logs <container-id> --tail 20
  ```

- [ ] Verify shutdown message:
  - [ ] "👋 LLS Study Portal shutting down..."
  - [ ] "Shutting down"
  - [ ] "Finished server process"

- [ ] Verify no error messages during shutdown

**Status:** ✅ Container stops cleanly

---

## Potential Issues Checklist

### Dependencies

- [x] All dependencies in requirements.txt
  - ✅ FastAPI, Uvicorn, Pydantic
  - ✅ Anthropic SDK
  - ✅ Jinja2 for templates
  - ✅ Google Cloud libraries
  - ✅ Text extraction libraries (PyMuPDF, python-docx, etc.)

### File Paths

- [x] Static files path correct in Dockerfile
  - ✅ `app.mount("/static", StaticFiles(directory="app/static"), name="static")`
  - ✅ Files copied with `COPY . .`

- [x] Templates directory copied correctly
  - ✅ `templates = Jinja2Templates(directory="templates")`
  - ✅ Directory exists in container

### Environment Variables

- [x] Environment variables passed correctly
  - ✅ `ANTHROPIC_API_KEY` - Required for AI features
  - ✅ `AUTH_ENABLED` - Set to false for testing
  - ✅ `ENV` - Set to development
  - ✅ `PORT` - Defaults to 8080

### System Dependencies

- [x] gcc installed for Python package compilation
  - ✅ Added in Dockerfile: `apt-get install -y gcc curl`

- [x] curl installed for health checks
  - ✅ Added in Dockerfile for HEALTHCHECK command

---

## Test Results Summary

### Build Phase

- [ ] Docker image builds successfully
- [ ] No build errors
- [ ] No missing dependencies
- [ ] Image size reasonable (< 1GB)

### Runtime Phase

- [ ] Container starts successfully
- [ ] Application initializes correctly
- [ ] All endpoints respond
- [ ] Static files load
- [ ] No critical errors in logs

### Shutdown Phase

- [ ] Container stops cleanly
- [ ] No errors during shutdown
- [ ] Graceful termination

---

## Sign-Off

**Tester Name:** ___________________________

**Date:** ___________________________

**Docker Version:** ___________________________

**Test Result:** ⬜ PASS  ⬜ FAIL

**Notes:**
```
[Add any additional notes or observations here]
```

---

## Next Steps After Testing

### If All Tests Pass ✅

1. Update Issue #8 with test results
2. Mark all checklist items as complete
3. Close Issue #8
4. Proceed with deployment to Cloud Run

### If Tests Fail ❌

1. Document which tests failed
2. Capture error messages and logs
3. Review [Troubleshooting Guide](./DOCKER-TESTING.md#troubleshooting)
4. Fix issues and re-test
5. Update Issue #8 with findings

---

## Additional Resources

- [Docker Testing Guide](./DOCKER-TESTING.md) - Comprehensive testing documentation
- [Automated Test Script](../scripts/test-docker.sh) - Run all tests automatically
- [Dockerfile](../Dockerfile) - Container configuration
- [Issue #8](https://github.com/TEJ42000/ALLMS/issues/8) - Original testing request

