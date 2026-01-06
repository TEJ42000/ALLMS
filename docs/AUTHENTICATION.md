# Authentication System

## Overview

The LLS Study Portal uses **Google Cloud Identity-Aware Proxy (IAP)** for enterprise-grade authentication and authorization. The system provides:

- **Domain-based access control**: Primary access for `@mgms.eu` domain users
- **Allow list support**: External users can be granted access via admin-managed allow list
- **Role-based authorization**: Admin vs. regular user permissions
- **Development mode**: Auth bypass for local development

## Purpose and Goals

1. **Security**: Protect sensitive educational content and student data
2. **Flexibility**: Support both internal staff and external guest users
3. **Simplicity**: Leverage Google's OAuth infrastructure
4. **Compliance**: Foundation for GDPR and data protection requirements

## Security Model

### Authentication Layers

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Google IAP (Infrastructure Layer)                        │
│    - OAuth 2.0 authentication                               │
│    - JWT token generation                                   │
│    - Domain verification                                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Auth Middleware (Application Layer)                      │
│    - IAP header validation                                  │
│    - User extraction                                        │
│    - Public path bypass                                     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Auth Dependencies (Route Layer)                          │
│    - Domain validation (@mgms.eu)                           │
│    - Allow list checking                                    │
│    - Role-based access control                              │
└─────────────────────────────────────────────────────────────┘
```

## Architecture

### Components

#### 1. Google IAP (External)
- **Location**: Google Cloud infrastructure
- **Responsibility**: OAuth authentication, JWT generation
- **Headers Provided**:
  - `X-Goog-Authenticated-User-Email`: User's email
  - `X-Goog-Authenticated-User-Id`: User's Google ID
  - `X-Goog-IAP-JWT-Assertion`: Signed JWT token

#### 2. Auth Middleware (`app/middleware/auth_middleware.py`)
- **Responsibility**: Request interception and user extraction
- **Behavior**:
  - Skips authentication when `AUTH_ENABLED=false`
  - Bypasses public paths (`/health`, `/static/*`, `/api/docs`)
  - Validates IAP headers and attaches user to `request.state`
  - Returns 401 for unauthenticated requests to protected paths

#### 3. Auth Service (`app/services/auth_service.py`)
- **Responsibility**: Core authentication logic
- **Functions**:
  - `extract_user_from_iap_headers()`: Parse IAP headers
  - `is_user_authorized()`: Check domain + allow list
  - `get_auth_config()`: Load configuration singleton

#### 4. Auth Dependencies (`app/dependencies/auth.py`)
- **Responsibility**: Route-level access control
- **Dependencies**:
  - `get_current_user()`: Extract user from request
  - `require_authenticated()`: Ensure user is logged in
  - `require_mgms_domain()`: Require `@mgms.eu` domain (admin)
  - `require_allowed_user()`: Allow domain OR allow-listed users

#### 5. Allow List Service (`app/services/allow_list_service.py`)
- **Responsibility**: Manage external user access
- **Storage**: Firestore collection `allowed_users`
- **Features**:
  - CRUD operations for allow list entries
  - Expiration date support
  - Active/inactive status
  - Admin notes

### Authentication Flow

```
┌──────┐
│ User │
└──┬───┘
   │
   │ 1. Request to https://your-app.com/dashboard
   ↓
┌────────────────┐
│ Load Balancer  │
└───────┬────────┘
        │
        │ 2. Redirect to Google OAuth
        ↓
┌────────────────┐
│  Google IAP    │ ← User logs in with Google
└───────┬────────┘
        │
        │ 3. Validate credentials, generate JWT
        ↓
┌────────────────────────┐
│ IAP adds headers:      │
│ - User email           │
│ - User ID              │
│ - JWT assertion        │
└───────┬────────────────┘
        │
        │ 4. Forward request with headers
        ↓
┌────────────────────────┐
│ Auth Middleware        │
│ - Extract user         │
│ - Validate domain      │
│ - Check allow list     │
└───────┬────────────────┘
        │
        │ 5. Attach user to request.state
        ↓
┌────────────────────────┐
│ Route Handler          │
│ - Access user info     │
│ - Apply authorization  │
└────────────────────────┘
```

## Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AUTH_ENABLED` | No | `true` | Enable/disable authentication |
| `AUTH_DOMAIN` | Yes | `mgms.eu` | Primary allowed domain |
| `GOOGLE_CLIENT_ID` | Yes* | - | OAuth client ID for JWT verification |
| `IAP_AUDIENCE` | No | Auto-detected | IAP audience for JWT validation |
| `AUTH_MOCK_USER_EMAIL` | No** | `dev@mgms.eu` | Mock user email for local dev |
| `AUTH_MOCK_USER_IS_ADMIN` | No** | `true` | Mock user admin status |

\* Required in production when `AUTH_ENABLED=true`  
\*\* Only used when `AUTH_ENABLED=false`

### Feature Flags

- **`AUTH_ENABLED=true`**: Production mode with full IAP authentication
- **`AUTH_ENABLED=false`**: Development mode with mock user (no IAP required)

## Access Control

### Domain Restrictions

Users with `@mgms.eu` email addresses have full access to the application.

**Implementation**: `require_mgms_domain()` dependency checks user email domain.

### Allow List

External users (non-`@mgms.eu`) can be granted access via the allow list.

**Features**:
- Email-based access control
- Expiration dates
- Active/inactive status
- Admin notes for tracking

**Management**: See [ALLOW-LIST-MANAGEMENT.md](ALLOW-LIST-MANAGEMENT.md)

### Admin Access

Admin-only endpoints require `@mgms.eu` domain:
- `/api/admin/users/*` - User management
- `/api/admin/courses/*` - Course management  
- `/api/admin/usage/*` - Usage analytics

**Implementation**: Routes use `dependencies=[Depends(require_mgms_domain)]`

## Security Considerations

### IAP Security

✅ **Strengths**:
- OAuth 2.0 authentication handled by Google
- JWT tokens signed by Google
- Infrastructure-level protection
- No credentials stored in application

⚠️ **Important**:
- IAP must be the only entry point (disable direct Cloud Run access)
- Validate IAP headers in application code
- Use HTTPS only

### Header Validation

The application validates IAP headers to prevent spoofing:

```python
# Headers must match expected format
IAP_EMAIL_PATTERN = r"^accounts\.google\.com:(.+@.+)$"
IAP_ID_PATTERN = r"^accounts\.google\.com:(.+)$"
```

### JWT Verification

**Current Status**: Basic header validation implemented  
**Future**: Full JWT signature verification (see issue #77)

### Public Paths

These paths bypass authentication:
- `/health` - Health check endpoint
- `/static/*` - Static assets (CSS, JS, images)
- `/api/docs` - API documentation
- `/api/redoc` - ReDoc documentation
- `/openapi.json` - OpenAPI schema

## Troubleshooting

### Common Issues

#### 1. "401 Unauthorized" on protected endpoints

**Cause**: No user attached to request  
**Solutions**:
- Verify IAP is enabled and configured
- Check IAP headers are present
- Ensure user's domain is authorized
- Check allow list if external user

#### 2. "403 Forbidden - requires @mgms.eu domain"

**Cause**: User authenticated but not authorized  
**Solutions**:
- Verify user email domain
- Add user to allow list if external
- Check endpoint requires correct dependency

#### 3. Headers not received by application

**Cause**: Accessing Cloud Run directly instead of via Load Balancer  
**Solutions**:
- Use Load Balancer URL, not Cloud Run URL
- Verify IAP is enabled on backend service
- Check Cloud Run ingress settings

#### 4. Auth works in production but not locally

**Cause**: IAP not available in local development  
**Solutions**:
- Set `AUTH_ENABLED=false` in `.env`
- Configure mock user settings
- See [LOCAL-DEVELOPMENT.md](LOCAL-DEVELOPMENT.md)

### Debug Logging

Enable debug logging to troubleshoot auth issues:

```bash
# In .env
LOG_LEVEL=DEBUG
```

Check logs for:
- `Auth middleware: user authenticated` - Successful auth
- `Auth middleware: no IAP headers found` - Missing headers
- `User not authorized` - Failed authorization

### Verification Steps

1. **Check IAP status**:
   ```bash
   gcloud iap web get-iam-policy \
       --resource-type=backend-services \
       --service=lls-portal-backend
   ```

2. **Verify headers** (in application logs):
   ```python
   logger.debug(f"IAP Email Header: {request.headers.get('X-Goog-Authenticated-User-Email')}")
   ```

3. **Test allow list**:
   ```bash
   curl -H "Authorization: Bearer $(gcloud auth print-identity-token)" \
        https://your-app.com/api/admin/users/allowed
   ```

## Related Documentation

- [IAP Setup Guide](IAP-SETUP.md) - Configure Google Cloud IAP
- [Local Development](LOCAL-DEVELOPMENT.md) - Run locally without IAP
- [Allow List Management](ALLOW-LIST-MANAGEMENT.md) - Manage external user access

## References

- [Google Cloud IAP Documentation](https://cloud.google.com/iap/docs)
- [IAP Signed Headers](https://cloud.google.com/iap/docs/signed-headers-howto)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

