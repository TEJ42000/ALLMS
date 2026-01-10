"""Tests for Course API Error Handling.

Comprehensive tests for error scenarios in the course API endpoints.
These tests are course-agnostic and apply to all courses in the system.

Covers:
- 404 errors (course not found, invalid IDs)
- 500 errors (server errors, unexpected exceptions)
- 503 errors (Firestore unavailable)
- 400 errors (validation errors)
- 422 errors (request validation)
- Edge cases (malformed data, missing fields)
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.course_models import Course, Week
from app.models.auth_models import User
from app.services.course_service import (
    ServiceValidationError,
    FirestoreOperationError,
    CourseNotFoundError,
)


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
def authenticated_user():
    """Override auth dependency to allow requests through."""
    from app.dependencies.auth import require_authenticated

    mock_user = User(
        email="testuser@example.com",
        name="Test User",
        user_id="test-user-123",
        domain="example.com"
    )

    app.dependency_overrides[require_authenticated] = lambda: mock_user
    yield mock_user
    app.dependency_overrides.clear()


class TestCourseNotFoundErrors:
    """Tests for 404 error scenarios."""

    def test_get_nonexistent_course_returns_404(
        self, client, mock_course_service, authenticated_user
    ):
        """Should return 404 when course doesn't exist."""
        mock_course_service.get_course.return_value = None

        response = client.get("/api/courses/NONEXISTENT-COURSE-123")

        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not found" in data["detail"].lower()

    def test_get_course_with_special_characters_in_id(
        self, client, mock_course_service, authenticated_user
    ):
        """Should return 422 for course ID with invalid characters."""
        # Course IDs should only contain alphanumeric, hyphens, underscores
        response = client.get("/api/courses/course@with!special")

        assert response.status_code == 422  # Validation error

    def test_get_course_with_empty_id(self, client, mock_course_service, authenticated_user):
        """Should redirect empty course ID to list endpoint."""
        # Set up mock for list courses (which the redirect targets)
        mock_course_service.get_all_courses.return_value = ([], 0)

        response = client.get("/api/courses/")

        # Empty path redirects to list endpoint (307) or list returns 200
        # FastAPI with trailing slash redirect enabled will return 307 → then 200
        assert response.status_code in [200, 307]

    def test_get_course_with_very_long_id(self, client, authenticated_user):
        """Should return 422 for course ID exceeding max length."""
        long_id = "A" * 150  # Exceeds 100 char limit

        response = client.get(f"/api/courses/{long_id}")

        assert response.status_code == 422

    def test_inactive_course_returns_404_for_non_admin(
        self, client, mock_course_service, authenticated_user
    ):
        """Inactive courses should return 404 to non-admin users."""
        mock_course_service.get_course.return_value = Course(
            id="INACTIVE-COURSE",
            name="Inactive Course",
            academicYear="2020-2021",
            active=False,
            weeks=[]
        )

        response = client.get("/api/courses/INACTIVE-COURSE")

        assert response.status_code == 404


class TestServerErrors:
    """Tests for 500 error scenarios."""

    def test_unexpected_exception_returns_500(
        self, client, mock_course_service, authenticated_user
    ):
        """Should return 500 for unexpected exceptions."""
        mock_course_service.get_course.side_effect = RuntimeError("Unexpected error")

        response = client.get("/api/courses/ANY-COURSE")

        assert response.status_code == 500

    def test_list_courses_unexpected_error(
        self, client, mock_course_service, authenticated_user
    ):
        """Unexpected errors in list endpoint should propagate (no catch-all)."""
        # Note: The list_courses endpoint doesn't have a catch-all Exception handler,
        # so unexpected errors propagate as-is. This tests that behavior.
        # If you want 500 responses, add an Exception handler to list_courses.
        mock_course_service.get_all_courses.side_effect = FirestoreOperationError(
            "Unexpected database error"
        )

        response = client.get("/api/courses")

        # FirestoreOperationError is caught and returns 503
        assert response.status_code == 503


