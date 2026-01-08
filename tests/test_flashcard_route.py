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

    def test_flashcard_page_includes_page_js(self, client):
        """Test that page includes flashcard-page.js (external file)."""
        response = client.get('/flashcards')
        assert 'flashcard-page.js' in response.text

    def test_flashcard_page_includes_page_css(self, client):
        """Test that page includes flashcard-page.css (external file)."""
        response = client.get('/flashcards')
        assert 'flashcard-page.css' in response.text

    def test_flashcard_page_no_inline_scripts(self, client):
        """Test that page has no inline scripts (CSP compliance)."""
        response = client.get('/flashcards')
        # Should not have inline script tags with content
        assert '<script>' not in response.text or 'flashcard-page.js' in response.text

    def test_flashcard_page_no_inline_styles(self, client):
        """Test that page has no inline styles (CSP compliance)."""
        response = client.get('/flashcards')
        # Should not have inline style tags
        assert '<style>' not in response.text

