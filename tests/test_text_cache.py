"""Tests for the Text Cache Service.

Tests cover:
- Cache model validation
- Cache service operations (when Firestore unavailable)
- Helper functions (file hashing, path normalization)
- Cache population logic
- API endpoint routing
"""

import hashlib
import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.models.text_cache_models import (
    TextCacheEntry,
    CacheStats,
    CachePopulateRequest,
    CachePopulateResponse,
    CacheInvalidateRequest,
    CacheInvalidateResponse,
)


client = TestClient(app)


# ============================================================================
# Model Tests
# ============================================================================


class TestTextCacheEntry:
    """Tests for TextCacheEntry model."""

    def test_create_valid_entry(self):
        """Test creating a valid cache entry."""
        entry = TextCacheEntry(
            file_path="Course_Materials/LLS/test.pdf",
            file_hash="abc123",
            file_size=1024,
            file_modified=datetime.now(timezone.utc),
            file_type="pdf",
            text="Sample extracted text",
            text_length=21,
            extraction_success=True,
        )
        assert entry.file_path == "Course_Materials/LLS/test.pdf"
        assert entry.text_length == 21
        assert entry.extraction_success is True

    def test_path_traversal_rejected(self):
        """Test that path traversal in file_path is rejected."""
        with pytest.raises(ValueError):
            TextCacheEntry(
                file_path="../etc/passwd",
                file_hash="abc123",
                file_size=100,
                file_modified=datetime.now(timezone.utc),
                file_type="text",
                text="",
                text_length=0,
                extraction_success=False,
            )

    def test_absolute_path_rejected(self):
        """Test that absolute paths are rejected."""
        with pytest.raises(ValueError):
            TextCacheEntry(
                file_path="/etc/passwd",
                file_hash="abc123",
                file_size=100,
                file_modified=datetime.now(timezone.utc),
                file_type="text",
                text="",
                text_length=0,
                extraction_success=False,
            )


class TestCacheStats:
    """Tests for CacheStats model."""

    def test_create_empty_stats(self):
        """Test creating empty cache stats."""
        stats = CacheStats(
            total_entries=0,
            total_characters=0,
            total_size_bytes=0,
        )
        assert stats.total_entries == 0
        assert stats.by_file_type == {}
        assert stats.cache_hit_rate is None

    def test_stats_with_data(self):
        """Test cache stats with data."""
        stats = CacheStats(
            total_entries=10,
            total_characters=50000,
            total_size_bytes=100000,
            successful_extractions=8,
            failed_extractions=2,
            by_file_type={"pdf": 5, "docx": 3, "md": 2},
            total_access_count=50,
        )
        assert stats.total_entries == 10
        assert stats.successful_extractions == 8


class TestCachePopulateRequest:
    """Tests for CachePopulateRequest model."""

    def test_valid_request(self):
        """Test valid populate request."""
        request = CachePopulateRequest(
            folder_path="Course_Materials/LLS",
            recursive=True,
            force_refresh=False,
        )
        assert request.folder_path == "Course_Materials/LLS"

    def test_path_traversal_rejected(self):
        """Test that path traversal is rejected."""
        with pytest.raises(ValueError):
            CachePopulateRequest(folder_path="../outside")

    def test_path_normalized(self):
        """Test that leading/trailing slashes are stripped."""
        request = CachePopulateRequest(folder_path="/Course_Materials/")
        assert request.folder_path == "Course_Materials"


class TestCacheInvalidateRequest:
    """Tests for CacheInvalidateRequest model."""

    def test_invalidate_single_file(self):
        """Test invalidate request for single file."""
        request = CacheInvalidateRequest(file_path="Course_Materials/test.pdf")
        assert request.file_path == "Course_Materials/test.pdf"
        assert request.all_stale is False

    def test_invalidate_stale(self):
        """Test invalidate all stale entries."""
        request = CacheInvalidateRequest(all_stale=True)
        assert request.all_stale is True


# ============================================================================
# Helper Function Tests
# ============================================================================


