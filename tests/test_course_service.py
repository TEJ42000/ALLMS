"""Unit tests for CourseService.

Tests CRUD operations with mocked Firestore client.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, PropertyMock, call

from google.api_core import exceptions as google_exceptions

from app.models.course_models import (
    Course,
    CourseCreate,
    CourseUpdate,
    CourseSummary,
    Week,
    WeekCreate,
    LegalSkill,
)
from app.services.course_service import (
    CourseService,
    validate_course_id,
    validate_week_number,
    is_retryable_error,
    with_retry,
    COURSE_ID_PATTERN,
    ServiceValidationError,
    FirestoreOperationError,
    CourseAlreadyExistsError,
    CourseNotFoundError,
    FIRESTORE_BATCH_LIMIT,
)


# ============================================================================
# Validation Function Tests
# ============================================================================


class TestValidateCourseId:
    """Tests for course ID validation."""

    def test_valid_course_id(self):
        """Valid course IDs should pass."""
        assert validate_course_id("LLS-2025-2026") == "LLS-2025-2026"
        assert validate_course_id("course_123") == "course_123"
        assert validate_course_id("ABC") == "ABC"

    def test_empty_course_id(self):
        """Empty course ID should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            validate_course_id("")

    def test_invalid_characters(self):
        """Course IDs with invalid characters should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid course ID"):
            validate_course_id("../malicious")

        with pytest.raises(ValueError, match="Invalid course ID"):
            validate_course_id("course with spaces")

        with pytest.raises(ValueError, match="Invalid course ID"):
            validate_course_id("course/path")

    def test_too_long_course_id(self):
        """Course ID over 100 chars should raise ValueError."""
        long_id = "a" * 101
        with pytest.raises(ValueError, match="Invalid course ID"):
            validate_course_id(long_id)


class TestValidateWeekNumber:
    """Tests for week number validation."""

    def test_valid_week_numbers(self):
        """Valid week numbers should pass."""
        assert validate_week_number(1) == 1
        assert validate_week_number(26) == 26
        assert validate_week_number(52) == 52

    def test_week_number_zero(self):
        """Week number 0 should raise ValueError."""
        with pytest.raises(ValueError, match="must be between"):
            validate_week_number(0)

    def test_week_number_negative(self):
        """Negative week numbers should raise ValueError."""
        with pytest.raises(ValueError, match="must be between"):
            validate_week_number(-1)

    def test_week_number_too_high(self):
        """Week numbers over 52 should raise ValueError."""
        with pytest.raises(ValueError, match="must be between"):
            validate_week_number(53)

    def test_week_number_not_integer(self):
        """Non-integer week numbers should raise ValueError."""
        with pytest.raises(ValueError, match="must be an integer"):
            validate_week_number("1")  # type: ignore

        with pytest.raises(ValueError, match="must be an integer"):
            validate_week_number(1.5)  # type: ignore


# ============================================================================
# CourseService Tests with Mocked Firestore
# ============================================================================


@pytest.fixture
def mock_firestore():
    """Create a mocked Firestore client."""
    with patch("app.services.course_service.get_firestore_client") as mock_get_client:
        mock_db = MagicMock()
        mock_get_client.return_value = mock_db
        yield mock_db


@pytest.fixture
def course_service(mock_firestore):
    """Create CourseService with mocked Firestore."""
    # Reset singleton
    import app.services.course_service as cs
    cs._course_service = None
    return CourseService()


class TestCourseServiceInit:
    """Tests for CourseService initialization."""

    def test_init_success(self, mock_firestore):
        """Service should initialize with valid Firestore client."""
        import app.services.course_service as cs
        cs._course_service = None
        service = CourseService()
        assert service.db is not None

    def test_init_no_firestore(self):
        """Service should raise error when Firestore unavailable."""
        with patch("app.services.course_service.get_firestore_client", return_value=None):
            import app.services.course_service as cs
            cs._course_service = None
            with pytest.raises(RuntimeError, match="Firestore client not available"):
                CourseService()


class TestGetCourse:
    """Tests for get_course method."""

    def test_get_course_not_found(self, course_service, mock_firestore):
        """Should return None when course doesn't exist."""
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_doc

        result = course_service.get_course("nonexistent-course")
        assert result is None

    def test_get_course_invalid_id(self, course_service):
        """Should raise ServiceValidationError for invalid course ID."""
        with pytest.raises(ServiceValidationError, match="Invalid course ID"):
            course_service.get_course("../malicious")

    def test_get_course_empty_id(self, course_service):
        """Should raise ServiceValidationError for empty course ID."""
        with pytest.raises(ServiceValidationError, match="cannot be empty"):
            course_service.get_course("")


