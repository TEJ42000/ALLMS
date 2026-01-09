"""Rate Limiting Service for Upload Operations.

Provides distributed rate limiting using Redis for production deployments.
Falls back to in-memory rate limiting for development/testing.

Environment Variables:
    RATE_LIMIT_BACKEND: 'redis' or 'memory' (default: 'memory')
    REDIS_HOST: Redis server host (default: 'localhost')
    REDIS_PORT: Redis server port (default: 6379)
    REDIS_PASSWORD: Redis password (optional)
    REDIS_DB: Redis database number (default: 0)
    REDIS_SSL: Use SSL for Redis connection (default: 'false')
"""

import logging
import os
import time
from collections import defaultdict
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Rate limit configuration
RATE_LIMIT_UPLOADS = int(os.getenv("RATE_LIMIT_UPLOADS", "10"))  # Max uploads per user per window
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))  # Window in seconds


class RateLimiter:
    """Base class for rate limiting implementations."""
    
    def check_rate_limit(self, user_id: str, client_ip: str) -> tuple[bool, Optional[str]]:
        """
        Check if request is within rate limit.
        
        Args:
            user_id: User identifier
            client_ip: Client IP address
            
        Returns:
            Tuple of (is_allowed, error_message)
        """
        raise NotImplementedError


class MemoryRateLimiter(RateLimiter):
    """In-memory rate limiter for development/testing.
    
    WARNING: Not suitable for production multi-instance deployments.
    """
    
    def __init__(self):
        self.store: Dict[str, List[float]] = defaultdict(list)
        logger.warning("Using in-memory rate limiter - NOT suitable for production!")
    
    def check_rate_limit(self, user_id: str, client_ip: str) -> tuple[bool, Optional[str]]:
        """Check rate limit using in-memory store."""
        key = f"{user_id}:{client_ip}"
        now = time.time()
        
        # Clean up old entries
        self.store[key] = [
            timestamp for timestamp in self.store[key]
            if now - timestamp < RATE_LIMIT_WINDOW
        ]
        
        # Check if limit exceeded
        if len(self.store[key]) >= RATE_LIMIT_UPLOADS:
            logger.warning(
                f"Rate limit exceeded for {key}",
                extra={
                    "event": "rate_limit_exceeded",
                    "user_id": user_id,
                    "client_ip": client_ip,
                    "current_count": len(self.store[key]),
                    "limit": RATE_LIMIT_UPLOADS,
                    "window_seconds": RATE_LIMIT_WINDOW,
                    "backend": "memory"
                }
            )
            return False, f"Rate limit exceeded. Maximum {RATE_LIMIT_UPLOADS} uploads per {RATE_LIMIT_WINDOW} seconds."
        
        # Add current request
        self.store[key].append(now)
        return True, None


