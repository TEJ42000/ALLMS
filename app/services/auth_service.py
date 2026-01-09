"""Authentication Service for Google IAP Integration.

Provides authentication functionality including:
- IAP header validation and user extraction
- Domain validation for access control
- Allow list checking against Firestore

This service is used by the authentication middleware to validate
requests and extract user information from Google IAP headers.
"""

import logging
import re
from typing import Optional

from fastapi import Request

from app.models.auth_models import AuthConfig, User, MockUser

logger = logging.getLogger(__name__)

# Load auth configuration from environment (thread-safe singleton via lru_cache)
from functools import lru_cache


@lru_cache(maxsize=1)
def get_auth_config() -> AuthConfig:
    """Get the authentication configuration singleton (thread-safe)."""
    return AuthConfig()


# ============================================================================
# IAP Header Constants
# ============================================================================

# Google IAP header names
IAP_USER_EMAIL_HEADER = "X-Goog-Authenticated-User-Email"
IAP_USER_ID_HEADER = "X-Goog-Authenticated-User-Id"
IAP_JWT_HEADER = "X-Goog-IAP-JWT-Assertion"  # TODO: Use in Phase 2 for JWT verification

# ⚠️ SECURITY WARNING: Phase 1 does NOT verify JWT signatures and is vulnerable
# to header spoofing. JWT verification will be implemented in Phase 2.
# DO NOT deploy to production with AUTH_ENABLED=true until JWT verification is added.

# Pattern for IAP email header value: "accounts.google.com:user@domain.com"
IAP_EMAIL_PATTERN = re.compile(r"^accounts\.google\.com:(.+@.+)$", re.IGNORECASE)
IAP_ID_PATTERN = re.compile(r"^accounts\.google\.com:(.+)$", re.IGNORECASE)


# ============================================================================
# Custom Exceptions
# ============================================================================

class AuthenticationError(Exception):
    """Raised when authentication fails."""
    pass


class AuthorizationError(Exception):
    """Raised when authorization fails (authenticated but not allowed)."""
    pass


# ============================================================================
# Core Authentication Functions
# ============================================================================

def extract_user_from_iap_headers(request: Request) -> Optional[User]:
    """
    Extract user information from Google IAP headers.

    Args:
        request: FastAPI request object

    Returns:
        User object if valid IAP headers present, None otherwise
    """
    config = get_auth_config()

    # Get IAP headers
    email_header = request.headers.get(IAP_USER_EMAIL_HEADER)
    id_header = request.headers.get(IAP_USER_ID_HEADER)

    if not email_header or not id_header:
        logger.debug("Missing IAP headers: email=%s, id=%s", 
                     bool(email_header), bool(id_header))
        return None

    # Parse email from header (format: "accounts.google.com:user@domain.com")
    email_match = IAP_EMAIL_PATTERN.match(email_header)
    if not email_match:
        logger.warning("Invalid IAP email header format: %s", email_header)
        return None

    email = email_match.group(1).lower().strip()

    # Parse user ID from header
    id_match = IAP_ID_PATTERN.match(id_header)
    if not id_match:
        logger.warning("Invalid IAP user ID header format: %s", id_header)
        return None

    user_id = id_match.group(1)

    # Extract domain from email
    if "@" not in email:
        logger.warning("Invalid email format (no @): %s", email)
        return None

    domain = email.split("@")[1].lower()

    # Determine admin status (admin if from primary domain)
    is_admin = domain == config.auth_domain.lower()

    user = User(
        email=email,
        user_id=user_id,
        domain=domain,
        is_admin=is_admin
    )

    logger.debug("Extracted user from IAP headers: %s", user)
    return user


def validate_domain(user: User) -> bool:
    """
    Check if user is from the allowed domain.

    Args:
        user: User object to validate

    Returns:
        True if user is from the primary domain (mgms.eu)
    """
    config = get_auth_config()
    return user.domain.lower() == config.auth_domain.lower()


def get_mock_user() -> MockUser:
    """
    Get a mock user for development mode.

    Returns:
        MockUser with settings from environment variables
    """
    return MockUser()


def is_auth_enabled() -> bool:
    """Check if authentication is enabled."""
    return get_auth_config().auth_enabled


async def check_allow_list(email: str) -> bool:
    """
    Check if an email is on the allow list in Firestore.

    Uses the AllowListService for consistent allow list checking.

    Args:
        email: Email address to check

    Returns:
        True if email is on the active, non-expired allow list
    """
    # Import here to avoid circular imports
    try:
        from app.services.allow_list_service import get_allow_list_service
    except ImportError:
        logger.warning("Allow list service not available, check skipped")
        return False

    try:
        service = get_allow_list_service()

        if not service.is_available:
            logger.warning("Allow list service is not available")
            return False

        # Use the service's is_user_allowed method which checks:
        # - User exists
        # - active=True
        # - Not expired
        is_allowed = service.is_user_allowed(email)

        if is_allowed:
            logger.info("User found in allow list and has effective access: %s", email)
        else:
            # Get more details for logging
            entry = service.get_user(email)
            if entry is None:
                logger.debug("Email not found in allow list: %s", email)
            else:
                logger.info(
                    "Allow list entry exists but not effective (active=%s, expired=%s): %s",
                    entry.active, entry.is_expired, email
                )

        return is_allowed

    except Exception as e:
        # Log unexpected errors with full traceback but don't crash
        logger.exception("Unexpected error checking allow list for %s: %s", email, str(e))
        return False


async def is_user_authorized(request: Request) -> tuple[bool, Optional[User], str]:
    """
    Check if a request is authorized.

    This is the main entry point for authentication checks.
    It handles:
    1. Auth disabled mode (returns mock user)
    2. IAP header validation
    3. Domain check for mgms.eu users
    4. Allow list check for external users

    Args:
        request: FastAPI request object

    Returns:
        Tuple of (is_authorized, user_or_none, reason_message)
    """
    config = get_auth_config()

    # If auth is disabled, return mock user
    if not config.auth_enabled:
        # Use debug level to avoid log spam on every request
        # Startup warning is logged elsewhere (main.py in Phase 2)
        logger.debug("Auth disabled - using mock user")
        return True, get_mock_user(), "Auth disabled (development mode)"

    # Extract user from IAP headers
    user = extract_user_from_iap_headers(request)

    if user is None:
        return False, None, "Missing or invalid IAP authentication headers"

    # Check if user is from primary domain
    if validate_domain(user):
        logger.debug("User authorized via domain: %s", user.email)
        return True, user, "Domain user"

    # Check allow list for non-domain users
    if await check_allow_list(user.email):
        # Non-domain users on allow list are NOT admins - create new User instance
        allow_list_user = User(
            email=user.email,
            user_id=user.user_id,
            domain=user.domain,
            is_admin=False
        )
        logger.debug("User authorized via allow list: %s", user.email)
        return True, allow_list_user, "Allow list user"

    # User not authorized
    logger.info("User not authorized: %s (domain: %s)", user.email, user.domain)
    return False, user, "Access denied. Contact admin for access."


def require_admin_domain(user: User) -> bool:
    """
    Check if user has admin privileges (must be from mgms.eu domain).

    Args:
        user: User to check

    Returns:
        True if user is from the admin domain

    Raises:
        AuthorizationError: If user is not from admin domain
    """
    if not user.is_admin:
        raise AuthorizationError(
            f"Admin access requires @{get_auth_config().auth_domain} domain. "
            f"Your domain: @{user.domain}"
        )
    return True

