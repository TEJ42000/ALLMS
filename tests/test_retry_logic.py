"""Tests for retry logic with exponential backoff.

Tests cover:
- Successful retry after transient failures
- Failure after max retries exhausted
- Exponential backoff timing
- Jitter behavior
- Exception type filtering
- Synchronous retry function
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch

from app.services.retry_logic import (
    retry_with_backoff,
    retry_sync,
    retry_on_network_error,
    RetryConfig
)


class TestRetryConfigValidation:
    """Tests for RetryConfig validation."""

    def test_valid_config(self):
        """Test that valid config is accepted."""
        config = RetryConfig(
            max_retries=5,
            initial_delay=1.0,
            max_delay=60.0,
            exponential_base=2.0,
            jitter=True
        )
        assert config.max_retries == 5

    def test_negative_max_retries(self):
        """Test that negative max_retries raises ValueError."""
        with pytest.raises(ValueError, match="max_retries must be >= 0"):
            RetryConfig(max_retries=-1)

    def test_negative_initial_delay(self):
        """Test that negative initial_delay raises ValueError."""
        with pytest.raises(ValueError, match="initial_delay must be >= 0"):
            RetryConfig(initial_delay=-1.0)

    def test_negative_max_delay(self):
        """Test that negative max_delay raises ValueError."""
        with pytest.raises(ValueError, match="max_delay must be >= 0"):
            RetryConfig(max_delay=-1.0)

    def test_max_delay_less_than_initial_delay(self):
        """Test that max_delay < initial_delay raises ValueError."""
        with pytest.raises(ValueError, match="max_delay .* must be >= initial_delay"):
            RetryConfig(initial_delay=10.0, max_delay=5.0)

    def test_zero_exponential_base(self):
        """Test that exponential_base <= 0 raises ValueError."""
        with pytest.raises(ValueError, match="exponential_base must be > 0"):
            RetryConfig(exponential_base=0)

    def test_negative_exponential_base(self):
        """Test that negative exponential_base raises ValueError."""
        with pytest.raises(ValueError, match="exponential_base must be > 0"):
            RetryConfig(exponential_base=-1.0)

    def test_retryable_exceptions_not_tuple(self):
        """Test that retryable_exceptions must be a tuple."""
        with pytest.raises(TypeError, match="retryable_exceptions must be a tuple"):
            RetryConfig(retryable_exceptions=[ValueError])

    def test_retryable_exceptions_invalid_type(self):
        """Test that retryable_exceptions must contain exception types."""
        with pytest.raises(TypeError, match="retryable_exceptions must contain exception types"):
            RetryConfig(retryable_exceptions=("not an exception",))

    def test_retryable_exceptions_valid(self):
        """Test that valid retryable_exceptions is accepted."""
        config = RetryConfig(
            retryable_exceptions=(ValueError, TypeError, ConnectionError)
        )
        assert config.retryable_exceptions == (ValueError, TypeError, ConnectionError)


class TestRetryWithBackoff:
    """Tests for async retry_with_backoff function."""

    @pytest.mark.asyncio
    async def test_success_on_first_attempt(self):
        """Test that successful function doesn't retry."""
        mock_func = AsyncMock(return_value="success")

        result = await retry_with_backoff(mock_func, "arg1", kwarg1="value1")

        assert result == "success"
        assert mock_func.call_count == 1
        mock_func.assert_called_once_with("arg1", kwarg1="value1")
    
    @pytest.mark.asyncio
    async def test_success_after_transient_failure(self):
        """Test successful retry after transient failure."""
        mock_func = AsyncMock(side_effect=[
            Exception("Transient error"),
            "success"
        ])
        
        result = await retry_with_backoff(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    @pytest.mark.asyncio
    async def test_failure_after_max_retries(self):
        """Test that function fails after max retries exhausted."""
        mock_func = AsyncMock(side_effect=Exception("Persistent error"))
        
        config = RetryConfig(max_retries=3)
        
        with pytest.raises(Exception, match="Persistent error"):
            await retry_with_backoff(mock_func, config=config)
        
        assert mock_func.call_count == 3
    
    @pytest.mark.asyncio
    async def test_exponential_backoff_timing(self):
        """Test that delays follow exponential backoff pattern using mocked sleep."""
        mock_func = AsyncMock(side_effect=[
            Exception("Error 1"),
            Exception("Error 2"),
            "success"
        ])

        config = RetryConfig(
            max_retries=3,
            initial_delay=1.0,
            exponential_base=2.0,
            jitter=False  # Disable jitter for predictable timing
        )

        # Track sleep calls
        sleep_calls = []

        async def mock_sleep(delay):
            sleep_calls.append(delay)

        with patch('asyncio.sleep', side_effect=mock_sleep):
            result = await retry_with_backoff(mock_func, config=config)

        # Verify result
        assert result == "success"
        assert mock_func.call_count == 3

        # Verify exponential backoff delays (without timing assertions)
        assert len(sleep_calls) == 2  # 2 retries = 2 sleeps
        assert sleep_calls[0] == 1.0  # First retry: initial_delay
        assert sleep_calls[1] == 2.0  # Second retry: initial_delay * exponential_base
    
    @pytest.mark.asyncio
    async def test_max_delay_cap(self):
        """Test that delay is capped at max_delay using mocked sleep."""
        mock_func = AsyncMock(side_effect=[
            Exception("Error 1"),
            Exception("Error 2"),
            Exception("Error 3"),
            "success"
        ])

        config = RetryConfig(
            max_retries=4,
            initial_delay=1.0,
            max_delay=2.0,  # Cap at 2.0s
            exponential_base=2.0,
            jitter=False
        )

        # Track sleep calls
        sleep_calls = []

        async def mock_sleep(delay):
            sleep_calls.append(delay)

        with patch('asyncio.sleep', side_effect=mock_sleep):
            result = await retry_with_backoff(mock_func, config=config)

        # Verify result
        assert result == "success"
        assert mock_func.call_count == 4

        # Verify delays are capped at max_delay
        assert len(sleep_calls) == 3  # 3 retries = 3 sleeps
        assert sleep_calls[0] == 1.0  # First retry: 1.0
        assert sleep_calls[1] == 2.0  # Second retry: 2.0 (capped from 2.0)
        assert sleep_calls[2] == 2.0  # Third retry: 2.0 (capped from 4.0)
    
    @pytest.mark.asyncio
    async def test_jitter_adds_randomness(self):
        """Test that jitter adds randomness to delays using mocked sleep."""
        mock_func = AsyncMock(side_effect=[
            Exception("Error"),
            "success"
        ])

        config = RetryConfig(
            max_retries=2,
            initial_delay=1.0,
            jitter=True
        )

        # Run multiple times and collect sleep delays
        all_sleep_calls = []
        for _ in range(5):
            mock_func.reset_mock()
            mock_func.side_effect = [Exception("Error"), "success"]

            sleep_calls = []

            async def mock_sleep(delay):
                sleep_calls.append(delay)

            with patch('asyncio.sleep', side_effect=mock_sleep):
                await retry_with_backoff(mock_func, config=config)

            all_sleep_calls.extend(sleep_calls)

        # With jitter, delays should vary (not all the same)
        unique_delays = set(all_sleep_calls)
        assert len(unique_delays) > 1, "Jitter should produce varying delays"

        # All delays should be within jitter range (0.75 to 1.25 for 1.0s ±25%)
        for delay in all_sleep_calls:
            assert 0.75 <= delay <= 1.25, f"Delay {delay:.3f}s outside jitter range [0.75, 1.25]"
    
    @pytest.mark.asyncio
    async def test_retryable_exceptions_filter(self):
        """Test that only specified exception types are retried."""
        mock_func = AsyncMock(side_effect=ValueError("Not retryable"))
        
        config = RetryConfig(
            max_retries=3,
            retryable_exceptions=(ConnectionError, TimeoutError)
        )
        
        # ValueError should not be retried
        with pytest.raises(ValueError, match="Not retryable"):
            await retry_with_backoff(mock_func, config=config)
        
        # Should fail immediately without retries
        assert mock_func.call_count == 1
    
    @pytest.mark.asyncio
    async def test_retryable_exceptions_allows_retry(self):
        """Test that specified exception types are retried."""
        mock_func = AsyncMock(side_effect=[
            ConnectionError("Network error"),
            "success"
        ])
        
        config = RetryConfig(
            max_retries=3,
            retryable_exceptions=(ConnectionError, TimeoutError)
        )
        
        result = await retry_with_backoff(mock_func, config=config)
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    @pytest.mark.asyncio
    async def test_logging_on_retry(self, caplog):
        """Test that retries are logged appropriately."""
        import logging
        caplog.set_level(logging.WARNING)
        
        mock_func = AsyncMock(side_effect=[
            Exception("Error 1"),
            Exception("Error 2"),
            "success"
        ])
        mock_func.__name__ = "test_function"
        
        config = RetryConfig(max_retries=3, initial_delay=0.01, jitter=False)
        
        await retry_with_backoff(mock_func, config=config)
        
        # Check that warnings were logged for retries
        assert "Attempt 1/3 failed" in caplog.text
        assert "Attempt 2/3 failed" in caplog.text
        assert "Retrying in" in caplog.text
    
    @pytest.mark.asyncio
    async def test_logging_on_final_failure(self, caplog):
        """Test that final failure is logged as error."""
        import logging
        caplog.set_level(logging.ERROR)
        
        mock_func = AsyncMock(side_effect=Exception("Persistent error"))
        mock_func.__name__ = "test_function"
        
        config = RetryConfig(max_retries=2, initial_delay=0.01)
        
        with pytest.raises(Exception):
            await retry_with_backoff(mock_func, config=config)
        
        # Check that error was logged
        assert "All 2 attempts failed" in caplog.text
        assert "Persistent error" in caplog.text


class TestRetrySyncFunction:
    """Tests for synchronous retry_sync function."""
    
    def test_success_on_first_attempt(self):
        """Test that successful function doesn't retry."""
        mock_func = Mock(return_value="success")
        
        result = retry_sync(mock_func, "arg1", kwarg1="value1")
        
        assert result == "success"
        assert mock_func.call_count == 1
        mock_func.assert_called_once_with("arg1", kwarg1="value1")
    
    def test_success_after_transient_failure(self):
        """Test successful retry after transient failure."""
        call_count = 0

        def mock_func():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Transient error")
            return "success"

        config = RetryConfig(initial_delay=0.01)
        result = retry_sync(mock_func, config=config)

        assert result == "success"
        assert call_count == 2
    
    def test_failure_after_max_retries(self):
        """Test that function fails after max retries exhausted."""
        call_count = 0

        def mock_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Persistent error")

        config = RetryConfig(max_retries=3, initial_delay=0.01)

        with pytest.raises(Exception, match="Persistent error"):
            retry_sync(mock_func, config=config)

        assert call_count == 3


class TestRetryOnNetworkError:
    """Tests for retry_on_network_error convenience function."""
    
    @pytest.mark.asyncio
    async def test_retries_connection_error(self):
        """Test that ConnectionError is retried."""
        mock_func = AsyncMock(side_effect=[
            ConnectionError("Network error"),
            "success"
        ])
        
        result = await retry_on_network_error(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    @pytest.mark.asyncio
    async def test_retries_timeout_error(self):
        """Test that TimeoutError is retried."""
        mock_func = AsyncMock(side_effect=[
            TimeoutError("Request timeout"),
            "success"
        ])
        
        result = await retry_on_network_error(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    @pytest.mark.asyncio
    async def test_does_not_retry_value_error(self):
        """Test that non-network errors are not retried."""
        mock_func = AsyncMock(side_effect=ValueError("Invalid input"))
        
        with pytest.raises(ValueError, match="Invalid input"):
            await retry_on_network_error(mock_func)
        
        # Should fail immediately without retries
        assert mock_func.call_count == 1
    
    @pytest.mark.asyncio
    async def test_uses_aggressive_config(self):
        """Test that retry_on_network_error uses 5 retries."""
        mock_func = AsyncMock(side_effect=[
            ConnectionError("Error 1"),
            ConnectionError("Error 2"),
            ConnectionError("Error 3"),
            ConnectionError("Error 4"),
            "success"
        ])
        
        result = await retry_on_network_error(mock_func)
        
        assert result == "success"
        assert mock_func.call_count == 5