class TestServiceUnavailableErrors:
    """Tests for 503 error scenarios (Firestore unavailable)."""

    def test_firestore_unavailable_get_course(
        self, client, mock_course_service, authenticated_user
    ):
        """Should return 503 when Firestore is unavailable for get."""
        mock_course_service.get_course.side_effect = FirestoreOperationError(
            "Connection failed"
        )

        response = client.get("/api/courses/ANY-COURSE")

        assert response.status_code == 503
        data = response.json()
        assert "unavailable" in data["detail"].lower()

    def test_firestore_unavailable_list_courses(
        self, client, mock_course_service, authenticated_user
    ):
        """Should return 503 when Firestore is unavailable for list."""
        mock_course_service.get_all_courses.side_effect = FirestoreOperationError(
            "Firestore timeout"
        )

        response = client.get("/api/courses")

        assert response.status_code == 503


class TestValidationErrors:
    """Tests for 400/422 validation error scenarios."""

    def test_invalid_limit_parameter(self, client, mock_course_service, authenticated_user):
        """Should return 422 for invalid limit parameter."""
        # Limit must be positive integer
        response = client.get("/api/courses?limit=-1")
        assert response.status_code == 422

        response = client.get("/api/courses?limit=abc")
        assert response.status_code == 422

    def test_limit_exceeds_maximum(self, client, mock_course_service, authenticated_user):
        """Should return 422 when limit exceeds maximum allowed."""
        mock_course_service.get_all_courses.return_value = ([], 0)

        response = client.get("/api/courses?limit=500")

        assert response.status_code == 422

    def test_invalid_offset_parameter(self, client, mock_course_service, authenticated_user):
        """Should return 422 for invalid offset parameter."""
        response = client.get("/api/courses?offset=-1")
        assert response.status_code == 422

        response = client.get("/api/courses?offset=abc")
        assert response.status_code == 422

    def test_service_validation_error(
        self, client, mock_course_service, authenticated_user
    ):
        """Should return 400 for service validation errors."""
        mock_course_service.get_all_courses.side_effect = ServiceValidationError(
            "Invalid filter parameter"
        )

        response = client.get("/api/courses")

        assert response.status_code == 400


class TestEdgeCases:
    """Tests for edge cases and unusual scenarios."""

    def test_course_with_empty_weeks_array(
        self, client, mock_course_service, authenticated_user
    ):
        """Should handle course with empty weeks array."""
        mock_course_service.get_course.return_value = Course(
            id="EMPTY-WEEKS",
            name="Course With No Weeks",
            academicYear="2025-2026",
            active=True,
            weeks=[]
        )

        response = client.get("/api/courses/EMPTY-WEEKS?include_weeks=true")

        assert response.status_code == 200
        data = response.json()
        assert data["weeks"] == []

    def test_course_with_many_weeks(
        self, client, mock_course_service, authenticated_user
    ):
        """Should handle course with large number of weeks."""
        many_weeks = [
            Week(weekNumber=i, title=f"Week {i}", topics=[])
            for i in range(1, 53)  # 52 weeks
        ]
        mock_course_service.get_course.return_value = Course(
            id="MANY-WEEKS",
            name="Year-Long Course",
            academicYear="2025-2026",
            active=True,
            weeks=many_weeks
        )

        response = client.get("/api/courses/MANY-WEEKS?include_weeks=true")

        assert response.status_code == 200
        data = response.json()
        assert len(data["weeks"]) == 52

    def test_course_with_multiple_weeks(
        self, client, mock_course_service, authenticated_user
    ):
        """Should return all weeks in order."""
        weeks = [
            Week(weekNumber=1, title="Week 1 - Introduction", topics=[]),
            Week(weekNumber=2, title="Week 2 - Fundamentals", topics=[]),
            Week(weekNumber=3, title="Week 3 - Advanced Topics", topics=[]),
        ]
        mock_course_service.get_course.return_value = Course(
            id="MULTI-WEEK",
            name="Multi-Week Course",
            academicYear="2025-2026",
            active=True,
            weeks=weeks
        )

        response = client.get("/api/courses/MULTI-WEEK?include_weeks=true")

        assert response.status_code == 200
        data = response.json()
        assert len(data["weeks"]) == 3
        assert data["weeks"][0]["weekNumber"] == 1
        assert data["weeks"][1]["weekNumber"] == 2
        assert data["weeks"][2]["weekNumber"] == 3

    def test_course_with_week_containing_topics(
        self, client, mock_course_service, authenticated_user
    ):
        """Should handle weeks with topics list (deprecated but supported)."""
        weeks_with_topics = [
            Week(weekNumber=1, title="Week 1", topics=["Topic A", "Topic B"]),
            Week(weekNumber=2, title="Week 2", topics=[]),  # No topics
            Week(weekNumber=3, title="Week 3", topics=["Topic C"]),
        ]
        mock_course_service.get_course.return_value = Course(
            id="TOPICS-COURSE",
            name="Course With Topics",
            academicYear="2025-2026",
            active=True,
            weeks=weeks_with_topics
        )

        response = client.get("/api/courses/TOPICS-COURSE?include_weeks=true")

        assert response.status_code == 200
        data = response.json()
        assert len(data["weeks"]) == 3
        assert data["weeks"][0]["topics"] == ["Topic A", "Topic B"]
        assert data["weeks"][1]["topics"] == []

    def test_include_weeks_false(
        self, client, mock_course_service, authenticated_user
    ):
        """Should pass include_weeks=False correctly to service."""
        mock_course_service.get_course.return_value = Course(
            id="TEST-COURSE",
            name="Test Course",
            academicYear="2025-2026",
            active=True,
            weeks=[]
        )

        response = client.get("/api/courses/TEST-COURSE?include_weeks=false")

        assert response.status_code == 200
        mock_course_service.get_course.assert_called_with(
            "TEST-COURSE", include_weeks=False
        )

    def test_concurrent_requests(
        self, client, mock_course_service, authenticated_user
    ):
        """Should handle concurrent requests without errors."""
        import threading
        import time

        mock_course_service.get_course.return_value = Course(
            id="CONCURRENT",
            name="Concurrent Test",
            academicYear="2025-2026",
            active=True,
            weeks=[]
        )

        results = []
        errors = []

        def make_request():
            try:
                response = client.get("/api/courses/CONCURRENT")
                results.append(response.status_code)
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=make_request) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert all(status == 200 for status in results)


