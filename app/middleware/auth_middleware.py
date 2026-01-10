"""Authentication Middleware for Google IAP and OAuth Integration.

This middleware intercepts all incoming requests and:
1. Checks if authentication is enabled
2. Skips authentication for public paths
3. Based on AUTH_MODE, validates either:
   - OAuth session cookies (auth_mode="oauth")
   - IAP headers (auth_mode="iap")
   - Both with OAuth priority (auth_mode="dual")
4. Attaches user to request.state for downstream use
5. Redirects unauthenticated HTML requests to login page
"""

import logging
from typing import Optional, Set
from urllib.parse import quote

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.models.auth_models import MockUser, User
from app.services.auth_service import (
    get_auth_config,
    is_user_authorized,
)
from app.services.session_service import get_session_service

logger = logging.getLogger(__name__)

# Public paths that don't require authentication
# Uses exact match or prefix match for paths ending with *
PUBLIC_PATHS: Set[str] = {
    "/",  # Homepage - publicly accessible to meet Google OAuth verification requirements
    "/health",
    "/api/docs",
    "/api/redoc",
    "/openapi.json",
    "/auth/login",
    "/auth/callback",
    "/auth/logout",
    "/privacy-policy",
    "/terms-of-service",
    "/cookie-policy",
}

# Path prefixes that don't require authentication
PUBLIC_PATH_PREFIXES: tuple[str, ...] = (
    "/static/",
)


class AuthMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for Google IAP and OAuth authentication.

    This middleware supports three authentication modes (via AUTH_MODE):
    - "iap": Uses Google Cloud IAP headers only (legacy)
    - "oauth": Uses application-level OAuth sessions only
    - "dual": Tries OAuth first, falls back to IAP (for migration)

    For all modes, it:
    - Skips auth when AUTH_ENABLED=false (development mode)
    - Bypasses auth for public paths (health, docs, static files, login)
    - Returns 401 JSON for API requests without authentication
    - Redirects browser requests to login page without authentication

    Note: Auth status logging is handled by main.py startup_event,
    not by this middleware (avoids thread-safety issues).
    """

    def __init__(self, app: ASGIApp) -> None:
        """Initialize the authentication middleware."""
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        """Process each request through authentication checks.

        Args:
            request: The incoming HTTP request
            call_next: The next middleware/handler in the chain

        Returns:
            The response from the next handler or an error response
        """
        config = get_auth_config()

        # If auth is disabled, attach mock user and continue
        if not config.auth_enabled:
            request.state.user = MockUser()
            return await call_next(request)

        # Skip auth for public paths
        if self._is_public_path(request.url.path):
            request.state.user = None  # No user for public paths
            return await call_next(request)

        # Authenticate based on configured mode
        user: Optional[User] = None
        reason: str = ""

        if config.auth_mode == "oauth":
            # OAuth-only mode: check session cookie
            user, reason = await self._authenticate_oauth(request, config)
        elif config.auth_mode == "iap":
            # IAP-only mode: check IAP headers
            is_authorized, user, reason = await is_user_authorized(request)
            if not is_authorized:
                user = None
        else:  # dual mode
            # Try OAuth first, fallback to IAP
            user, reason = await self._authenticate_oauth(request, config)
            if user is None:
                is_authorized, user, reason = await is_user_authorized(request)
                if not is_authorized:
                    user = None

        # Handle unauthenticated requests
        if user is None:
            return self._handle_unauthenticated(request, reason)

        # Attach user to request state for downstream use
        request.state.user = user
        logger.debug("User %s authenticated for %s", user.email, request.url.path)

        return await call_next(request)

    async def _authenticate_oauth(
        self, request: Request, config
    ) -> tuple[Optional[User], str]:
        """Authenticate using OAuth session cookie.

        Args:
            request: The incoming request
            config: Auth configuration

        Returns:
            Tuple of (User or None, reason message)
        """
        session_id = request.cookies.get(config.session_cookie_name)

        if not session_id:
            return None, "No session cookie found"

        session_service = get_session_service()
        is_valid, user = await session_service.validate_session(session_id)

        if not is_valid or user is None:
            return None, "Invalid or expired session"

        return user, "OAuth session valid"

    def _handle_unauthenticated(self, request: Request, reason: str):
        """Handle unauthenticated request based on request type.

        - API requests (Accept: application/json or /api/ path): return 401 JSON
        - Browser requests: redirect to login page

        Args:
            request: The incoming request
            reason: Reason for authentication failure

        Returns:
            JSONResponse or RedirectResponse
        """
        accept_header = request.headers.get("accept", "")
        path = request.url.path

        # Check if this is an API request
        is_api_request = (
            "application/json" in accept_header
            or path.startswith("/api/")
            or request.headers.get("x-requested-with") == "XMLHttpRequest"
        )

        if is_api_request:
            logger.warning("Authentication failed for API %s: %s", path, reason)
            return JSONResponse(
                status_code=401,
                content={"detail": "Not authenticated", "reason": reason}
            )

        # Browser request - redirect to login
        logger.info("Redirecting unauthenticated user to login: %s", path)
        next_url = quote(str(request.url), safe="")
        return RedirectResponse(
            url=f"/auth/login?next={next_url}",
            status_code=302
        )

    def _is_public_path(self, path: str) -> bool:
        """Check if a path is public (doesn't require authentication).

        Args:
            path: The request URL path

        Returns:
            True if the path is public, False otherwise
        """
        # Check exact matches
        if path in PUBLIC_PATHS:
            return True

        # Check prefix matches (for static files, etc.)
        if path.startswith(PUBLIC_PATH_PREFIXES):
            return True

        return False

