"""Tests for health and pages endpoints."""


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check_returns_ok(self, client):
        """Test that health check returns healthy status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "lls-study-portal"
        assert "version" in data

    def test_health_check_version(self, client):
        """Test that health check returns correct version."""
        response = client.get("/health")

        data = response.json()
        assert data["version"] == "2.0.0"


class TestPagesEndpoint:
    """Tests for page rendering endpoints."""

    def test_index_page_returns_html(self, client):
        """Test that index page returns HTML content."""
        response = client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
        # Updated to match new branding (homepage redesign)
        assert "LLMRMS" in response.text or "LLS Study Portal" in response.text

    def test_index_page_contains_main_elements(self, client):
        """Test that index page contains expected elements."""
        response = client.get("/")

        # Check for main UI elements
        assert "AI Tutor" in response.text or "tutor" in response.text.lower()


class TestAPIDocsEndpoint:
    """Tests for API documentation endpoints."""

    def test_swagger_docs_accessible(self, client):
        """Test that Swagger docs are accessible."""
        response = client.get("/api/docs")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_redoc_accessible(self, client):
        """Test that ReDoc is accessible."""
        response = client.get("/api/redoc")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]
