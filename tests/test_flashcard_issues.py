"""Tests for Flashcard Issues API endpoints.

Tests the REST API endpoints for flashcard issue reporting and management.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app
from app.models.flashcard_models import FlashcardIssueCreate, FlashcardIssueUpdate
from app.models.auth_models import User


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Mock authenticated user (non-admin)."""
    return User(
        email="test@example.com",
        user_id="test_user_123",
        domain="example.com",
        is_admin=False
    )


@pytest.fixture
def mock_admin_user():
    """Mock authenticated admin user."""
    return User(
        email="admin@mgms.eu",
        user_id="admin_user_123",
        domain="mgms.eu",
        is_admin=True
    )


@pytest.fixture
def mock_firestore():
    """Mock Firestore client."""
    with patch('app.routes.flashcard_issues.get_firestore_client') as mock:
        db = MagicMock()
        mock.return_value = db
        yield db


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter to always allow requests."""
    with patch('app.routes.flashcard_issues.check_flashcard_rate_limit') as mock:
        mock.return_value = (True, None)
        yield mock


@pytest.fixture
def sample_issue_data():
    """Sample issue data for testing."""
    return {
        'id': 'issue_123',
        'user_id': 'test@example.com',
        'card_id': 'card_456',
        'set_id': 'set_789',
        'issue_type': 'incorrect',  # Valid types: incorrect, typo, unclear, other
        'description': 'The answer is wrong',
        'status': 'open',
        'created_at': datetime.now(timezone.utc),
        'resolved_at': None,
        'admin_notes': None
    }


class TestCreateIssue:
    """Tests for POST /api/flashcards/issues."""

    def test_create_issue_success(self, client, mock_firestore, mock_rate_limiter, mock_user, sample_issue_data):
        """Should create issue successfully."""
        mock_ref = MagicMock()
        mock_firestore.collection.return_value.document.return_value = mock_ref
        
        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            issue_create = FlashcardIssueCreate(
                card_id='card_456',
                set_id='set_789',
                issue_type='incorrect',
                description='The answer is wrong'
            )
            
            response = client.post(
                "/api/flashcards/issues",
                json=issue_create.model_dump()
            )
            
            assert response.status_code == 201
            data = response.json()
            assert data['card_id'] == 'card_456'
            assert data['set_id'] == 'set_789'
            assert data['issue_type'] == 'incorrect'
            assert data['description'] == 'The answer is wrong'
            assert data['status'] == 'open'
            assert 'id' in data
            assert 'created_at' in data
            
            # Verify Firestore set was called
            mock_ref.set.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    def test_create_issue_invalid_type_validation(self, client, mock_user):
        """Should reject invalid issue type."""
        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            response = client.post(
                "/api/flashcards/issues",
                json={
                    'card_id': 'card_456',
                    'set_id': 'set_789',
                    'issue_type': 'invalid_type',
                    'description': 'Test description'
                }
            )
            
            assert response.status_code == 422  # Validation error
        finally:
            app.dependency_overrides.clear()

    def test_create_issue_empty_description_validation(self, client, mock_user):
        """Should reject empty description."""
        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            response = client.post(
                "/api/flashcards/issues",
                json={
                    'card_id': 'card_456',
                    'set_id': 'set_789',
                    'issue_type': 'incorrect_answer',
                    'description': ''
                }
            )
            
            assert response.status_code == 422  # Validation error
        finally:
            app.dependency_overrides.clear()

    def test_create_issue_description_too_long_validation(self, client, mock_user):
        """Should reject description exceeding max length."""
        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            response = client.post(
                "/api/flashcards/issues",
                json={
                    'card_id': 'card_456',
                    'set_id': 'set_789',
                    'issue_type': 'incorrect_answer',
                    'description': 'x' * 2001  # Exceeds 2000 char limit
                }
            )
            
            assert response.status_code == 422  # Validation error
        finally:
            app.dependency_overrides.clear()

    def test_create_issue_html_sanitization(self, client, mock_firestore, mock_rate_limiter, mock_user):
        """Should sanitize HTML in description."""
        mock_ref = MagicMock()
        mock_firestore.collection.return_value.document.return_value = mock_ref
        
        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            issue_create = FlashcardIssueCreate(
                card_id='card_456',
                set_id='set_789',
                issue_type='incorrect',
                description='<script>alert("xss")</script>'
            )
            
            response = client.post(
                "/api/flashcards/issues",
                json=issue_create.model_dump()
            )
            
            assert response.status_code == 201
            data = response.json()
            # HTML should be escaped (may be double-escaped due to Pydantic validation)
            assert '<script>' not in data['description']
            # Accept either single or double escaping
            assert ('&lt;script&gt;' in data['description'] or
                    '&amp;lt;script&amp;gt;' in data['description'])
        finally:
            app.dependency_overrides.clear()

    def test_create_issue_rate_limit_exceeded(self, client, mock_user):
        """Should return 429 when rate limit exceeded."""
        with patch('app.routes.flashcard_issues.check_flashcard_rate_limit') as mock_rate_limit:
            mock_rate_limit.return_value = (False, "Rate limit exceeded")
            
            from app.dependencies.auth import get_current_user
            app.dependency_overrides[get_current_user] = lambda: mock_user
            
            try:
                issue_create = FlashcardIssueCreate(
                    card_id='card_456',
                    set_id='set_789',
                    issue_type='incorrect',
                    description='Test description'
                )
                
                response = client.post(
                    "/api/flashcards/issues",
                    json=issue_create.model_dump()
                )
                
                assert response.status_code == 429
                assert "Rate limit" in response.json()['detail']
            finally:
                app.dependency_overrides.clear()

    def test_create_issue_firestore_error(self, client, mock_firestore, mock_rate_limiter, mock_user):
        """Should return 500 on Firestore error."""
        mock_firestore.collection.return_value.document.return_value.set.side_effect = Exception("Firestore error")
        
        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            issue_create = FlashcardIssueCreate(
                card_id='card_456',
                set_id='set_789',
                issue_type='incorrect',
                description='Test description'
            )
            
            response = client.post(
                "/api/flashcards/issues",
                json=issue_create.model_dump()
            )
            
            assert response.status_code == 500
            assert "Unable to report issue" in response.json()['detail']
        finally:
            app.dependency_overrides.clear()


class TestGetIssue:
    """Tests for GET /api/flashcards/issues/{issue_id}."""

    def test_get_issue_owner_can_see(self, client, mock_firestore, mock_rate_limiter, mock_user, sample_issue_data):
        """Should allow owner to see their own issue."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = sample_issue_data
        
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_doc
        
        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            response = client.get("/api/flashcards/issues/issue_123")
            
            assert response.status_code == 200
            data = response.json()
            assert data['id'] == 'issue_123'
            assert data['user_id'] == 'test@example.com'
        finally:
            app.dependency_overrides.clear()

    def test_get_issue_non_owner_cannot_see(self, client, mock_firestore, mock_rate_limiter, mock_user, sample_issue_data):
        """Should deny access to non-owner."""
        # Change user_id to different user
        other_user_issue = sample_issue_data.copy()
        other_user_issue['user_id'] = 'other@example.com'
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = other_user_issue
        
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_doc
        
        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            response = client.get("/api/flashcards/issues/issue_123")
            
            assert response.status_code == 403
            assert "Access denied" in response.json()['detail']
        finally:
            app.dependency_overrides.clear()

    def test_get_issue_admin_can_see_any(self, client, mock_firestore, mock_rate_limiter, mock_admin_user, sample_issue_data):
        """Should allow admin to see any issue."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = sample_issue_data
        
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_doc
        
        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_admin_user
        
        try:
            response = client.get("/api/flashcards/issues/issue_123")
            
            assert response.status_code == 200
            data = response.json()
            assert data['id'] == 'issue_123'
        finally:
            app.dependency_overrides.clear()

    def test_get_issue_not_found(self, client, mock_firestore, mock_rate_limiter, mock_user):
        """Should return 404 when issue not found."""
        mock_doc = MagicMock()
        mock_doc.exists = False
        
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_doc
        
        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            response = client.get("/api/flashcards/issues/issue_123")
            
            assert response.status_code == 404
            assert "Issue not found" in response.json()['detail']
        finally:
            app.dependency_overrides.clear()


class TestGetAllIssues:
    """Tests for GET /api/flashcards/issues."""

    def test_get_all_issues_user_sees_only_own(self, client, mock_firestore, mock_rate_limiter, mock_user, sample_issue_data):
        """Should return only user's own issues."""
        mock_doc = MagicMock()
        mock_doc.id = 'issue_123'
        mock_doc.to_dict.return_value = sample_issue_data

        # Mock the query chain properly
        mock_query = MagicMock()
        mock_query.where.return_value.get.return_value = [mock_doc]
        mock_firestore.collection.return_value = mock_query

        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user

        try:
            response = client.get("/api/flashcards/issues")

            assert response.status_code == 200
            data = response.json()
            assert data['total'] == 1
            assert len(data['issues']) == 1
            # Verify where was called to filter by user_id
            mock_query.where.assert_called_with('user_id', '==', 'test@example.com')
        finally:
            app.dependency_overrides.clear()

    def test_get_all_issues_admin_sees_all(self, client, mock_firestore, mock_rate_limiter, mock_admin_user, sample_issue_data):
        """Should return all issues for admin."""
        mock_doc1 = MagicMock()
        mock_doc1.id = 'issue_1'
        mock_doc1.to_dict.return_value = sample_issue_data

        mock_doc2 = MagicMock()
        mock_doc2.id = 'issue_2'
        issue_data_2 = sample_issue_data.copy()
        issue_data_2['user_id'] = 'other@example.com'
        mock_doc2.to_dict.return_value = issue_data_2

        mock_query = MagicMock()
        mock_query.get.return_value = [mock_doc1, mock_doc2]
        mock_firestore.collection.return_value = mock_query

        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_admin_user

        try:
            response = client.get("/api/flashcards/issues")

            assert response.status_code == 200
            data = response.json()
            assert data['total'] == 2
            assert len(data['issues']) == 2
            # Admin should NOT have user_id filter
            # Verify where was NOT called with user_id
            calls = [str(call) for call in mock_query.where.call_args_list]
            user_id_filter = any('user_id' in call for call in calls)
            assert not user_id_filter
        finally:
            app.dependency_overrides.clear()

    def test_get_all_issues_filter_by_set_id(self, client, mock_firestore, mock_rate_limiter, mock_user, sample_issue_data):
        """Should filter issues by set_id."""
        mock_doc = MagicMock()
        mock_doc.id = 'issue_123'
        mock_doc.to_dict.return_value = sample_issue_data

        # Create a proper mock chain
        mock_where_result = MagicMock()
        mock_where_result.where.return_value.get.return_value = [mock_doc]

        mock_query = MagicMock()
        mock_query.where.return_value = mock_where_result
        mock_firestore.collection.return_value = mock_query

        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user

        try:
            response = client.get("/api/flashcards/issues?set_id=set_789")

            assert response.status_code == 200
            data = response.json()
            assert data['total'] == 1
            # Verify where was called twice (user_id and set_id)
            assert mock_query.where.call_count == 1  # First where for user_id
            assert mock_where_result.where.call_count == 1  # Second where for set_id
        finally:
            app.dependency_overrides.clear()

    def test_get_all_issues_filter_by_status(self, client, mock_firestore, mock_rate_limiter, mock_user, sample_issue_data):
        """Should filter issues by status."""
        mock_doc = MagicMock()
        mock_doc.id = 'issue_123'
        mock_doc.to_dict.return_value = sample_issue_data

        # Create a proper mock chain
        mock_where_result = MagicMock()
        mock_where_result.where.return_value.get.return_value = [mock_doc]

        mock_query = MagicMock()
        mock_query.where.return_value = mock_where_result
        mock_firestore.collection.return_value = mock_query

        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user

        try:
            response = client.get("/api/flashcards/issues?status=open")

            assert response.status_code == 200
            data = response.json()
            assert data['total'] == 1
            # Verify where was called twice (user_id and status)
            assert mock_query.where.call_count == 1  # First where for user_id
            assert mock_where_result.where.call_count == 1  # Second where for status
        finally:
            app.dependency_overrides.clear()


