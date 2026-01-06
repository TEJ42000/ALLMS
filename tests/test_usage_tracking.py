"""Tests for LLM Usage Tracking Service."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.usage_models import (
    LLMUsageRecord,
    UsageSummary,
    UserUsageSummary,
    UserContext,
    calculate_cost,
    COST_INPUT_PER_MILLION,
    COST_OUTPUT_PER_MILLION,
    COST_CACHE_WRITE_PER_MILLION,
    COST_CACHE_READ_PER_MILLION,
)
from app.services.usage_tracking_service import (
    UsageTrackingService,
    get_usage_tracking_service,
    USAGE_COLLECTION,
)


class TestCalculateCost:
    """Tests for the cost calculation function."""

    def test_calculate_cost_input_only(self):
        """Test cost calculation with only input tokens."""
        cost = calculate_cost(input_tokens=1_000_000, output_tokens=0)
        assert cost == COST_INPUT_PER_MILLION

    def test_calculate_cost_output_only(self):
        """Test cost calculation with only output tokens."""
        cost = calculate_cost(input_tokens=0, output_tokens=1_000_000)
        assert cost == COST_OUTPUT_PER_MILLION

    def test_calculate_cost_with_cache(self):
        """Test cost calculation with cache tokens."""
        cost = calculate_cost(
            input_tokens=1_000_000,
            output_tokens=1_000_000,
            cache_creation_tokens=1_000_000,
            cache_read_tokens=1_000_000,
        )
        expected = (
            COST_INPUT_PER_MILLION +
            COST_OUTPUT_PER_MILLION +
            COST_CACHE_WRITE_PER_MILLION +
            COST_CACHE_READ_PER_MILLION
        )
        assert cost == expected

    def test_calculate_cost_small_usage(self):
        """Test cost calculation with small token counts."""
        # 1000 input tokens, 500 output tokens
        cost = calculate_cost(input_tokens=1000, output_tokens=500)
        expected = (1000 / 1_000_000) * 3.00 + (500 / 1_000_000) * 15.00
        assert abs(cost - expected) < 0.000001

    def test_calculate_cost_zero(self):
        """Test cost calculation with zero tokens."""
        cost = calculate_cost(input_tokens=0, output_tokens=0)
        assert cost == 0.0


class TestLLMUsageRecord:
    """Tests for the LLMUsageRecord model."""

    def test_create_record(self):
        """Test creating a usage record."""
        record = LLMUsageRecord(
            id="test-id",
            user_email="test@example.com",
            user_id="user-123",
            model="claude-sonnet-4-20250514",
            operation_type="tutor",
            input_tokens=1000,
            output_tokens=500,
            estimated_cost_usd=0.0105,
        )
        assert record.id == "test-id"
        assert record.user_email == "test@example.com"
        assert record.input_tokens == 1000
        assert record.output_tokens == 500

    def test_record_with_optional_fields(self):
        """Test creating a record with optional fields."""
        record = LLMUsageRecord(
            id="test-id",
            user_email="test@example.com",
            user_id="user-123",
            model="claude-sonnet-4-20250514",
            operation_type="study_guide",
            input_tokens=5000,
            output_tokens=2000,
            cache_creation_tokens=3000,
            cache_read_tokens=1000,
            estimated_cost_usd=0.05,
            course_id="LLS-2025-2026",
            request_metadata={"context": "Private Law"},
        )
        assert record.course_id == "LLS-2025-2026"
        assert record.cache_creation_tokens == 3000
        assert record.request_metadata["context"] == "Private Law"


class TestUsageTrackingService:
    """Tests for the UsageTrackingService."""

    @pytest.fixture
    def mock_firestore(self):
        """Create a mock Firestore client."""
        with patch('app.services.usage_tracking_service.get_firestore_client') as mock:
            mock_db = MagicMock()
            mock.return_value = mock_db
            yield mock_db

    @pytest.fixture
    def service(self, mock_firestore):
        """Create a service instance with mocked Firestore."""
        return UsageTrackingService()

    @pytest.mark.asyncio
    async def test_record_usage(self, service, mock_firestore):
        """Test recording usage."""
        mock_doc_ref = MagicMock()
        mock_firestore.collection.return_value.document.return_value = mock_doc_ref

        record = await service.record_usage(
            user_email="test@example.com",
            user_id="user-123",
            model="claude-sonnet-4-20250514",
            operation_type="tutor",
            input_tokens=1000,
            output_tokens=500,
        )

        assert record is not None
        assert record.user_email == "test@example.com"
        assert record.operation_type == "tutor"
        mock_firestore.collection.assert_called_with(USAGE_COLLECTION)
        mock_doc_ref.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_record_usage_no_firestore(self):
        """Test recording usage when Firestore is unavailable."""
        with patch('app.services.usage_tracking_service.get_firestore_client', return_value=None):
            service = UsageTrackingService()
            record = await service.record_usage(
                user_email="test@example.com",
                user_id="user-123",
                model="claude-sonnet-4-20250514",
                operation_type="tutor",
                input_tokens=1000,
                output_tokens=500,
            )
            assert record is None

    @pytest.mark.asyncio
    async def test_record_usage_with_metadata(self, service, mock_firestore):
        """Test recording usage with request metadata."""
        mock_doc_ref = MagicMock()
        mock_firestore.collection.return_value.document.return_value = mock_doc_ref

        record = await service.record_usage(
            user_email="test@example.com",
            user_id="user-123",
            model="claude-sonnet-4-20250514",
            operation_type="study_guide",
            input_tokens=5000,
            output_tokens=2000,
            cache_creation_tokens=3000,
            cache_read_tokens=1000,
            course_id="LLS-2025-2026",
            request_metadata={"topic": "Private Law", "week_numbers": [1, 2]},
        )

        assert record is not None
        assert record.course_id == "LLS-2025-2026"
        assert record.cache_creation_tokens == 3000
        assert record.request_metadata["topic"] == "Private Law"

    @pytest.mark.asyncio
    async def test_record_usage_cost_calculation(self, service, mock_firestore):
        """Test that cost is calculated correctly when recording usage."""
        mock_doc_ref = MagicMock()
        mock_firestore.collection.return_value.document.return_value = mock_doc_ref

        record = await service.record_usage(
            user_email="test@example.com",
            user_id="user-123",
            model="claude-sonnet-4-20250514",
            operation_type="tutor",
            input_tokens=1000,
            output_tokens=500,
        )

        # Verify cost calculation: (1000/1M)*3 + (500/1M)*15 = 0.003 + 0.0075 = 0.0105
        expected_cost = (1000 / 1_000_000) * 3.00 + (500 / 1_000_000) * 15.00
        assert abs(record.estimated_cost_usd - expected_cost) < 0.000001


class TestUserContext:
    """Tests for the UserContext dataclass."""

    def test_create_user_context(self):
        """Test creating a UserContext."""
        ctx = UserContext(
            email="test@example.com",
            user_id="user-123",
        )
        assert ctx.email == "test@example.com"
        assert ctx.user_id == "user-123"
        assert ctx.course_id is None

    def test_create_user_context_with_course(self):
        """Test creating a UserContext with course_id."""
        ctx = UserContext(
            email="test@example.com",
            user_id="user-123",
            course_id="LLS-2025-2026",
        )
        assert ctx.course_id == "LLS-2025-2026"

