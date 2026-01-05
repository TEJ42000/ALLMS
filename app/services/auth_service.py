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

from app.models.auth_models import AuthConfig, User, MockUser, AllowListEntry

logger = logging.getLogger(__name__)

# Load auth configuration from environment
_auth_config: Optional[AuthConfig] = None


def get_auth_config() -> AuthConfig:
    """Get the authentication configuration singleton."""
    global _auth_config
    if _auth_config is None:
        _auth_config = AuthConfig()
    return _auth_config


# ============================================================================
# IAP Header Constants
# ============================================================================

# Google IAP header names
IAP_USER_EMAIL_HEADER = "X-Goog-Authenticated-User-Email"
IAP_USER_ID_HEADER = "X-Goog-Authenticated-User-Id"
IAP_JWT_HEADER = "X-Goog-IAP-JWT-Assertion"  # TODO: Use in Phase 2 for JWT verification

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

    Args:
        email: Email address to check

    Returns:
        True if email is on the active, non-expired allow list
    """
    # Import here to avoid circular imports and allow lazy loading
    try:
        from app.services.gcp_service import get_firestore_client
    except ImportError:
        logger.warning("Firestore client not available, allow list check skipped")
        return False

    try:
        db = get_firestore_client()
        if db is None:
            logger.warning("Firestore client is None, allow list check skipped")
            return False

        # Normalize email for lookup
        normalized_email = email.lower().strip()

        # Use email as document ID (with dots replaced to avoid Firestore issues)
        doc_id = normalized_email.replace(".", "_dot_")
        doc_ref = db.collection("allowed_users").document(doc_id)
        doc = doc_ref.get()

        if not doc.exists:
            logger.debug("Email not found in allow list: %s", normalized_email)
            return False

        # Parse the entry and check validity
        entry = AllowListEntry.from_firestore_dict(doc.to_dict())

        if not entry.is_valid:
            logger.info(
                "Allow list entry invalid (active=%s, expired=%s): %s",
                entry.active, entry.is_expired, normalized_email
            )
            return False

        logger.info("User found in allow list: %s", normalized_email)
        return True

    except (ValueError, KeyError, AttributeError) as e:
        # Handle expected errors (validation, missing fields, etc.)
        logger.error("Error checking allow list: %s", str(e))
        return False
    except Exception as e:
        # Log unexpected errors with full traceback but don't crash
        logger.exception("Unexpected error checking allow list: %s", str(e))
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
        logger.warning("⚠️  Authentication is DISABLED - using mock user")
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

