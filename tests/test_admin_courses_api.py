"""Tests for Admin Courses API endpoints.

Tests the REST API endpoints for course management.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.course_models import (
    Course,
    CourseSummary,
    Week,
)


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_course_service():
    """Mock the CourseService."""
    with patch("app.routes.admin_courses.get_course_service") as mock_get:
        mock_service = MagicMock()
        mock_get.return_value = mock_service
        yield mock_service


class TestListCourses:
    """Tests for GET /api/admin/courses."""

    def test_list_courses_success(self, client, mock_course_service):
        """Should return list of courses."""
        # Mock returns tuple (items, total) for pagination
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
            1  # total count
        )

        response = client.get("/api/admin/courses")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == "LLS-2025-2026"
        assert data["items"][0]["name"] == "Law and Legal Skills"

    def test_list_courses_include_inactive(self, client, mock_course_service):
        """Should pass include_inactive parameter."""
        # Mock returns tuple (items, total) for pagination
        mock_course_service.get_all_courses.return_value = ([], 0)

        client.get("/api/admin/courses?include_inactive=true")

        mock_course_service.get_all_courses.assert_called_with(
            include_inactive=True, limit=50, offset=0
        )


class TestGetCourse:
    """Tests for GET /api/admin/courses/{course_id}."""

    def test_get_course_success(self, client, mock_course_service):
        """Should return course details."""
        mock_course_service.get_course.return_value = Course(
            id="LLS-2025-2026",
            name="Law and Legal Skills",
            academicYear="2025-2026",
        )

        response = client.get("/api/admin/courses/LLS-2025-2026")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "LLS-2025-2026"

    def test_get_course_not_found(self, client, mock_course_service):
        """Should return 404 for nonexistent course."""
        mock_course_service.get_course.return_value = None

        response = client.get("/api/admin/courses/nonexistent")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_course_invalid_id(self, client, mock_course_service):
        """Should return 400 for invalid course ID."""
        mock_course_service.get_course.side_effect = ValueError("Invalid course ID")

        response = client.get("/api/admin/courses/invalid@id")

        assert response.status_code == 400


class TestGetWeek:
    """Tests for GET /api/admin/courses/{course_id}/weeks/{week_number}."""

    def test_get_week_success(self, client, mock_course_service):
        """Should return week details."""
        mock_course_service.get_week.return_value = Week(
            weekNumber=1,
            title="Introduction to Law",
            topics=["Topic 1", "Topic 2"]
        )

        response = client.get("/api/admin/courses/LLS-2025-2026/weeks/1")

        assert response.status_code == 200
        data = response.json()
        assert data["weekNumber"] == 1
        assert data["title"] == "Introduction to Law"

    def test_get_week_not_found(self, client, mock_course_service):
        """Should return 404 for nonexistent week within valid range."""
        mock_course_service.get_week.return_value = None

        response = client.get("/api/admin/courses/LLS-2025-2026/weeks/50")

        assert response.status_code == 404

    def test_get_week_invalid_week_number_too_high(self, client, mock_course_service):
        """Should return 422 for week number > 52 (Path validation)."""
        response = client.get("/api/admin/courses/LLS-2025-2026/weeks/100")

        assert response.status_code == 422  # Unprocessable Entity from Path validation

    def test_get_week_invalid_week_number_zero(self, client, mock_course_service):
        """Should return 422 for week number < 1 (Path validation)."""
        response = client.get("/api/admin/courses/LLS-2025-2026/weeks/0")

        assert response.status_code == 422  # Unprocessable Entity from Path validation


class TestDeactivateCourse:
    """Tests for DELETE /api/admin/courses/{course_id}."""

    def test_deactivate_success(self, client, mock_course_service):
        """Should return 204 on successful deactivation."""
        mock_course_service.deactivate_course.return_value = True

        response = client.delete("/api/admin/courses/LLS-2025-2026")

        assert response.status_code == 204

    def test_deactivate_not_found(self, client, mock_course_service):
        """Should return 404 for nonexistent course."""
        mock_course_service.deactivate_course.return_value = False

        response = client.delete("/api/admin/courses/nonexistent")

        assert response.status_code == 404


class TestCreateCourse:
    """Tests for POST /api/admin/courses."""

    def test_create_course_success(self, client, mock_course_service):
        """Should return 201 on successful creation."""
        mock_course_service.create_course.return_value = Course(
            id="NEW-COURSE-2026",
            name="New Course",
            academicYear="2025-2026",
        )

        response = client.post("/api/admin/courses", json={
            "id": "NEW-COURSE-2026",
            "name": "New Course",
            "academicYear": "2025-2026"
        })

        assert response.status_code == 201
        assert response.json()["id"] == "NEW-COURSE-2026"

    def test_create_duplicate_course(self, client, mock_course_service):
        """Should return 400 when trying to create duplicate course."""
        mock_course_service.create_course.side_effect = ValueError(
            "Course with ID 'LLS-2025-2026' already exists"
        )

        response = client.post("/api/admin/courses", json={
            "id": "LLS-2025-2026",
            "name": "Duplicate Course",
            "academicYear": "2025-2026"
        })

        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


class TestUpsertWeek:
    """Tests for PUT /api/admin/courses/{course_id}/weeks/{week_number}."""

    def test_upsert_week_success(self, client, mock_course_service):
        """Should return 200 on successful upsert."""
        mock_course_service.upsert_week.return_value = Week(
            weekNumber=1,
            title="Week 1 Title",
            topics=["Topic 1"]
        )

        response = client.put("/api/admin/courses/LLS-2025-2026/weeks/1", json={
            "weekNumber": 1,
            "title": "Week 1 Title",
            "topics": ["Topic 1"]
        })

        assert response.status_code == 200
        assert response.json()["weekNumber"] == 1

    def test_upsert_week_number_mismatch(self, client, mock_course_service):
        """Should return 400 when URL week number doesn't match body."""
        response = client.put("/api/admin/courses/LLS-2025-2026/weeks/1", json={
            "weekNumber": 2,  # Mismatched - URL says 1, body says 2
            "title": "Week Title",
            "topics": ["Topic"]
        })

        assert response.status_code == 400
        assert "mismatch" in response.json()["detail"].lower()

    def test_upsert_week_invalid_number_too_high(self, client, mock_course_service):
        """Should return 422 for week number > 52 (Path validation)."""
        response = client.put("/api/admin/courses/LLS-2025-2026/weeks/100", json={
            "weekNumber": 100,
            "title": "Invalid Week",
            "topics": []
        })

        assert response.status_code == 422  # Unprocessable Entity from Path validation

    def test_upsert_week_invalid_number_zero(self, client, mock_course_service):
        """Should return 422 for week number < 1 (Path validation)."""
        response = client.put("/api/admin/courses/LLS-2025-2026/weeks/0", json={
            "weekNumber": 0,
            "title": "Invalid Week",
            "topics": []
        })

        assert response.status_code == 422  # Unprocessable Entity from Path validation


