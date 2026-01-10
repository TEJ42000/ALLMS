"""Tests for Public Courses API endpoints.

Tests the REST API endpoints for course listing available to all authenticated users.
Unlike admin_courses API, these endpoints don't require @mgms.eu domain.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.course_models import CourseSummary
from app.models.auth_models import User
from app.services.course_service import ServiceValidationError, FirestoreOperationError


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_course_service():
    """Mock the CourseService."""
    with patch("app.routes.courses.get_course_service") as mock_get:
        mock_service = MagicMock()
        mock_get.return_value = mock_service
        yield mock_service


@pytest.fixture
def override_auth_dependency():
    """Override auth dependency to allow requests through."""
    from app.dependencies.auth import require_authenticated

    mock_user = User(
        email="testuser@gmail.com",
        name="Test User",
        user_id="test-user-123",
        domain="gmail.com"
    )

    app.dependency_overrides[require_authenticated] = lambda: mock_user
    yield mock_user
    app.dependency_overrides.clear()


class TestListCoursesPublic:
    """Tests for GET /api/courses."""

    def test_list_courses_authenticated_user(self, client, mock_course_service, override_auth_dependency):
        """Should return list of courses for authenticated non-admin user."""
        mock_course_service.get_all_courses.return_value = (
            [
                CourseSummary(
                    id="LLS-2025-2026",
                    name="Law and Legal Skills",
                    academicYear="2025-2026",
                    weekCount=6,
                    active=True
                )
            ],
            1
        )

        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == "LLS-2025-2026"
        assert data["items"][0]["name"] == "Law and Legal Skills"

    def test_list_courses_unauthenticated(self, client):
        """Should return 401 for unauthenticated requests."""
        from fastapi import HTTPException
        from app.dependencies.auth import require_authenticated

        # Override to simulate unauthenticated user
        def raise_unauthorized():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[require_authenticated] = raise_unauthorized

        response = client.get("/api/courses")

        assert response.status_code == 401
        app.dependency_overrides.clear()

    def test_list_courses_only_active(self, client, mock_course_service, override_auth_dependency):
        """Should only return active courses (include_inactive=False)."""
        mock_course_service.get_all_courses.return_value = ([], 0)

        client.get("/api/courses")

        # Verify include_inactive is always False for public endpoint
        mock_course_service.get_all_courses.assert_called_with(
            include_inactive=False, limit=50, offset=0
        )

    def test_list_courses_pagination(self, client, mock_course_service, override_auth_dependency):
        """Should respect pagination parameters."""
        mock_course_service.get_all_courses.return_value = ([], 0)

        client.get("/api/courses?limit=10&offset=20")

        mock_course_service.get_all_courses.assert_called_with(
            include_inactive=False, limit=10, offset=20
        )

    def test_list_courses_pagination_limits(self, client, mock_course_service, override_auth_dependency):
        """Should enforce max limit of 100."""
        mock_course_service.get_all_courses.return_value = ([], 0)

        # Request with limit > 100 should be rejected
        response = client.get("/api/courses?limit=200")
        
        assert response.status_code == 422  # Validation error

    def test_list_courses_firestore_error(self, client, mock_course_service, override_auth_dependency):
        """Should return 503 when Firestore is unavailable."""
        mock_course_service.get_all_courses.side_effect = FirestoreOperationError("Connection failed")

        response = client.get("/api/courses")

        assert response.status_code == 503
        assert "temporarily unavailable" in response.json()["detail"].lower()

    def test_list_courses_validation_error(self, client, mock_course_service, override_auth_dependency):
        """Should return 400 for invalid parameters."""
        mock_course_service.get_all_courses.side_effect = ServiceValidationError("Invalid params")

        response = client.get("/api/courses")

        assert response.status_code == 400

    def test_list_courses_empty(self, client, mock_course_service, override_auth_dependency):
        """Should return empty list when no courses available."""
        mock_course_service.get_all_courses.return_value = ([], 0)

        response = client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []
        assert data["has_more"] is False


class TestGetCoursePublic:
    """Tests for GET /api/courses/{course_id}."""

    def test_get_course_authenticated_user(self, client, mock_course_service, override_auth_dependency):
        """Should return course details for authenticated user."""
        from app.models.course_models import Course

        mock_course_service.get_course.return_value = Course(
            id="LLS-2025-2026",
            name="Law and Legal Skills",
            academicYear="2025-2026",
            active=True,
            weeks=[]
        )

        response = client.get("/api/courses/LLS-2025-2026")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "LLS-2025-2026"
        assert data["name"] == "Law and Legal Skills"

    def test_get_course_unauthenticated(self, client):
        """Should return 401 for unauthenticated requests."""
        from fastapi import HTTPException
        from app.dependencies.auth import require_authenticated

        def raise_unauthorized():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[require_authenticated] = raise_unauthorized

        response = client.get("/api/courses/LLS-2025-2026")

        assert response.status_code == 401
        app.dependency_overrides.clear()

    def test_get_course_not_found(self, client, mock_course_service, override_auth_dependency):
        """Should return 404 when course not found."""
        mock_course_service.get_course.return_value = None

        response = client.get("/api/courses/NONEXISTENT")

        assert response.status_code == 404

    def test_get_course_inactive_hidden(self, client, mock_course_service, override_auth_dependency):
        """Should return 404 for inactive courses (hidden from non-admin users)."""
        from app.models.course_models import Course

        mock_course_service.get_course.return_value = Course(
            id="OLD-COURSE",
            name="Old Course",
            academicYear="2020-2021",
            active=False,
            weeks=[]
        )

        response = client.get("/api/courses/OLD-COURSE")

        assert response.status_code == 404

    def test_get_course_with_weeks(self, client, mock_course_service, override_auth_dependency):
        """Should include weeks when requested."""
        from app.models.course_models import Course, Week

        mock_course_service.get_course.return_value = Course(
            id="LLS-2025-2026",
            name="Law and Legal Skills",
            academicYear="2025-2026",
            active=True,
            weeks=[
                Week(weekNumber=1, title="Introduction", topics=[])
            ]
        )

        response = client.get("/api/courses/LLS-2025-2026?include_weeks=true")

        assert response.status_code == 200
        data = response.json()
        assert len(data["weeks"]) == 1
        assert data["weeks"][0]["weekNumber"] == 1

    def test_get_course_firestore_error(self, client, mock_course_service, override_auth_dependency):
        """Should return 503 when Firestore is unavailable."""
        mock_course_service.get_course.side_effect = FirestoreOperationError("Connection failed")

        response = client.get("/api/courses/LLS-2025-2026")

        assert response.status_code == 503
