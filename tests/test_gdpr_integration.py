"""
Integration Tests for GDPR API Endpoints

Tests the full GDPR API flow including authentication, validation,
rate limiting, and data operations.
"""

import pytest
import json
from datetime import datetime
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock

from app.main import app
from app.models.auth_models import User
from app.models.gdpr_models import ConsentType, ConsentStatus


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Create mock authenticated user."""
    return User(
        email="test@example.com",
        user_id="test-user-123",
        domain="example.com",
        is_admin=False
    )


@pytest.fixture
def mock_firestore():
    """Create mock Firestore client."""
    mock_db = Mock()
    return mock_db


class TestConsentEndpoints:
    """Test consent management endpoints."""
    
    def test_record_consent_success(self, client, mock_user, mock_firestore):
        """Test successful consent recording."""
        with patch('app.dependencies.auth.get_current_user', return_value=mock_user):
            with patch('app.services.gcp_service.get_firestore_client', return_value=mock_firestore):
                # Setup mock
                mock_collection = Mock()
                mock_doc = Mock()
                mock_firestore.collection.return_value = mock_collection
                mock_collection.document.return_value = mock_doc
                
                # Make request
                response = client.post(
                    "/api/gdpr/consent",
                    json={
                        "consent_type": "analytics",
                        "status": "granted"
                    }
                )
                
                # Verify
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "consent" in data
                assert data["consent"]["consent_type"] == "analytics"
                assert data["consent"]["status"] == "granted"
    
    def test_record_consent_invalid_type(self, client, mock_user):
        """Test consent recording with invalid type."""
        with patch('app.dependencies.auth.get_current_user', return_value=mock_user):
            response = client.post(
                "/api/gdpr/consent",
                json={
                    "consent_type": "invalid_type",
                    "status": "granted"
                }
            )
            
            assert response.status_code == 422  # Validation error
    
    def test_record_consent_unauthenticated(self, client):
        """Test consent recording without authentication."""
        with patch('app.dependencies.auth.get_current_user', return_value=None):
            response = client.post(
                "/api/gdpr/consent",
                json={
                    "consent_type": "analytics",
                    "status": "granted"
                }
            )
            
            assert response.status_code == 401
    
    def test_get_consents_success(self, client, mock_user, mock_firestore):
        """Test retrieving consent history."""
        with patch('app.dependencies.auth.get_current_user', return_value=mock_user):
            with patch('app.services.gcp_service.get_firestore_client', return_value=mock_firestore):
                # Setup mock
                mock_collection = Mock()
                mock_firestore.collection.return_value = mock_collection
                mock_collection.where.return_value.stream.return_value = []
                
                # Make request
                response = client.get("/api/gdpr/consent")
                
                # Verify
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "consents" in data
                assert isinstance(data["consents"], list)


class TestDataExportEndpoint:
    """Test data export endpoint."""
    
    def test_export_data_success(self, client, mock_user, mock_firestore):
        """Test successful data export."""
        with patch('app.dependencies.auth.get_current_user', return_value=mock_user):
            with patch('app.services.gcp_service.get_firestore_client', return_value=mock_firestore):
                # Setup mock
                mock_user_doc = Mock()
                mock_user_doc.exists = True
                mock_user_doc.to_dict.return_value = {"email": "test@example.com"}
                
                mock_firestore.collection.return_value.document.return_value.get.return_value = mock_user_doc
                mock_firestore.collection.return_value.where.return_value.stream.return_value = []
                
                # Make request
                response = client.post("/api/gdpr/export")
                
                # Verify
                assert response.status_code == 200
                assert response.headers["content-type"] == "application/json"
                assert "attachment" in response.headers.get("content-disposition", "")
                
                # Verify JSON structure
                data = json.loads(response.content)
                assert "user_id" in data
                assert "export_date" in data
                assert "profile_data" in data
    
    def test_export_data_unauthenticated(self, client):
        """Test data export without authentication."""
        with patch('app.dependencies.auth.get_current_user', return_value=None):
            response = client.post("/api/gdpr/export")
            assert response.status_code == 401
    
    def test_export_data_rate_limiting(self, client, mock_user, mock_firestore):
        """Test rate limiting on data export."""
        with patch('app.dependencies.auth.get_current_user', return_value=mock_user):
            with patch('app.services.gcp_service.get_firestore_client', return_value=mock_firestore):
                # Setup mock
                mock_user_doc = Mock()
                mock_user_doc.exists = True
                mock_user_doc.to_dict.return_value = {"email": "test@example.com"}
                
                mock_firestore.collection.return_value.document.return_value.get.return_value = mock_user_doc
                mock_firestore.collection.return_value.where.return_value.stream.return_value = []
                
                # Make 6 requests (limit is 5 per day)
                for i in range(6):
                    response = client.post("/api/gdpr/export")
                    
                    if i < 5:
                        assert response.status_code == 200
                    else:
                        # 6th request should be rate limited
                        assert response.status_code == 429
                        assert "Rate limit exceeded" in response.json()["detail"]


class TestAccountDeletionEndpoints:
    """Test account deletion endpoints."""
    
    @patch('app.services.token_service.send_deletion_confirmation_email')
    def test_request_deletion_success(self, mock_send_email, client, mock_user):
        """Test requesting account deletion."""
        mock_send_email.return_value = True
        
        with patch('app.dependencies.auth.get_current_user', return_value=mock_user):
            response = client.post("/api/gdpr/delete/request")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "message" in data
            assert data["email"] == mock_user.email
            assert "expires_at" in data
            
            # Verify email was sent
            mock_send_email.assert_called_once()
    
    def test_request_deletion_unauthenticated(self, client):
        """Test requesting deletion without authentication."""
        with patch('app.dependencies.auth.get_current_user', return_value=None):
            response = client.post("/api/gdpr/delete/request")
            assert response.status_code == 401
    
    @patch('app.services.token_service.validate_deletion_token')
    def test_delete_account_success(self, mock_validate, client, mock_user, mock_firestore):
        """Test successful account deletion with valid token."""
        mock_validate.return_value = (True, None)
        
        with patch('app.dependencies.auth.get_current_user', return_value=mock_user):
            with patch('app.services.gcp_service.get_firestore_client', return_value=mock_firestore):
                # Setup mock
                mock_user_ref = Mock()
                mock_firestore.collection.return_value.document.return_value = mock_user_ref
                
                # Make request
                response = client.post(
                    "/api/gdpr/delete",
                    json={
                        "user_id": mock_user.user_id,
                        "email": mock_user.email,
                        "confirmation_token": "valid-token-123",
                        "delete_all_data": True
                    }
                )
                
                # Verify
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "permanent_deletion_date" in data
                
                # Verify soft delete was called
                mock_user_ref.update.assert_called_once()
    
    @patch('app.services.token_service.validate_deletion_token')
    def test_delete_account_invalid_token(self, mock_validate, client, mock_user):
        """Test account deletion with invalid token."""
        mock_validate.return_value = (False, "Token has expired")
        
        with patch('app.dependencies.auth.get_current_user', return_value=mock_user):
            response = client.post(
                "/api/gdpr/delete",
                json={
                    "user_id": mock_user.user_id,
                    "email": mock_user.email,
                    "confirmation_token": "invalid-token",
                    "delete_all_data": True
                }
            )
            
            assert response.status_code == 400
            assert "Invalid confirmation token" in response.json()["detail"]
    
    def test_delete_account_email_mismatch(self, client, mock_user):
        """Test account deletion with mismatched email."""
        with patch('app.dependencies.auth.get_current_user', return_value=mock_user):
            response = client.post(
                "/api/gdpr/delete",
                json={
                    "user_id": mock_user.user_id,
                    "email": "wrong@example.com",
                    "confirmation_token": "token",
                    "delete_all_data": True
                }
            )
            
            assert response.status_code == 403
            assert "Email mismatch" in response.json()["detail"]


class TestPrivacySettingsEndpoints:
    """Test privacy settings endpoints."""
    
    def test_get_privacy_settings_success(self, client, mock_user, mock_firestore):
        """Test retrieving privacy settings."""
        with patch('app.dependencies.auth.get_current_user', return_value=mock_user):
            with patch('app.services.gcp_service.get_firestore_client', return_value=mock_firestore):
                # Setup mock - no existing settings
                mock_doc = Mock()
                mock_doc.exists = False
                mock_firestore.collection.return_value.document.return_value.get.return_value = mock_doc
                
                # Make request
                response = client.get("/api/gdpr/privacy-settings")
                
                # Verify
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "settings" in data
                assert data["settings"]["user_id"] == mock_user.user_id
    
    def test_update_privacy_settings_success(self, client, mock_user, mock_firestore):
        """Test updating privacy settings."""
        with patch('app.dependencies.auth.get_current_user', return_value=mock_user):
            with patch('app.services.gcp_service.get_firestore_client', return_value=mock_firestore):
                # Setup mock
                mock_ref = Mock()
                mock_firestore.collection.return_value.document.return_value = mock_ref
                
                # Make request
                response = client.put(
                    "/api/gdpr/privacy-settings",
                    json={
                        "user_id": mock_user.user_id,
                        "ai_tutoring_enabled": False,
                        "analytics_enabled": True,
                        "marketing_emails_enabled": False,
                        "data_retention_days": 365,
                        "updated_at": datetime.utcnow().isoformat()
                    }
                )
                
                # Verify
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert data["settings"]["ai_tutoring_enabled"] is False
                
                # Verify Firestore was updated
                mock_ref.set.assert_called_once()

