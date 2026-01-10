"""Tests for Flashcard Notes API endpoints.

Tests the REST API endpoints for flashcard note CRUD operations.
"""

import pytest
from unittest.mock import MagicMock, patch, Mock
from fastapi.testclient import TestClient
from datetime import datetime, timezone

from app.main import app
from app.models.flashcard_models import FlashcardNoteCreate, FlashcardNoteUpdate
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
    with patch('app.routes.flashcard_notes.get_firestore_client') as mock:
        db = MagicMock()
        mock.return_value = db
        yield db


@pytest.fixture
def mock_rate_limiter():
    """Mock rate limiter to always allow requests."""
    with patch('app.routes.flashcard_notes.check_flashcard_rate_limit') as mock:
        mock.return_value = (True, None)
        yield mock


@pytest.fixture
def sample_note_data():
    """Sample note data for testing."""
    return {
        'id': 'note_123',
        'user_id': 'test@example.com',
        'card_id': 'card_456',
        'set_id': 'set_789',
        'note_text': 'This is a test note',
        'created_at': datetime.now(timezone.utc),
        'updated_at': datetime.now(timezone.utc)
    }


class TestCreateNote:
    """Tests for POST /api/flashcards/notes."""

    def test_create_note_new(self, client, mock_firestore, mock_rate_limiter, mock_user, sample_note_data):
        """Should create a new note when none exists."""
        # Mock transaction and query to return no existing notes
        mock_transaction = MagicMock()
        mock_firestore.transaction.return_value = mock_transaction
        
        # Mock query to return empty list (no existing notes)
        mock_query = MagicMock()
        mock_query.get.return_value = []
        mock_firestore.collection.return_value.document.return_value.collection.return_value.where.return_value.where.return_value.limit.return_value = mock_query
        
        # Mock the transactional function
        with patch('app.routes.flashcard_notes.create_or_update_note_transactional') as mock_transactional:
            mock_transactional.return_value = ('note_123', sample_note_data)
            
            # Mock authentication
            from app.dependencies.auth import get_current_user
            app.dependency_overrides[get_current_user] = lambda: mock_user
            
            try:
                note_create = FlashcardNoteCreate(
                    card_id='card_456',
                    set_id='set_789',
                    note_text='This is a test note'
                )
                
                response = client.post(
                    "/api/flashcards/notes",
                    json=note_create.model_dump()
                )
                
                assert response.status_code == 201
                data = response.json()
                assert data['card_id'] == 'card_456'
                assert data['set_id'] == 'set_789'
                assert data['note_text'] == 'This is a test note'
                assert 'id' in data
                assert 'created_at' in data
                assert 'updated_at' in data
                
                # Verify transactional function was called
                mock_transactional.assert_called_once()
            finally:
                app.dependency_overrides.clear()

    def test_create_note_update_existing(self, client, mock_firestore, mock_rate_limiter, mock_user, sample_note_data):
        """Should update existing note when one exists for the same card."""
        mock_transaction = MagicMock()
        mock_firestore.transaction.return_value = mock_transaction
        
        # Update sample data
        updated_data = sample_note_data.copy()
        updated_data['note_text'] = 'Updated note text'
        
        with patch('app.routes.flashcard_notes.create_or_update_note_transactional') as mock_transactional:
            mock_transactional.return_value = ('note_123', updated_data)
            
            from app.dependencies.auth import get_current_user
            app.dependency_overrides[get_current_user] = lambda: mock_user
            
            try:
                note_create = FlashcardNoteCreate(
                    card_id='card_456',
                    set_id='set_789',
                    note_text='Updated note text'
                )
                
                response = client.post(
                    "/api/flashcards/notes",
                    json=note_create.model_dump()
                )
                
                assert response.status_code == 201
                data = response.json()
                assert data['note_text'] == 'Updated note text'
            finally:
                app.dependency_overrides.clear()

    def test_create_note_empty_text_validation(self, client, mock_user):
        """Should reject empty note text."""
        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            response = client.post(
                "/api/flashcards/notes",
                json={
                    'card_id': 'card_456',
                    'set_id': 'set_789',
                    'note_text': ''
                }
            )
            
            assert response.status_code == 422  # Validation error
        finally:
            app.dependency_overrides.clear()

    def test_create_note_text_too_long_validation(self, client, mock_user):
        """Should reject note text exceeding max length."""
        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            response = client.post(
                "/api/flashcards/notes",
                json={
                    'card_id': 'card_456',
                    'set_id': 'set_789',
                    'note_text': 'x' * 5001  # Exceeds 5000 char limit
                }
            )
            
            assert response.status_code == 422  # Validation error
        finally:
            app.dependency_overrides.clear()

    def test_create_note_html_sanitization(self, client, mock_firestore, mock_rate_limiter, mock_user, sample_note_data):
        """Should sanitize HTML in note text."""
        mock_transaction = MagicMock()
        mock_firestore.transaction.return_value = mock_transaction
        
        sanitized_data = sample_note_data.copy()
        sanitized_data['note_text'] = '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;'
        
        with patch('app.routes.flashcard_notes.create_or_update_note_transactional') as mock_transactional:
            mock_transactional.return_value = ('note_123', sanitized_data)
            
            from app.dependencies.auth import get_current_user
            app.dependency_overrides[get_current_user] = lambda: mock_user
            
            try:
                note_create = FlashcardNoteCreate(
                    card_id='card_456',
                    set_id='set_789',
                    note_text='<script>alert("xss")</script>'
                )
                
                response = client.post(
                    "/api/flashcards/notes",
                    json=note_create.model_dump()
                )
                
                assert response.status_code == 201
                data = response.json()
                # HTML should be escaped
                assert '<script>' not in data['note_text']
                assert '&lt;script&gt;' in data['note_text']
            finally:
                app.dependency_overrides.clear()

    def test_create_note_rate_limit_exceeded(self, client, mock_user):
        """Should return 429 when rate limit exceeded."""
        with patch('app.routes.flashcard_notes.check_flashcard_rate_limit') as mock_rate_limit:
            mock_rate_limit.return_value = (False, "Rate limit exceeded")
            
            from app.dependencies.auth import get_current_user
            app.dependency_overrides[get_current_user] = lambda: mock_user
            
            try:
                note_create = FlashcardNoteCreate(
                    card_id='card_456',
                    set_id='set_789',
                    note_text='Test note'
                )
                
                response = client.post(
                    "/api/flashcards/notes",
                    json=note_create.model_dump()
                )
                
                assert response.status_code == 429
                assert "Rate limit" in response.json()['detail']
            finally:
                app.dependency_overrides.clear()

    def test_create_note_firestore_error(self, client, mock_firestore, mock_rate_limiter, mock_user):
        """Should return 500 on Firestore error."""
        mock_firestore.transaction.side_effect = Exception("Firestore error")
        
        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            note_create = FlashcardNoteCreate(
                card_id='card_456',
                set_id='set_789',
                note_text='Test note'
            )
            
            response = client.post(
                "/api/flashcards/notes",
                json=note_create.model_dump()
            )
            
            assert response.status_code == 500
            assert "Unable to create note" in response.json()['detail']
        finally:
            app.dependency_overrides.clear()


