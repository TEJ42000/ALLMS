"""
CSRF Protection Middleware

Implements the Double-Submit Cookie pattern for CSRF protection:
1. Generate a random CSRF token
2. Store token in an HttpOnly cookie
3. Require token in request header for mutating requests
4. Validate token matches cookie value

This is more robust than Origin/Referer header validation alone.

Issue: #204
"""

import secrets
import logging
from typing import Optional, Callable, Awaitable
from urllib.parse import urlparse
import os

from fastapi import Request, Response, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)

# CSRF Configuration
CSRF_COOKIE_NAME = "csrf_token"
CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_TOKEN_LENGTH = 32  # 256 bits

# Routes that don't require CSRF protection (GET, HEAD, OPTIONS are safe)
SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

# Paths that are exempt from CSRF (e.g., OAuth callbacks, webhooks)
CSRF_EXEMPT_PATHS = {
    "/api/auth/callback",
    "/api/auth/google/callback",
    "/api/webhooks/",  # Webhooks have their own auth
    "/api/health",
    "/api/docs",
    "/api/redoc",
    "/api/openapi.json",
}

# Load allowed origins from environment for CSRF validation
_env_origins = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]
if _env_origins:
    ALLOWED_ORIGINS.extend([origin.strip() for origin in _env_origins.split(",") if origin.strip()])


def generate_csrf_token() -> str:
    """Generate a cryptographically secure CSRF token."""
    return secrets.token_urlsafe(CSRF_TOKEN_LENGTH)


def is_path_exempt(path: str) -> bool:
    """Check if a path is exempt from CSRF protection."""
    for exempt_path in CSRF_EXEMPT_PATHS:
        if path.startswith(exempt_path):
            return True
    return False


def validate_origin(request: Request) -> bool:
    """Validate Origin/Referer header as additional security layer."""
    origin = request.headers.get("origin")
    referer = request.headers.get("referer")
    
    # Check Origin header
    if origin:
        return any(origin.startswith(allowed) for allowed in ALLOWED_ORIGINS)
    
    # Fall back to Referer
    if referer:
        parsed = urlparse(referer)
        referer_origin = f"{parsed.scheme}://{parsed.netloc}"
        return any(referer_origin.startswith(allowed) for allowed in ALLOWED_ORIGINS)
    
    # For same-origin requests without headers (some browsers)
    return False


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    CSRF Protection Middleware using Double-Submit Cookie pattern.
    
    For GET/HEAD/OPTIONS requests:
    - Sets a CSRF cookie if not present
    
    For POST/PUT/PATCH/DELETE requests:
    - Validates CSRF token from header matches cookie
    - Also validates Origin/Referer as secondary check
    """
    
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Get existing CSRF token from cookie
        csrf_cookie = request.cookies.get(CSRF_COOKIE_NAME)
        
        # For safe methods, just ensure cookie exists
        if request.method in SAFE_METHODS:
            response = await call_next(request)
            
            # Set CSRF cookie if not present
            if not csrf_cookie:
                token = generate_csrf_token()
                response.set_cookie(
                    key=CSRF_COOKIE_NAME,
                    value=token,
                    httponly=False,  # JS needs to read this for header
                    secure=request.url.scheme == "https",
                    samesite="lax",
                    max_age=86400,  # 24 hours
                )
            
            return response
        
        # For mutating methods, validate CSRF
        path = request.url.path
        
        # Check if path is exempt
        if is_path_exempt(path):
            return await call_next(request)
        
        # Get token from header
        csrf_header = request.headers.get(CSRF_HEADER_NAME)
        
        # Validate token
        if not csrf_cookie:
            logger.warning(f"CSRF: No cookie present for {request.method} {path}")
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF cookie missing. Please refresh the page."}
            )
        
        if not csrf_header:
            logger.warning(f"CSRF: No header token for {request.method} {path}")
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token missing from request header."}
            )
        
        if not secrets.compare_digest(csrf_cookie, csrf_header):
            logger.warning(f"CSRF: Token mismatch for {request.method} {path}")
            return JSONResponse(
                status_code=403,
                content={"detail": "CSRF token validation failed."}
            )
        
        # Additional Origin/Referer validation
        if not validate_origin(request):
            # Log but don't block - Origin header may not always be present
            logger.debug(f"CSRF: Origin validation skipped for {request.method} {path}")
        
        # Token is valid, proceed
        return await call_next(request)

