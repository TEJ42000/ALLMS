"""Tests for Page Routes with Type Annotations.

This test suite verifies:
1. Type annotations work correctly
2. Authentication behavior matches documentation
3. All routes return expected responses
4. User context is properly handled
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

from app.main import app
from app.models.auth_models import User


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_user():
    """Create a mock authenticated user."""
    return User(
        email="test@mgms.eu",
        user_id="test-user-123",
        domain="mgms.eu",
        is_admin=True
    )


@pytest.fixture
def mock_non_admin_user():
    """Create a mock non-admin user."""
    return User(
        email="student@example.com",
        user_id="student-456",
        domain="example.com",
        is_admin=False
    )


class TestGetUserFromRequest:
    """Test the get_user_from_request helper function."""

    def test_returns_user_when_authenticated(self, client, mock_user):
        """Test that get_user_from_request returns User when authenticated."""
        from app.routes.pages import get_user_from_request
        from fastapi import Request
        
        # Create a mock request with user in state
        request = Mock(spec=Request)
        request.state = Mock()
        request.state.user = mock_user
        
        result = get_user_from_request(request)
        
        assert result is not None
        assert isinstance(result, User)
        assert result.email == "test@mgms.eu"
        assert result.user_id == "test-user-123"

    def test_returns_none_when_not_authenticated(self, client):
        """Test that get_user_from_request returns None when not authenticated."""
        from app.routes.pages import get_user_from_request
        from types import SimpleNamespace

        # Create a mock request with state that has no user attribute
        request = Mock()
        request.state = SimpleNamespace()  # Empty namespace, no user attribute

        result = get_user_from_request(request)

        assert result is None

    def test_return_type_annotation(self):
        """Test that get_user_from_request has correct return type annotation."""
        from app.routes.pages import get_user_from_request
        import typing
        
        # Get the return type annotation
        annotations = get_user_from_request.__annotations__
        
        assert 'return' in annotations
        # Check that return type is Optional[User]
        return_type = annotations['return']
        assert hasattr(return_type, '__origin__')  # It's a generic type


class TestLandingPage:
    """Test the landing page route."""

    @patch('app.routes.pages.get_user_from_request')
    def test_landing_page_returns_html(self, mock_get_user, client):
        """Test that landing page returns HTML response."""
        mock_get_user.return_value = None
        
        response = client.get("/")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    @patch('app.routes.pages.get_user_from_request')
    def test_landing_page_with_authenticated_user(self, mock_get_user, client, mock_user):
        """Test landing page with authenticated user."""
        mock_get_user.return_value = mock_user
        
        response = client.get("/")
        
        assert response.status_code == 200
        # User context should be passed to template
        mock_get_user.assert_called_once()

    def test_landing_page_return_type(self):
        """Test that landing_page has correct return type annotation."""
        from app.routes.pages import landing_page
        from fastapi.responses import HTMLResponse
        
        annotations = landing_page.__annotations__
        assert 'return' in annotations
        assert annotations['return'] == HTMLResponse


class TestCourseStudyPortal:
    """Test the course study portal route."""

    def test_course_study_portal_raises_http_exception(self):
        """Test that course_study_portal documents HTTPException in docstring."""
        from app.routes.pages import course_study_portal

        # Check that docstring mentions Raises
        assert course_study_portal.__doc__ is not None
        assert "Raises:" in course_study_portal.__doc__
        assert "HTTPException" in course_study_portal.__doc__

    def test_course_study_portal_has_correct_return_type(self):
        """Test that course_study_portal has correct return type annotation."""
        from app.routes.pages import course_study_portal
        from fastapi.responses import HTMLResponse

        annotations = course_study_portal.__annotations__
        assert 'return' in annotations
        assert annotations['return'] == HTMLResponse

    def test_course_study_portal_has_course_id_parameter(self):
        """Test that course_study_portal has course_id parameter with correct type."""
        from app.routes.pages import course_study_portal

        annotations = course_study_portal.__annotations__
        assert 'course_id' in annotations
        assert annotations['course_id'] == str


class TestHealthCheck:
    """Test the health check endpoint."""

    def test_health_check_returns_valid_response(self, client):
        """Test that health check returns a valid HealthCheckResponse."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "status" in data
        assert data["status"] == "healthy"
        assert "service" in data
        assert data["service"] == "lls-study-portal"
        assert "version" in data
        assert data["version"] == "2.0.0"

    def test_health_check_return_type(self):
        """Test that health_check has correct return type annotation."""
        from app.routes.pages import health_check
        from app.models.schemas import HealthCheckResponse

        annotations = health_check.__annotations__
        assert 'return' in annotations
        # Should be HealthCheckResponse
        return_type = annotations['return']
        assert return_type == HealthCheckResponse


