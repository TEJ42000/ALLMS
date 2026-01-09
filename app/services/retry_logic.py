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
    
    for attempt in range(config.max_retries):
        try:
            # Attempt to execute the function
            result = await func(*args, **kwargs)
            
            # Success!
            if attempt > 0:
                logger.info(
                    f"Function {func.__name__} succeeded on attempt {attempt + 1}/{config.max_retries}"
                )
            
            return result
            
        except Exception as e:
            last_exception = e
            
            # Check if this exception type should be retried
            if config.retryable_exceptions is not None:
                if not isinstance(e, config.retryable_exceptions):
                    logger.error(
                        f"Non-retryable exception in {func.__name__}: {type(e).__name__}: {e}"
                    )
                    raise
            
            # Log the failure
            if attempt < config.max_retries - 1:
                # Cap delay at max_delay before applying jitter
                delay = min(delay, config.max_delay)

                # Calculate delay with optional jitter
                actual_delay = delay
                if config.jitter:
                    # Add ±25% jitter to prevent thundering herd
                    jitter_range = delay * 0.25
                    actual_delay = delay + random.uniform(-jitter_range, jitter_range)
                    actual_delay = max(0.1, actual_delay)  # Ensure positive delay

                func_name = getattr(func, '__name__', repr(func))
                logger.warning(
                    f"Attempt {attempt + 1}/{config.max_retries} failed for {func_name}: "
                    f"{type(e).__name__}: {e}. "
                    f"Retrying in {actual_delay:.2f}s..."
                )

                # Wait before retrying
                await asyncio.sleep(actual_delay)

                # Calculate next delay (exponential backoff)
                delay = delay * config.exponential_base
            else:
                # Final attempt failed
                func_name = getattr(func, '__name__', repr(func))
                logger.error(
                    f"All {config.max_retries} attempts failed for {func_name}. "
                    f"Last error: {type(e).__name__}: {e}",
                    exc_info=True
                )
    
    # All retries exhausted, raise the last exception
    raise last_exception


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
    
    for attempt in range(config.max_retries):
        try:
            # Attempt to execute the function
            result = func(*args, **kwargs)
            
            # Success!
            if attempt > 0:
                logger.info(
                    f"Function {func.__name__} succeeded on attempt {attempt + 1}/{config.max_retries}"
                )
            
            return result
            
        except Exception as e:
            last_exception = e
            
            # Check if this exception type should be retried
            if config.retryable_exceptions is not None:
                if not isinstance(e, config.retryable_exceptions):
                    logger.error(
                        f"Non-retryable exception in {func.__name__}: {type(e).__name__}: {e}"
                    )
                    raise
            
            # Log the failure
            if attempt < config.max_retries - 1:
                # Cap delay at max_delay before applying jitter
                delay = min(delay, config.max_delay)

                # Calculate delay with optional jitter
                actual_delay = delay
                if config.jitter:
                    # Add ±25% jitter
                    jitter_range = delay * 0.25
                    actual_delay = delay + random.uniform(-jitter_range, jitter_range)
                    actual_delay = max(0.1, actual_delay)

                func_name = getattr(func, '__name__', repr(func))
                logger.warning(
                    f"Attempt {attempt + 1}/{config.max_retries} failed for {func_name}: "
                    f"{type(e).__name__}: {e}. "
                    f"Retrying in {actual_delay:.2f}s..."
                )

                # Wait before retrying
                time.sleep(actual_delay)

                # Calculate next delay
                delay = delay * config.exponential_base
            else:
                # Final attempt failed
                func_name = getattr(func, '__name__', repr(func))
                logger.error(
                    f"All {config.max_retries} attempts failed for {func_name}. "
                    f"Last error: {type(e).__name__}: {e}",
                    exc_info=True
                )
    
    # All retries exhausted
    raise last_exception


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