class RedisRateLimiter(RateLimiter):
    """Redis-based distributed rate limiter for production.
    
    Uses Redis sorted sets for efficient rate limiting across multiple instances.
    """
    
    def __init__(self):
        try:
            import redis
            
            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            redis_password = os.getenv("REDIS_PASSWORD")
            redis_db = int(os.getenv("REDIS_DB", "0"))
            redis_ssl = os.getenv("REDIS_SSL", "false").lower() == "true"
            
            self.client = redis.Redis(
                host=redis_host,
                port=redis_port,
                password=redis_password,
                db=redis_db,
                ssl=redis_ssl,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            
            # Test connection
            self.client.ping()
            logger.info(f"Redis rate limiter connected to {redis_host}:{redis_port}")
            
        except ImportError:
            logger.error("Redis package not installed. Install with: pip install redis")
            raise
        except Exception as e:
            # ALERT: Redis connection failure (CRITICAL)
            logger.error(
                f"Failed to connect to Redis: {e}",
                exc_info=True,
                extra={
                    "alert": "redis_connection_failure",
                    "severity": "CRITICAL",
                    "redis_host": redis_host,
                    "redis_port": redis_port,
                    "error_type": type(e).__name__
                }
            )
            raise
    
    def check_rate_limit(self, user_id: str, client_ip: str) -> tuple[bool, Optional[str]]:
        """Check rate limit using Redis sorted set."""
        key = f"rate_limit:upload:{user_id}:{client_ip}"
        now = time.time()
        window_start = now - RATE_LIMIT_WINDOW
        
        try:
            # Use Redis pipeline for atomic operations
            pipe = self.client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current entries
            pipe.zcard(key)
            
            # Execute pipeline
            results = pipe.execute()
            current_count = results[1]
            
            # Check if limit exceeded
            if current_count >= RATE_LIMIT_UPLOADS:
                # ALERT: Rate limit hit (for capacity monitoring)
                logger.warning(
                    f"Rate limit exceeded for {key}",
                    extra={
                        "event": "rate_limit_exceeded",
                        "user_id": user_id,
                        "client_ip": client_ip,
                        "current_count": current_count,
                        "limit": RATE_LIMIT_UPLOADS,
                        "window_seconds": RATE_LIMIT_WINDOW
                    }
                )
                return False, f"Rate limit exceeded. Maximum {RATE_LIMIT_UPLOADS} uploads per {RATE_LIMIT_WINDOW} seconds."
            
            # Add current request
            self.client.zadd(key, {str(now): now})
            
            # Set expiry on key (cleanup)
            self.client.expire(key, RATE_LIMIT_WINDOW * 2)
            
            return True, None
            
        except Exception as e:
            # ALERT: Rate limiter backend failure (HIGH)
            logger.error(
                f"Redis rate limit check failed: {e}",
                exc_info=True,
                extra={
                    "alert": "rate_limiter_backend_failure",
                    "severity": "HIGH",
                    "user_id": user_id,
                    "client_ip": client_ip,
                    "error_type": type(e).__name__,
                    "fail_open": True
                }
            )
            # Fail open - allow request if Redis is down
            logger.warning(
                "Allowing request due to Redis failure (fail-open)",
                extra={
                    "user_id": user_id,
                    "client_ip": client_ip
                }
            )
            return True, None


# Singleton instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get the configured rate limiter instance (singleton)."""
    global _rate_limiter
    
    if _rate_limiter is not None:
        return _rate_limiter
    
    backend = os.getenv("RATE_LIMIT_BACKEND", "memory").lower()
    
    if backend == "redis":
        try:
            _rate_limiter = RedisRateLimiter()
            logger.info("Using Redis rate limiter (production mode)")
        except Exception as e:
            # ALERT: Redis initialization failure (HIGH)
            logger.error(
                f"Failed to initialize Redis rate limiter: {e}",
                exc_info=True,
                extra={
                    "alert": "redis_initialization_failure",
                    "severity": "HIGH",
                    "error_type": type(e).__name__,
                    "fallback": "memory"
                }
            )
            logger.warning(
                "Falling back to in-memory rate limiter",
                extra={"backend": "memory", "production_ready": False}
            )
            _rate_limiter = MemoryRateLimiter()
    else:
        _rate_limiter = MemoryRateLimiter()
        logger.info("Using in-memory rate limiter (development mode)")
    
    return _rate_limiter


def check_upload_rate_limit(user_id: str, client_ip: str) -> tuple[bool, Optional[str]]:
    """
    Check if upload request is within rate limit.

    Args:
        user_id: User identifier
        client_ip: Client IP address

    Returns:
        Tuple of (is_allowed, error_message)

    Example:
        is_allowed, error = check_upload_rate_limit("user123", "192.168.1.1")
        if not is_allowed:
            raise HTTPException(429, error)
    """
    limiter = get_rate_limiter()
    return limiter.check_rate_limit(user_id, client_ip)


def check_flashcard_rate_limit(
    user_id: str,
    client_ip: str,
    endpoint_type: str,
    max_requests: int,
    window_seconds: int
) -> tuple[bool, Optional[str]]:
    """
    Check if flashcard endpoint request is within rate limit.

    Args:
        user_id: User identifier
        client_ip: Client IP address
        endpoint_type: Type of endpoint (e.g., 'note_create', 'issue_create', 'note_list')
        max_requests: Maximum requests allowed in window
        window_seconds: Time window in seconds

    Returns:
        Tuple of (is_allowed, error_message)

    Example:
        is_allowed, error = check_flashcard_rate_limit(
            "user123", "192.168.1.1", "note_create", 10, 60
        )
        if not is_allowed:
            raise HTTPException(429, error)
    """
    limiter = get_rate_limiter()
    key = f"flashcard:{endpoint_type}:{user_id}:{client_ip}"
    now = time.time()

    # For in-memory limiter, we need to track separately
    if isinstance(limiter, MemoryRateLimiter):
        # Clean up old entries
        limiter.store[key] = [
            timestamp for timestamp in limiter.store[key]
            if now - timestamp < window_seconds
        ]

        # Check if limit exceeded
        if len(limiter.store[key]) >= max_requests:
            logger.warning(
                f"Flashcard rate limit exceeded for {key}",
                extra={
                    "event": "flashcard_rate_limit_exceeded",
                    "user_id": user_id,
                    "client_ip": client_ip,
                    "endpoint_type": endpoint_type,
                    "current_count": len(limiter.store[key]),
                    "limit": max_requests,
                    "window_seconds": window_seconds,
                    "backend": "memory"
                }
            )
            return False, f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds."

        # Add current request
        limiter.store[key].append(now)
        return True, None

    elif isinstance(limiter, RedisRateLimiter):
        # Use Redis for distributed rate limiting
        window_start = now - window_seconds

        try:
            pipe = limiter.client.pipeline()
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            results = pipe.execute()
            current_count = results[1]

            if current_count >= max_requests:
                logger.warning(
                    f"Flashcard rate limit exceeded for {key}",
                    extra={
                        "event": "flashcard_rate_limit_exceeded",
                        "user_id": user_id,
                        "client_ip": client_ip,
                        "endpoint_type": endpoint_type,
                        "current_count": current_count,
                        "limit": max_requests,
                        "window_seconds": window_seconds,
                        "backend": "redis"
                    }
                )
                return False, f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds."

            limiter.client.zadd(key, {str(now): now})
            limiter.client.expire(key, window_seconds * 2)
            return True, None

        except Exception as e:
            logger.error(
                f"Redis flashcard rate limit check failed: {e}",
                exc_info=True,
                extra={
                    "alert": "flashcard_rate_limiter_failure",
                    "severity": "HIGH",
                    "user_id": user_id,
                    "client_ip": client_ip,
                    "endpoint_type": endpoint_type,
                    "fail_open": True
                }
            )
            # Fail open - allow request if Redis is down
            return True, None

    # Fallback
    return True, None

