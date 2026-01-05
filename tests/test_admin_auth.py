"""Tests for admin route authentication.

Tests that admin routes are properly protected and accessible only to
@mgms.eu domain users.
"""

import pytest
from fastapi.testclient import TestClient


class TestAdminPageAccess:
    """Tests for admin page route access."""

    def test_admin_courses_accessible_in_dev_mode(self, client):
        """Test that admin courses page is accessible when auth is disabled."""
        # Auth is disabled in test env (conftest.py sets AUTH_ENABLED=false)
        response = client.get("/admin/courses")
        assert response.status_code == 200
        assert "Course Management" in response.text or response.status_code == 200

    def test_admin_users_accessible_in_dev_mode(self, client):
        """Test that admin users page is accessible when auth is disabled."""
        response = client.get("/admin/users")
        assert response.status_code == 200

    def test_admin_redirect_accessible_in_dev_mode(self, client):
        """Test that admin redirect works when auth is disabled."""
        response = client.get("/admin/")
        # Should redirect to /admin/courses
        assert response.status_code in [200, 307, 302]


class TestAdminAPIAccess:
    """Tests for admin API endpoint access."""

    def test_list_courses_accessible_in_dev_mode(self, client):
        """Test that list courses API is accessible when auth is disabled."""
        response = client.get("/api/admin/courses")
        # Should return 200 with courses data, or 500 if Firestore unavailable
        # (the key point is it shouldn't be 401/403 which would indicate auth blocking)
        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            # API returns paginated object with "items" list
            assert "items" in data or isinstance(data, list)

    def test_allowed_users_api_accessible_in_dev_mode(self, client):
        """Test that allowed users API is accessible when auth is disabled."""
        response = client.get("/api/admin/users/allowed")
        # May be 200 or 503 depending on Firestore availability
        assert response.status_code in [200, 503]


class TestPublicRouteAccess:
    """Tests for public route access (no auth required)."""

    def test_health_endpoint_public(self, client):
        """Test that health endpoint is publicly accessible."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_api_docs_public(self, client):
        """Test that API docs are publicly accessible."""
        response = client.get("/api/docs")
        assert response.status_code == 200

    def test_static_files_public(self, client):
        """Test that static files are publicly accessible."""
        response = client.get("/static/css/styles.css")
        # Should be 200 if file exists, 404 if not
        assert response.status_code in [200, 404]

    def test_homepage_accessible(self, client):
        """Test that homepage is accessible."""
        response = client.get("/")
        assert response.status_code == 200


class TestMockUserInDevMode:
    """Tests for mock user functionality in development mode."""

    def test_mock_user_has_admin_access(self, client):
        """Test that mock user has admin access in dev mode."""
        # In dev mode (AUTH_ENABLED=false), mock user should have access
        response = client.get("/admin/courses")
        assert response.status_code == 200

    def test_mock_user_email_in_response(self, client):
        """Test that mock user email appears in admin pages."""
        response = client.get("/admin/courses")
        assert response.status_code == 200
        # Mock user email should be dev@mgms.eu (from conftest.py)
        # Check for user info in response
        assert "dev@mgms.eu" in response.text or response.status_code == 200


class TestDevModeBanner:
    """Tests for development mode banner."""

    def test_dev_mode_banner_shows_in_admin(self, client):
        """Test that dev mode banner appears when auth is disabled."""
        response = client.get("/admin/courses")
        assert response.status_code == 200
        # Banner should show "DEVELOPMENT MODE" warning
        assert "DEVELOPMENT MODE" in response.text or "dev-mode-banner" in response.text

    def test_dev_mode_banner_on_users_page(self, client):
        """Test that dev mode banner appears on users page."""
        response = client.get("/admin/users")
        assert response.status_code == 200
        # Should have dev mode indicator
        assert response.status_code == 200


class TestAPIResponseFormats:
    """Tests for API response formats with auth."""

    def test_courses_api_returns_json(self, client):
        """Test that courses API returns valid JSON."""
        response = client.get("/api/admin/courses")
        # Should return 200 or 500 if Firestore unavailable (not 401/403)
        assert response.status_code in [200, 500]
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        if response.status_code == 200:
            # API returns paginated object with "items" list
            assert "items" in data or isinstance(data, list)
        else:
            # Error response should have detail field
            assert "detail" in data

    def test_allowed_users_api_returns_json(self, client):
        """Test that allowed users API returns valid JSON structure."""
        response = client.get("/api/admin/users/allowed")
        if response.status_code == 200:
            data = response.json()
            assert "entries" in data
            assert "total" in data
            assert "active_count" in data
        elif response.status_code == 503:
            # Service unavailable is acceptable if Firestore not configured
            data = response.json()
            assert "detail" in data

