"""Integration tests for Text Extraction Status UI.

Tests the complete workflow of the extraction status UI.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.models.text_cache_models import CacheStats


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_firestore_available():
    """Mock Firestore availability."""
    with patch("app.routes.text_cache.is_firestore_available") as mock_check:
        mock_check.return_value = True
        yield mock_check


class TestDashboardDataLoading:
    """Tests for dashboard data loading workflow."""

    def test_load_dashboard_metrics(self, client, mock_firestore_available):
        """Should load dashboard metrics on page load."""
        with patch("app.routes.text_cache.get_text_cache_service") as mock_service:
            mock_cache = MagicMock()
            mock_stats = CacheStats(
                total_entries=42,
                total_characters=150000,
                total_size_bytes=5242880,
                by_file_type={"pdf": 30, "docx": 10, "png": 2},
                cache_hit_rate=0.85,
                stale_entries=3
            )
            mock_cache.get_stats.return_value = mock_stats
            mock_cache.count_stale_entries.return_value = 3
            mock_service.return_value = mock_cache

            response = client.get("/api/admin/cache/stats")

            assert response.status_code == 200
            data = response.json()
            
            # Verify metrics match expected dashboard values
            assert data["total_entries"] == 42
            assert data["total_characters"] == 150000
            assert data["by_file_type"]["pdf"] == 30
            assert data["cache_hit_rate"] == 0.85


class TestExtractionWorkflow:
    """Integration tests for extraction workflow."""

    def test_check_stats_workflow(
        self, client, mock_firestore_available
    ):
        """Test workflow: check stats, verify structure."""
        with patch("app.routes.text_cache.get_text_cache_service") as mock_service:
            mock_cache = MagicMock()
            
            # Step 1: Check initial stats
            initial_stats = CacheStats(
                total_entries=0,
                total_characters=0,
                total_size_bytes=0,
            )
            mock_cache.get_stats.return_value = initial_stats
            mock_cache.count_stale_entries.return_value = 0
            mock_service.return_value = mock_cache
            
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
            mock_cache.get_stats.return_value = final_stats
            
            response = client.get("/api/admin/cache/stats")
            assert response.status_code == 200
            assert response.json()["total_entries"] == 3
            assert response.json()["by_file_type"]["pdf"] == 3


class TestErrorHandlingWorkflow:
    """Tests for error handling in UI workflows."""

    def test_handle_firestore_unavailable(self, client):
        """Should handle Firestore unavailability gracefully."""
        with patch("app.routes.text_cache.is_firestore_available") as mock_check:
            mock_check.return_value = False
            
            response = client.get("/api/admin/cache/stats")
            
            assert response.status_code == 503
            assert "Firestore not available" in response.json()["detail"]

    def test_handle_file_not_found(self, client, mock_firestore_available):
        """Should handle missing files gracefully."""
        from pathlib import Path
        with patch("app.routes.text_cache.validate_cache_path") as mock_validate:
            mock_path = MagicMock(spec=Path)
            mock_path.exists.return_value = False
            mock_validate.return_value = mock_path
            
            response = client.get("/api/admin/cache/file/nonexistent.pdf")
            
            assert response.status_code == 404


class TestHealthEndpoint:
    """Tests for cache health endpoint."""

    def test_cache_health_available(self, client, mock_firestore_available):
        """Should return healthy status when Firestore is available."""
        with patch("app.routes.text_cache.get_text_cache_service") as mock_service:
            mock_cache = MagicMock()
            mock_cache.is_available = True
            mock_service.return_value = mock_cache
            
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


class TestAPIEndpointStructure:
    """Tests for API endpoint structure and responses."""

    def test_stats_endpoint_structure(self, client, mock_firestore_available):
        """Should return properly structured stats response."""
        with patch("app.routes.text_cache.get_text_cache_service") as mock_service:
            mock_cache = MagicMock()
            mock_stats = CacheStats(
                total_entries=10,
                total_characters=5000,
                total_size_bytes=100000,
                by_file_type={"pdf": 8, "docx": 2},
            )
            mock_cache.get_stats.return_value = mock_stats
            mock_cache.count_stale_entries.return_value = 1
            mock_service.return_value = mock_cache

            response = client.get("/api/admin/cache/stats")

            assert response.status_code == 200
            data = response.json()
            
            # Verify required fields
            assert "total_entries" in data
            assert "total_characters" in data
            assert "total_size_bytes" in data
            assert "by_file_type" in data
            assert isinstance(data["by_file_type"], dict)

    def test_health_endpoint_structure(self, client):
        """Should return properly structured health response."""
        with patch("app.routes.text_cache.is_firestore_available") as mock_check:
            mock_check.return_value = True
            
            with patch("app.routes.text_cache.get_text_cache_service") as mock_service:
                mock_cache = MagicMock()
                mock_cache.is_available = True
                mock_service.return_value = mock_cache
                
                response = client.get("/api/admin/cache/health")

                assert response.status_code == 200
                data = response.json()
                
                # Verify required fields
                assert "firestore_available" in data
                assert "cache_available" in data
                assert "status" in data
                assert data["status"] in ["healthy", "degraded"]