class TestHelperFunctions:
    """Tests for helper functions in text_cache_service."""

    def test_compute_file_hash(self, tmp_path, monkeypatch):
        """Test file hash computation."""
        from app.services import text_cache_service
        from app.services.text_cache_service import _compute_file_hash

        # Mock path validation to allow temp files for testing
        monkeypatch.setattr(text_cache_service, "_validate_path_within_materials", lambda p: True)

        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        hash_result = _compute_file_hash(test_file)

        # Verify it's a valid MD5 hash
        assert len(hash_result) == 32
        assert all(c in "0123456789abcdef" for c in hash_result)

        # Hash should be consistent
        assert hash_result == _compute_file_hash(test_file)

    def test_compute_file_hash_different_content(self, tmp_path, monkeypatch):
        """Test that different content produces different hashes."""
        from app.services import text_cache_service
        from app.services.text_cache_service import _compute_file_hash

        # Mock path validation to allow temp files for testing
        monkeypatch.setattr(text_cache_service, "_validate_path_within_materials", lambda p: True)

        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("Content A")
        file2.write_text("Content B")

        assert _compute_file_hash(file1) != _compute_file_hash(file2)

    def test_compute_file_hash_rejects_outside_materials(self, tmp_path):
        """Test that file hash computation rejects files outside Materials."""
        from app.services.text_cache_service import _compute_file_hash

        # Create a test file outside Materials
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello, World!")

        # Should return empty string for files outside Materials
        hash_result = _compute_file_hash(test_file)
        assert hash_result == ""

    def test_path_to_doc_id(self):
        """Test conversion of file path to Firestore document ID."""
        from app.services.text_cache_service import _path_to_doc_id

        doc_id = _path_to_doc_id("Course_Materials/LLS/lecture.pdf")

        # Should be 64 chars or less (SHA256 truncated)
        assert len(doc_id) <= 64
        # Should contain only hex chars
        assert all(c in "0123456789abcdef" for c in doc_id)
        # Should be consistent
        assert doc_id == _path_to_doc_id("Course_Materials/LLS/lecture.pdf")

    def test_extract_subject_and_tier(self):
        """Test extraction of subject and tier from file path."""
        from app.services.text_cache_service import _extract_subject_and_tier

        subject, tier = _extract_subject_and_tier("Syllabus/LLS/syllabus.pdf")
        assert subject == "LLS"
        assert tier == "Syllabus"

        subject, tier = _extract_subject_and_tier("Course_Materials/Criminal_Law/lecture.pdf")
        assert subject == "Criminal_Law"
        assert tier == "Course_Materials"


# ============================================================================
# Cache Service Tests (with mocked Firestore)
# ============================================================================


class TestTextCacheServiceNoFirestore:
    """Tests for TextCacheService when Firestore is not available."""

    def test_service_unavailable(self):
        """Test service behavior when Firestore is unavailable."""
        with patch('app.services.text_cache_service.get_firestore_client', return_value=None):
            from app.services.text_cache_service import TextCacheService

            service = TextCacheService()

            assert service.is_available is False
            assert service.get_cached("any/path.pdf") is None
            assert service.invalidate("any/path.pdf") is False
            assert service.invalidate_folder("any/folder") == 0

    def test_stats_when_unavailable(self):
        """Test stats returns empty when Firestore unavailable."""
        with patch('app.services.text_cache_service.get_firestore_client', return_value=None):
            from app.services.text_cache_service import TextCacheService

            service = TextCacheService()
            stats = service.get_stats()

            assert stats.total_entries == 0
            assert stats.total_characters == 0


# ============================================================================
# API Endpoint Tests
# ============================================================================


class TestCacheAPIEndpoints:
    """Tests for cache API endpoints."""

    def test_cache_health_endpoint(self):
        """Test cache health check endpoint."""
        response = client.get("/api/admin/cache/health")
        assert response.status_code == 200
        data = response.json()
        assert "firestore_available" in data
        assert "status" in data

    def test_cache_stats_endpoint_no_firestore(self):
        """Test cache stats endpoint when Firestore unavailable."""
        with patch('app.routes.text_cache.is_firestore_available', return_value=False):
            response = client.get("/api/admin/cache/stats")
            # Should return 503 when Firestore is unavailable
            assert response.status_code == 503

    def test_populate_invalid_path(self):
        """Test populate with path traversal is rejected."""
        with patch('app.routes.text_cache.is_firestore_available', return_value=True):
            response = client.post(
                "/api/admin/cache/populate",
                json={"folder_path": "../etc"}
            )
            # 422 = Pydantic validation rejects path traversal
            assert response.status_code == 422

    def test_invalidate_requires_target(self):
        """Test invalidate requires at least one target."""
        with patch('app.routes.text_cache.is_firestore_available', return_value=True):
            with patch('app.routes.text_cache.get_text_cache_service') as mock:
                mock_service = MagicMock()
                mock.return_value = mock_service

                response = client.post(
                    "/api/admin/cache/invalidate",
                    json={}
                )
                assert response.status_code == 400


# ============================================================================
# Extract Cached Function Tests
# ============================================================================


class TestExtractTextCached:
    """Tests for the extract_text_cached function."""

    def test_extract_nonexistent_file(self, tmp_path):
        """Test extracting from nonexistent file."""
        with patch('app.services.text_cache_service.get_firestore_client', return_value=None):
            from app.services.text_cache_service import extract_text_cached

            result = extract_text_cached(tmp_path / "nonexistent.pdf", _skip_path_validation=True)

            assert result.success is False
            assert "not found" in result.error.lower() or "invalid path" in result.error.lower()

    def test_extract_from_real_file(self):
        """Test extracting from a real file (no cache)."""
        with patch('app.services.text_cache_service.get_firestore_client', return_value=None):
            from app.services.text_cache_service import extract_text_cached

            # Use a real file that exists
            readme_path = Path("README.md")
            if readme_path.exists():
                result = extract_text_cached(readme_path)

                # Even without cache, should extract successfully
                assert result.success is True
                assert len(result.text) > 0
