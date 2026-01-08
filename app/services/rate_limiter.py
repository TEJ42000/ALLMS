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
            logger.warning(f"Rate limit exceeded for {key}")
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
            logger.error(f"Failed to connect to Redis: {e}")
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
                logger.warning(f"Rate limit exceeded for {key}")
                return False, f"Rate limit exceeded. Maximum {RATE_LIMIT_UPLOADS} uploads per {RATE_LIMIT_WINDOW} seconds."
            
            # Add current request
            self.client.zadd(key, {str(now): now})
            
            # Set expiry on key (cleanup)
            self.client.expire(key, RATE_LIMIT_WINDOW * 2)
            
            return True, None
            
        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            # Fail open - allow request if Redis is down
            logger.warning("Allowing request due to Redis failure (fail-open)")
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
            logger.error(f"Failed to initialize Redis rate limiter: {e}")
            logger.warning("Falling back to in-memory rate limiter")
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

