"""Allow List Models for User Management.

Pydantic models for the allow list feature that enables @mgms.eu admins
to grant access to external users.
"""

from datetime import datetime, timezone
from typing import Optional, List

from pydantic import BaseModel, Field, EmailStr, field_validator


class AllowListEntry(BaseModel):
    """An entry in the allow list stored in Firestore."""

    email: EmailStr = Field(..., description="User's email address (normalized to lowercase)")
    added_by: EmailStr = Field(..., description="Admin who added this user")
    added_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the user was added"
    )
    reason: str = Field(..., description="Reason for granting access")
    expires_at: Optional[datetime] = Field(
        None,
        description="When access expires (None = never)"
    )
    active: bool = Field(True, description="Whether the entry is active")
    notes: Optional[str] = Field(None, description="Additional notes")
    updated_at: Optional[datetime] = Field(None, description="Last update timestamp")

    @property
    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_effective(self) -> bool:
        """Check if this entry grants effective access (active and not expired)."""
        return self.active and not self.is_expired

    def model_dump_for_firestore(self) -> dict:
        """Convert to dict suitable for Firestore storage."""
        data = self.model_dump()
        # Ensure email is lowercase
        data["email"] = data["email"].lower()
        return data


class AllowListCreateRequest(BaseModel):
    """Request model for adding a user to the allow list."""

    email: EmailStr = Field(..., description="Email address to add")
    reason: str = Field(..., min_length=1, max_length=500, description="Reason for access")
    expires_at: Optional[datetime] = Field(
        None,
        description="When access should expire (ISO 8601 format)"
    )
    notes: Optional[str] = Field(None, max_length=1000, description="Additional notes")

    @field_validator("email")
    @classmethod
    def validate_not_mgms_domain(cls, v: str) -> str:
        """Prevent adding @mgms.eu users (they already have access)."""
        email_lower = v.lower().strip()
        if email_lower.endswith("@mgms.eu"):
            raise ValueError("Cannot add @mgms.eu users to allow list - they already have access")
        return email_lower


class AllowListUpdateRequest(BaseModel):
    """Request model for updating an allow list entry."""

    reason: Optional[str] = Field(None, min_length=1, max_length=500)
    expires_at: Optional[datetime] = Field(None)
    active: Optional[bool] = Field(None)
    notes: Optional[str] = Field(None, max_length=1000)


class AllowListResponse(BaseModel):
    """Response model for a single allow list entry."""

    email: str
    added_by: str
    added_at: datetime
    reason: str
    expires_at: Optional[datetime] = None
    active: bool
    notes: Optional[str] = None
    updated_at: Optional[datetime] = None
    is_expired: bool
    is_effective: bool

    @classmethod
    def from_entry(cls, entry: AllowListEntry) -> "AllowListResponse":
        """Create response from AllowListEntry."""
        return cls(
            email=entry.email,
            added_by=entry.added_by,
            added_at=entry.added_at,
            reason=entry.reason,
            expires_at=entry.expires_at,
            active=entry.active,
            notes=entry.notes,
            updated_at=entry.updated_at,
            is_expired=entry.is_expired,
            is_effective=entry.is_effective,
        )


class AllowListListResponse(BaseModel):
    """Response model for listing allow list entries."""

    entries: List[AllowListResponse]
    total: int
    active_count: int
    expired_count: int
    inactive_count: int

