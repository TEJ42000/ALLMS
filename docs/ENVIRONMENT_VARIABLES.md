# Environment Variables

This document lists all environment variables used by ALLMS and their purposes.

## GDPR & Security

### GDPR_TOKEN_SECRET

**Required for Production:** ✅ Yes  
**Type:** String (hex)  
**Default:** Random (development only)

Secret key used for generating and validating GDPR-related secure tokens (account deletion, email verification, etc.).

**Security Requirements:**
- Must be at least 64 characters (32 bytes hex-encoded)
- Should be cryptographically random
- Must be kept secret and never committed to version control
- Should be rotated periodically (e.g., every 90 days)

**Generation:**
```bash
# Generate a secure random secret
python3 -c "import secrets; print(secrets.token_hex(32))"
```

**Example:**
```bash
GDPR_TOKEN_SECRET=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
```

**Storage:**
- **Development:** Can use random generation (tokens invalidated on restart)
- **Production:** Store in Google Secret Manager or similar
- **Docker:** Pass via environment variable or secrets file
- **Kubernetes:** Store in Kubernetes Secrets

**Consequences of Not Setting:**
- ⚠️ Development: Random secret generated on startup (tokens invalidated on restart)
- ❌ Production: Application will log warning and use random secret (NOT RECOMMENDED)

**Token Rotation:**
When rotating the secret:
1. Generate new secret
2. Keep old secret for grace period (e.g., 30 minutes)
3. Validate tokens with both old and new secrets
4. After grace period, remove old secret

---

## Database

### FIRESTORE_PROJECT_ID

**Required for Production:** ✅ Yes  
**Type:** String  
**Default:** None

Google Cloud Project ID for Firestore database.

**Example:**
```bash
FIRESTORE_PROJECT_ID=allms-production
```

### FIRESTORE_CREDENTIALS

**Required for Production:** ✅ Yes (if not using default credentials)  
**Type:** JSON string or file path  
**Default:** Application Default Credentials

Path to Google Cloud service account credentials JSON file.

**Example:**
```bash
FIRESTORE_CREDENTIALS=/path/to/service-account-key.json
```

---

## Rate Limiting

### RATE_LIMIT_BACKEND

**Required for Production:** ⚠️ Recommended  
**Type:** String (enum)  
**Default:** `memory`  
**Options:** `memory`, `redis`, `database`

Backend to use for rate limiting.

**Example:**
```bash
RATE_LIMIT_BACKEND=redis
```

**Recommendations:**
- **Development:** `memory` (simple, no setup)
- **Production:** `redis` (distributed, persistent)

### REDIS_HOST

**Required if:** `RATE_LIMIT_BACKEND=redis`  
**Type:** String  
**Default:** `localhost`

Redis server hostname.

**Example:**
```bash
REDIS_HOST=redis.example.com
```

### REDIS_PORT

**Required if:** `RATE_LIMIT_BACKEND=redis`  
**Type:** Integer  
**Default:** `6379`

Redis server port.

**Example:**
```bash
REDIS_PORT=6379
```

### REDIS_PASSWORD

**Required if:** Redis requires authentication  
**Type:** String  
**Default:** None

Redis server password.

**Example:**
```bash
REDIS_PASSWORD=your-redis-password
```

### REDIS_DB

**Required if:** `RATE_LIMIT_BACKEND=redis`  
**Type:** Integer  
**Default:** `0`

Redis database number.

**Example:**
```bash
REDIS_DB=0
```

### REDIS_SSL

**Required if:** Using Redis with SSL  
**Type:** Boolean  
**Default:** `false`

Enable SSL/TLS for Redis connection.

**Example:**
```bash
REDIS_SSL=true
```

---

## Rate Limit Configuration

### RATE_LIMIT_CONSENT_MAX

**Required:** ❌ No  
**Type:** Integer  
**Default:** `100`

Maximum consent changes per user per window.

**Example:**
```bash
RATE_LIMIT_CONSENT_MAX=100
```

### RATE_LIMIT_CONSENT_WINDOW

**Required:** ❌ No  
**Type:** Integer (minutes)  
**Default:** `60`

Time window for consent rate limiting.

**Example:**
```bash
RATE_LIMIT_CONSENT_WINDOW=60
```

### RATE_LIMIT_EXPORT_MAX

**Required:** ❌ No  
**Type:** Integer  
**Default:** `5`

Maximum data exports per user per window.

**Example:**
```bash
RATE_LIMIT_EXPORT_MAX=5
```

### RATE_LIMIT_EXPORT_WINDOW

**Required:** ❌ No  
**Type:** Integer (minutes)  
**Default:** `1440` (24 hours)

Time window for export rate limiting.

**Example:**
```bash
RATE_LIMIT_EXPORT_WINDOW=1440
```

### RATE_LIMIT_DELETE_MAX

**Required:** ❌ No  
**Type:** Integer  
**Default:** `3`

