"""Tests for the allow list service.

Tests CRUD operations, expiration logic, and email validation.
"""

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from app.models.allow_list_models import (
    AllowListEntry,
    AllowListCreateRequest,
    AllowListUpdateRequest,
    AllowListResponse,
)


class TestAllowListEntry:
    """Tests for AllowListEntry model."""

    def test_create_entry(self):
        """Test creating a valid allow list entry."""
        entry = AllowListEntry(
            email="guest@external.com",
            added_by="admin@mgms.eu",
            reason="Guest lecturer"
        )
        assert entry.email == "guest@external.com"
        assert entry.active is True
        assert entry.is_expired is False
        assert entry.is_effective is True

    def test_entry_with_expiration_future(self):
        """Test entry with future expiration date."""
        future = datetime.now(timezone.utc) + timedelta(days=30)
        entry = AllowListEntry(
            email="guest@external.com",
            added_by="admin@mgms.eu",
            reason="Temporary access",
            expires_at=future
        )
        assert entry.is_expired is False
        assert entry.is_effective is True

    def test_entry_with_expiration_past(self):
        """Test entry with past expiration date."""
        past = datetime.now(timezone.utc) - timedelta(days=1)
        entry = AllowListEntry(
            email="guest@external.com",
            added_by="admin@mgms.eu",
            reason="Expired access",
            expires_at=past
        )
        assert entry.is_expired is True
        assert entry.is_effective is False

    def test_inactive_entry_not_effective(self):
        """Test that inactive entries are not effective."""
        entry = AllowListEntry(
            email="guest@external.com",
            added_by="admin@mgms.eu",
            reason="Deactivated user",
            active=False
        )
        assert entry.is_effective is False

    def test_entry_firestore_dump(self):
        """Test conversion to Firestore format."""
        entry = AllowListEntry(
            email="GUEST@External.COM",  # Mixed case
            added_by="admin@mgms.eu",
            reason="Test"
        )
        data = entry.model_dump_for_firestore()
        assert data["email"] == "guest@external.com"  # Lowercase


class TestAllowListCreateRequest:
    """Tests for AllowListCreateRequest validation."""

    def test_valid_request(self):
        """Test creating a valid request."""
        request = AllowListCreateRequest(
            email="guest@university.edu",
            reason="Research assistant"
        )
        assert request.email == "guest@university.edu"
        assert request.reason == "Research assistant"

    def test_email_normalized_to_lowercase(self):
        """Test that email is normalized to lowercase."""
        request = AllowListCreateRequest(
            email="GUEST@University.EDU",
            reason="Test"
        )
        assert request.email == "guest@university.edu"

    def test_cannot_add_mgms_domain(self):
        """Test that @mgms.eu users cannot be added."""
        with pytest.raises(ValidationError) as exc_info:
            AllowListCreateRequest(
                email="user@mgms.eu",
                reason="Already has access"
            )
        assert "Cannot add @mgms.eu users" in str(exc_info.value)

    def test_reason_required(self):
        """Test that reason is required."""
        with pytest.raises(ValidationError):
            AllowListCreateRequest(
                email="guest@external.com",
                reason=""  # Empty reason
            )

    def test_invalid_email_rejected(self):
        """Test that invalid emails are rejected."""
        with pytest.raises(ValidationError):
            AllowListCreateRequest(
                email="not-an-email",
                reason="Test"
            )


class TestAllowListUpdateRequest:
    """Tests for AllowListUpdateRequest validation."""

    def test_partial_update(self):
        """Test that partial updates work."""
        request = AllowListUpdateRequest(active=False)
        assert request.active is False
        assert request.reason is None

    def test_full_update(self):
        """Test full update with all fields."""
        future = datetime.now(timezone.utc) + timedelta(days=30)
        request = AllowListUpdateRequest(
            reason="Updated reason",
            expires_at=future,
            active=True,
            notes="Updated notes"
        )
        assert request.reason == "Updated reason"
        assert request.active is True


class TestAllowListResponse:
    """Tests for AllowListResponse creation."""

    def test_from_entry(self):
        """Test creating response from entry."""
        entry = AllowListEntry(
            email="guest@external.com",
            added_by="admin@mgms.eu",
            reason="Test user"
        )
        response = AllowListResponse.from_entry(entry)
        assert response.email == "guest@external.com"
        assert response.is_expired is False
        assert response.is_effective is True

