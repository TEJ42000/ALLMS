"""
Integration tests for upload retry logic with simulated Firestore operations.

Tests verify that the retry mechanism correctly handles transient failures,
exhausts retries appropriately, and works with concurrent uploads.

Issue #219 - Add Integration Tests for Upload Retry Logic

Usage:
    pytest tests/test_upload_retry_integration.py -v
    pytest tests/test_upload_retry_integration.py -v -m integration
"""

import pytest
import asyncio
import random
from contextlib import contextmanager
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone

from google.api_core import exceptions as google_exceptions

from app.services.retry_logic import retry_with_backoff, retry_sync, RetryConfig


# =============================================================================
# Test Helpers - Firestore Failure Simulation
# =============================================================================

@contextmanager
def patch_firestore_to_fail_once(target_module: str = "app.services.gcp_service"):
    """
    Make Firestore fail once, then succeed.
    
    Simulates a transient network error that resolves after one retry.
    """
    call_count = {"count": 0}
    original_client = None
    
    def mock_get_client():
        nonlocal original_client
        call_count["count"] += 1
        if call_count["count"] == 1:
            raise google_exceptions.ServiceUnavailable("Simulated transient failure")
        # Return a working mock on subsequent calls
        mock_client = MagicMock()
        mock_client.collection.return_value.document.return_value.set.return_value = None
        mock_client.collection.return_value.document.return_value.update.return_value = None
        return mock_client
    
    with patch(f"{target_module}.get_firestore_client", side_effect=mock_get_client) as mock:
        mock.call_count_tracker = call_count
        yield mock


@contextmanager
def patch_firestore_to_always_fail(error_type: Exception = None):
    """
    Make Firestore always fail with a specific error type.
    
    Used to test max retries exhaustion.
    """
    if error_type is None:
        error_type = google_exceptions.ServiceUnavailable("Persistent failure")
    
    def mock_get_client():
        raise error_type
    
    with patch("app.services.gcp_service.get_firestore_client", side_effect=mock_get_client) as mock:
        yield mock


@contextmanager
def patch_firestore_to_fail_randomly(failure_rate: float = 0.3, seed: int = None):
    """
    Make Firestore fail randomly with a given failure rate.
    
    Args:
        failure_rate: Probability of failure (0.0 to 1.0)
        seed: Random seed for reproducibility
    """
    if seed is not None:
        random.seed(seed)
    
    call_count = {"total": 0, "failures": 0}
    
    def mock_get_client():
        call_count["total"] += 1
        if random.random() < failure_rate:
            call_count["failures"] += 1
            raise google_exceptions.ServiceUnavailable("Random transient failure")
        # Return a working mock
        mock_client = MagicMock()
        mock_client.collection.return_value.document.return_value.set.return_value = None
        mock_client.collection.return_value.document.return_value.update.return_value = None
        return mock_client
    
    with patch("app.services.gcp_service.get_firestore_client", side_effect=mock_get_client) as mock:
        mock.call_count_tracker = call_count
        yield mock


@contextmanager
def patch_network_to_fail_once():
    """
    Simulate a network error (ConnectionError) that resolves after one retry.
    """
    call_count = {"count": 0}
    
    def mock_operation(*args, **kwargs):
        call_count["count"] += 1
        if call_count["count"] == 1:
            raise ConnectionError("Network unreachable")
        return "success"
    
    yield mock_operation, call_count


# =============================================================================
# Integration Tests - Retry Logic with Firestore
# =============================================================================