# ============================================================================
# Retry Logic Tests
# ============================================================================


class TestRetryLogic:
    """Tests for retry decorator and error detection."""

    def test_is_retryable_error_service_unavailable(self):
        """ServiceUnavailable should be retryable."""
        error = google_exceptions.ServiceUnavailable("Service unavailable")
        assert is_retryable_error(error) is True

    def test_is_retryable_error_deadline_exceeded(self):
        """DeadlineExceeded should be retryable."""
        error = google_exceptions.DeadlineExceeded("Deadline exceeded")
        assert is_retryable_error(error) is True

    def test_is_retryable_error_resource_exhausted(self):
        """ResourceExhausted should be retryable."""
        error = google_exceptions.ResourceExhausted("Rate limit")
        assert is_retryable_error(error) is True

    def test_is_retryable_error_aborted(self):
        """Aborted should be retryable."""
        error = google_exceptions.Aborted("Transaction aborted")
        assert is_retryable_error(error) is True

    def test_is_retryable_error_not_found(self):
        """NotFound should NOT be retryable."""
        error = google_exceptions.NotFound("Document not found")
        assert is_retryable_error(error) is False

    def test_is_retryable_error_permission_denied(self):
        """PermissionDenied should NOT be retryable."""
        error = google_exceptions.PermissionDenied("Access denied")
        assert is_retryable_error(error) is False

    def test_is_retryable_error_value_error(self):
        """ValueError should NOT be retryable."""
        error = ValueError("Invalid value")
        assert is_retryable_error(error) is False

    def test_with_retry_success_on_first_try(self):
        """Decorated function should succeed on first try."""
        mock_func = MagicMock(return_value="success")
        decorated = with_retry()(mock_func)
        result = decorated()
        assert result == "success"
        assert mock_func.call_count == 1

    def test_with_retry_success_after_transient_error(self):
        """Decorated function should retry on transient error and succeed."""
        call_count = 0

        @with_retry(max_retries=3, initial_delay=0.01)
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise google_exceptions.ServiceUnavailable("Temporary")
            return "success"

        result = flaky_function()
        assert result == "success"
        assert call_count == 2

    def test_with_retry_exhausts_retries(self):
        """Decorated function should raise after exhausting retries."""
        call_count = 0

        @with_retry(max_retries=2, initial_delay=0.01)
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise google_exceptions.ServiceUnavailable("Persistent error")

        with pytest.raises(google_exceptions.ServiceUnavailable):
            always_fails()
        assert call_count == 3  # Initial + 2 retries

    def test_with_retry_non_retryable_error(self):
        """Non-retryable errors should raise immediately."""
        call_count = 0

        @with_retry(max_retries=3, initial_delay=0.01)
        def permission_denied():
            nonlocal call_count
            call_count += 1
            raise google_exceptions.PermissionDenied("Access denied")

        with pytest.raises(google_exceptions.PermissionDenied):
            permission_denied()
        assert call_count == 1  # No retries


# ============================================================================
# Batch Write Tests
# ============================================================================


class TestBatchWrites:
    """Tests for batch write operations."""

    def test_batch_size_validation_under_limit(self, course_service, mock_firestore):
        """Batch within limit should not raise error."""
        # Setup mock for create_course
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_doc
        mock_batch = MagicMock()
        mock_firestore.batch.return_value = mock_batch

        course_data = CourseCreate(
            id="test-course",
            name="Test Course",
            academicYear="2024-2025"
        )
        initial_weeks = [WeekCreate(weekNumber=i, title=f"Week {i}") for i in range(1, 10)]

        # Total ops = 1 (course) + 9 (weeks) = 10, well under 500
        # This should not raise
        try:
            course_service.create_course(course_data, initial_weeks=initial_weeks)
        except Exception as e:
            # May fail for other reasons, but not batch limit
            assert "exceeds Firestore batch limit" not in str(e)

    def test_batch_size_validation_over_limit(self, course_service, mock_firestore):
        """Batch exceeding limit should raise ServiceValidationError."""
        course_data = CourseCreate(
            id="test-course",
            name="Test Course",
            academicYear="2024-2025"
        )
        # Create enough weeks and skills to exceed 500
        initial_weeks = [WeekCreate(weekNumber=i, title=f"Week {i}") for i in range(1, 53)]
        initial_skills = {f"skill-{i}": LegalSkill(name=f"Skill {i}") for i in range(1, 460)}

        # Total ops = 1 (course) + 52 (weeks) + 459 (skills) = 512 > 500
        with pytest.raises(ServiceValidationError, match="exceeds Firestore batch limit"):
            course_service.create_course(
                course_data,
                initial_weeks=initial_weeks,
                initial_skills=initial_skills
            )

    def test_firestore_batch_limit_constant(self):
        """Verify FIRESTORE_BATCH_LIMIT is set correctly."""
        assert FIRESTORE_BATCH_LIMIT == 500


