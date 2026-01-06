"""Authentication Middleware for Google IAP Integration.

This middleware intercepts all incoming requests and:
1. Checks if authentication is enabled
2. Skips authentication for public paths
3. Validates IAP headers and extracts user info
4. Attaches user to request.state for downstream use
"""

import logging
from typing import Set

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.models.auth_models import MockUser
from app.services.auth_service import (
    get_auth_config,
    is_user_authorized,
)

logger = logging.getLogger(__name__)

# Public paths that don't require authentication
# Uses exact match or prefix match for paths ending with *
PUBLIC_PATHS: Set[str] = {
    "/health",
    "/api/docs",
    "/api/redoc",
    "/openapi.json",
}

# Path prefixes that don't require authentication
PUBLIC_PATH_PREFIXES: tuple[str, ...] = (
    "/static/",
)


class AuthMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for Google IAP authentication.

    This middleware:
    - Skips auth when AUTH_ENABLED=false (development mode)
    - Bypasses auth for public paths (health, docs, static files)
    - Validates IAP headers and attaches user to request.state
    - Returns 401 for unauthenticated requests to protected paths

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

        # Validate user authorization
        is_authorized, user, reason = await is_user_authorized(request)

        if not is_authorized:
            logger.warning(
                "Authentication failed for %s: %s",
                request.url.path,
                reason
            )
            return JSONResponse(
                status_code=401,
                content={"detail": "Not authenticated", "reason": reason}
            )

        # Attach user to request state for downstream use
        request.state.user = user
        logger.debug("User %s authenticated for %s", user.email, request.url.path)

        return await call_next(request)

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