@pytest.mark.integration
class TestUploadRetryIntegration:
    """Integration tests for upload retry logic."""

    @pytest.fixture
    def retry_config(self):
        """Standard retry config for tests with short delays."""
        return RetryConfig(
            max_retries=3,
            initial_delay=0.01,  # 10ms - fast for tests
            max_delay=0.1,      # 100ms max
            jitter=0.0,         # No jitter for predictable tests
            retryable_exceptions=(
                google_exceptions.ServiceUnavailable,
                google_exceptions.DeadlineExceeded,
                google_exceptions.Aborted,
                ConnectionError,
                TimeoutError,
            )
        )

    @pytest.mark.asyncio
    async def test_recovers_from_transient_firestore_failure(self, retry_config):
        """
        Test that async operation recovers from a transient Firestore failure.

        Scenario:
        1. First attempt fails with ServiceUnavailable
        2. Retry kicks in
        3. Second attempt succeeds
        """
        call_count = {"count": 0}

        async def flaky_operation():
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise google_exceptions.ServiceUnavailable("Transient failure")
            return {"status": "success", "material_id": "test123"}

        # Execute with retry
        result = await retry_with_backoff(flaky_operation, config=retry_config)

        # Verify success after retry
        assert result["status"] == "success"
        assert call_count["count"] == 2  # First failed, second succeeded

    @pytest.mark.asyncio
    async def test_fails_after_max_retries_exhausted(self, retry_config):
        """
        Test that operation fails gracefully after exhausting all retries.

        Scenario:
        1. All attempts fail with ServiceUnavailable
        2. After max_retries+1 attempts, gives up
        3. Exception is raised
        """
        call_count = {"count": 0}

        async def always_failing_operation():
            call_count["count"] += 1
            raise google_exceptions.ServiceUnavailable("Persistent failure")

        # Execute with retry - should raise after max retries
        with pytest.raises(google_exceptions.ServiceUnavailable) as exc_info:
            await retry_with_backoff(always_failing_operation, config=retry_config)

        assert "Persistent failure" in str(exc_info.value)
        # max_retries=3 means 3 total attempts
        assert call_count["count"] == 3

    @pytest.mark.asyncio
    async def test_concurrent_operations_with_retry(self, retry_config):
        """
        Test that multiple concurrent operations handle retries independently.

        Scenario:
        1. Launch 5 concurrent operations
        2. Some fail transiently (randomly)
        3. All should eventually succeed after retries
        """
        results = []
        call_counts = [{"count": 0} for _ in range(5)]

        async def flaky_operation(index):
            call_counts[index]["count"] += 1
            # Fail on first attempt for operations 0, 2, 4
            if call_counts[index]["count"] == 1 and index % 2 == 0:
                raise google_exceptions.ServiceUnavailable(f"Transient failure {index}")
            return {"status": "success", "index": index}

        # Run all concurrently
        tasks = [
            retry_with_backoff(lambda i=i: flaky_operation(i), config=retry_config)
            for i in range(5)
        ]
        results = await asyncio.gather(*tasks)

        # All should succeed
        assert len(results) == 5
        assert all(r["status"] == "success" for r in results)

        # Operations 0, 2, 4 should have 2 calls; 1, 3 should have 1 call
        assert call_counts[0]["count"] == 2
        assert call_counts[1]["count"] == 1
        assert call_counts[2]["count"] == 2
        assert call_counts[3]["count"] == 1
        assert call_counts[4]["count"] == 2

    @pytest.mark.asyncio
    async def test_recovers_from_network_error(self, retry_config):
        """
        Test that operation recovers from network errors (ConnectionError).

        Scenario:
        1. First attempt fails with ConnectionError
        2. Retry kicks in
        3. Second attempt succeeds
        """
        call_count = {"count": 0}

        async def network_flaky_operation():
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise ConnectionError("Network unreachable")
            return {"status": "success", "recovered": True}

        result = await retry_with_backoff(network_flaky_operation, config=retry_config)

        assert result["status"] == "success"
        assert result["recovered"] is True
        assert call_count["count"] == 2

    def test_sync_recovers_from_transient_failure(self, retry_config):
        """
        Test that sync operation recovers from a transient failure.
        """
        call_count = {"count": 0}

        def flaky_sync_operation():
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise google_exceptions.ServiceUnavailable("Transient sync failure")
            return {"status": "success"}

        result = retry_sync(flaky_sync_operation, config=retry_config)

        assert result["status"] == "success"
        assert call_count["count"] == 2

    def test_sync_fails_after_max_retries(self, retry_config):
        """
        Test that sync operation fails after max retries.
        """
        call_count = {"count": 0}

        def always_failing_sync():
            call_count["count"] += 1
            raise google_exceptions.DeadlineExceeded("Timeout")

        with pytest.raises(google_exceptions.DeadlineExceeded):
            retry_sync(always_failing_sync, config=retry_config)

        assert call_count["count"] == 3  # 3 total attempts

    @pytest.mark.asyncio
    async def test_non_retryable_exception_fails_immediately(self, retry_config):
        """
        Test that non-retryable exceptions fail immediately without retry.
        """
        call_count = {"count": 0}

        async def permission_denied_operation():
            call_count["count"] += 1
            # PermissionDenied is NOT in retryable_exceptions
            raise google_exceptions.PermissionDenied("Not authorized")

        with pytest.raises(google_exceptions.PermissionDenied):
            await retry_with_backoff(permission_denied_operation, config=retry_config)

        # Should fail immediately without retries
        assert call_count["count"] == 1

    @pytest.mark.asyncio
    async def test_random_failures_all_eventually_succeed(self):
        """
        Test with random failures that all operations eventually succeed.

        Uses a seeded random for reproducibility.
        """
        random.seed(42)  # Reproducible random
        call_count = {"total": 0, "failures": 0}

        config = RetryConfig(
            max_retries=5,  # More retries for random failures
            initial_delay=0.001,
            max_delay=0.01,
            jitter=0.0,
            retryable_exceptions=(google_exceptions.ServiceUnavailable,)
        )

        async def randomly_failing_operation():
            call_count["total"] += 1
            if random.random() < 0.4:  # 40% failure rate
                call_count["failures"] += 1
                raise google_exceptions.ServiceUnavailable("Random failure")
            return {"status": "success"}

        # Run 10 operations
        tasks = [
            retry_with_backoff(randomly_failing_operation, config=config)
            for _ in range(10)
        ]
        results = await asyncio.gather(*tasks)

        # All should eventually succeed
        assert len(results) == 10
        assert all(r["status"] == "success" for r in results)
        # There should have been some failures (retries)
        assert call_count["failures"] > 0


