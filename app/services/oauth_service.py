"""OAuth Service for Google OAuth 2.0 Integration.

Provides OAuth authentication functionality including:
- OAuth URL generation with state parameter
- Authorization code exchange for tokens
- User info retrieval from Google
- Token refresh
- State token management for CSRF protection
"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from typing import Optional
from urllib.parse import urlencode

import httpx

from app.models.auth_models import AuthConfig
from app.models.session_models import GoogleUserInfo, OAuthState, OAuthTokens

logger = logging.getLogger(__name__)

# Google OAuth 2.0 endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"


def _hash_identifier_for_logging(value: str) -> str:
    """Create a short hash of a value for safe logging (no PII).

    Uses SHA256 to create a non-reversible identifier for log correlation.
    Example: user@example.com -> "a1b2c3d4e5f6"
    """
    if not value:
        return "unknown"
    return hashlib.sha256(value.encode()).hexdigest()[:12]
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"

# OAuth scopes
OAUTH_SCOPES = [
    "openid",
    "email",
    "profile",
]

# In-memory state token storage (use Redis in production for multi-instance)
_state_tokens: dict[str, OAuthState] = {}


@lru_cache(maxsize=1)
def get_auth_config() -> AuthConfig:
    """Get the authentication configuration singleton."""
    return AuthConfig()


class OAuthService:
    """Service for Google OAuth 2.0 authentication."""

    def __init__(self):
        """Initialize the OAuth service."""
        self.config = get_auth_config()
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate OAuth configuration."""
        if self.config.auth_mode in ("oauth", "dual"):
            if not self.config.is_oauth_configured:
                logger.warning(
                    "OAuth mode enabled but not fully configured. "
                    "Missing: client_id=%s, client_secret=%s, redirect_uri=%s, secret_key=%s",
                    bool(self.config.google_oauth_client_id),
                    bool(self.config.google_oauth_client_secret),
                    bool(self.config.oauth_redirect_uri),
                    bool(self.config.session_secret_key),
                )

    def generate_state_token(self, redirect_uri: Optional[str] = None) -> str:
        """Generate a state token for CSRF protection.

        Args:
            redirect_uri: Original URL to redirect after login

        Returns:
            State token string
        """
        state = OAuthState(
            state_token=secrets.token_urlsafe(32),
            redirect_uri=redirect_uri,
        )
        _state_tokens[state.state_token] = state
        logger.debug("Generated state token: %s", state.state_token[:8])
        return state.state_token

    def validate_state_token(self, state: str) -> tuple[bool, Optional[str]]:
        """Validate a state token and return the redirect URI.

        Args:
            state: State token to validate

        Returns:
            Tuple of (is_valid, redirect_uri or None)
        """
        if state not in _state_tokens:
            logger.warning("State token not found: %s", state[:8] if state else "None")
            return False, None

        oauth_state = _state_tokens.pop(state)

        if oauth_state.is_expired:
            logger.warning("State token expired: %s", state[:8])
            return False, None

        logger.debug("State token validated: %s", state[:8])
        return True, oauth_state.redirect_uri

    def generate_oauth_url(self, state: str) -> str:
        """Generate the Google OAuth authorization URL.

        Args:
            state: State token for CSRF protection

        Returns:
            Full OAuth authorization URL
        """
        params = {
            "client_id": self.config.google_oauth_client_id,
            "redirect_uri": self.config.oauth_redirect_uri,
            "response_type": "code",
            "scope": " ".join(OAUTH_SCOPES),
            "state": state,
            "access_type": "offline",  # Get refresh token
            "prompt": "consent",  # Force consent to get refresh token
        }
        url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
        logger.debug("Generated OAuth URL for state: %s", state[:8])
        return url

    async def exchange_code_for_tokens(self, code: str) -> OAuthTokens:
        """Exchange authorization code for OAuth tokens.

        Args:
            code: Authorization code from Google

        Returns:
            OAuthTokens containing access and refresh tokens

        Raises:
            ValueError: If token exchange fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.config.google_oauth_client_id,
                    "client_secret": self.config.google_oauth_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.config.oauth_redirect_uri,
                },
            )

            if response.status_code != 200:
                logger.error(
                    "Token exchange failed: %s - %s",
                    response.status_code,
                    response.text,
                )
                raise ValueError(f"Token exchange failed: {response.status_code}")

            data = response.json()
            logger.info("Successfully exchanged code for tokens")
            return OAuthTokens(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token"),
                token_type=data.get("token_type", "Bearer"),
                expires_in=data.get("expires_in", 3600),
                scope=data.get("scope"),
            )

    async def get_user_info(self, access_token: str) -> GoogleUserInfo:
        """Get user information from Google.

        Args:
            access_token: Valid OAuth access token

        Returns:
            GoogleUserInfo with user details

        Raises:
            ValueError: If user info retrieval fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )

            if response.status_code != 200:
                logger.error(
                    "User info retrieval failed: %s - %s",
                    response.status_code,
                    response.text,
                )
                raise ValueError(f"User info retrieval failed: {response.status_code}")

            data = response.json()
            logger.info("Retrieved user info for: %s", _hash_identifier_for_logging(data.get("email", "")))
            return GoogleUserInfo(**data)

    async def refresh_access_token(self, refresh_token: str) -> OAuthTokens:
        """Refresh an expired access token.

        Args:
            refresh_token: Valid refresh token

        Returns:
            OAuthTokens with new access token

        Raises:
            ValueError: If token refresh fails
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": self.config.google_oauth_client_id,
                    "client_secret": self.config.google_oauth_client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
            )

            if response.status_code != 200:
                logger.error(
                    "Token refresh failed: %s - %s",
                    response.status_code,
                    response.text,
                )
                raise ValueError(f"Token refresh failed: {response.status_code}")

            data = response.json()
            logger.info("Successfully refreshed access token")
            return OAuthTokens(
                access_token=data["access_token"],
                refresh_token=refresh_token,  # Keep existing refresh token
                token_type=data.get("token_type", "Bearer"),
                expires_in=data.get("expires_in", 3600),
                scope=data.get("scope"),
            )

    async def revoke_token(self, token: str) -> bool:
        """Revoke an OAuth token.

        Args:
            token: Access or refresh token to revoke

        Returns:
            True if revoked successfully
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_REVOKE_URL,
                params={"token": token},
            )

            if response.status_code == 200:
                logger.info("Token revoked successfully")
                return True
            else:
                logger.warning("Token revocation failed: %s", response.status_code)
                return False

    def cleanup_expired_states(self) -> int:
        """Remove expired state tokens from memory.

        Returns:
            Number of tokens removed
        """
        now = datetime.now(timezone.utc)
        expired = [
            token for token, state in _state_tokens.items()
            if state.is_expired
        ]
        for token in expired:
            del _state_tokens[token]

        if expired:
            logger.info("Cleaned up %d expired state tokens", len(expired))
        return len(expired)


def get_oauth_service() -> OAuthService:
    """Get an OAuthService instance."""
    return OAuthService()

