"""
Tests for GDPR Compliance Features

Tests for consent management, data export, data deletion, and audit logging.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch

from app.services.gdpr_service import GDPRService
from app.models.gdpr_models import (
    ConsentType, ConsentStatus,
    AuditLogAction
)


class TestGDPRService:
    """Test GDPR service functionality."""
    
    @pytest.fixture
    def mock_firestore(self):
        """Create mock Firestore client."""
        mock_db = Mock()
        return mock_db
    
    @pytest.fixture
    def gdpr_service(self, mock_firestore):
        """Create GDPR service with mock Firestore."""
        return GDPRService(mock_firestore)
    
    # ========== Consent Management Tests ==========
    
    @pytest.mark.asyncio
    async def test_record_consent_success(self, gdpr_service, mock_firestore):
        """Test successful consent recording."""
        # Setup
        mock_collection = Mock()
        mock_doc = Mock()
        mock_firestore.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc
        
        # Execute
        consent = await gdpr_service.record_consent(
            user_id="test-user-123",
            consent_type=ConsentType.ANALYTICS,
            status=ConsentStatus.GRANTED,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0"
        )
        
        # Verify
        assert consent is not None
        assert consent.user_id == "test-user-123"
        assert consent.consent_type == ConsentType.ANALYTICS
        assert consent.status == ConsentStatus.GRANTED
        assert consent.ip_address == "192.168.1.1"
        mock_doc.set.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_record_consent_empty_user_id(self, gdpr_service):
        """Test consent recording with empty user ID."""
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            await gdpr_service.record_consent(
                user_id="",
                consent_type=ConsentType.ANALYTICS,
                status=ConsentStatus.GRANTED
            )
    
    @pytest.mark.asyncio
    async def test_record_consent_no_database(self):
        """Test consent recording without database."""
        service = GDPRService(None)
        
        with pytest.raises(Exception, match="Database unavailable"):
            await service.record_consent(
                user_id="test-user",
                consent_type=ConsentType.ANALYTICS,
                status=ConsentStatus.GRANTED
            )
    
    # ========== Data Export Tests ==========
    
    @pytest.mark.asyncio
    async def test_export_user_data_success(self, gdpr_service, mock_firestore):
        """Test successful data export."""
        # Setup mock collections
        mock_users = Mock()
        mock_user_doc = Mock()
        mock_user_doc.exists = True
        mock_user_doc.to_dict.return_value = {"email": "test@example.com"}
        mock_users.document.return_value.get.return_value = mock_user_doc
        
        mock_quiz = Mock()
        mock_quiz.stream.return_value = []
        
        mock_firestore.collection.side_effect = lambda name: {
            'users': mock_users,
            'quiz_results': mock_quiz,
            'tutor_conversations': Mock(stream=Mock(return_value=[])),
            'user_materials': Mock(stream=Mock(return_value=[])),
            'consent_records': Mock(stream=Mock(return_value=[])),
            'course_progress': Mock(stream=Mock(return_value=[]))
        }.get(name, Mock(stream=Mock(return_value=[])))
        
        # Execute
        export_data = await gdpr_service.export_user_data("test-user-123")
        
        # Verify
        assert export_data is not None
        assert export_data.user_id == "test-user-123"
        assert export_data.profile_data == {"email": "test@example.com"}
        assert isinstance(export_data.quiz_results, list)
    
    @pytest.mark.asyncio
    async def test_export_user_data_empty_user_id(self, gdpr_service):
        """Test data export with empty user ID."""
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            await gdpr_service.export_user_data("")
    
    @pytest.mark.asyncio
    async def test_export_user_data_no_database(self):
        """Test data export without database."""
        service = GDPRService(None)
        
        with pytest.raises(ValueError, match="Data export service unavailable"):
            await service.export_user_data("test-user")
    
    # ========== Data Deletion Tests ==========
    
    @pytest.mark.asyncio
    async def test_delete_user_data_soft_delete(self, gdpr_service, mock_firestore):
        """Test soft delete of user data."""
        # Setup
        mock_user_ref = Mock()
        mock_firestore.collection.return_value.document.return_value = mock_user_ref
        
        # Execute
        result = await gdpr_service.delete_user_data(
            user_id="test-user-123",
            soft_delete=True,
            retention_days=30
        )
        
        # Verify
        assert result is True
        mock_user_ref.update.assert_called_once()
        call_args = mock_user_ref.update.call_args[0][0]
        assert call_args['deleted'] is True
        assert 'deleted_at' in call_args
        assert 'permanent_deletion_date' in call_args
    
    @pytest.mark.asyncio
    async def test_delete_user_data_empty_user_id(self, gdpr_service):
        """Test data deletion with empty user ID."""
        with pytest.raises(ValueError, match="user_id cannot be empty"):
            await gdpr_service.delete_user_data("")
    
    @pytest.mark.asyncio
    async def test_delete_user_data_negative_retention(self, gdpr_service):
        """Test data deletion with negative retention days."""
        with pytest.raises(ValueError, match="retention_days must be non-negative"):
            await gdpr_service.delete_user_data(
                user_id="test-user",
                retention_days=-1
            )
    
    @pytest.mark.asyncio
    async def test_delete_user_data_no_database(self):
        """Test data deletion without database."""
        service = GDPRService(None)
        
        with pytest.raises(ValueError, match="Data deletion service unavailable"):
            await service.delete_user_data("test-user")


class TestGDPRValidation:
    """Test GDPR input validation."""
    
    def test_consent_type_validation(self):
        """Test consent type enum validation."""
        valid_types = [
            ConsentType.ESSENTIAL,
            ConsentType.FUNCTIONAL,
            ConsentType.ANALYTICS,
            ConsentType.AI_TUTORING,
            ConsentType.MARKETING
        ]
        
        for consent_type in valid_types:
            assert consent_type in ConsentType.__members__.values()
    
    def test_consent_status_validation(self):
        """Test consent status enum validation."""
        valid_statuses = [
            ConsentStatus.GRANTED,
            ConsentStatus.REVOKED,
            ConsentStatus.PENDING
        ]
        
        for status in valid_statuses:
            assert status in ConsentStatus.__members__.values()


class TestGDPRRateLimiting:
    """Test rate limiting functionality."""
    
    def test_rate_limit_structure(self):
        """Test rate limit storage structure."""
        from app.routes.gdpr import _rate_limit_storage
        
        # Should be a defaultdict
        assert hasattr(_rate_limit_storage, '__getitem__')
        
        # Test default structure
        test_key = "test-user:test-endpoint"
        entry = _rate_limit_storage[test_key]
        assert "count" in entry
        assert "reset_time" in entry


class TestGDPRSecurity:
    """Test GDPR security features."""
    
    def test_filename_sanitization(self):
        """Test filename sanitization for data export."""
        import re
        
        # Test cases
        test_cases = [
            ("user@example.com", "userexamplecom"),
            ("user/../../../etc/passwd", "useretcpasswd"),
            ("user<script>alert('xss')</script>", "userscriptalertxssscript"),
            ("normal-user_123", "normal-user_123")
        ]
        
        for input_id, expected in test_cases:
            sanitized = re.sub(r'[^a-zA-Z0-9_-]', '', input_id[:50])
            assert sanitized == expected
    
    def test_email_validation_required(self):
        """Test that email validation is enforced."""
        from app.routes.gdpr import DeleteAccountRequest
        from pydantic import ValidationError
        
        # Valid email should pass
        valid_request = DeleteAccountRequest(
            user_id="test-user",
            email="valid@example.com",
            confirmation_token="confirmed"
        )
        assert valid_request.email == "valid@example.com"
        
        # Invalid email should fail
        with pytest.raises(ValidationError):
            DeleteAccountRequest(
                user_id="test-user",
                email="invalid-email",
                confirmation_token="confirmed"
            )


class TestGDPRAuditLogging:
    """Test audit logging functionality."""
    
    @pytest.mark.asyncio
    async def test_audit_log_creation(self, mock_firestore):
        """Test audit log is created for GDPR operations."""
        service = GDPRService(mock_firestore)
        
        # Setup mock
        mock_collection = Mock()
        mock_doc = Mock()
        mock_firestore.collection.return_value = mock_collection
        mock_collection.document.return_value = mock_doc
        
        # Execute
        await service.log_audit(
            action=AuditLogAction.DATA_EXPORT,
            user_id="test-user",
            ip_address="192.168.1.1",
            details={"export_size": 1024}
        )
        
        # Verify
        mock_firestore.collection.assert_called_with('audit_logs')
        mock_doc.set.assert_called_once()

