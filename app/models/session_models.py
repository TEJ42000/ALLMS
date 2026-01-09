"""Session Models for OAuth Authentication.

Provides Pydantic models for session management, OAuth tokens,
and Google user information for the application-level OAuth flow.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional
import uuid

from pydantic import BaseModel, EmailStr, Field, field_validator


# ============================================================================
# OAuth Token Models
# ============================================================================

class OAuthTokens(BaseModel):
    """OAuth tokens returned from Google OAuth flow."""

    access_token: str = Field(..., description="OAuth access token")
    refresh_token: Optional[str] = Field(
        default=None,
        description="OAuth refresh token (only on first authorization)"
    )
    token_type: str = Field(default="Bearer", description="Token type")
    expires_in: int = Field(
        default=3600,
        description="Access token expiry in seconds"
    )
    scope: Optional[str] = Field(default=None, description="OAuth scopes granted")

    @property
    def expires_at(self) -> datetime:
        """Calculate token expiry datetime."""
        return datetime.now(timezone.utc).replace(
            microsecond=0
        ) + timedelta(seconds=self.expires_in)


class GoogleUserInfo(BaseModel):
    """User information from Google OAuth userinfo endpoint."""

    sub: str = Field(..., description="Google's unique user ID")
    email: EmailStr = Field(..., description="User's email address")
    email_verified: bool = Field(default=False, description="Whether email is verified")
    name: Optional[str] = Field(default=None, description="User's full name")
    given_name: Optional[str] = Field(default=None, description="User's first name")
    family_name: Optional[str] = Field(default=None, description="User's last name")
    picture: Optional[str] = Field(default=None, description="URL to profile picture")
    hd: Optional[str] = Field(default=None, description="Hosted domain (for Google Workspace)")

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower().strip()

    @property
    def domain(self) -> str:
        """Extract domain from email."""
        return self.email.split("@")[1] if "@" in self.email else ""


# ============================================================================
# OAuth State Model (CSRF Protection)
# ============================================================================

class OAuthState(BaseModel):
    """OAuth state for CSRF protection during OAuth flow."""

    state_token: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Random state token for CSRF protection"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the state was created"
    )
    redirect_uri: Optional[str] = Field(
        default=None,
        description="Original URL to redirect after login"
    )
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(
            microsecond=0
        ) + timedelta(minutes=10),
        description="State token expiry (10 minutes)"
    )

    @property
    def is_expired(self) -> bool:
        """Check if state token has expired."""
        now = datetime.now(timezone.utc)
        return now > self.expires_at


# ============================================================================
# Session Model
# ============================================================================

class Session(BaseModel):
    """User session stored in Firestore."""

    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique session identifier (UUID)"
    )
    user_email: EmailStr = Field(..., description="User's email address")
    user_id: str = Field(..., description="Google's unique user ID")
    domain: str = Field(..., description="Email domain (e.g., 'mgms.eu')")
    is_admin: bool = Field(
        default=False,
        description="Whether user has admin privileges"
    )
    
    # Token storage (encrypted)
    access_token_encrypted: str = Field(
        ...,
        description="Encrypted OAuth access token"
    )
    refresh_token_encrypted: Optional[str] = Field(
        default=None,
        description="Encrypted OAuth refresh token"
    )
    token_expiry: datetime = Field(
        ...,
        description="When the access token expires"
    )
    
    # Session timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the session was created"
    )
    last_accessed: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last request using this session"
    )
    expires_at: datetime = Field(
        ...,
        description="When the session expires"
    )
    
    # Security metadata
    user_agent: Optional[str] = Field(
        default=None,
        description="Browser user agent at session creation"
    )
    ip_address: Optional[str] = Field(
        default=None,
        description="IP address at session creation"
    )

    @field_validator('user_email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower().strip()

    @property
    def is_expired(self) -> bool:
        """Check if session has expired."""
        now = datetime.now(timezone.utc)
        return now > self.expires_at

    @property
    def is_token_expired(self) -> bool:
        """Check if the access token has expired."""
        now = datetime.now(timezone.utc)
        return now > self.token_expiry

    def to_firestore_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Firestore storage."""
        return {
            "session_id": self.session_id,
            "user_email": self.user_email,
            "user_id": self.user_id,
            "domain": self.domain,
            "is_admin": self.is_admin,
            "access_token_encrypted": self.access_token_encrypted,
            "refresh_token_encrypted": self.refresh_token_encrypted,
            "token_expiry": self.token_expiry,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "expires_at": self.expires_at,
            "user_agent": self.user_agent,
            "ip_address": self.ip_address,
        }

    @classmethod
    def from_firestore_dict(cls, data: dict[str, Any]) -> "Session":
        """Create from Firestore document data."""
        return cls(**data)