Maximum deletion requests per user per window.

**Example:**
```bash
RATE_LIMIT_DELETE_MAX=3
```

### RATE_LIMIT_DELETE_WINDOW

**Required:** ❌ No  
**Type:** Integer (minutes)  
**Default:** `1440` (24 hours)

Time window for deletion rate limiting.

**Example:**
```bash
RATE_LIMIT_DELETE_WINDOW=1440
```

---

## AI Services

### ANTHROPIC_API_KEY

**Required for Production:** ✅ Yes  
**Type:** String  
**Default:** None

API key for Anthropic Claude API (AI tutoring features).

**Example:**
```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
```

**Security:**
- Never commit to version control
- Store in Google Secret Manager
- Rotate periodically

---

## Email Service

### EMAIL_SERVICE_PROVIDER

**Required for Production:** ⚠️ Recommended  
**Type:** String (enum)  
**Default:** `console` (logs to console)  
**Options:** `console`, `sendgrid`, `ses`, `smtp`

Email service provider for sending GDPR confirmation emails.

**Example:**
```bash
EMAIL_SERVICE_PROVIDER=sendgrid
```

### SENDGRID_API_KEY

**Required if:** `EMAIL_SERVICE_PROVIDER=sendgrid`  
**Type:** String  
**Default:** None

SendGrid API key.

**Example:**
```bash
SENDGRID_API_KEY=SG.xxx
```

### AWS_SES_REGION

**Required if:** `EMAIL_SERVICE_PROVIDER=ses`  
**Type:** String  
**Default:** `us-east-1`

AWS SES region.

**Example:**
```bash
AWS_SES_REGION=us-east-1
```

### SMTP_HOST

**Required if:** `EMAIL_SERVICE_PROVIDER=smtp`  
**Type:** String  
**Default:** None

SMTP server hostname.

**Example:**
```bash
SMTP_HOST=smtp.gmail.com
```

### SMTP_PORT

**Required if:** `EMAIL_SERVICE_PROVIDER=smtp`  
**Type:** Integer  
**Default:** `587`

SMTP server port.

**Example:**
```bash
SMTP_PORT=587
```

### SMTP_USERNAME

**Required if:** `EMAIL_SERVICE_PROVIDER=smtp`  
**Type:** String  
**Default:** None

SMTP username.

**Example:**
```bash
SMTP_USERNAME=your-email@example.com
```

### SMTP_PASSWORD

**Required if:** `EMAIL_SERVICE_PROVIDER=smtp`  
**Type:** String  
**Default:** None

SMTP password.

**Example:**
```bash
SMTP_PASSWORD=your-password
```

---

## Example Configuration Files

### Development (.env.development)

```bash
# GDPR (development - random secret is OK)
# GDPR_TOKEN_SECRET will be auto-generated

# Database
FIRESTORE_PROJECT_ID=allms-dev

# Rate Limiting (in-memory is OK for dev)
RATE_LIMIT_BACKEND=memory

# AI Services
ANTHROPIC_API_KEY=sk-ant-api03-dev-key

# Email (console logging is OK for dev)
EMAIL_SERVICE_PROVIDER=console
```

### Production (.env.production)

```bash
# GDPR (REQUIRED - use Google Secret Manager)
GDPR_TOKEN_SECRET=${GDPR_TOKEN_SECRET}

# Database
FIRESTORE_PROJECT_ID=allms-production
FIRESTORE_CREDENTIALS=/secrets/firestore-credentials.json

# Rate Limiting (Redis required for production)
RATE_LIMIT_BACKEND=redis
REDIS_HOST=redis.production.internal
REDIS_PORT=6379
REDIS_PASSWORD=${REDIS_PASSWORD}
REDIS_DB=0
REDIS_SSL=true

# AI Services
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}

# Email (SendGrid recommended)
EMAIL_SERVICE_PROVIDER=sendgrid
SENDGRID_API_KEY=${SENDGRID_API_KEY}
```

---

## Security Best Practices

1. **Never commit secrets to version control**
   - Use `.env` files (add to `.gitignore`)
   - Use environment variables
   - Use secret management services

2. **Use different secrets for each environment**
   - Development secrets ≠ Production secrets
   - Rotate production secrets regularly

3. **Store production secrets securely**
   - Google Secret Manager (recommended)
   - AWS Secrets Manager
   - HashiCorp Vault
   - Kubernetes Secrets

4. **Rotate secrets periodically**
   - GDPR_TOKEN_SECRET: Every 90 days
   - API keys: Every 180 days
   - Database credentials: Every 365 days

5. **Monitor secret usage**
   - Log secret access (not values!)
   - Alert on unusual patterns
   - Audit secret rotation

---

## Related Documentation

- [GDPR Implementation Guide](GDPR_IMPLEMENTATION.md)
- [Rate Limiting Guide](GDPR_RATE_LIMITING.md)
- [Deployment Guide](DEPLOYMENT.md)

