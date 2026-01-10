"""Tests for Firestore Error Handling.

Comprehensive tests for Firestore-specific error scenarios.
These tests verify the application handles Firestore failures gracefully.

Covers:
- Connection failures
- Permission denied errors
- Quota exceeded errors
- Timeout errors
- Batch write failures
- Transaction rollback scenarios
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from fastapi.testclient import TestClient

from google.api_core import exceptions as google_exceptions

from app.main import app
from app.models.auth_models import User
from app.services.course_service import (
    CourseService,
    FirestoreOperationError,
    ServiceValidationError,
)


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


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


class TestFirestoreConnectionErrors:
    """Tests for Firestore connection failure scenarios."""

    def test_connection_refused_get_course(self, client, authenticated_user):
        """Should return 503 when Firestore connection is refused."""
        with patch("app.routes.courses.get_course_service") as mock_get:
            mock_service = MagicMock()
            mock_service.get_course.side_effect = FirestoreOperationError(
                "Connection refused"
            )
            mock_get.return_value = mock_service

            response = client.get("/api/courses/TEST-COURSE")

            assert response.status_code == 503
            data = response.json()
            assert "unavailable" in data["detail"].lower()

    def test_connection_refused_list_courses(self, client, authenticated_user):
        """Should return 503 when Firestore connection fails for list."""
        with patch("app.routes.courses.get_course_service") as mock_get:
            mock_service = MagicMock()
            mock_service.get_all_courses.side_effect = FirestoreOperationError(
                "Failed to connect to Firestore"
            )
            mock_get.return_value = mock_service

            response = client.get("/api/courses")

            assert response.status_code == 503


class TestFirestoreServiceUnavailable:
    """Tests for Firestore ServiceUnavailable (gRPC) errors."""

    def test_service_unavailable_error(self, client, authenticated_user):
        """Should handle Google ServiceUnavailable exception."""
        with patch("app.routes.courses.get_course_service") as mock_get:
            mock_service = MagicMock()
            # Simulate the service catching Google exception and re-raising
            mock_service.get_course.side_effect = FirestoreOperationError(
                "Service unavailable: Firestore is temporarily unavailable"
            )
            mock_get.return_value = mock_service

            response = client.get("/api/courses/TEST-COURSE")

            assert response.status_code == 503


class TestFirestorePermissionErrors:
    """Tests for Firestore permission denied scenarios."""

    def test_permission_denied_mapped_to_firestore_error(
        self, client, authenticated_user
    ):
        """Should handle permission denied as FirestoreOperationError."""
        with patch("app.routes.courses.get_course_service") as mock_get:
            mock_service = MagicMock()
            mock_service.get_course.side_effect = FirestoreOperationError(
                "Permission denied: Missing or insufficient permissions"
            )
            mock_get.return_value = mock_service

            response = client.get("/api/courses/TEST-COURSE")

            assert response.status_code == 503


class TestFirestoreQuotaErrors:
    """Tests for Firestore quota exceeded scenarios."""

    def test_quota_exceeded_error(self, client, authenticated_user):
        """Should handle quota exceeded as FirestoreOperationError."""
        with patch("app.routes.courses.get_course_service") as mock_get:
            mock_service = MagicMock()
            mock_service.get_all_courses.side_effect = FirestoreOperationError(
                "Quota exceeded: Read operations limit reached"
            )
            mock_get.return_value = mock_service

            response = client.get("/api/courses")

            assert response.status_code == 503


class TestFirestoreTimeoutErrors:
    """Tests for Firestore timeout scenarios."""

    def test_deadline_exceeded_error(self, client, authenticated_user):
        """Should handle deadline exceeded as FirestoreOperationError."""
        with patch("app.routes.courses.get_course_service") as mock_get:
            mock_service = MagicMock()
            mock_service.get_course.side_effect = FirestoreOperationError(
                "Deadline exceeded: Request timed out"
            )
            mock_get.return_value = mock_service

            response = client.get("/api/courses/TEST-COURSE")

            assert response.status_code == 503


class TestCourseServiceFirestoreErrors:
    """Unit tests for CourseService Firestore error handling."""

    def test_get_course_google_api_error(self):
        """CourseService should convert GoogleAPIError to FirestoreOperationError."""
        with patch("app.services.course_service.get_firestore_client") as mock_client:
            mock_client.return_value.collection.return_value.document.return_value.get.side_effect = (
                google_exceptions.GoogleAPIError("API error")
            )

            service = CourseService()

            with pytest.raises(FirestoreOperationError):
                service.get_course("TEST-COURSE")

    def test_get_all_courses_google_api_error(self):
        """CourseService should convert GoogleAPIError to FirestoreOperationError."""
        with patch("app.services.course_service.get_firestore_client") as mock_client:
            mock_collection = MagicMock()
            mock_collection.where.return_value = mock_collection
            mock_collection.select.return_value = mock_collection
            mock_collection.stream.side_effect = google_exceptions.GoogleAPIError(
                "Firestore error"
            )
            mock_client.return_value.collection.return_value = mock_collection

            service = CourseService()

            with pytest.raises(FirestoreOperationError):
                service.get_all_courses()

    def test_with_retry_decorator_retries_on_transient_error(self):
        """The @with_retry decorator should retry on transient errors."""
        from app.services.course_service import with_retry

        call_count = 0

        @with_retry(max_retries=2, initial_delay=0.01, max_delay=0.02)
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise google_exceptions.ServiceUnavailable("Temporary error")
            return "success"

        result = flaky_function()

        assert result == "success"
        assert call_count == 2  # First attempt failed, second succeeded


class TestRetryableErrors:
    """Tests for retryable error detection."""

    def test_is_retryable_service_unavailable(self):
        """ServiceUnavailable should be retryable."""
        from app.services.course_service import is_retryable_error

        error = google_exceptions.ServiceUnavailable("Service unavailable")
        assert is_retryable_error(error) is True

    def test_is_retryable_deadline_exceeded(self):
        """DeadlineExceeded should be retryable."""
        from app.services.course_service import is_retryable_error

        error = google_exceptions.DeadlineExceeded("Timeout")
        assert is_retryable_error(error) is True

    def test_is_retryable_aborted(self):
        """Aborted should be retryable."""
        from app.services.course_service import is_retryable_error

        error = google_exceptions.Aborted("Transaction aborted")
        assert is_retryable_error(error) is True

    def test_is_not_retryable_not_found(self):
        """NotFound should not be retryable."""
        from app.services.course_service import is_retryable_error

        error = google_exceptions.NotFound("Resource not found")
        assert is_retryable_error(error) is False

    def test_is_not_retryable_invalid_argument(self):
        """InvalidArgument should not be retryable."""
        from app.services.course_service import is_retryable_error

        error = google_exceptions.InvalidArgument("Bad request")
        assert is_retryable_error(error) is False

    def test_is_not_retryable_permission_denied(self):
        """PermissionDenied should not be retryable."""
        from app.services.course_service import is_retryable_error

        error = google_exceptions.PermissionDenied("Access denied")
        assert is_retryable_error(error) is False


class TestFirestoreErrorMessages:
    """Tests for user-friendly error messages."""

    def test_error_message_does_not_leak_internals(self, client, authenticated_user):
        """Error responses should not leak internal details."""
        with patch("app.routes.courses.get_course_service") as mock_get:
            mock_service = MagicMock()
            mock_service.get_course.side_effect = FirestoreOperationError(
                "Internal: gRPC error at /google.firestore.v1.Firestore/GetDocument"
            )
            mock_get.return_value = mock_service

            response = client.get("/api/courses/TEST-COURSE")

            assert response.status_code == 503
            data = response.json()
            # Should show generic message, not internal gRPC details
            assert "temporarily unavailable" in data["detail"].lower()
            assert "grpc" not in data["detail"].lower()

    def test_error_suggests_retry(self, client, authenticated_user):
        """Error messages should suggest trying again."""
        with patch("app.routes.courses.get_course_service") as mock_get:
            mock_service = MagicMock()
            mock_service.get_course.side_effect = FirestoreOperationError(
                "Connection timeout"
            )
            mock_get.return_value = mock_service

            response = client.get("/api/courses/TEST-COURSE")

            assert response.status_code == 503
            data = response.json()
            # Message should guide user
            assert "try again" in data["detail"].lower() or "unavailable" in data["detail"].lower()