class TestGetNote:
    """Tests for GET /api/flashcards/notes/{card_id}."""

    def test_get_note_found(self, client, mock_firestore, mock_rate_limiter, mock_user, sample_note_data):
        """Should return note when found."""
        # Mock Firestore query
        mock_doc = MagicMock()
        mock_doc.id = 'note_123'
        mock_doc.to_dict.return_value = sample_note_data
        
        mock_query = MagicMock()
        mock_query.get.return_value = [mock_doc]
        mock_firestore.collection.return_value.document.return_value.collection.return_value.where.return_value.where.return_value.limit.return_value = mock_query
        
        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            response = client.get("/api/flashcards/notes/card_456?set_id=set_789")
            
            assert response.status_code == 200
            data = response.json()
            assert data['card_id'] == 'card_456'
            assert data['set_id'] == 'set_789'
            assert data['note_text'] == 'This is a test note'
        finally:
            app.dependency_overrides.clear()

    def test_get_note_not_found(self, client, mock_firestore, mock_rate_limiter, mock_user):
        """Should return 404 when note not found."""
        mock_query = MagicMock()
        mock_query.get.return_value = []
        mock_firestore.collection.return_value.document.return_value.collection.return_value.where.return_value.where.return_value.limit.return_value = mock_query
        
        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            response = client.get("/api/flashcards/notes/card_456?set_id=set_789")
            
            assert response.status_code == 404
            assert "Note not found" in response.json()['detail']
        finally:
            app.dependency_overrides.clear()

    def test_get_note_rate_limit_exceeded(self, client, mock_user):
        """Should return 429 when rate limit exceeded."""
        with patch('app.routes.flashcard_notes.check_flashcard_rate_limit') as mock_rate_limit:
            mock_rate_limit.return_value = (False, "Rate limit exceeded")

            from app.dependencies.auth import get_current_user
            app.dependency_overrides[get_current_user] = lambda: mock_user

            try:
                response = client.get("/api/flashcards/notes/card_456?set_id=set_789")

                assert response.status_code == 429
            finally:
                app.dependency_overrides.clear()


