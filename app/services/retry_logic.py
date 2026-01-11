"""Retry Logic with Exponential Backoff.

Provides utilities for retrying operations with exponential backoff,
particularly useful for handling transient failures in background tasks.

Features:
- Configurable retry attempts
- Exponential backoff with jitter
- Maximum delay cap
- Comprehensive logging
- Exception type filtering

Usage:
    from app.services.retry_logic import retry_with_backoff, RetryConfig
    
    # Basic usage with defaults
    result = await retry_with_backoff(some_async_function, arg1, arg2)
    
    # Custom configuration
    config = RetryConfig(
        max_retries=5,
        initial_delay=2.0,
        max_delay=120.0,
        exponential_base=2.0,
        jitter=True
    )
    result = await retry_with_backoff(
        some_async_function,
        arg1,
        arg2,
        config=config
    )
"""

import asyncio
import logging
import random
from dataclasses import dataclass
from typing import Callable, Any, Optional, Type, Tuple

logger = logging.getLogger(__name__)


@dataclass
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay in seconds before first retry (default: 1.0)
        max_delay: Maximum delay in seconds between retries (default: 60.0)
        exponential_base: Base for exponential backoff calculation (default: 2.0)
        jitter: Whether to add random jitter to delays (default: True)
        retryable_exceptions: Tuple of exception types to retry (default: all exceptions)
    """
    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None

    def __post_init__(self):
        """Validate configuration parameters."""
        if self.max_retries < 0:
            raise ValueError(f"max_retries must be >= 0, got {self.max_retries}")

        if self.initial_delay < 0:
            raise ValueError(f"initial_delay must be >= 0, got {self.initial_delay}")

        if self.max_delay < 0:
            raise ValueError(f"max_delay must be >= 0, got {self.max_delay}")

        if self.max_delay < self.initial_delay:
            raise ValueError(
                f"max_delay ({self.max_delay}) must be >= initial_delay ({self.initial_delay})"
            )

        if self.exponential_base <= 0:
            raise ValueError(f"exponential_base must be > 0, got {self.exponential_base}")

        if self.retryable_exceptions is not None:
            if not isinstance(self.retryable_exceptions, tuple):
                raise TypeError(
                    f"retryable_exceptions must be a tuple, got {type(self.retryable_exceptions).__name__}"
                )

            for exc_type in self.retryable_exceptions:
                if not isinstance(exc_type, type) or not issubclass(exc_type, BaseException):
                    raise TypeError(
                        f"retryable_exceptions must contain exception types, got {exc_type}"
                    )


# =============================================================================
# Issue #218: Extracted Common Retry Logic
# =============================================================================
# The following helper functions reduce code duplication between retry_with_backoff
# and retry_sync by extracting shared logic for delay calculation, exception
# handling, and logging.


def _calculate_delay_with_jitter(delay: float, config: RetryConfig) -> float:
    """
    Calculate the actual delay with optional jitter.

    Args:
        delay: Base delay in seconds
        config: Retry configuration

    Returns:
        Actual delay with jitter applied (if enabled)
    """
    # Cap delay at max_delay before applying jitter
    delay = min(delay, config.max_delay)

    if config.jitter:
        # Add ±25% jitter to prevent thundering herd
        jitter_range = delay * 0.25
        actual_delay = delay + random.uniform(-jitter_range, jitter_range)
        return max(0.1, actual_delay)  # Ensure positive delay

    return delay


def _should_retry_exception(exception: Exception, config: RetryConfig) -> bool:
    """
    Check if an exception should be retried based on configuration.

    Args:
        exception: The exception that was raised
        config: Retry configuration

    Returns:
        True if the exception should be retried, False otherwise
    """
    if config.retryable_exceptions is None:
        return True
    return isinstance(exception, config.retryable_exceptions)


def _log_retry_attempt(
    func_name: str,
    attempt: int,
    max_retries: int,
    exception: Exception,
    delay: float
) -> None:
    """
    Log a retry attempt with structured metadata.

    Args:
        func_name: Name of the function being retried
        attempt: Current attempt number (1-based)
        max_retries: Maximum number of retries
        exception: The exception that triggered the retry
        delay: Delay before next retry
    """
    logger.warning(
        f"Attempt {attempt}/{max_retries} failed for {func_name}: "
        f"{type(exception).__name__}: {exception}. "
        f"Retrying in {delay:.2f}s...",
        extra={
            "function": func_name,
            "attempt": attempt,
            "max_retries": max_retries,
            "error_type": type(exception).__name__,
            "error_message": str(exception),
            "retry_delay": delay
        }
    )


def _log_all_retries_exhausted(
    func_name: str,
    max_retries: int,
    exception: Exception
) -> None:
    """
    Log when all retry attempts have been exhausted.

    Args:
        func_name: Name of the function that failed
        max_retries: Maximum number of retries attempted
        exception: The final exception
    """
    logger.error(
        f"All {max_retries} attempts failed for {func_name}. "
        f"Last error: {type(exception).__name__}: {exception}",
        exc_info=True,
        extra={
            "function": func_name,
            "max_retries": max_retries,
            "error_type": type(exception).__name__,
            "error_message": str(exception),
            "all_attempts_failed": True
        }
    )


def _log_non_retryable_exception(func_name: str, exception: Exception) -> None:
    """
    Log when a non-retryable exception is encountered.

    Args:
        func_name: Name of the function that failed
        exception: The non-retryable exception
    """
    logger.error(
        f"Non-retryable exception in {func_name}: {type(exception).__name__}: {exception}"
    )


async def retry_with_backoff(
    func: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> Any:
    """
    Execute an async function with exponential backoff retry.

    Retries the function on failure with exponentially increasing delays.
    Logs each attempt and the final result.

    Args:
        func: Async function to execute
        *args: Positional arguments to pass to func
        config: Retry configuration (uses defaults if None)
        **kwargs: Keyword arguments to pass to func

    Returns:
        The return value of func if successful

    Raises:
        The last exception encountered if all retries fail

    Example:
        async def flaky_api_call(user_id: str) -> dict:
            # May fail due to network issues
            return await api.get_user(user_id)

        # Retry with default config (3 attempts, 1s initial delay)
        user = await retry_with_backoff(flaky_api_call, "user123")

        # Custom config for critical operations
        config = RetryConfig(max_retries=5, initial_delay=2.0)
        user = await retry_with_backoff(flaky_api_call, "user123", config=config)
    """
    if config is None:
        config = RetryConfig()

    last_exception = None
    delay = config.initial_delay
    func_name = getattr(func, '__name__', repr(func))

    for attempt in range(config.max_retries):
        try:
            # Attempt to execute the function
            result = await func(*args, **kwargs)

            # Success!
            if attempt > 0:
                logger.info(
                    f"Function {func_name} succeeded on attempt {attempt + 1}/{config.max_retries}"
                )

            return result

        except Exception as e:
            last_exception = e

            # Issue #218: Use helper function for exception check
            if not _should_retry_exception(e, config):
                _log_non_retryable_exception(func_name, e)
                raise

            # Log the failure and retry or give up
            if attempt < config.max_retries - 1:
                # Issue #218: Use helper function for delay calculation
                actual_delay = _calculate_delay_with_jitter(delay, config)

                # Issue #218: Use helper function for logging
                _log_retry_attempt(func_name, attempt + 1, config.max_retries, e, actual_delay)

                # Wait before retrying
                await asyncio.sleep(actual_delay)

                # Calculate next delay (exponential backoff)
                delay = delay * config.exponential_base
            else:
                # Final attempt failed
                # Issue #218: Use helper function for logging
                _log_all_retries_exhausted(func_name, config.max_retries, e)

    # All retries exhausted, raise the last exception
    if last_exception is not None:
        raise last_exception
    else:
        # Should never happen, but handle gracefully
        raise RuntimeError(f"Function {func_name} failed with no exception recorded")


def retry_sync(
    func: Callable,
    *args,
    config: Optional[RetryConfig] = None,
    **kwargs
) -> Any:
    """
    Execute a synchronous function with exponential backoff retry.

    Similar to retry_with_backoff but for synchronous functions.
    Uses time.sleep instead of asyncio.sleep.

    Args:
        func: Synchronous function to execute
        *args: Positional arguments to pass to func
        config: Retry configuration (uses defaults if None)
        **kwargs: Keyword arguments to pass to func

    Returns:
        The return value of func if successful

    Raises:
        The last exception encountered if all retries fail

    Example:
        def flaky_database_query(query: str) -> list:
            # May fail due to connection issues
            return db.execute(query)

        results = retry_sync(flaky_database_query, "SELECT * FROM users")
    """
    import time

    if config is None:
        config = RetryConfig()

    last_exception = None
    delay = config.initial_delay
    func_name = getattr(func, '__name__', repr(func))

    for attempt in range(config.max_retries):
        try:
            # Attempt to execute the function
            result = func(*args, **kwargs)

            # Success!
            if attempt > 0:
                logger.info(
                    f"Function {func_name} succeeded on attempt {attempt + 1}/{config.max_retries}"
                )

            return result

        except Exception as e:
            last_exception = e

            # Issue #218: Use helper function for exception check
            if not _should_retry_exception(e, config):
                _log_non_retryable_exception(func_name, e)
                raise

            # Log the failure and retry or give up
            if attempt < config.max_retries - 1:
                # Issue #218: Use helper function for delay calculation
                actual_delay = _calculate_delay_with_jitter(delay, config)

                # Issue #218: Use helper function for logging
                _log_retry_attempt(func_name, attempt + 1, config.max_retries, e, actual_delay)

                # Wait before retrying (sync version uses time.sleep)
                time.sleep(actual_delay)

                # Calculate next delay (exponential backoff)
                delay = delay * config.exponential_base
            else:
                # Final attempt failed
                # Issue #218: Use helper function for logging
                _log_all_retries_exhausted(func_name, config.max_retries, e)
    
    # All retries exhausted
    if last_exception is not None:
        raise last_exception
    else:
        # Should never happen, but handle gracefully
        raise RuntimeError(f"Function {getattr(func, '__name__', repr(func))} failed with no exception recorded")


# Convenience function for common retry scenarios
async def retry_on_network_error(func: Callable, *args, **kwargs) -> Any:
    """
    Retry function on common network-related errors.
    
    Retries on:
    - ConnectionError
    - TimeoutError
    - OSError (network-related)
    
    Uses aggressive retry config (5 attempts, 2s initial delay).
    """
    config = RetryConfig(
        max_retries=5,
        initial_delay=2.0,
        max_delay=120.0,
        retryable_exceptions=(ConnectionError, TimeoutError, OSError)
    )
    return await retry_with_backoff(func, *args, config=config, **kwargs)

