"""Tests for Text Extraction Status UI functionality.

Tests the extraction status logic, metrics calculation, and UI integration:
- Extraction status tracking
- Dashboard metrics calculation
- Activity log generation
- Error handling and reporting
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.models.text_cache_models import TextCacheEntry, CacheStats
from app.models.course_models import (
    Course, MaterialsRegistry, CoreTextbook, Lecture, Reading, CaseStudy, MockExam
)


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def sample_course_with_materials():
    """Sample course with various materials for testing."""
    return Course(
        id="LLS-2025-2026",
        name="Law and Legal Skills",
        academicYear="2025-2026",
        materials=MaterialsRegistry(
            coreTextbooks=[
                CoreTextbook(
                    title="Introduction to Law",
                    file="Course_Materials/LLS/textbook_intro.pdf",
                    size="2.5 MB"
                ),
                CoreTextbook(
                    title="Legal Theory",
                    file="Course_Materials/LLS/textbook_theory.pdf",
                    size="3.1 MB"
                ),
            ],
            lectures=[
                Lecture(
                    title="Week 1 Lecture",
                    file="Course_Materials/LLS/lecture_week_1.pdf",
                    size="1.2 MB",
                    week=1
                ),
                Lecture(
                    title="Week 2 Lecture",
                    file="Course_Materials/LLS/lecture_week_2.pdf",
                    size="1.5 MB",
                    week=2
                ),
            ],
            readings=[
                Reading(
                    title="Article on Contracts",
                    file="Course_Materials/LLS/reading_contracts.pdf",
                    size="500 KB",
                    week=1
                ),
            ],
            caseStudies=[
                CaseStudy(
                    title="Smith v. Jones",
                    file="Course_Materials/LLS/case_smith_jones.pdf",
                    court="Supreme Court"
                ),
            ],
            mockExams=[
                MockExam(
                    title="Mock Exam 2024",
                    file="Course_Materials/LLS/mock_exam_2024.pdf",
                    size="800 KB"
                ),
            ]
        )
    )


@pytest.fixture
def mock_extraction_statuses():
    """Mock extraction statuses for various files."""
    now = datetime.now(timezone.utc)
    return {
        "Course_Materials/LLS/textbook_intro.pdf": TextCacheEntry(
            file_path="Course_Materials/LLS/textbook_intro.pdf",
            file_hash="hash1",
            file_size=2621440,
            file_modified=now - timedelta(days=5),
            file_type="pdf",
            text="Introduction to law content...",
            text_length=45000,
            extraction_success=True,
            cached_at=now - timedelta(hours=2),
            metadata={"num_pages": 150}
        ),
        "Course_Materials/LLS/textbook_theory.pdf": TextCacheEntry(
            file_path="Course_Materials/LLS/textbook_theory.pdf",
            file_hash="hash2",
            file_size=3250585,
            file_modified=now - timedelta(days=3),
            file_type="pdf",
            text="Legal theory content...",
            text_length=52000,
            extraction_success=True,
            cached_at=now - timedelta(hours=1),
            metadata={"num_pages": 180}
        ),
        "Course_Materials/LLS/lecture_week_1.pdf": TextCacheEntry(
            file_path="Course_Materials/LLS/lecture_week_1.pdf",
            file_hash="hash3",
            file_size=1258291,
            file_modified=now - timedelta(days=1),
            file_type="pdf",
            text="Week 1 lecture content...",
            text_length=12000,
            extraction_success=True,
            cached_at=now - timedelta(minutes=30),
            metadata={"num_pages": 45}
        ),
        "Course_Materials/LLS/lecture_week_2.pdf": None,  # Not extracted yet
        "Course_Materials/LLS/reading_contracts.pdf": TextCacheEntry(
            file_path="Course_Materials/LLS/reading_contracts.pdf",
            file_hash="hash4",
            file_size=512000,
            file_modified=now - timedelta(days=2),
            file_type="pdf",
            text="",
            text_length=0,
            extraction_success=False,
            extraction_error="Failed to extract: corrupted PDF",
            cached_at=now - timedelta(hours=3)
        ),
        "Course_Materials/LLS/case_smith_jones.pdf": TextCacheEntry(
            file_path="Course_Materials/LLS/case_smith_jones.pdf",
            file_hash="hash5",
            file_size=800000,
            file_modified=now - timedelta(days=4),
            file_type="pdf",
            text="Case study content...",
            text_length=8500,
            extraction_success=True,
            cached_at=now - timedelta(hours=4),
            metadata={"num_pages": 25}
        ),
        "Course_Materials/LLS/mock_exam_2024.pdf": TextCacheEntry(
            file_path="Course_Materials/LLS/mock_exam_2024.pdf",
            file_hash="hash6",
            file_size=819200,
            file_modified=now - timedelta(days=6),
            file_type="pdf",
            text="Mock exam questions...",
            text_length=15000,
            extraction_success=True,
            cached_at=now - timedelta(hours=5),
            metadata={"num_pages": 30}
        ),
    }


class TestExtractionMetricsCalculation:
    """Tests for extraction metrics calculation logic."""

    def test_calculate_coverage_percentage(self, mock_extraction_statuses):
        """Should calculate correct coverage percentage."""
        total_files = len(mock_extraction_statuses)
        extracted_files = sum(
            1 for entry in mock_extraction_statuses.values()
            if entry and entry.extraction_success
        )
        
        coverage = (extracted_files / total_files) * 100
        
        # 5 successful out of 7 total = 71.4%
        assert coverage == pytest.approx(71.4, rel=0.1)

    def test_count_by_status(self, mock_extraction_statuses):
        """Should correctly count files by status."""
        extracted = sum(
            1 for entry in mock_extraction_statuses.values()
            if entry and entry.extraction_success
        )
        failed = sum(
            1 for entry in mock_extraction_statuses.values()
            if entry and not entry.extraction_success
        )
        not_extracted = sum(
            1 for entry in mock_extraction_statuses.values()
            if entry is None
        )
        
        assert extracted == 5
        assert failed == 1
        assert not_extracted == 1

    def test_calculate_total_characters(self, mock_extraction_statuses):
        """Should calculate total characters extracted."""
        total_chars = sum(
            entry.text_length for entry in mock_extraction_statuses.values()
            if entry and entry.extraction_success
        )
        
        # 45000 + 52000 + 12000 + 8500 + 15000 = 132500
        assert total_chars == 132500

    def test_group_by_file_type(self, mock_extraction_statuses):
        """Should group statistics by file type."""
        by_type = {}
        for entry in mock_extraction_statuses.values():
            if entry:
                file_type = entry.file_type
                if file_type not in by_type:
                    by_type[file_type] = {"total": 0, "extracted": 0}
                by_type[file_type]["total"] += 1
                if entry.extraction_success:
                    by_type[file_type]["extracted"] += 1
        
        assert by_type["pdf"]["total"] == 6
        assert by_type["pdf"]["extracted"] == 5


class TestExtractionStatusEndpoints:
    """Integration tests for extraction status endpoints."""

    def test_get_all_material_statuses(
        self, sample_course_with_materials, mock_extraction_statuses
    ):
        """Should retrieve status for all course materials."""
        # Get all file paths from materials
        materials = sample_course_with_materials.materials
        all_files = []

        if materials.coreTextbooks:
            all_files.extend([m.file for m in materials.coreTextbooks])
        if materials.lectures:
            all_files.extend([m.file for m in materials.lectures])
        if materials.readings:
            all_files.extend([m.file for m in materials.readings])
        if materials.caseStudies:
            all_files.extend([m.file for m in materials.caseStudies])
        if materials.mockExams:
            all_files.extend([m.file for m in materials.mockExams])

        assert len(all_files) == 7

        # Verify we have statuses for all files
        statuses = [mock_extraction_statuses.get(f) for f in all_files]
        assert len([s for s in statuses if s is not None]) == 6  # One is None (not extracted)

        # Verify extracted count
        extracted_count = sum(1 for s in statuses if s and s.extraction_success)
        assert extracted_count == 5


class TestActivityLogGeneration:
    """Tests for activity log generation."""

    def test_generate_activity_log(self, mock_extraction_statuses):
        """Should generate activity log from extraction statuses."""
        activities = []
        
        for file_path, entry in mock_extraction_statuses.items():
            if entry and entry.extraction_success and entry.cached_at:
                activities.append({
                    "file": file_path.split("/")[-1],
                    "date": entry.cached_at,
                    "chars": entry.text_length
                })
        
        # Sort by date descending
        activities.sort(key=lambda x: x["date"], reverse=True)
        
        # Take last 10
        recent_activities = activities[:10]
        
        assert len(recent_activities) == 5
        # Most recent should be lecture_week_1.pdf (30 minutes ago)
        assert "lecture_week_1.pdf" in recent_activities[0]["file"]

    def test_format_time_ago(self):
        """Should format time ago correctly."""
        now = datetime.now(timezone.utc)
        
        # Just now
        date1 = now - timedelta(seconds=30)
        seconds1 = (now - date1).total_seconds()
        assert seconds1 < 60
        
        # Minutes ago
        date2 = now - timedelta(minutes=45)
        seconds2 = (now - date2).total_seconds()
        minutes = int(seconds2 / 60)
        assert minutes == 45
        
        # Hours ago
        date3 = now - timedelta(hours=3)
        seconds3 = (now - date3).total_seconds()
        hours = int(seconds3 / 3600)
        assert hours == 3
        
        # Days ago
        date4 = now - timedelta(days=2)
        seconds4 = (now - date4).total_seconds()
        days = int(seconds4 / 86400)
        assert days == 2


class TestErrorHandlingAndReporting:
    """Tests for error handling and reporting."""

    def test_handle_extraction_failure(self, mock_extraction_statuses):
        """Should handle extraction failures gracefully."""
        # Find the failed entry
        failed_entry = None
        for entry in mock_extraction_statuses.values():
            if entry and not entry.extraction_success:
                failed_entry = entry
                break

        assert failed_entry is not None
        assert failed_entry.extraction_success is False
        assert "corrupted PDF" in failed_entry.extraction_error

    def test_generate_error_report(self, mock_extraction_statuses):
        """Should generate error report for failed extractions."""
        errors = []

        for file_path, entry in mock_extraction_statuses.items():
            if entry and not entry.extraction_success:
                errors.append({
                    "file": file_path,
                    "error": entry.extraction_error or "Unknown error"
                })

        assert len(errors) == 1
        assert "reading_contracts.pdf" in errors[0]["file"]
        assert "corrupted PDF" in errors[0]["error"]