class TestIncludeWeeksParameter:
    """Tests for include_weeks query parameter."""

    def test_get_course_without_weeks(self, client, mock_course_service):
        """Should call service with include_weeks=False."""
        mock_course_service.get_course.return_value = Course(
            id="LLS-2025-2026",
            name="Law and Legal Skills",
            academicYear="2025-2026",
        )

        client.get("/api/admin/courses/LLS-2025-2026?include_weeks=false")

        mock_course_service.get_course.assert_called_with(
            "LLS-2025-2026",
            include_weeks=False
        )

    def test_get_course_with_weeks_default(self, client, mock_course_service):
        """Should default to include_weeks=True."""
        mock_course_service.get_course.return_value = Course(
            id="LLS-2025-2026",
            name="Law and Legal Skills",
            academicYear="2025-2026",
        )

        client.get("/api/admin/courses/LLS-2025-2026")

        mock_course_service.get_course.assert_called_with(
            "LLS-2025-2026",
            include_weeks=True
        )


# ============================================================================
# Tests for Path Resolution Functions (PR #55)
# ============================================================================


class TestResolveIncompletePath:
    """Tests for resolve_incomplete_path function."""

    @patch("app.routes.admin_courses.MATERIALS_BASE")
    def test_resolve_incomplete_path_success(self, mock_base, tmp_path):
        """Should resolve incomplete path to full path when file exists."""
        from app.routes.admin_courses import resolve_incomplete_path

        # Setup mock directory structure
        course_materials = tmp_path / "Course_Materials"
        lls_dir = course_materials / "LLS"
        readings_dir = lls_dir / "Readings"
        readings_dir.mkdir(parents=True)
        test_file = readings_dir / "test.pdf"
        test_file.touch()

        mock_base.__truediv__ = lambda self, other: tmp_path / other
        mock_base.return_value = tmp_path
        
        # Patch MATERIALS_BASE in the actual module
        with patch("app.routes.admin_courses.MATERIALS_BASE", tmp_path):
            result = resolve_incomplete_path("Readings/test.pdf")

        assert result == "Course_Materials/LLS/Readings/test.pdf"

    @patch("app.routes.admin_courses.MATERIALS_BASE")
    def test_resolve_incomplete_path_already_complete(self, mock_base, tmp_path):
        """Should return None for paths that already start with known prefixes."""
        from app.routes.admin_courses import resolve_incomplete_path

        mock_base.__truediv__ = lambda self, other: tmp_path / other
        
        with patch("app.routes.admin_courses.MATERIALS_BASE", tmp_path):
            # Already complete paths should return None
            assert resolve_incomplete_path("Course_Materials/LLS/Readings/file.pdf") is None
            assert resolve_incomplete_path("Syllabus/file.pdf") is None
            assert resolve_incomplete_path("Supplementary_Sources/file.pdf") is None

    @patch("app.routes.admin_courses.MATERIALS_BASE")
    def test_resolve_incomplete_path_not_found(self, mock_base, tmp_path):
        """Should return None when file is not found in any subject directory."""
        from app.routes.admin_courses import resolve_incomplete_path

        # Setup mock directory structure without the target file
        course_materials = tmp_path / "Course_Materials"
        lls_dir = course_materials / "LLS"
        readings_dir = lls_dir / "Readings"
        readings_dir.mkdir(parents=True)

        mock_base.__truediv__ = lambda self, other: tmp_path / other
        
        with patch("app.routes.admin_courses.MATERIALS_BASE", tmp_path):
            result = resolve_incomplete_path("Readings/nonexistent.pdf")

        assert result is None

    @patch("app.routes.admin_courses.MATERIALS_BASE")
    def test_resolve_incomplete_path_no_course_materials_dir(self, mock_base, tmp_path):
        """Should return None when Course_Materials directory doesn't exist."""
        from app.routes.admin_courses import resolve_incomplete_path

        mock_base.__truediv__ = lambda self, other: tmp_path / other
        
        with patch("app.routes.admin_courses.MATERIALS_BASE", tmp_path):
            result = resolve_incomplete_path("Readings/file.pdf")

        assert result is None