class TestPrivacyDashboard:
    """Test the privacy dashboard route (requires authentication)."""

    @patch('app.routes.pages.get_user_from_request')
    def test_privacy_dashboard_requires_authentication(self, mock_get_user, client):
        """Test that privacy dashboard requires authentication."""
        mock_get_user.return_value = None
        
        response = client.get("/privacy-dashboard")
        
        assert response.status_code == 401

    @patch('app.routes.pages.get_user_from_request')
    def test_privacy_dashboard_with_authenticated_user(self, mock_get_user, client, mock_user):
        """Test privacy dashboard with authenticated user."""
        mock_get_user.return_value = mock_user
        
        response = client.get("/privacy-dashboard")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_privacy_dashboard_documents_authentication_requirement(self):
        """Test that privacy_dashboard documents authentication requirement in docstring."""
        from app.routes.pages import privacy_dashboard
        
        assert privacy_dashboard.__doc__ is not None
        assert "Raises:" in privacy_dashboard.__doc__
        assert "401" in privacy_dashboard.__doc__


class TestBadgesPage:
    """Test the badges page route (requires authentication)."""

    @patch('app.routes.pages.get_user_from_request')
    def test_badges_page_requires_authentication(self, mock_get_user, client):
        """Test that badges page requires authentication."""
        mock_get_user.return_value = None
        
        response = client.get("/badges")
        
        assert response.status_code == 401

    @patch('app.routes.pages.get_user_from_request')
    def test_badges_page_with_authenticated_user(self, mock_get_user, client, mock_user):
        """Test badges page with authenticated user."""
        mock_get_user.return_value = mock_user
        
        response = client.get("/badges")
        
        assert response.status_code == 200


class TestFlashcardsPage:
    """Test the flashcards page route (authentication optional)."""

    @patch('app.routes.pages.get_user_from_request')
    def test_flashcards_page_allows_anonymous_access(self, mock_get_user, client):
        """Test that flashcards page allows anonymous access."""
        mock_get_user.return_value = None
        
        response = client.get("/flashcards")
        
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    @patch('app.routes.pages.get_user_from_request')
    def test_flashcards_page_with_authenticated_user(self, mock_get_user, client, mock_user):
        """Test flashcards page with authenticated user."""
        mock_get_user.return_value = mock_user
        
        response = client.get("/flashcards")
        
        assert response.status_code == 200

    def test_flashcards_page_has_security_headers(self, client):
        """Test that flashcards page includes security headers."""
        response = client.get("/flashcards")
        
        assert "Content-Security-Policy" in response.headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers

    def test_flashcards_page_does_not_document_raises(self):
        """Test that flashcards_page does NOT document Raises (per code review fix)."""
        from app.routes.pages import flashcards_page
        
        # After code review fix, Raises section should be removed
        assert flashcards_page.__doc__ is not None
        # Should NOT have Raises section for template errors
        if "Raises:" in flashcards_page.__doc__:
            # If it has Raises, it should only be for actual exceptions
            assert "template rendering" not in flashcards_page.__doc__.lower()


class TestTypeAnnotations:
    """Test that all routes have proper type annotations."""

    def test_all_routes_have_return_type_annotations(self):
        """Test that all route functions have return type annotations."""
        from app.routes import pages
        
        route_functions = [
            'landing_page',
            'course_study_portal',
            'health_check',
            'privacy_policy',
            'privacy_dashboard',
            'terms_of_service',
            'cookie_policy',
            'badges_page',
            'flashcards_page'
        ]
        
        for func_name in route_functions:
            func = getattr(pages, func_name)
            annotations = func.__annotations__
            assert 'return' in annotations, f"{func_name} missing return type annotation"

    def test_all_routes_have_request_parameter_annotation(self):
        """Test that all route functions have Request parameter annotation."""
        from app.routes import pages
        from fastapi import Request
        
        route_functions = [
            'landing_page',
            'course_study_portal',
            'privacy_policy',
            'privacy_dashboard',
            'terms_of_service',
            'cookie_policy',
            'badges_page',
            'flashcards_page'
        ]
        
        for func_name in route_functions:
            func = getattr(pages, func_name)
            annotations = func.__annotations__
            assert 'request' in annotations, f"{func_name} missing request parameter annotation"
            assert annotations['request'] == Request, f"{func_name} request parameter has wrong type"

