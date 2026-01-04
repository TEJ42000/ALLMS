"""Tests for the ECHR (European Court of Human Rights) case law service.

This module tests the ECHR service functionality including:
- API client methods
- Local SQLite caching
- Case parsing and data models
- Search and filtering
"""

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.echr_models import (
    ECHRCase,
    ECHRCaseSummary,
    ECHRConclusion,
    ECHRDocument,
    ECHRSearchRequest,
    ECHRSearchResponse,
    ECHRStatsResponse,
    ECHRSyncStatus,
)
from app.services.echr_service import (
    ECHRAPIError,
    ECHRService,
    ECHRServiceError,
    get_echr_service,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create a temporary cache directory."""
    cache_dir = tmp_path / "echr_cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def echr_service(temp_cache_dir):
    """Create an ECHR service with temporary cache."""
    service = ECHRService(cache_dir=temp_cache_dir)
    service._init_database()
    return service


@pytest.fixture
def sample_case_data():
    """Sample case data as returned by ECHR API."""
    return {
        "itemid": "001-57574",
        "appno": "12345/67",
        "docname": "CASE OF TEST v. COUNTRY",
        "ecli": "ECLI:CE:ECHR:2020:0115JUD001234567",
        "doctype": "JUDGMENT",
        "doctypebranch": "GRANDCHAMBER",
        "importance": 1,
        "judgementdate": "2020-01-15T00:00:00Z",
        "respondent": "TUR",
        "article": "6;6-1;8",
        "conclusion": "Violation of Article 6-1",
        "violation": "6-1",
        "nonviolation": "8",
        "languageisocode": "ENG",
        "scl": "Right to a fair trial",
        "separateopinion": True,
    }


@pytest.fixture
def sample_case(sample_case_data):
    """Create a sample ECHRCase from test data."""
    service = ECHRService()
    return service._parse_case(sample_case_data)


# ============================================================================
# Data Model Tests
# ============================================================================


class TestECHRModels:
    """Tests for ECHR data models."""

    def test_echr_case_creation(self):
        """Test creating an ECHRCase model."""
        case = ECHRCase(
            item_id="001-12345",
            application_number="12345/67",
            case_name="Test v. Country",
            judgment_date=datetime(2020, 1, 15, tzinfo=timezone.utc),
            respondent_state="TUR",
            articles=["6", "8"],
            violations=["6"],
            non_violations=["8"],
        )

        assert case.item_id == "001-12345"
        assert case.application_number == "12345/67"
        assert case.articles == ["6", "8"]
        assert case.violations == ["6"]

    def test_echr_case_summary_creation(self):
        """Test creating an ECHRCaseSummary model."""
        summary = ECHRCaseSummary(
            item_id="001-12345",
            application_number="12345/67",
            case_name="Test v. Country",
            respondent_state="TUR",
            articles=["6"],
            importance_level=1,
        )

        assert summary.item_id == "001-12345"
        assert summary.importance_level == 1

    def test_echr_search_request_defaults(self):
        """Test ECHRSearchRequest default values."""
        request = ECHRSearchRequest()

        assert request.page == 1
        assert request.limit == 20
        assert request.query is None
        assert request.articles is None

    def test_echr_search_request_with_filters(self):
        """Test ECHRSearchRequest with filters."""
        request = ECHRSearchRequest(
            articles=["6", "8"],
            respondent="TURKEY",
            importance=1,
            page=2,
            limit=50,
        )

        assert request.articles == ["6", "8"]
        assert request.respondent == "TURKEY"
        assert request.page == 2
        assert request.limit == 50


# ============================================================================
# Case Parsing Tests
# ============================================================================


class TestCaseParsing:
    """Tests for parsing API responses into models."""

    def test_parse_case_basic(self, echr_service, sample_case_data):
        """Test parsing a basic case from API response."""
        case = echr_service._parse_case(sample_case_data)

        assert case.item_id == "001-57574"
        assert case.application_number == "12345/67"
        assert case.case_name == "CASE OF TEST v. COUNTRY"
        assert case.ecli == "ECLI:CE:ECHR:2020:0115JUD001234567"
        assert case.document_type == "JUDGMENT"
        assert case.importance_level == 1
        assert case.respondent_state == "TUR"

    def test_parse_case_articles(self, echr_service, sample_case_data):
        """Test parsing articles from semicolon-separated string."""
        case = echr_service._parse_case(sample_case_data)

        assert case.articles == ["6", "6-1", "8"]

    def test_parse_case_violations(self, echr_service, sample_case_data):
        """Test parsing violations and non-violations."""
        case = echr_service._parse_case(sample_case_data)

        assert case.violations == ["6-1"]
        assert case.non_violations == ["8"]

    def test_parse_case_dates(self, echr_service, sample_case_data):
        """Test parsing dates from ISO format."""
        case = echr_service._parse_case(sample_case_data)

        assert case.judgment_date is not None
        assert case.judgment_date.year == 2020
        assert case.judgment_date.month == 1
        assert case.judgment_date.day == 15

    def test_parse_case_with_missing_fields(self, echr_service):
        """Test parsing a case with minimal data."""
        minimal_data = {"itemid": "001-99999"}
        case = echr_service._parse_case(minimal_data)

        assert case.item_id == "001-99999"
        assert case.application_number is None
        assert case.articles == []
        assert case.violations == []

    def test_parse_case_summary(self, echr_service, sample_case_data):
        """Test parsing a case summary."""
        summary = echr_service._parse_case_summary(sample_case_data)

        assert summary.item_id == "001-57574"
        assert summary.case_name == "CASE OF TEST v. COUNTRY"
        assert summary.articles == ["6", "6-1", "8"]


# ============================================================================
# Cache Tests
# ============================================================================


class TestCaching:
    """Tests for local SQLite caching."""

    def test_database_initialization(self, echr_service, temp_cache_dir):
        """Test that database is properly initialized."""
        db_path = temp_cache_dir / "echr_cases.db"
        assert db_path.exists()

    def test_cache_case(self, echr_service, sample_case):
        """Test caching a case to SQLite."""
        echr_service._cache_case(sample_case)

        # Retrieve from cache
        cached = echr_service._get_cached_case(sample_case.item_id)

        assert cached is not None
        assert cached.item_id == sample_case.item_id
        assert cached.case_name == sample_case.case_name

    def test_cache_memory_layer(self, echr_service, sample_case):
        """Test in-memory cache layer."""
        echr_service._cache_case(sample_case)

        # Should be in memory cache
        assert sample_case.item_id in echr_service._memory_cache

    def test_cache_miss(self, echr_service):
        """Test cache miss returns None."""
        result = echr_service._get_cached_case("nonexistent-id")
        assert result is None

    def test_clear_cache_specific(self, echr_service, sample_case):
        """Test clearing a specific case from cache."""
        echr_service._cache_case(sample_case)

        echr_service.clear_cache(sample_case.item_id)

        assert sample_case.item_id not in echr_service._memory_cache
        assert echr_service._get_cached_case(sample_case.item_id) is None

    def test_clear_cache_all(self, echr_service, sample_case):
        """Test clearing entire cache."""
        echr_service._cache_case(sample_case)

        echr_service.clear_cache()

        assert len(echr_service._memory_cache) == 0
        assert echr_service.get_cached_case_count() == 0

    def test_cached_case_count(self, echr_service, sample_case):
        """Test counting cached cases."""
        assert echr_service.get_cached_case_count() == 0

        echr_service._cache_case(sample_case)

        assert echr_service.get_cached_case_count() == 1


# ============================================================================
# Local Search Tests
# ============================================================================


class TestLocalSearch:
    """Tests for searching locally cached cases."""

    def test_search_cached_by_query(self, echr_service, sample_case):
        """Test searching cached cases by text query."""
        echr_service._cache_case(sample_case)

        results = echr_service.search_cached_cases(query="TEST")

        assert len(results) == 1
        assert results[0].item_id == sample_case.item_id

    def test_search_cached_by_respondent(self, echr_service, sample_case):
        """Test searching cached cases by respondent state."""
        echr_service._cache_case(sample_case)

        results = echr_service.search_cached_cases(respondent="TUR")

        assert len(results) == 1
        assert results[0].respondent_state == "TUR"

    def test_search_cached_by_articles(self, echr_service, sample_case):
        """Test searching cached cases by articles."""
        echr_service._cache_case(sample_case)

        results = echr_service.search_cached_cases(articles=["6"])

        assert len(results) == 1

    def test_search_cached_no_results(self, echr_service, sample_case):
        """Test search with no matching results."""
        echr_service._cache_case(sample_case)

        results = echr_service.search_cached_cases(query="NONEXISTENT")

        assert len(results) == 0

    def test_search_cached_pagination(self, echr_service):
        """Test pagination in cached search."""
        # Add multiple cases
        for i in range(5):
            case = ECHRCase(
                item_id=f"001-{i:05d}",
                case_name=f"CASE {i}",
                articles=["6"],
            )
            echr_service._cache_case(case)

        # Get first page
        page1 = echr_service.search_cached_cases(limit=2, offset=0)
        assert len(page1) == 2

        # Get second page
        page2 = echr_service.search_cached_cases(limit=2, offset=2)
        assert len(page2) == 2

        # Ensure different results
        assert page1[0].item_id != page2[0].item_id


# ============================================================================
# Filter Tests
# ============================================================================


class TestFiltering:
    """Tests for case filtering logic."""

    def test_filter_by_articles(self, echr_service):
        """Test filtering cases by articles."""
        cases = [
            ECHRCaseSummary(item_id="1", articles=["6", "8"]),
            ECHRCaseSummary(item_id="2", articles=["10"]),
            ECHRCaseSummary(item_id="3", articles=["6"]),
        ]

        request = ECHRSearchRequest(articles=["6"])
        filtered = echr_service._filter_cases(cases, request)

        assert len(filtered) == 2
        assert all("6" in c.articles for c in filtered)

    def test_filter_by_respondent(self, echr_service):
        """Test filtering cases by respondent state."""
        cases = [
            ECHRCaseSummary(item_id="1", respondent_state="TURKEY"),
            ECHRCaseSummary(item_id="2", respondent_state="FRANCE"),
            ECHRCaseSummary(item_id="3", respondent_state="TURKEY"),
        ]

        request = ECHRSearchRequest(respondent="TURKEY")
        filtered = echr_service._filter_cases(cases, request)

        assert len(filtered) == 2

    def test_filter_by_importance(self, echr_service):
        """Test filtering cases by importance level."""
        cases = [
            ECHRCaseSummary(item_id="1", importance_level=1),
            ECHRCaseSummary(item_id="2", importance_level=3),
            ECHRCaseSummary(item_id="3", importance_level=1),
        ]

        request = ECHRSearchRequest(importance=1)
        filtered = echr_service._filter_cases(cases, request)

        assert len(filtered) == 2

    def test_filter_by_query(self, echr_service):
        """Test filtering cases by text query."""
        cases = [
            ECHRCaseSummary(item_id="1", case_name="ALPHA v. STATE"),
            ECHRCaseSummary(item_id="2", case_name="BETA v. STATE"),
            ECHRCaseSummary(item_id="3", case_name="GAMMA v. STATE"),
        ]

        request = ECHRSearchRequest(query="alpha")
        filtered = echr_service._filter_cases(cases, request)

        assert len(filtered) == 1
        assert filtered[0].case_name == "ALPHA v. STATE"

    def test_filter_combined(self, echr_service):
        """Test combining multiple filters."""
        cases = [
            ECHRCaseSummary(item_id="1", case_name="A v. TUR", respondent_state="TURKEY", articles=["6"]),
            ECHRCaseSummary(item_id="2", case_name="B v. TUR", respondent_state="TURKEY", articles=["8"]),
            ECHRCaseSummary(item_id="3", case_name="C v. FRA", respondent_state="FRANCE", articles=["6"]),
        ]

        request = ECHRSearchRequest(respondent="TURKEY", articles=["6"])
        filtered = echr_service._filter_cases(cases, request)

        assert len(filtered) == 1
        assert filtered[0].item_id == "1"


# ============================================================================
# API Client Tests (Mocked)
# ============================================================================


class TestAPIClient:
    """Tests for API client methods with mocked HTTP."""

    @pytest.mark.asyncio
    async def test_get_case_from_api(self, echr_service, sample_case_data):
        """Test fetching a case from API."""
        with patch.object(echr_service, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = sample_case_data

            case = await echr_service.get_case("001-57574", use_cache=False)

            assert case is not None
            assert case.item_id == "001-57574"
            mock_get.assert_called_once_with("/cases/001-57574")

    @pytest.mark.asyncio
    async def test_get_case_from_cache(self, echr_service, sample_case):
        """Test fetching a case from cache."""
        echr_service._cache_case(sample_case)

        with patch.object(echr_service, "_get", new_callable=AsyncMock) as mock_get:
            case = await echr_service.get_case(sample_case.item_id, use_cache=True)

            assert case is not None
            assert case.item_id == sample_case.item_id
            mock_get.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_case_not_found(self, echr_service):
        """Test handling of 404 response."""
        with patch.object(echr_service, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = ECHRAPIError("Not found", status_code=404)

            case = await echr_service.get_case("nonexistent")

            assert case is None

    @pytest.mark.asyncio
    async def test_get_cases_paginated(self, echr_service, sample_case_data):
        """Test fetching paginated list of cases."""
        with patch.object(echr_service, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [sample_case_data, sample_case_data]

            cases, total = await echr_service.get_cases(page=1, limit=10)

            assert len(cases) == 2
            mock_get.assert_called_once_with("/cases", params={"page": 1, "limit": 10})

    @pytest.mark.asyncio
    async def test_get_stats(self, echr_service):
        """Test fetching API statistics."""
        with patch.object(echr_service, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"total_cases": 16096}

            stats = await echr_service.get_stats()

            assert stats.total_cases == 16096

    @pytest.mark.asyncio
    async def test_get_conclusions(self, echr_service):
        """Test fetching conclusions list."""
        with patch.object(echr_service, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {"id": "1", "article": "6", "type": "violation"},
                {"id": "2", "article": "8", "type": "no-violation"},
            ]

            conclusions = await echr_service.get_conclusions()

            assert len(conclusions) == 2
            assert conclusions[0].article == "6"

    @pytest.mark.asyncio
    async def test_get_case_documents(self, echr_service):
        """Test fetching case documents."""
        with patch.object(echr_service, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = [
                {"doctype": "JUDGMENT", "languageisocode": "ENG"},
            ]

            docs = await echr_service.get_case_documents("001-57574")

            assert len(docs) == 1
            assert docs[0].doc_type == "JUDGMENT"

    @pytest.mark.asyncio
    async def test_get_cited_applications(self, echr_service):
        """Test fetching cited applications."""
        with patch.object(echr_service, "_get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = ["12345/67", "23456/78"]

            cited = await echr_service.get_cited_applications("001-57574")

            assert len(cited) == 2
            assert "12345/67" in cited


# ============================================================================
# Sync Status Tests
# ============================================================================


class TestSyncStatus:
    """Tests for sync status functionality."""

    def test_get_sync_status_empty(self, echr_service):
        """Test sync status with empty cache."""
        status = echr_service.get_sync_status()

        assert status.cases_synced == 0
        assert status.last_sync is None
        assert status.sync_in_progress is False

    def test_get_sync_status_with_cases(self, echr_service, sample_case):
        """Test sync status with cached cases."""
        echr_service._cache_case(sample_case)

        status = echr_service.get_sync_status()

        assert status.cases_synced == 1


# ============================================================================
# Singleton Tests
# ============================================================================


class TestSingleton:
    """Tests for service singleton pattern."""

    def test_get_echr_service_singleton(self):
        """Test that get_echr_service returns same instance."""
        # Reset singleton
        import app.services.echr_service as echr_module
        echr_module._echr_service = None

        service1 = get_echr_service()
        service2 = get_echr_service()

        assert service1 is service2


# ============================================================================
# Error Handling Tests
# ============================================================================


class TestErrorHandling:
    """Tests for error handling."""

    def test_echr_api_error(self):
        """Test ECHRAPIError exception."""
        error = ECHRAPIError("Test error", status_code=500)

        assert str(error) == "Test error"
        assert error.status_code == 500

    def test_echr_service_error(self):
        """Test base ECHRServiceError exception."""
        error = ECHRServiceError("Base error")

        assert str(error) == "Base error"
        assert isinstance(error, Exception)
