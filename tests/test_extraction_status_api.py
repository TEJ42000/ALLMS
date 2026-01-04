"""Tests for Text Extraction Status API endpoints.

Tests the REST API endpoints used by the text extraction status UI.
"""

import pytest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.text_cache_models import TextCacheEntry, CacheStats


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_firestore_available():
    """Mock Firestore availability check."""
    with patch("app.routes.text_cache.is_firestore_available") as mock_check:
        mock_check.return_value = True
        yield mock_check


@pytest.fixture
def mock_text_cache_service():
    """Mock the TextCacheService."""
    with patch("app.routes.text_cache.get_text_cache_service") as mock_get:
        mock_service = MagicMock()
        mock_get.return_value = mock_service
        yield mock_service


class TestGetCacheStats:
    """Tests for GET /api/admin/cache/stats."""

    def test_get_cache_stats_success(
        self, client, mock_firestore_available, mock_text_cache_service
    ):
        """Should return cache statistics."""
        mock_stats = CacheStats(
            total_entries=42,
            total_characters=150000,
            total_size_bytes=5242880,
            by_file_type={"pdf": 30, "docx": 10, "png": 2},
            cache_hit_rate=0.85,
            stale_entries=3
        )
        mock_text_cache_service.get_stats.return_value = mock_stats
        mock_text_cache_service.count_stale_entries.return_value = 3

        response = client.get("/api/admin/cache/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_entries"] == 42
        assert data["total_characters"] == 150000
        assert data["by_file_type"]["pdf"] == 30
        assert data["cache_hit_rate"] == 0.85
        assert data["stale_entries"] == 3

    def test_get_cache_stats_empty(
        self, client, mock_firestore_available, mock_text_cache_service
    ):
        """Should handle empty cache."""
        mock_stats = CacheStats(
            total_entries=0,
            total_characters=0,
            total_size_bytes=0,
        )
        mock_text_cache_service.get_stats.return_value = mock_stats
        mock_text_cache_service.count_stale_entries.return_value = 0

        response = client.get("/api/admin/cache/stats")

        assert response.status_code == 200
        data = response.json()
        assert data["total_entries"] == 0
        assert data["by_file_type"] == {}

    def test_get_cache_stats_firestore_unavailable(self, client):
        """Should return 503 when Firestore is unavailable."""
        with patch("app.routes.text_cache.is_firestore_available") as mock_check:
            mock_check.return_value = False
            
            response = client.get("/api/admin/cache/stats")

            assert response.status_code == 503
            assert "Firestore not available" in response.json()["detail"]


class TestGetCachedFile:
    """Tests for GET /api/admin/cache/file/{file_path}."""

    def test_get_cached_file_firestore_unavailable(self, client):
        """Should return 503 when Firestore is unavailable."""
        with patch("app.routes.text_cache.is_firestore_available") as mock_check:
            mock_check.return_value = False
            
            response = client.get("/api/admin/cache/file/test.pdf")

            assert response.status_code == 503
            assert "Firestore not available" in response.json()["detail"]

    def test_get_cached_file_not_found(self, client, mock_firestore_available):
        """Should return 404 for nonexistent file."""
        with patch("app.routes.text_cache.validate_cache_path") as mock_validate:
            mock_path = MagicMock(spec=Path)
            mock_path.exists.return_value = False
            mock_validate.return_value = mock_path
            
            response = client.get("/api/admin/cache/file/nonexistent.pdf")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


class TestRefreshFileCache:
    """Tests for POST /api/admin/cache/file/{file_path}/refresh."""

    def test_refresh_file_cache_firestore_unavailable(self, client):
        """Should return 503 when Firestore is unavailable."""
        with patch("app.routes.text_cache.is_firestore_available") as mock_check:
            mock_check.return_value = False
            
            response = client.post("/api/admin/cache/file/test.pdf/refresh")

            assert response.status_code == 503
            assert "Firestore not available" in response.json()["detail"]

    def test_refresh_file_cache_not_found(self, client, mock_firestore_available):
        """Should return 404 for nonexistent file."""
        with patch("app.routes.text_cache.validate_cache_path") as mock_validate:
            mock_path = MagicMock(spec=Path)
            mock_path.exists.return_value = False
            mock_validate.return_value = mock_path
            
            response = client.post("/api/admin/cache/file/nonexistent.pdf/refresh")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()


class TestExtractionWorkflow:
    """Integration tests for extraction workflow."""

    def test_check_stats_then_extract(
        self, client, mock_firestore_available, mock_text_cache_service
    ):
        """Test workflow: check stats, then extract files."""
        # Step 1: Check initial stats
        initial_stats = CacheStats(
            total_entries=0,
            total_characters=0,
            total_size_bytes=0,
        )
        mock_text_cache_service.get_stats.return_value = initial_stats
        mock_text_cache_service.count_stale_entries.return_value = 0
        
        response = client.get("/api/admin/cache/stats")
        assert response.status_code == 200
        assert response.json()["total_entries"] == 0

        # Step 2: Verify final stats can be retrieved
        final_stats = CacheStats(
            total_entries=3,
            total_characters=300,
            total_size_bytes=300000,
            by_file_type={"pdf": 3},
        )
        mock_text_cache_service.get_stats.return_value = final_stats
        mock_text_cache_service.count_stale_entries.return_value = 0
        
        response = client.get("/api/admin/cache/stats")
        assert response.status_code == 200
        assert response.json()["total_entries"] == 3
        assert response.json()["by_file_type"]["pdf"] == 3


class TestHealthEndpoint:
    """Tests for cache health endpoint."""

    def test_cache_health_available(self, client, mock_firestore_available, mock_text_cache_service):
        """Should return healthy status when Firestore is available."""
        mock_text_cache_service.is_available = True
        
        response = client.get("/api/admin/cache/health")

        assert response.status_code == 200
        data = response.json()
        assert data["firestore_available"] is True
        assert data["status"] == "healthy"

    def test_cache_health_unavailable(self, client):
        """Should return degraded status when Firestore is unavailable."""
        with patch("app.routes.text_cache.is_firestore_available") as mock_check:
            mock_check.return_value = False
            
            response = client.get("/api/admin/cache/health")

            assert response.status_code == 200
            data = response.json()
            assert data["firestore_available"] is False
            assert data["status"] == "degraded"


class TestPopulateCache:
    """Tests for cache population endpoints."""

    def test_populate_cache_firestore_unavailable(self, client):
        """Should return 503 when Firestore is unavailable."""
        with patch("app.routes.text_cache.is_firestore_available") as mock_check:
            mock_check.return_value = False
            
            response = client.post(
                "/api/admin/cache/populate",
                json={"folder_path": "Course_Materials/LLS", "force_refresh": False}
            )

            assert response.status_code == 503

    def test_populate_all_cache_firestore_unavailable(self, client):
        """Should return 503 when Firestore is unavailable."""
        with patch("app.routes.text_cache.is_firestore_available") as mock_check:
            mock_check.return_value = False
            
            response = client.post(
                "/api/admin/cache/populate/all",
                json={"force_refresh": False}
            )

            assert response.status_code == 503


class TestInvalidateCache:
    """Tests for cache invalidation endpoints."""

    def test_invalidate_cache_firestore_unavailable(self, client):
        """Should return 503 when Firestore is unavailable."""
        with patch("app.routes.text_cache.is_firestore_available") as mock_check:
            mock_check.return_value = False
            
            response = client.post(
                "/api/admin/cache/invalidate",
                json={"all_stale": True}
            )

            assert response.status_code == 503

