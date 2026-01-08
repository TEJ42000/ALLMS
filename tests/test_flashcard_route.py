"""
Unit Tests for Flashcard Route

Tests the /flashcards route endpoint.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestFlashcardRoute:
    """Test flashcard route functionality."""

    def test_flashcard_route_exists(self, client):
        """Test that /flashcards route exists."""
        response = client.get('/flashcards')
        assert response.status_code == 200

    def test_flashcard_route_returns_html(self, client):
        """Test that /flashcards returns HTML."""
        response = client.get('/flashcards')
        assert 'text/html' in response.headers['content-type']

    def test_flashcard_page_has_title(self, client):
        """Test that flashcard page has correct title."""
        response = client.get('/flashcards')
        assert 'Flashcards' in response.text
        assert 'ECHR Learning' in response.text

    def test_flashcard_page_includes_viewer_js(self, client):
        """Test that page includes flashcard-viewer.js."""
        response = client.get('/flashcards')
        assert 'flashcard-viewer.js' in response.text

    def test_flashcard_page_includes_viewer_css(self, client):
        """Test that page includes flashcard-viewer.css."""
        response = client.get('/flashcards')
        assert 'flashcard-viewer.css' in response.text

    def test_flashcard_page_has_viewer_container(self, client):
        """Test that page has flashcard viewer container."""
        response = client.get('/flashcards')
        assert 'id="flashcard-viewer"' in response.text

    def test_flashcard_page_has_sets_container(self, client):
        """Test that page has flashcard sets container."""
        response = client.get('/flashcards')
        assert 'id="flashcard-sets"' in response.text

    def test_flashcard_page_has_sample_data(self, client):
        """Test that page includes sample flashcard data."""
        response = client.get('/flashcards')
        assert 'ECHR Fundamentals' in response.text
        assert 'Legal Terminology' in response.text
        assert 'Case Law Essentials' in response.text

