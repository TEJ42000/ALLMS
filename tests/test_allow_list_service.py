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


class TestAllowListServiceAddUser:
    """Tests for AllowListService.add_user() method."""

    @pytest.fixture
    def mock_firestore(self):
        """Mock Firestore client."""
        with patch('app.services.allow_list_service.get_firestore_client') as mock_get_client:
            mock_db = MagicMock()
            mock_get_client.return_value = mock_db
            yield mock_db

    @pytest.fixture
    def service(self, mock_firestore):
        """Create AllowListService with mocked Firestore."""
        from app.services.allow_list_service import AllowListService
        return AllowListService()

    def test_add_new_user_success(self, service, mock_firestore):
        """Test adding a new user that doesn't exist."""
        # Mock: User doesn't exist
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_doc

        request = AllowListCreateRequest(
            email="newuser@external.com",
            reason="New guest lecturer"
        )

        result = service.add_user(request, added_by="admin@mgms.eu")

        # Verify user was created
        assert result.email == "newuser@external.com"
        assert result.active is True
        assert result.reason == "New guest lecturer"
        assert result.added_by == "admin@mgms.eu"

        # Verify Firestore set() was called
        mock_firestore.collection.return_value.document.return_value.set.assert_called_once()

    def test_add_existing_active_user_fails(self, service, mock_firestore):
        """Test that adding an already-active user raises ValueError."""
        # Mock: User exists and is active
        existing_entry = AllowListEntry(
            email="active@external.com",
            added_by="admin@mgms.eu",
            reason="Already active",
            active=True
        )
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = existing_entry.model_dump_for_firestore()
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_doc

        request = AllowListCreateRequest(
            email="active@external.com",
            reason="Trying to add again"
        )

        with pytest.raises(ValueError) as exc_info:
            service.add_user(request, added_by="admin@mgms.eu")

        assert "already on the allow list and has active access" in str(exc_info.value)
        # Verify Firestore update() was NOT called
        mock_firestore.collection.return_value.document.return_value.update.assert_not_called()

    def test_reactivate_inactive_user_success(self, service, mock_firestore):
        """Test reactivating a soft-deleted (inactive) user."""
        # Mock: User exists but is inactive
        existing_entry = AllowListEntry(
            email="inactive@external.com",
            added_by="old_admin@mgms.eu",
            reason="Old reason",
            active=False  # Soft-deleted
        )

        # Mock the reactivated user (after update)
        reactivated_entry = AllowListEntry(
            email="inactive@external.com",
            added_by="new_admin@mgms.eu",
            reason="Reactivated for new project",
            active=True
        )

        # Create separate mock document references for each call
        mock_doc_ref = MagicMock()

        # First get() call returns inactive user
        mock_doc_get_1 = MagicMock()
        mock_doc_get_1.exists = True
        mock_doc_get_1.to_dict.return_value = existing_entry.model_dump_for_firestore()

        # Second get() call (after update) returns reactivated user
        mock_doc_get_2 = MagicMock()
        mock_doc_get_2.exists = True
        mock_doc_get_2.to_dict.return_value = reactivated_entry.model_dump_for_firestore()

        # Setup side_effect for get() to return different values
        mock_doc_ref.get.side_effect = [mock_doc_get_1, mock_doc_get_2]

        # Setup collection().document() to return our mock document reference
        mock_firestore.collection.return_value.document.return_value = mock_doc_ref

        request = AllowListCreateRequest(
            email="inactive@external.com",
            reason="Reactivated for new project"
        )

        result = service.add_user(request, added_by="new_admin@mgms.eu")

        # Verify user was reactivated
        assert result.email == "inactive@external.com"
        assert result.active is True
        assert result.reason == "Reactivated for new project"
        assert result.added_by == "new_admin@mgms.eu"

        # Verify Firestore update() was called (not set())
        mock_doc_ref.update.assert_called_once()
        update_call_args = mock_doc_ref.update.call_args[0][0]
        assert update_call_args["active"] is True
        assert update_call_args["reason"] == "Reactivated for new project"

        # Verify set() was NOT called (we're updating, not creating)
        mock_doc_ref.set.assert_not_called()

    def test_reactivate_expired_user_success(self, service, mock_firestore):
        """Test reactivating an expired user."""
        # Mock: User exists but is expired
        past = datetime.now(timezone.utc) - timedelta(days=1)
        existing_entry = AllowListEntry(
            email="expired@external.com",
            added_by="admin@mgms.eu",
            reason="Expired access",
            active=True,
            expires_at=past  # Expired
        )

        # Mock the renewed user (after update)
        future = datetime.now(timezone.utc) + timedelta(days=30)
        renewed_entry = AllowListEntry(
            email="expired@external.com",
            added_by="admin@mgms.eu",
            reason="Renewed access",
            active=True,
            expires_at=future
        )

        # Create separate mock document reference
        mock_doc_ref = MagicMock()

        # First get() call returns expired user
        mock_doc_get_1 = MagicMock()
        mock_doc_get_1.exists = True
        mock_doc_get_1.to_dict.return_value = existing_entry.model_dump_for_firestore()

        # Second get() call (after update) returns renewed user
        mock_doc_get_2 = MagicMock()
        mock_doc_get_2.exists = True
        mock_doc_get_2.to_dict.return_value = renewed_entry.model_dump_for_firestore()

        # Setup side_effect for get() to return different values
        mock_doc_ref.get.side_effect = [mock_doc_get_1, mock_doc_get_2]

        # Setup collection().document() to return our mock document reference
        mock_firestore.collection.return_value.document.return_value = mock_doc_ref

        request = AllowListCreateRequest(
            email="expired@external.com",
            reason="Renewed access",
            expires_at=future
        )

        result = service.add_user(request, added_by="admin@mgms.eu")

        # Verify user was renewed
        assert result.email == "expired@external.com"
        assert result.active is True
        assert result.expires_at == future
        assert result.is_expired is False

        # Verify Firestore update() was called
        mock_doc_ref.update.assert_called_once()
        update_call_args = mock_doc_ref.update.call_args[0][0]
        assert update_call_args["active"] is True
        assert update_call_args["expires_at"] == future

        # Verify set() was NOT called (we're updating, not creating)
        mock_doc_ref.set.assert_not_called()

    def test_add_user_with_expiration(self, service, mock_firestore):
        """Test adding a new user with expiration date."""
        # Mock: User doesn't exist
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_doc

        future = datetime.now(timezone.utc) + timedelta(days=30)
        request = AllowListCreateRequest(
            email="temp@external.com",
            reason="Temporary access",
            expires_at=future
        )

        result = service.add_user(request, added_by="admin@mgms.eu")

        assert result.email == "temp@external.com"
        assert result.expires_at == future
        assert result.is_expired is False

    def test_add_user_normalizes_email(self, service, mock_firestore):
        """Test that email is normalized to lowercase."""
        # Mock: User doesn't exist
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_doc

        request = AllowListCreateRequest(
            email="MixedCase@External.COM",
            reason="Test"
        )

        result = service.add_user(request, added_by="Admin@MGMS.EU")

        assert result.email == "mixedcase@external.com"
        assert result.added_by == "admin@mgms.eu"

    def test_add_user_service_unavailable(self, mock_firestore):
        """Test that add_user raises ValueError when service is unavailable."""
        # Mock: Firestore client returns None (service unavailable)
        with patch('app.services.allow_list_service.get_firestore_client') as mock_get_client:
            mock_get_client.return_value = None

            from app.services.allow_list_service import AllowListService
            service = AllowListService()

            request = AllowListCreateRequest(
                email="test@external.com",
                reason="Test"
            )

            with pytest.raises(ValueError) as exc_info:
                service.add_user(request, added_by="admin@mgms.eu")

            assert "Allow list service is not available" in str(exc_info.value)

    def test_add_user_firestore_set_error(self, service, mock_firestore):
        """Test handling of Firestore set() errors when adding new user."""
        # Mock: User doesn't exist
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_doc

        # Mock: Firestore set() raises exception
        mock_firestore.collection.return_value.document.return_value.set.side_effect = Exception("Firestore error")

        request = AllowListCreateRequest(
            email="newuser@external.com",
            reason="Test"
        )

        with pytest.raises(ValueError) as exc_info:
            service.add_user(request, added_by="admin@mgms.eu")

        assert "Failed to add user" in str(exc_info.value)

    def test_reactivate_user_firestore_update_error(self, service, mock_firestore):
        """Test handling of Firestore update() errors when reactivating user."""
        # Mock: User exists but is inactive
        existing_entry = AllowListEntry(
            email="inactive@external.com",
            added_by="admin@mgms.eu",
            reason="Old reason",
            active=False
        )
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = existing_entry.model_dump_for_firestore()
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_doc

        # Mock: Firestore update() raises exception
        mock_firestore.collection.return_value.document.return_value.update.side_effect = Exception("Firestore error")

        request = AllowListCreateRequest(
            email="inactive@external.com",
            reason="Reactivating"
        )

        with pytest.raises(ValueError) as exc_info:
            service.add_user(request, added_by="admin@mgms.eu")

        assert "Failed to reactivate user" in str(exc_info.value)

    def test_add_user_with_notes(self, service, mock_firestore):
        """Test adding a user with notes field."""
        # Mock: User doesn't exist
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_doc

        request = AllowListCreateRequest(
            email="newuser@external.com",
            reason="Guest lecturer",
            notes="Visiting professor for Spring 2026"
        )

        result = service.add_user(request, added_by="admin@mgms.eu")

        assert result.email == "newuser@external.com"
        assert result.notes == "Visiting professor for Spring 2026"

        # Verify notes were passed to Firestore
        call_args = mock_firestore.collection.return_value.document.return_value.set.call_args[0][0]
        assert call_args["notes"] == "Visiting professor for Spring 2026"

