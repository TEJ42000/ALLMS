# Docker Build and Container Testing Guide

This guide provides comprehensive instructions for testing the Docker build and container deployment of the LLS Study Portal.

## Table of Contents

- [Quick Start](#quick-start)
- [Automated Testing](#automated-testing)
- [Manual Testing](#manual-testing)
- [Troubleshooting](#troubleshooting)
- [CI/CD Integration](#cicd-integration)

---

## Quick Start

### Prerequisites

- Docker installed and running
- Docker daemon accessible
- At least 2GB free disk space
- Port 8080 available

### Run Automated Tests

```bash
# Run the automated test script
./scripts/test-docker.sh
```

This script will:
1. ✅ Build the Docker image
2. ✅ Start a container
3. ✅ Test all endpoints
4. ✅ Verify static files
5. ✅ Check logs for errors
6. ✅ Test clean shutdown
7. ✅ Provide a summary report

---

## Automated Testing

### Test Script Features

The `scripts/test-docker.sh` script provides:

- **Automated Build**: Builds the Docker image with proper tagging
- **Container Lifecycle**: Starts, monitors, and stops the container
- **Health Checks**: Waits for container to be healthy before testing
- **Endpoint Testing**: Tests all critical endpoints
- **Log Analysis**: Checks for errors in container logs
- **Cleanup**: Automatically cleans up containers on exit
- **Color-Coded Output**: Easy-to-read test results

### Test Coverage

The automated script tests:

| Test | Endpoint | Expected | Description |
|------|----------|----------|-------------|
| Health Check | `GET /health` | 200 | Application health status |
| Landing Page | `GET /` | 200 | Main course selection page |
| API Docs | `GET /api/docs` | 200 | Swagger UI documentation |
| Static Files | `GET /static/css/styles.css` | 200 | CSS file serving |
| AI Tutor | `POST /api/tutor/chat` | 200 | AI Tutor endpoint |

### Environment Variables

The test script uses these environment variables:

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...  # Your Anthropic API key

# Optional (defaults provided)
AUTH_ENABLED=false            # Disable auth for testing
ENV=development               # Set environment mode
```

---

## Manual Testing

### Step 1: Build Docker Image

```bash
docker build -t lls-study-portal:test .
```

**Expected Output:**
```
[+] Building 45.2s (12/12) FINISHED
 => [internal] load build definition from Dockerfile
 => => transferring dockerfile: 1.23kB
 => [internal] load .dockerignore
 => ...
 => exporting to image
 => => exporting layers
 => => writing image sha256:...
 => => naming to docker.io/library/lls-study-portal:test
```

**Verify:**
```bash
docker images | grep lls-study-portal
```

### Step 2: Run Container

```bash
docker run -d \
  --name lls-study-portal-test \
  -p 8080:8080 \
  -e ANTHROPIC_API_KEY="your-api-key-here" \
  -e AUTH_ENABLED=false \
  -e ENV=development \
  lls-study-portal:test
```

**Verify Container is Running:**
```bash
docker ps | grep lls-study-portal-test
```

**Check Logs:**
```bash
docker logs lls-study-portal-test
```

**Expected Log Output:**
```
🚀 LLS Study Portal starting up...
⚠️  Authentication: DISABLED (development mode)
✅ Anthropic API key loaded
✅ Application ready!
INFO:     Started server process [1]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080
```

### Step 3: Test Endpoints

#### Test 1: Health Check

```bash
curl http://localhost:8080/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "service": "lls-study-portal",
  "version": "2.0.0"
}
```

#### Test 2: Main Page

```bash
curl -I http://localhost:8080/
```

**Expected Response:**
```
HTTP/1.1 200 OK
content-type: text/html; charset=utf-8
```

#### Test 3: API Documentation

```bash
curl -I http://localhost:8080/api/docs
```

**Expected Response:**
```
HTTP/1.1 200 OK
content-type: text/html; charset=utf-8
```

#### Test 4: Static Files

```bash
curl -I http://localhost:8080/static/css/styles.css
```

**Expected Response:**
```
HTTP/1.1 200 OK
content-type: text/css; charset=utf-8
```

#### Test 5: AI Tutor (POST)

```bash
curl -X POST http://localhost:8080/api/tutor/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is constitutional law?",
    "conversation_history": []
  }'
```

**Expected Response:**
```json
{
  "response": "Constitutional law is...",
  "conversation_history": [...]
}
```

#### Test 6: Assessment (POST)

```bash
curl -X POST http://localhost:8080/api/assessment/assess \
  -H "Content-Type: application/json" \
  -d '{
    "essay": "This is a test essay about legal principles...",
    "topic": "Constitutional Law"
  }'
```

**Expected Response:**
```json
{
  "grade": 7,
  "feedback": "...",
  "strengths": [...],
  "improvements": [...]
}
```

### Step 4: Verify Static Files

Open in browser:
- http://localhost:8080/ - Should show course selection page
- http://localhost:8080/api/docs - Should show Swagger UI
- Check browser console for any 404 errors on static files

### Step 5: Check Container Health

```bash
docker inspect --format='{{.State.Health.Status}}' lls-study-portal-test
```

**Expected Output:**
```
healthy
```

### Step 6: Test Container Stop

```bash
docker stop lls-study-portal-test
```

**Expected Behavior:**
- Container stops within 10 seconds
- No error messages in logs
- Clean shutdown

**Verify:**
```bash
docker logs lls-study-portal-test --tail 10
```

**Expected Log Output:**
```
👋 LLS Study Portal shutting down...
INFO:     Shutting down
INFO:     Finished server process [1]
```

### Step 7: Cleanup

```bash
# Remove container
docker rm lls-study-portal-test

# Remove image (optional)
docker rmi lls-study-portal:test
```

---

## Troubleshooting

### Issue: Build Fails with "gcc not found"

**Symptom:**
```
error: command 'gcc' failed: No such file or directory
```

**Solution:**
The Dockerfile already includes `gcc` in system dependencies. If this error occurs, verify the Dockerfile has:
```dockerfile
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*
```

### Issue: Container Exits Immediately

**Symptom:**
```bash
docker ps  # Container not listed
docker ps -a  # Shows "Exited (1)"
```

**Solution:**
Check logs for errors:
```bash
docker logs lls-study-portal-test
```

Common causes:
- Missing required environment variables
- Port 8080 already in use
- Application startup error

### Issue: Health Check Fails

**Symptom:**
```bash
docker inspect --format='{{.State.Health.Status}}' lls-study-portal-test
# Output: unhealthy
```

**Solution:**
1. Check if application is listening on port 8080:
   ```bash
   docker exec lls-study-portal-test netstat -tlnp | grep 8080
   ```

2. Test health endpoint manually:
   ```bash
   docker exec lls-study-portal-test curl http://localhost:8080/health
   ```

3. Check application logs:
   ```bash
   docker logs lls-study-portal-test
   ```

### Issue: Static Files Return 404

**Symptom:**
```bash
curl -I http://localhost:8080/static/css/styles.css
# HTTP/1.1 404 Not Found
```

**Solution:**
1. Verify static files were copied to container:
   ```bash
   docker exec lls-study-portal-test ls -la /app/app/static/css/
   ```

2. Check Dockerfile has:
   ```dockerfile
   COPY . .
   ```

3. Verify `.dockerignore` doesn't exclude static files

### Issue: Templates Not Found

**Symptom:**
```
jinja2.exceptions.TemplateNotFound: index.html
```

**Solution:**
1. Verify templates directory was copied:
   ```bash
   docker exec lls-study-portal-test ls -la /app/templates/
   ```

2. Check Dockerfile copies all files:
   ```dockerfile
   COPY . .
   ```

### Issue: Permission Denied Errors

**Symptom:**
```
PermissionError: [Errno 13] Permission denied: '/app/...'
```

**Solution:**
The Dockerfile creates a non-root user. Verify ownership:
```bash
docker exec lls-study-portal-test ls -la /app/
```

All files should be owned by `appuser:appuser`.

### Issue: Port Already in Use

**Symptom:**
```
Error starting userland proxy: listen tcp4 0.0.0.0:8080: bind: address already in use
```

**Solution:**
1. Find what's using port 8080:
   ```bash
   lsof -i :8080
   ```

2. Either stop that process or use a different port:
   ```bash
   docker run -p 8081:8080 ...
   ```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Docker Build Test

on: [push, pull_request]

jobs:
  docker-test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Build Docker image
        run: docker build -t lls-study-portal:test .
      
      - name: Run automated tests
        run: ./scripts/test-docker.sh
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

### Cloud Build Example

```yaml
steps:
  # Build the container image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/lls-study-portal:$COMMIT_SHA', '.']
  
  # Run tests
  - name: 'gcr.io/$PROJECT_ID/lls-study-portal:$COMMIT_SHA'
    entrypoint: 'bash'
    args: ['./scripts/test-docker.sh']
    env:
      - 'ANTHROPIC_API_KEY=${_ANTHROPIC_API_KEY}'
```

---

## Best Practices

### Development

1. **Use Test API Keys**: Never use production API keys in local testing
2. **Disable Auth**: Set `AUTH_ENABLED=false` for local testing
3. **Check Logs**: Always review container logs after tests
4. **Clean Up**: Remove test containers and images regularly

### Production

1. **Enable Auth**: Set `AUTH_ENABLED=true` in production
2. **Use Secrets**: Store API keys in Secret Manager
3. **Health Checks**: Ensure health endpoint is accessible
4. **Resource Limits**: Set memory and CPU limits
5. **Logging**: Configure structured logging

### Security

1. **Non-Root User**: Container runs as `appuser` (UID 1000)
2. **Minimal Base Image**: Uses `python:3.11-slim`
3. **No Secrets in Image**: All secrets via environment variables
4. **Regular Updates**: Keep base image and dependencies updated

---

## Additional Resources

- [Dockerfile Reference](https://docs.docker.com/engine/reference/builder/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/docker/)
- [Cloud Run Documentation](https://cloud.google.com/run/docs)

---

## Support

For issues or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review container logs: `docker logs <container-name>`
3. Open an issue on GitHub with logs and error messages

