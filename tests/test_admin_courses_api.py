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
        mock_course_service.get_all_courses.return_value = [
            CourseSummary(
                id="LLS-2025-2026",
                name="Law and Legal Skills",
                academicYear="2025-2026",
                weekCount=6,
                active=True
            )
        ]

        response = client.get("/api/admin/courses")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "LLS-2025-2026"
        assert data[0]["name"] == "Law and Legal Skills"

    def test_list_courses_include_inactive(self, client, mock_course_service):
        """Should pass include_inactive parameter."""
        mock_course_service.get_all_courses.return_value = []

        client.get("/api/admin/courses?include_inactive=true")

        mock_course_service.get_all_courses.assert_called_with(include_inactive=True)


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
        """Should return 404 for nonexistent week."""
        mock_course_service.get_week.return_value = None

        response = client.get("/api/admin/courses/LLS-2025-2026/weeks/99")

        assert response.status_code == 404

    def test_get_week_invalid_week_number(self, client, mock_course_service):
        """Should return 400 for invalid week number."""
        mock_course_service.get_week.side_effect = ValueError("Invalid week number")

        response = client.get("/api/admin/courses/LLS-2025-2026/weeks/100")

        assert response.status_code == 400


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