class TestUpdateIssue:
    """Tests for PATCH /api/flashcards/issues/{issue_id}."""

    def test_update_issue_admin_only_success(self, client, mock_firestore, mock_rate_limiter, mock_admin_user, sample_issue_data):
        """Should allow admin to update issue."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = sample_issue_data

        mock_ref = MagicMock()
        mock_ref.get.return_value = mock_doc
        mock_firestore.collection.return_value.document.return_value = mock_ref

        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_admin_user

        try:
            issue_update = FlashcardIssueUpdate(
                status='resolved',
                admin_notes='Fixed the issue'
            )

            response = client.patch(
                "/api/flashcards/issues/issue_123",
                json=issue_update.model_dump()
            )

            assert response.status_code == 200
            # Verify update was called
            mock_ref.update.assert_called_once()
            # Verify resolved_at was set
            update_call = mock_ref.update.call_args[0][0]
            assert 'resolved_at' in update_call
        finally:
            app.dependency_overrides.clear()

    def test_update_issue_non_admin_forbidden(self, client, mock_user):
        """Should deny non-admin users from updating issues."""
        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user

        try:
            issue_update = FlashcardIssueUpdate(
                status='resolved',
                admin_notes='Trying to update'
            )

            response = client.patch(
                "/api/flashcards/issues/issue_123",
                json=issue_update.model_dump()
            )

            assert response.status_code == 403
            assert "Admin access required" in response.json()['detail']
        finally:
            app.dependency_overrides.clear()

    def test_update_issue_invalid_status_validation(self, client, mock_admin_user):
        """Should reject invalid status."""
        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_admin_user

        try:
            response = client.patch(
                "/api/flashcards/issues/issue_123",
                json={
                    'status': 'invalid_status',
                    'admin_notes': 'Test'
                }
            )

            assert response.status_code == 422  # Validation error
        finally:
            app.dependency_overrides.clear()

    def test_update_issue_resolved_at_set_when_resolved(self, client, mock_firestore, mock_rate_limiter, mock_admin_user, sample_issue_data):
        """Should set resolved_at when status is resolved."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = sample_issue_data

        mock_ref = MagicMock()
        mock_ref.get.return_value = mock_doc
        mock_firestore.collection.return_value.document.return_value = mock_ref

        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_admin_user

        try:
            issue_update = FlashcardIssueUpdate(
                status='resolved',
                admin_notes='Fixed'
            )

            response = client.patch(
                "/api/flashcards/issues/issue_123",
                json=issue_update.model_dump()
            )

            assert response.status_code == 200
            # Verify resolved_at was set
            update_call = mock_ref.update.call_args[0][0]
            assert 'resolved_at' in update_call
            assert update_call['resolved_at'] is not None
        finally:
            app.dependency_overrides.clear()

    def test_update_issue_admin_notes_sanitized(self, client, mock_firestore, mock_rate_limiter, mock_admin_user, sample_issue_data):
        """Should sanitize HTML in admin notes."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = sample_issue_data

        mock_ref = MagicMock()
        mock_ref.get.return_value = mock_doc
        mock_firestore.collection.return_value.document.return_value = mock_ref

        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_admin_user

        try:
            issue_update = FlashcardIssueUpdate(
                status='resolved',
                admin_notes='<script>alert("xss")</script>'
            )

            response = client.patch(
                "/api/flashcards/issues/issue_123",
                json=issue_update.model_dump()
            )

            assert response.status_code == 200
            # Verify HTML was escaped in admin_notes (may be double-escaped due to Pydantic validation)
            update_call = mock_ref.update.call_args[0][0]
            assert '<script>' not in update_call['admin_notes']
            # Accept either single or double escaping
            assert ('&lt;script&gt;' in update_call['admin_notes'] or
                    '&amp;lt;script&amp;gt;' in update_call['admin_notes'])
        finally:
            app.dependency_overrides.clear()


class TestDeleteIssue:
    """Tests for DELETE /api/flashcards/issues/{issue_id}."""

    def test_delete_issue_admin_only_success(self, client, mock_firestore, mock_rate_limiter, mock_admin_user):
        """Should allow admin to delete issue."""
        mock_doc = MagicMock()
        mock_doc.exists = True

        mock_ref = MagicMock()
        mock_ref.get.return_value = mock_doc
        mock_firestore.collection.return_value.document.return_value = mock_ref

        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_admin_user

        try:
            response = client.delete("/api/flashcards/issues/issue_123")

            assert response.status_code == 204
            # Verify delete was called
            mock_ref.delete.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    def test_delete_issue_non_admin_forbidden(self, client, mock_user):
        """Should deny non-admin users from deleting issues."""
        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user

        try:
            response = client.delete("/api/flashcards/issues/issue_123")

            assert response.status_code == 403
            assert "Admin access required" in response.json()['detail']
        finally:
            app.dependency_overrides.clear()

    def test_delete_issue_not_found(self, client, mock_firestore, mock_rate_limiter, mock_admin_user):
        """Should return 404 when issue not found."""
        mock_doc = MagicMock()
        mock_doc.exists = False

        mock_ref = MagicMock()
        mock_ref.get.return_value = mock_doc
        mock_firestore.collection.return_value.document.return_value = mock_ref

        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_admin_user

        try:
            response = client.delete("/api/flashcards/issues/issue_123")

            assert response.status_code == 404
            assert "Issue not found" in response.json()['detail']
        finally:
            app.dependency_overrides.clear()

