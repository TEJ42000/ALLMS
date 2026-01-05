"""Authentication Models for Google IAP Integration.

Provides Pydantic models for user authentication, allow list management,
and configuration settings for Google Identity-Aware Proxy (IAP).
"""

import os
from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field, EmailStr, field_validator
from pydantic_settings import BaseSettings


# ============================================================================
# Configuration Settings
# ============================================================================

class AuthConfig(BaseSettings):
    """Authentication configuration loaded from environment variables."""

    auth_enabled: bool = Field(
        default=True,
        description="Enable/disable authentication (set to false for local dev)"
    )
    auth_domain: str = Field(
        default="mgms.eu",
        description="Primary allowed domain for full access"
    )
    google_client_id: Optional[str] = Field(
        default=None,
        description="Google OAuth Client ID for IAP JWT verification"
    )
    iap_audience: Optional[str] = Field(
        default=None,
        description="IAP audience for JWT validation"
    )
    auth_mock_user_email: str = Field(
        default="dev@local.test",
        description="Mock user email when auth is disabled"
    )
    auth_mock_user_is_admin: bool = Field(
        default=True,
        description="Mock user admin status when auth is disabled"
    )

    class Config:
        """Pydantic settings configuration."""
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# ============================================================================
# User Models
# ============================================================================

class User(BaseModel):
    """Authenticated user information extracted from IAP headers."""

    email: str = Field(..., description="User's email address")
    user_id: str = Field(..., description="User's unique identifier from IAP")
    domain: str = Field(..., description="Email domain (e.g., 'mgms.eu')")
    is_admin: bool = Field(
        default=False,
        description="Whether user has admin privileges (true for @mgms.eu)"
    )

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower().strip()

    @property
    def is_domain_user(self) -> bool:
        """Check if user is from the primary domain (mgms.eu)."""
        return self.domain.lower() == "mgms.eu"

    def __str__(self) -> str:
        """String representation of user."""
        return f"User({self.email}, admin={self.is_admin})"


class MockUser(User):
    """Mock user for development mode when authentication is disabled."""

    def __init__(self, **data):
        """Create a mock user from environment variables."""
        email = os.getenv('AUTH_MOCK_USER_EMAIL', 'dev@local.test')
        is_admin_str = os.getenv('AUTH_MOCK_USER_IS_ADMIN', 'true')
        is_admin = is_admin_str.lower() in ('true', '1', 'yes')
        domain = email.split('@')[1] if '@' in email else 'local.test'

        super().__init__(
            email=email,
            user_id='mock-user-id-12345',
            domain=domain,
            is_admin=is_admin,
            **data
        )


# ============================================================================
# Allow List Models
# ============================================================================

class AllowListEntry(BaseModel):
    """Entry in the allow list for external users (stored in Firestore)."""

    email: str = Field(..., description="User's email address")
    added_by: str = Field(..., description="Admin who added this user")
    added_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the user was added"
    )
    reason: str = Field(..., description="Reason for granting access")
    expires_at: Optional[datetime] = Field(
        default=None,
        description="When access expires (None = never)"
    )
    active: bool = Field(default=True, description="Whether entry is active")
    notes: Optional[str] = Field(default=None, description="Additional notes")

    @field_validator('email')
    @classmethod
    def validate_and_normalize_email(cls, v: str) -> str:
        """Normalize email to lowercase."""
        return v.lower().strip()

    @property
    def is_expired(self) -> bool:
        """Check if the entry has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_valid(self) -> bool:
        """Check if the entry is valid (active and not expired)."""
        return self.active and not self.is_expired

    def to_firestore_dict(self) -> dict:
        """Convert to dictionary for Firestore storage."""
        return {
            "email": self.email,
            "added_by": self.added_by,
            "added_at": self.added_at,
            "reason": self.reason,
            "expires_at": self.expires_at,
            "active": self.active,
            "notes": self.notes,
        }

    @classmethod
    def from_firestore_dict(cls, data: dict) -> "AllowListEntry":
        """Create from Firestore document data."""
        return cls(**data)

