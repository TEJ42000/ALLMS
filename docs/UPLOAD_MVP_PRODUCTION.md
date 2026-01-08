# Upload Feature: MVP vs Production Readiness

**Issue #200 - Phase 1 Implementation**

This document outlines what is MVP-ready versus what needs to be enhanced for production deployment.

---

## ✅ Production-Ready Features

### Security
- ✅ **Authentication Integration**: Fully integrated with existing IAP authentication system
  - Uses `require_allowed_user` dependency injection
  - Works with both @mgms.eu domain users and allow-listed external users
  - Properly extracts user_id from authenticated user
  
- ✅ **CSRF Protection**: Origin/Referer header validation
  - Configurable via `ALLOWED_ORIGINS` environment variable
  - Rejects requests without proper headers
  - Supports multiple production domains
  
- ✅ **Path Traversal Prevention**: Comprehensive sanitization
  - Validates course_id against dangerous patterns
  - Blocks directory traversal attempts (../, \\, etc.)
  - Prevents shell injection characters
  
- ✅ **File Type Validation**: Whitelist-based approach
  - Extension validation (pdf, docx, pptx, txt, md, html)
  - Magic number validation for binary files
  - Content-type verification
  
- ✅ **File Size Limits**: 25MB maximum
  - Prevents DoS via large uploads
  - Configurable via `MAX_SIZE_MB` constant
  
- ✅ **Race Condition Handling**: Safe file cleanup
  - Uses `unlink(missing_ok=True)` for Python 3.8+
  - Graceful error handling if file already deleted

### Functionality
- ✅ **Text Extraction**: Uses existing `text_extractor.py` service
  - Supports PDF, DOCX, PPTX, images (OCR), HTML, text
  - Handles slide archives and complex documents
  
- ✅ **Firestore Integration**: Metadata storage
  - Stores upload metadata in `courses/{course_id}/materials` collection
  - Tracks extraction status and errors
  - Compatible with existing course materials system
  
- ✅ **Error Handling**: Comprehensive error responses
  - Sanitized error messages (no path disclosure)
  - Proper HTTP status codes
  - Detailed logging for debugging

---

## ⚠️ MVP-Only Features (Needs Production Enhancement)

### 1. Rate Limiting (CRITICAL for Production)

**Current Implementation (MVP):**
```python
# In-memory rate limiting
rate_limit_store: Dict[str, List[float]] = defaultdict(list)
```

**Limitations:**
- ❌ Not suitable for multi-instance deployments
- ❌ Resets on application restart
- ❌ No distributed state sharing
- ❌ Memory grows unbounded (no cleanup of old entries beyond window)

**Production Requirements:**
```python
# Use Redis for distributed rate limiting
from redis import Redis
from slowapi import Limiter
from slowapi.util import get_remote_address

redis_client = Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    password=os.getenv("REDIS_PASSWORD"),
    db=int(os.getenv("REDIS_DB", 0)),
    ssl=os.getenv("REDIS_SSL", "false").lower() == "true"
)

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=f"redis://{redis_client.connection_pool.connection_kwargs['host']}"
)

@router.post("")
@limiter.limit("10/minute")
async def upload_file(...):
    ...
```

**Action Items:**
- [ ] Add Redis to infrastructure (Cloud Memorystore)
- [ ] Install `slowapi` and `redis` packages
- [ ] Configure Redis connection via environment variables
- [ ] Replace in-memory rate limiting with Redis-backed limiter
- [ ] Add rate limit headers to responses (X-RateLimit-Limit, X-RateLimit-Remaining)

---

### 2. CSRF Protection (MEDIUM Priority)

**Current Implementation (MVP):**
```python
# Origin/Referer header validation
def validate_csrf(origin: Optional[str] = None, referer: Optional[str] = None):
    if origin and origin.startswith(allowed_origin):
        return
    # Fallback to Referer
```

**Limitations:**
- ⚠️ Relies on browser-provided headers (can be missing in some scenarios)
- ⚠️ No token-based verification
- ⚠️ Not suitable for API-only clients

**Production Recommendations:**
```python
# Add session-based CSRF tokens
from fastapi_csrf_protect import CsrfProtect

@router.post("")
async def upload_file(
    csrf_protect: CsrfProtect = Depends(),
    ...
):
    await csrf_protect.validate_csrf(request)
    ...
```

**Action Items:**
- [ ] Evaluate if API clients need upload access (if yes, use API keys instead)
- [ ] If web-only, current implementation is acceptable
- [ ] Consider adding CSRF tokens for defense-in-depth

---

### 3. File Storage (MEDIUM Priority)

**Current Implementation (MVP):**
```python
# Local filesystem storage
UPLOAD_DIR = Path("Materials/uploads")
file_path = UPLOAD_DIR / course_id / safe_filename
```

**Limitations:**
- ⚠️ Not suitable for multi-instance deployments (files on one instance not visible to others)
- ⚠️ No automatic backups
- ⚠️ Limited scalability
- ⚠️ Ephemeral storage on Cloud Run (files lost on redeploy)

**Production Requirements:**
```python
# Use Google Cloud Storage
from google.cloud import storage

storage_client = storage.Client()
bucket = storage_client.bucket(os.getenv("UPLOAD_BUCKET", "allms-uploads"))

blob = bucket.blob(f"uploads/{course_id}/{safe_filename}")
blob.upload_from_file(file.file)

# Store GCS path in Firestore
material.storagePath = f"gs://{bucket.name}/{blob.name}"
```

**Action Items:**
- [ ] Create GCS bucket for uploads (`allms-uploads`)
- [ ] Configure bucket lifecycle policies (auto-delete after X days if not referenced)
- [ ] Update upload endpoint to use GCS
- [ ] Update text extraction to read from GCS
- [ ] Add signed URL generation for download access

