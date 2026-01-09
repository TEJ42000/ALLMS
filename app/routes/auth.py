"""Authentication Routes for OAuth Login/Logout.

Provides endpoints for Google OAuth authentication including:
- Login initiation with redirect to Google
- OAuth callback handling
- Logout with session invalidation
- Current user info endpoint
"""

import logging
from typing import Optional

from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.models.auth_models import AuthConfig, User
from app.models.session_models import GoogleUserInfo
from app.services.auth_service import get_auth_config, check_allow_list
from app.services.oauth_service import get_oauth_service
from app.services.session_service import get_session_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])
templates = Jinja2Templates(directory="templates")


def _mask_email_for_logging(email: str) -> str:
    """Mask email address for safe logging (PII protection).

    Example: user@example.com -> u***@e***.com
    """
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    masked_local = local[0] + "***" if local else "***"
    # Mask domain but keep TLD
    domain_parts = domain.rsplit(".", 1)
    if len(domain_parts) == 2:
        masked_domain = domain_parts[0][0] + "***." + domain_parts[1] if domain_parts[0] else "***." + domain_parts[1]
    else:
        masked_domain = "***"
    return f"{masked_local}@{masked_domain}"


def _get_user_from_request(request: Request) -> Optional[User]:
    """Extract user from request state."""
    return getattr(request.state, 'user', None)


def _set_session_cookie(response: Response, session_id: str, config: AuthConfig) -> None:
    """Set the session cookie on the response."""
    response.set_cookie(
        key=config.session_cookie_name,
        value=session_id,
        httponly=True,
        secure=config.session_cookie_secure,
        samesite=config.session_cookie_samesite,
        max_age=config.session_expiry_days * 24 * 60 * 60,
        path="/",
    )


def _clear_session_cookie(response: Response, config: AuthConfig) -> None:
    """Clear the session cookie."""
    response.delete_cookie(
        key=config.session_cookie_name,
        path="/",
    )


@router.get("/login")
async def login(request: Request, next: Optional[str] = None):
    """Initiate OAuth login flow.

    Args:
        request: The incoming request
        next: Optional URL to redirect after login

    Returns:
        Redirect to Google OAuth consent screen
    """
    config = get_auth_config()

    if not config.is_oauth_configured:
        logger.error("OAuth not configured - cannot initiate login")
        raise HTTPException(
            status_code=500,
            detail="OAuth authentication is not configured"
        )

    oauth_service = get_oauth_service()

    # Generate state token with redirect URL
    redirect_uri = next or "/"
    state = oauth_service.generate_state_token(redirect_uri)

    # Generate Google OAuth URL
    oauth_url = oauth_service.generate_oauth_url(state)

    logger.info("Initiating OAuth login, redirect after: %s", redirect_uri)
    return RedirectResponse(url=oauth_url, status_code=302)


@router.get("/callback")
async def oauth_callback(
    request: Request,
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
):
    """Handle OAuth callback from Google.

    Args:
        request: The incoming request
        code: Authorization code from Google
        state: State parameter for CSRF verification
        error: Error from Google OAuth (if any)

    Returns:
        Redirect to original URL or error page
    """
    config = get_auth_config()
    oauth_service = get_oauth_service()
    session_service = get_session_service()

    # Handle OAuth errors from Google
    if error:
        logger.warning("OAuth error from Google: %s", error)
        return templates.TemplateResponse(
            "errors/403_access_denied.html",
            {
                "request": request,
                "error_message": f"Google authentication failed: {error}",
                "user_email": None,
            },
            status_code=403,
        )

    # Validate required parameters
    if not code or not state:
        logger.warning("Missing code or state in callback")
        raise HTTPException(status_code=400, detail="Missing authorization code or state")

    # Validate state token (CSRF protection)
    is_valid, redirect_uri = oauth_service.validate_state_token(state)
    if not is_valid:
        logger.warning("Invalid or expired state token")
        raise HTTPException(status_code=400, detail="Invalid or expired state token")

    try:
        # Exchange code for tokens
        tokens = await oauth_service.exchange_code_for_tokens(code)

        # Get user info from Google
        user_info = await oauth_service.get_user_info(tokens.access_token)

        # Mask email immediately for logging purposes (CodeQL: prevent PII in logs)
        masked_email = _mask_email_for_logging(user_info.email)

        # Authorize user (domain check or allow list)
        is_authorized, user, reason = await _authorize_oauth_user(user_info, config)

        if not is_authorized:
            logger.warning("User not authorized: %s - %s", masked_email, reason)
            return templates.TemplateResponse(
                "errors/403_access_denied.html",
                {
                    "request": request,
                    "error_message": reason,
                    "user_email": user_info.email,
                },
                status_code=403,
            )

        # Create session
        user_agent = request.headers.get("user-agent")
        ip_address = request.client.host if request.client else None

        session = await session_service.create_session(
            user=user,
            tokens=tokens,
            user_agent=user_agent,
            ip_address=ip_address,
        )

        # Create response with redirect
        response = RedirectResponse(url=redirect_uri or "/", status_code=302)
        _set_session_cookie(response, session.session_id, config)

        logger.info("User logged in: %s (admin=%s)", masked_email, user.is_admin)
        return response

    except ValueError as e:
        logger.error("OAuth callback error: %s", e)
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error in OAuth callback: %s", e)
        raise HTTPException(status_code=500, detail="Authentication failed")


@router.post("/logout")
async def logout(request: Request):
    """Logout and invalidate session.

    Args:
        request: The incoming request

    Returns:
        Redirect to home page
    """
    config = get_auth_config()
    session_service = get_session_service()

    # Get session ID from cookie
    session_id = request.cookies.get(config.session_cookie_name)

    if session_id:
        await session_service.invalidate_session(session_id)
        logger.info("Session invalidated: %s", session_id[:8])

    # Create response and clear cookie
    response = RedirectResponse(url="/", status_code=302)
    _clear_session_cookie(response, config)

    return response


@router.get("/me")
async def get_current_user(request: Request):
    """Get current authenticated user info.

    Args:
        request: The incoming request

    Returns:
        JSON with user info or 401 if not authenticated
    """
    user = _get_user_from_request(request)

    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return JSONResponse({
        "email": user.email,
        "user_id": user.user_id,
        "domain": user.domain,
        "is_admin": user.is_admin,
    })


async def _authorize_oauth_user(
    user_info: GoogleUserInfo,
    config: AuthConfig,
) -> tuple[bool, Optional[User], str]:
    """Authorize a user from OAuth login.

    Args:
        user_info: User info from Google
        config: Auth configuration

    Returns:
        Tuple of (is_authorized, User or None, reason)
    """
    email = user_info.email.lower()
    domain = user_info.domain

    # Check if user is from primary domain (admin access)
    if domain.lower() == config.auth_domain.lower():
        user = User(
            email=email,
            user_id=user_info.sub,
            domain=domain,
            is_admin=True,
        )
        return True, user, "Domain user"

    # Check allow list for non-domain users
    if await check_allow_list(email):
        user = User(
            email=email,
            user_id=user_info.sub,
            domain=domain,
            is_admin=False,
        )
        return True, user, "Allow list user"

    # Not authorized
    return False, None, "Access denied. Your email is not authorized. Contact admin for access."