class TestValidateMaterialsPathWithResolution:
    """Tests for validate_materials_path with try_resolve parameter."""

    @patch("app.routes.admin_courses.MATERIALS_BASE")
    def test_validate_path_with_resolution_finds_file(self, mock_base, tmp_path):
        """Should resolve and return corrected path when file exists."""
        from app.routes.admin_courses import validate_materials_path

        # Setup mock directory structure
        course_materials = tmp_path / "Course_Materials"
        lls_dir = course_materials / "LLS"
        readings_dir = lls_dir / "Readings"
        readings_dir.mkdir(parents=True)
        test_file = readings_dir / "test.pdf"
        test_file.touch()

        with patch("app.routes.admin_courses.MATERIALS_BASE", tmp_path):
            result = validate_materials_path("Readings/test.pdf", try_resolve=True)

        assert result == test_file
        assert result.exists()

    @patch("app.routes.admin_courses.MATERIALS_BASE")
    def test_validate_path_without_resolution(self, mock_base, tmp_path):
        """Should not attempt resolution when try_resolve=False."""
        from app.routes.admin_courses import validate_materials_path

        # Setup mock directory structure
        course_materials = tmp_path / "Course_Materials"
        lls_dir = course_materials / "LLS"
        readings_dir = lls_dir / "Readings"
        readings_dir.mkdir(parents=True)
        test_file = readings_dir / "test.pdf"
        test_file.touch()

        with patch("app.routes.admin_courses.MATERIALS_BASE", tmp_path):
            # With try_resolve=False, should return the incomplete path (not resolved)
            result = validate_materials_path("Readings/test.pdf", try_resolve=False)

        # Result should be the non-existent incomplete path
        assert not result.exists()

    @patch("app.routes.admin_courses.MATERIALS_BASE")
    def test_validate_path_rejects_null_bytes(self, mock_base, tmp_path):
        """Should reject paths with null bytes."""
        from app.routes.admin_courses import validate_materials_path
        from fastapi import HTTPException

        with patch("app.routes.admin_courses.MATERIALS_BASE", tmp_path):
            with pytest.raises(HTTPException) as exc_info:
                validate_materials_path("test\x00.pdf")
        
        assert exc_info.value.status_code == 400
        assert "null bytes" in exc_info.value.detail

    @patch("app.routes.admin_courses.MATERIALS_BASE")
    def test_validate_path_blocks_traversal(self, mock_base, tmp_path):
        """Should block path traversal attempts."""
        from app.routes.admin_courses import validate_materials_path
        from fastapi import HTTPException

        with patch("app.routes.admin_courses.MATERIALS_BASE", tmp_path):
            with pytest.raises(HTTPException) as exc_info:
                validate_materials_path("../../../etc/passwd")
        
        assert exc_info.value.status_code == 403
        assert "outside" in exc_info.value.detail.lower() or "access denied" in exc_info.value.detail.lower()

    @patch("app.routes.admin_courses.MATERIALS_BASE")
    def test_validate_path_corrected_path_must_exist(self, mock_base, tmp_path):
        """Should not return corrected path if it doesn't exist on disk."""
        from app.routes.admin_courses import validate_materials_path, resolve_incomplete_path

        # Setup mock directory structure WITHOUT the target file
        course_materials = tmp_path / "Course_Materials"
        lls_dir = course_materials / "LLS"
        readings_dir = lls_dir / "Readings"
        readings_dir.mkdir(parents=True)

        with patch("app.routes.admin_courses.MATERIALS_BASE", tmp_path):
            # File doesn't exist, so even with resolution attempt, should return original path
            result = validate_materials_path("Readings/nonexistent.pdf", try_resolve=True)

        # Result should be the non-existent path (not corrected)
        assert not result.exists()
        assert "nonexistent.pdf" in str(result)