class TestGetAllNotes:
    """Tests for GET /api/flashcards/notes."""

    def test_get_all_notes_no_filter(self, client, mock_firestore, mock_rate_limiter, mock_user, sample_note_data):
        """Should return all notes for user without filter."""
        mock_doc1 = MagicMock()
        mock_doc1.id = 'note_1'
        mock_doc1.to_dict.return_value = sample_note_data

        mock_doc2 = MagicMock()
        mock_doc2.id = 'note_2'
        note_data_2 = sample_note_data.copy()
        note_data_2['card_id'] = 'card_999'
        mock_doc2.to_dict.return_value = note_data_2

        mock_query = MagicMock()
        mock_query.get.return_value = [mock_doc1, mock_doc2]
        mock_firestore.collection.return_value.document.return_value.collection.return_value = mock_query

        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user

        try:
            response = client.get("/api/flashcards/notes")

            assert response.status_code == 200
            data = response.json()
            assert data['total'] == 2
            assert len(data['notes']) == 2
        finally:
            app.dependency_overrides.clear()

    def test_get_all_notes_with_set_filter(self, client, mock_firestore, mock_rate_limiter, mock_user, sample_note_data):
        """Should filter notes by set_id."""
        mock_doc = MagicMock()
        mock_doc.id = 'note_1'
        mock_doc.to_dict.return_value = sample_note_data

        mock_query = MagicMock()
        mock_query.where.return_value.get.return_value = [mock_doc]
        mock_firestore.collection.return_value.document.return_value.collection.return_value = mock_query

        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user

        try:
            response = client.get("/api/flashcards/notes?set_id=set_789")

            assert response.status_code == 200
            data = response.json()
            assert data['total'] == 1
            # Verify where was called with set_id filter
            mock_query.where.assert_called_once_with('set_id', '==', 'set_789')
        finally:
            app.dependency_overrides.clear()

    def test_get_all_notes_empty_result(self, client, mock_firestore, mock_rate_limiter, mock_user):
        """Should handle empty notes list gracefully."""
        mock_query = MagicMock()
        mock_query.get.return_value = []
        mock_firestore.collection.return_value.document.return_value.collection.return_value = mock_query

        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user

        try:
            response = client.get("/api/flashcards/notes")

            assert response.status_code == 200
            data = response.json()
            assert data['total'] == 0
            assert len(data['notes']) == 0
        finally:
            app.dependency_overrides.clear()


class TestUpdateNote:
    """Tests for PUT /api/flashcards/notes/{note_id}."""

    def test_update_note_success(self, client, mock_firestore, mock_rate_limiter, mock_user, sample_note_data):
        """Should update note successfully."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = sample_note_data

        mock_ref = MagicMock()
        mock_ref.get.return_value = mock_doc
        mock_firestore.collection.return_value.document.return_value.collection.return_value.document.return_value = mock_ref

        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user

        try:
            note_update = FlashcardNoteUpdate(note_text='Updated text')

            response = client.put(
                "/api/flashcards/notes/note_123",
                json=note_update.model_dump()
            )

            assert response.status_code == 200
            # Verify update was called
            mock_ref.update.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    def test_update_note_not_found(self, client, mock_firestore, mock_rate_limiter, mock_user):
        """Should return 404 when note not found."""
        mock_doc = MagicMock()
        mock_doc.exists = False

        mock_ref = MagicMock()
        mock_ref.get.return_value = mock_doc
        mock_firestore.collection.return_value.document.return_value.collection.return_value.document.return_value = mock_ref

        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user

        try:
            note_update = FlashcardNoteUpdate(note_text='Updated text')

            response = client.put(
                "/api/flashcards/notes/note_123",
                json=note_update.model_dump()
            )

            assert response.status_code == 404
            assert "Note not found" in response.json()['detail']
        finally:
            app.dependency_overrides.clear()


class TestDeleteNote:
    """Tests for DELETE /api/flashcards/notes/card/{card_id}."""

    def test_delete_note_success(self, client, mock_firestore, mock_rate_limiter, mock_user):
        """Should delete note successfully."""
        mock_doc = MagicMock()
        mock_doc.reference.delete = MagicMock()

        mock_query = MagicMock()
        mock_query.get.return_value = [mock_doc]
        mock_firestore.collection.return_value.document.return_value.collection.return_value.where.return_value.where.return_value.limit.return_value = mock_query

        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user

        try:
            response = client.delete("/api/flashcards/notes/card/card_456?set_id=set_789")

            assert response.status_code == 204
            # Verify delete was called
            mock_doc.reference.delete.assert_called_once()
        finally:
            app.dependency_overrides.clear()

    def test_delete_note_not_found(self, client, mock_firestore, mock_rate_limiter, mock_user):
        """Should return 404 when note not found."""
        mock_query = MagicMock()
        mock_query.get.return_value = []
        mock_firestore.collection.return_value.document.return_value.collection.return_value.where.return_value.where.return_value.limit.return_value = mock_query

        from app.dependencies.auth import get_current_user
        app.dependency_overrides[get_current_user] = lambda: mock_user

        try:
            response = client.delete("/api/flashcards/notes/card/card_456?set_id=set_789")

            assert response.status_code == 404
            assert "Note not found" in response.json()['detail']
        finally:
            app.dependency_overrides.clear()