---

### 4. Background Processing (LOW Priority)

**Current Implementation (MVP):**
```python
# Synchronous text extraction
result = extract_text(file_path)
```

**Limitations:**
- ⚠️ Blocks request until extraction completes
- ⚠️ Timeout risk for large files
- ⚠️ Poor user experience (long wait times)

**Production Recommendations:**
```python
# Use Cloud Tasks for background processing
from google.cloud import tasks_v2

tasks_client = tasks_v2.CloudTasksClient()
task = {
    "http_request": {
        "http_method": tasks_v2.HttpMethod.POST,
        "url": f"{base_url}/api/upload/{material_id}/extract",
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"course_id": course_id}).encode()
    }
}
tasks_client.create_task(parent=queue_path, task=task)

# Return immediately with status="processing"
return {"status": "success", "material_id": material_id, "processing_status": "queued"}
```

**Action Items:**
- [ ] Create Cloud Tasks queue for upload processing
- [ ] Add background extraction endpoint
- [ ] Update frontend to poll for extraction status
- [ ] Add WebSocket support for real-time status updates (optional)

---

## 📋 Production Deployment Checklist

### Before Deploying to Production

#### Critical (Must Fix)
- [ ] Replace in-memory rate limiting with Redis
- [ ] Migrate file storage to Google Cloud Storage
- [ ] Set `ALLOWED_ORIGINS` environment variable with production domains
- [ ] Verify authentication is enabled (`AUTH_ENABLED=true`)
- [ ] Test with real IAP headers (not mock user)

#### High Priority (Should Fix)
- [ ] Add background processing for large files
- [ ] Implement upload progress tracking
- [ ] Add file virus scanning (Cloud Security Scanner)
- [ ] Set up monitoring and alerting for upload failures

#### Medium Priority (Nice to Have)
- [ ] Add CSRF token-based protection
- [ ] Implement upload quotas per user
- [ ] Add file deduplication (hash-based)
- [ ] Create admin dashboard for upload management

#### Low Priority (Future Enhancement)
- [ ] Add batch upload support
- [ ] Implement resumable uploads for large files
- [ ] Add image compression/optimization
- [ ] Support for additional file types (ZIP, EPUB, etc.)

---

## 🔧 Configuration Reference

### Environment Variables

```bash
# Required for Production
ALLOWED_ORIGINS=https://allms.app,https://www.allms.app
AUTH_ENABLED=true
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com

# Recommended for Production
REDIS_HOST=10.0.0.3  # Cloud Memorystore IP
REDIS_PORT=6379
UPLOAD_BUCKET=allms-uploads
MAX_UPLOAD_SIZE_MB=25

# Optional
UPLOAD_VIRUS_SCAN=true
UPLOAD_BACKGROUND_PROCESSING=true
```

### Code Constants

```python
# app/routes/upload.py
ALLOWED_EXTENSIONS = {"pdf", "docx", "pptx", "txt", "md", "html"}
MAX_SIZE_MB = 25
RATE_LIMIT_UPLOADS = 10  # per minute
RATE_LIMIT_WINDOW = 60  # seconds
```

---

## 🧪 Testing Recommendations

### MVP Testing (Current)
- ✅ Unit tests for validation functions
- ✅ Integration tests with mock Firestore
- ✅ CSRF protection tests
- ✅ Authentication integration tests

### Production Testing (Required)
- [ ] Load testing with concurrent uploads
- [ ] Rate limit testing with distributed instances
- [ ] GCS integration tests
- [ ] Background processing tests
- [ ] Virus scanning tests
- [ ] Failover and recovery tests

---

## 📊 Monitoring and Observability

### Metrics to Track
- Upload success/failure rate
- Average upload time
- File size distribution
- Rate limit hits per user
- Storage usage growth
- Extraction success rate

### Alerts to Configure
- Upload failure rate > 5%
- Average upload time > 30s
- Storage usage > 80% of quota
- Rate limit abuse (same user hitting limit repeatedly)
- Extraction failures > 10%

---

## 🔒 Security Considerations

### Current Security Posture
- ✅ Authentication required (IAP integration)
- ✅ CSRF protection (Origin/Referer)
- ✅ Path traversal prevention
- ✅ File type validation
- ✅ File size limits
- ✅ Content validation (magic numbers)

### Additional Production Security
- [ ] Virus/malware scanning (ClamAV or Cloud Security Scanner)
- [ ] Content Security Policy headers
- [ ] Rate limiting per user (not just per IP)
- [ ] Audit logging of all uploads
- [ ] Encryption at rest (GCS default)
- [ ] Encryption in transit (HTTPS enforced)

---

## 📝 Summary

**MVP Status:** ✅ Ready for internal testing with limited users

**Production Status:** ⚠️ Requires enhancements (primarily rate limiting and storage)

**Estimated Effort to Production-Ready:** 2-3 days
- Day 1: Redis rate limiting + GCS storage
- Day 2: Background processing + monitoring
- Day 3: Testing + documentation

**Risk Assessment:**
- **Low Risk:** Authentication, CSRF, validation (production-ready)
- **Medium Risk:** File storage (works but not scalable)
- **High Risk:** Rate limiting (vulnerable to abuse in multi-instance setup)

---

## 📚 Related Documentation

- [CLAUDE.md](../CLAUDE.md) - Overall architecture and implementation guide
- [AUTHENTICATION.md](AUTHENTICATION.md) - IAP authentication details
- [DOCUMENT_UPLOAD_FEATURE.md](DOCUMENT_UPLOAD_FEATURE.md) - Original feature spec
- [ENVIRONMENT_VARIABLES.md](ENVIRONMENT_VARIABLES.md) - Configuration reference