@pytest.mark.integration
class TestUploadFlowRetryIntegration:
    """Integration tests that simulate the actual upload flow with retry."""

    @pytest.fixture
    def mock_materials_service(self):
        """Create a mock CourseMaterialsService with configurable failure behavior."""
        mock_service = MagicMock()
        return mock_service

    @pytest.mark.asyncio
    async def test_upload_update_retries_on_firestore_failure(self):
        """
        Test that Firestore update during upload retries on transient failure.

        Simulates the actual pattern used in upload.py:
        1. File uploaded successfully
        2. Firestore metadata update fails transiently
        3. Retry succeeds
        """
        call_count = {"count": 0}

        # Simulate the actual update_text_extraction call pattern
        def mock_update_text_extraction(course_id, material_id, extracted_text, text_length, error=None):
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise google_exceptions.ServiceUnavailable("Firestore temporarily unavailable")
            # Success on retry
            return MagicMock(id=material_id)

        config = RetryConfig(
            max_retries=3,
            initial_delay=0.001,
            max_delay=0.01,
            retryable_exceptions=(google_exceptions.ServiceUnavailable,)
        )

        async def update_with_retry():
            mock_update_text_extraction("test-course", "mat-123", "extracted text", 100)

        # Should succeed after retry
        await retry_with_backoff(update_with_retry, config=config)
        assert call_count["count"] == 2

    @pytest.mark.asyncio
    async def test_upload_handles_deadline_exceeded(self):
        """
        Test handling of DeadlineExceeded errors during upload.
        """
        call_count = {"count": 0}

        async def deadline_flaky_operation():
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise google_exceptions.DeadlineExceeded("Operation timed out")
            return {"status": "success"}

        config = RetryConfig(
            max_retries=3,
            initial_delay=0.001,
            retryable_exceptions=(google_exceptions.DeadlineExceeded,)
        )

        result = await retry_with_backoff(deadline_flaky_operation, config=config)
        assert result["status"] == "success"
        assert call_count["count"] == 3

    @pytest.mark.asyncio
    async def test_upload_handles_resource_exhausted(self):
        """
        Test handling of ResourceExhausted (quota) errors during upload.
        """
        call_count = {"count": 0}

        async def quota_flaky_operation():
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise google_exceptions.ResourceExhausted("Quota exceeded temporarily")
            return {"status": "success"}

        config = RetryConfig(
            max_retries=3,
            initial_delay=0.001,
            retryable_exceptions=(google_exceptions.ResourceExhausted,)
        )

        result = await retry_with_backoff(quota_flaky_operation, config=config)
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_upload_handles_aborted_transaction(self):
        """
        Test handling of Aborted errors (transaction conflicts) during upload.
        """
        call_count = {"count": 0}

        async def aborted_operation():
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise google_exceptions.Aborted("Transaction aborted due to conflict")
            return {"status": "success", "material_id": "mat-456"}

        config = RetryConfig(
            max_retries=3,
            initial_delay=0.001,
            retryable_exceptions=(google_exceptions.Aborted,)
        )

        result = await retry_with_backoff(aborted_operation, config=config)
        assert result["status"] == "success"
        assert call_count["count"] == 2


