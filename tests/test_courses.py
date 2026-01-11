"""Tests for Public Courses API endpoints.

Tests the REST API endpoints for public course access (non-admin users).
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
def mock_course_service():
    """Mock the CourseService."""
    with patch("app.routes.courses.get_course_service") as mock_get:
        mock_service = MagicMock()
        mock_get.return_value = mock_service
        yield mock_service


@pytest.fixture
def sample_courses():
    """Sample course data for testing."""
    return [
        CourseSummary(
            id="LLS-2025-2026",
            name="Law and Legal Skills",
            academicYear="2025-2026",
            weekCount=6,
            active=True
        ),
        CourseSummary(
            id="CRIM-2025-2026",
            name="Criminal Law",
            academicYear="2025-2026",
            weekCount=8,
            active=True
        )
    ]


class TestListCourses:
    """Tests for GET /api/courses."""

    def test_list_courses_success(self, client, mock_course_service, mock_user, sample_courses):
        """Should return list of active courses for authenticated user."""
        # Mock service returns tuple (items, total)
        mock_course_service.get_all_courses.return_value = (sample_courses, 2)

        # Mock authentication
        from app.dependencies.auth import require_authenticated
        app.dependency_overrides[require_authenticated] = lambda: mock_user

        try:
            response = client.get("/api/courses")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
            assert len(data["items"]) == 2
            assert data["items"][0]["id"] == "LLS-2025-2026"
            assert data["items"][1]["id"] == "CRIM-2025-2026"
            assert data["has_more"] is False
            assert data["limit"] == 50  # Default limit
            assert data["offset"] == 0

            # Verify service was called with include_inactive=False
            mock_course_service.get_all_courses.assert_called_once_with(
                include_inactive=False,
                limit=50,
                offset=0
            )
        finally:
            app.dependency_overrides.clear()

    def test_list_courses_with_pagination(self, client, mock_course_service, mock_user, sample_courses):
        """Should support pagination parameters."""
        mock_course_service.get_all_courses.return_value = (sample_courses[:1], 10)

        from app.dependencies.auth import require_authenticated
        app.dependency_overrides[require_authenticated] = lambda: mock_user

        try:
            response = client.get("/api/courses?limit=1&offset=5")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 10
            assert len(data["items"]) == 1
            assert data["limit"] == 1
            assert data["offset"] == 5
            assert data["has_more"] is True  # 5 + 1 < 10

            mock_course_service.get_all_courses.assert_called_once_with(
                include_inactive=False,
                limit=1,
                offset=5
            )
        finally:
            app.dependency_overrides.clear()

    def test_list_courses_max_limit_enforced(self, client, mock_course_service, mock_user):
        """Should enforce maximum limit of 100."""
        from app.dependencies.auth import require_authenticated
        app.dependency_overrides[require_authenticated] = lambda: mock_user

        try:
            response = client.get("/api/courses?limit=200")

            # FastAPI validation should reject this
            assert response.status_code == 422  # Validation error
        finally:
            app.dependency_overrides.clear()

    def test_list_courses_min_limit_enforced(self, client, mock_course_service, mock_user):
        """Should enforce minimum limit of 1."""
        from app.dependencies.auth import require_authenticated
        app.dependency_overrides[require_authenticated] = lambda: mock_user

        try:
            response = client.get("/api/courses?limit=0")

            # FastAPI validation should reject this
            assert response.status_code == 422  # Validation error
        finally:
            app.dependency_overrides.clear()

    def test_list_courses_negative_offset_rejected(self, client, mock_course_service, mock_user):
        """Should reject negative offset."""
        from app.dependencies.auth import require_authenticated
        app.dependency_overrides[require_authenticated] = lambda: mock_user

        try:
            response = client.get("/api/courses?offset=-1")

            # FastAPI validation should reject this
            assert response.status_code == 422  # Validation error
        finally:
            app.dependency_overrides.clear()

    def test_list_courses_unauthenticated(self, client, mock_course_service):
        """Should return 401 for unauthenticated requests."""
        # Mock the dependency to return None (unauthenticated)
        from app.dependencies.auth import require_authenticated
        from fastapi import HTTPException

        def mock_unauthenticated():
            raise HTTPException(status_code=401, detail="Not authenticated")

        app.dependency_overrides[require_authenticated] = mock_unauthenticated

        try:
            response = client.get("/api/courses")

            # Should return 401
            assert response.status_code == 401
            assert "authenticated" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_list_courses_service_validation_error(self, client, mock_course_service, mock_user):
        """Should return 400 for invalid pagination parameters."""
        mock_course_service.get_all_courses.side_effect = ServiceValidationError("Invalid limit")

        from app.dependencies.auth import require_authenticated
        app.dependency_overrides[require_authenticated] = lambda: mock_user

        try:
            response = client.get("/api/courses")

            assert response.status_code == 400
            assert "Invalid limit" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_list_courses_firestore_error(self, client, mock_course_service, mock_user):
        """Should return 503 for Firestore errors."""
        mock_course_service.get_all_courses.side_effect = FirestoreOperationError("Database error")

        from app.dependencies.auth import require_authenticated
        app.dependency_overrides[require_authenticated] = lambda: mock_user

        try:
            response = client.get("/api/courses")

            assert response.status_code == 503
            assert "temporarily unavailable" in response.json()["detail"].lower()
        finally:
            app.dependency_overrides.clear()

    def test_list_courses_empty_result(self, client, mock_course_service, mock_user):
        """Should handle empty course list gracefully."""
        mock_course_service.get_all_courses.return_value = ([], 0)

        from app.dependencies.auth import require_authenticated
        app.dependency_overrides[require_authenticated] = lambda: mock_user

        try:
            response = client.get("/api/courses")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 0
            assert len(data["items"]) == 0
            assert data["has_more"] is False
        finally:
            app.dependency_overrides.clear()

    def test_list_courses_admin_user_allowed(self, client, mock_course_service, mock_admin_user, sample_courses):
        """Should allow admin users to access public endpoint."""
        mock_course_service.get_all_courses.return_value = (sample_courses, 2)

        from app.dependencies.auth import require_authenticated
        app.dependency_overrides[require_authenticated] = lambda: mock_admin_user

        try:
            response = client.get("/api/courses")

            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 2
        finally:
            app.dependency_overrides.clear()

    def test_list_courses_only_active_returned(self, client, mock_course_service, mock_user):
        """Should only return active courses (include_inactive=False)."""
        mock_course_service.get_all_courses.return_value = ([], 0)

        from app.dependencies.auth import require_authenticated
        app.dependency_overrides[require_authenticated] = lambda: mock_user

        try:
            client.get("/api/courses")

            # Verify include_inactive=False was passed
            mock_course_service.get_all_courses.assert_called_once()
            call_kwargs = mock_course_service.get_all_courses.call_args[1]
            assert call_kwargs["include_inactive"] is False
        finally:
            app.dependency_overrides.clear()

    def test_list_courses_has_more_calculation(self, client, mock_course_service, mock_user, sample_courses):
        """Should correctly calculate has_more flag."""
        # Test case 1: has_more = True (offset + items < total)
        mock_course_service.get_all_courses.return_value = (sample_courses[:1], 10)

        from app.dependencies.auth import require_authenticated
        app.dependency_overrides[require_authenticated] = lambda: mock_user

        try:
            response = client.get("/api/courses?limit=1&offset=0")
            assert response.json()["has_more"] is True  # 0 + 1 < 10

            # Test case 2: has_more = False (offset + items >= total)
            mock_course_service.get_all_courses.return_value = (sample_courses, 2)
            response = client.get("/api/courses?limit=50&offset=0")
            assert response.json()["has_more"] is False  # 0 + 2 >= 2
        finally:
            app.dependency_overrides.clear()

    def test_list_courses_logs_user_email(self, client, mock_course_service, mock_user, sample_courses, caplog):
        """Should log user email when listing courses."""
        import logging
        caplog.set_level(logging.INFO)

        mock_course_service.get_all_courses.return_value = (sample_courses, 2)

        from app.dependencies.auth import require_authenticated
        app.dependency_overrides[require_authenticated] = lambda: mock_user

        try:
            client.get("/api/courses")

            # Check that user email was logged
            assert any(mock_user.email in record.message for record in caplog.records)
        finally:
            app.dependency_overrides.clear()

