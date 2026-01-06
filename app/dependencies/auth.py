"""FastAPI Dependencies for Authentication and Authorization.

Provides injectable dependencies for route-level access control:
- get_current_user: Extract authenticated user from request
- require_authenticated: Ensure request is authenticated
- require_mgms_domain: Require @mgms.eu domain (admin access)
- require_allowed_user: Allow domain users OR allow-listed users
"""

import logging
from typing import Optional

from fastapi import HTTPException, Request, Depends

from app.models.auth_models import User
from app.services.auth_service import get_auth_config

logger = logging.getLogger(__name__)


async def get_current_user(request: Request) -> Optional[User]:
    """Extract the current user from request state.

    This dependency retrieves the user attached by AuthMiddleware.
    Returns None if no user is attached (public paths or auth disabled).

    Args:
        request: The FastAPI request object

    Returns:
        User object if authenticated, None otherwise
    """
    return getattr(request.state, 'user', None)


async def require_authenticated(
    request: Request,
    user: Optional[User] = Depends(get_current_user)
) -> User:
    """Require that the request is authenticated.

    Raises 401 Unauthorized if no user is attached to the request.

    Args:
        request: The FastAPI request object
        user: User from get_current_user dependency

    Returns:
        The authenticated User

    Raises:
        HTTPException: 401 if not authenticated
    """
    if user is None:
        logger.warning("Unauthenticated access attempt to %s", request.url.path)
        raise HTTPException(
            status_code=401,
            detail="Not authenticated"
        )
    return user


async def require_mgms_domain(
    request: Request,
    user: User = Depends(require_authenticated)
) -> User:
    """Require that the user is from the @mgms.eu domain.

    This is used for admin routes that should only be accessible
    to internal domain users.

    Args:
        request: The FastAPI request object
        user: Authenticated user from require_authenticated

    Returns:
        The authenticated User (guaranteed to be from mgms.eu)

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not from @mgms.eu domain
    """
    config = get_auth_config()
    required_domain = config.auth_domain.lower()

    if user.domain.lower() != required_domain:
        logger.warning(
            "Domain access denied for %s (required: @%s, got: @%s) on %s",
            user.email, required_domain, user.domain, request.url.path
        )
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. This page requires @{required_domain} domain."
        )

    return user


async def require_allowed_user(
    request: Request,
    user: User = Depends(require_authenticated)
) -> User:
    """Require that the user is either from the domain OR on the allow list.

    This provides access to:
    1. All @mgms.eu domain users
    2. External users who have been added to the allow list

    Note: The allow list check is already done in the middleware,
    so if the user made it this far, they are authorized.

    Args:
        request: The FastAPI request object
        user: Authenticated user from require_authenticated

    Returns:
        The authenticated User

    Raises:
        HTTPException: 401 if not authenticated
    """
    # If user is attached by middleware, they've already been authorized
    # (either domain user or on allow list)
    return user


async def get_optional_user(request: Request) -> Optional[User]:
    """Get the current user if available, without requiring authentication.

    Useful for routes that behave differently for authenticated vs anonymous users.
    This is async for consistency with other auth dependencies.

    Args:
        request: The FastAPI request object

    Returns:
        User if authenticated, None otherwise
    """
    return getattr(request.state, 'user', None)