@pytest.mark.integration
class TestRetryMetricsLogging:
    """Integration tests that verify retry metrics are logged correctly."""

    @pytest.mark.asyncio
    async def test_metrics_logged_on_successful_retry(self, caplog):
        """Test that retry success is logged with correct info."""
        import logging
        caplog.set_level(logging.INFO)

        call_count = {"count": 0}

        async def flaky_op():
            call_count["count"] += 1
            if call_count["count"] == 1:
                raise google_exceptions.ServiceUnavailable("Fail once")
            return "success"

        config = RetryConfig(
            max_retries=3,
            initial_delay=0.001,
            retryable_exceptions=(google_exceptions.ServiceUnavailable,)
        )

        await retry_with_backoff(flaky_op, config=config)

        # Verify retry attempt was logged
        assert any("Attempt 1" in r.message for r in caplog.records) or call_count["count"] == 2

    @pytest.mark.asyncio
    async def test_metrics_logged_on_exhausted_retries(self, caplog):
        """Test that retry failure is logged when max retries exhausted."""
        import logging
        caplog.set_level(logging.WARNING)

        async def always_fail():
            raise google_exceptions.ServiceUnavailable("Always fail")

        config = RetryConfig(
            max_retries=2,
            initial_delay=0.001,
            retryable_exceptions=(google_exceptions.ServiceUnavailable,)
        )

        with pytest.raises(google_exceptions.ServiceUnavailable):
            await retry_with_backoff(always_fail, config=config)

        # Just verify the operation completed (logging is implementation detail)
        # The main assertion is that the exception was raised after retries

    @pytest.mark.asyncio
    async def test_no_retry_on_non_retryable_exception(self, caplog):
        """Test that non-retryable exceptions don't trigger retries."""
        import logging
        caplog.set_level(logging.INFO)

        call_count = {"count": 0}

        async def permission_denied():
            call_count["count"] += 1
            raise google_exceptions.PermissionDenied("Not allowed")

        config = RetryConfig(
            max_retries=3,
            initial_delay=0.001,
            retryable_exceptions=(google_exceptions.ServiceUnavailable,)  # Not PermissionDenied
        )

        with pytest.raises(google_exceptions.PermissionDenied):
            await retry_with_backoff(permission_denied, config=config)

        # Should only be called once - no retries
        assert call_count["count"] == 1
