"""Unit tests for CourseService.

Tests CRUD operations with mocked Firestore client.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, PropertyMock

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
    COURSE_ID_PATTERN,
    ServiceValidationError,
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