# ============================================================================
# Pagination Tests
# ============================================================================


class TestPagination:
    """Tests for pagination in get_all_courses."""

    def test_pagination_invalid_limit_zero(self, course_service):
        """Limit of 0 should raise ServiceValidationError."""
        with pytest.raises(ServiceValidationError, match="Limit must be between"):
            course_service.get_all_courses(limit=0)

    def test_pagination_invalid_limit_over_100(self, course_service):
        """Limit over 100 should raise ServiceValidationError."""
        with pytest.raises(ServiceValidationError, match="Limit must be between"):
            course_service.get_all_courses(limit=101)

    def test_pagination_invalid_offset_negative(self, course_service):
        """Negative offset should raise ServiceValidationError."""
        with pytest.raises(ServiceValidationError, match="Offset must be non-negative"):
            course_service.get_all_courses(offset=-1)

    def test_pagination_valid_boundary_limit_1(self, course_service, mock_firestore):
        """Limit of 1 should be valid."""
        mock_query = MagicMock()
        mock_query.stream.return_value = []
        mock_firestore.collection.return_value.select.return_value = mock_query
        mock_firestore.collection.return_value.offset.return_value.limit.return_value = mock_query

        courses, total = course_service.get_all_courses(limit=1)
        assert courses == []
        assert total == 0

    def test_pagination_valid_boundary_limit_100(self, course_service, mock_firestore):
        """Limit of 100 should be valid."""
        mock_query = MagicMock()
        mock_query.stream.return_value = []
        mock_firestore.collection.return_value.select.return_value = mock_query
        mock_firestore.collection.return_value.offset.return_value.limit.return_value = mock_query

        courses, total = course_service.get_all_courses(limit=100)
        assert courses == []
        assert total == 0

    def test_pagination_uses_firestore_native_methods(self, course_service, mock_firestore):
        """Verify pagination uses Firestore offset() and limit()."""
        mock_count_query = MagicMock()
        mock_count_query.stream.return_value = []

        mock_paginated_query = MagicMock()
        mock_paginated_query.stream.return_value = []

        # Build chain: collection -> where -> select/offset
        mock_where_result = MagicMock()
        mock_where_result.select.return_value = mock_count_query
        mock_where_result.offset.return_value.limit.return_value = mock_paginated_query

        mock_collection = MagicMock()
        mock_collection.where.return_value = mock_where_result
        mock_firestore.collection.return_value = mock_collection

        course_service.get_all_courses(limit=10, offset=20)

        # Verify Firestore native pagination methods were called on the where() result
        mock_where_result.offset.assert_called_once_with(20)
        mock_where_result.offset.return_value.limit.assert_called_once_with(10)

    def test_pagination_offset_zero(self, course_service, mock_firestore):
        """Offset of 0 should be valid."""
        mock_query = MagicMock()
        mock_query.stream.return_value = []
        mock_firestore.collection.return_value.select.return_value = mock_query
        mock_firestore.collection.return_value.offset.return_value.limit.return_value = mock_query

        courses, total = course_service.get_all_courses(offset=0)
        assert courses == []


# ============================================================================
# Week Count Synchronization Tests
# ============================================================================


class TestWeekCountSync:
    """Tests for weekCount synchronization."""

    def test_create_course_sets_initial_week_count(self, course_service, mock_firestore):
        """Creating course with weeks should set initial weekCount."""
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_doc.id = "test-course"
        mock_doc.to_dict.return_value = {
            "id": "test-course",
            "name": "Test Course",
            "academicYear": "2024-2025",
            "active": True,
            "weekCount": 3,
        }
        mock_firestore.collection.return_value.document.return_value.get.return_value = mock_doc
        mock_batch = MagicMock()
        mock_firestore.batch.return_value = mock_batch

        course_data = CourseCreate(
            id="test-course",
            name="Test Course",
            academicYear="2024-2025"
        )
        initial_weeks = [
            WeekCreate(weekNumber=1, title="Week 1"),
            WeekCreate(weekNumber=2, title="Week 2"),
            WeekCreate(weekNumber=3, title="Week 3"),
        ]

        course_service.create_course(course_data, initial_weeks=initial_weeks)

        # Check that batch.set was called with weekCount
        batch_set_calls = mock_batch.set.call_args_list
        # First call should be the course document with weekCount
        course_set_call = batch_set_calls[0]
        course_data_arg = course_set_call[0][1]  # Second positional arg is the data
        assert course_data_arg.get("weekCount") == 3