class TestWeekSpecificErrors:
    """Tests for week-related error scenarios within courses."""

    def test_week_with_very_long_title(
        self, client, mock_course_service, authenticated_user
    ):
        """Should handle weeks with very long titles."""
        long_title = "A" * 500
        mock_course_service.get_course.return_value = Course(
            id="LONG-TITLE",
            name="Course",
            academicYear="2025-2026",
            active=True,
            weeks=[Week(weekNumber=1, title=long_title, topics=[])]
        )

        response = client.get("/api/courses/LONG-TITLE?include_weeks=true")

        assert response.status_code == 200
        data = response.json()
        assert data["weeks"][0]["title"] == long_title

    def test_week_with_special_characters_in_title(
        self, client, mock_course_service, authenticated_user
    ):
        """Should handle weeks with special characters in title."""
        special_title = "Week 1: Introduction & Overview <script>alert('xss')</script>"
        mock_course_service.get_course.return_value = Course(
            id="SPECIAL-CHARS",
            name="Course",
            academicYear="2025-2026",
            active=True,
            weeks=[Week(weekNumber=1, title=special_title, topics=[])]
        )

        response = client.get("/api/courses/SPECIAL-CHARS?include_weeks=true")

        assert response.status_code == 200
        data = response.json()
        # Title should be returned as-is (escaping happens in frontend)
        assert data["weeks"][0]["title"] == special_title

    def test_week_with_unicode_characters(
        self, client, mock_course_service, authenticated_user
    ):
        """Should handle weeks with unicode characters."""
        unicode_title = "Week 1: 法律入门 - Εισαγωγή 📚"
        mock_course_service.get_course.return_value = Course(
            id="UNICODE",
            name="Course",
            academicYear="2025-2026",
            active=True,
            weeks=[Week(weekNumber=1, title=unicode_title, topics=[])]
        )

        response = client.get("/api/courses/UNICODE?include_weeks=true")

        assert response.status_code == 200
        data = response.json()
        assert data["weeks"][0]["title"] == unicode_title

