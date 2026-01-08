# GDPR Rate Limiting Documentation

## Overview

This document describes the rate limiting implementation for GDPR endpoints in ALLMS, including current limitations and production recommendations.

## Current Implementation

### In-Memory Rate Limiting

**File:** `app/routes/gdpr.py`

The current implementation uses an in-memory dictionary to track rate limits:

```python
_rate_limit_storage: Dict[str, Dict[str, any]] = defaultdict(lambda: {"count": 0, "reset_time": datetime.utcnow()})
```

### Rate Limits

| Endpoint | Limit | Window | Purpose |
|----------|-------|--------|---------|
| `POST /api/gdpr/consent` | 100 requests | 1 hour | Prevent consent spam |
| `POST /api/gdpr/export` | 5 requests | 24 hours | Prevent data export abuse |
| `POST /api/gdpr/delete/request` | 3 requests | 24 hours | Prevent deletion request spam |
| `POST /api/gdpr/delete` | 3 requests | 24 hours | Prevent deletion attempt spam |

### Implementation Details

```python
def check_rate_limit(user_id: str, endpoint: str, max_requests: int = 10, window_minutes: int = 60) -> bool:
    """Check if user has exceeded rate limit for endpoint."""
    key = f"{user_id}:{endpoint}"
    now = datetime.utcnow()
    
    # Get or create rate limit entry
    limit_data = _rate_limit_storage[key]
    
    # Reset if window has passed
    if now >= limit_data["reset_time"]:
        limit_data["count"] = 0
        limit_data["reset_time"] = now + timedelta(minutes=window_minutes)
    
    # Check limit
    if limit_data["count"] >= max_requests:
        reset_in = (limit_data["reset_time"] - now).total_seconds()
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {int(reset_in)} seconds."
        )
    
    # Increment counter
    limit_data["count"] += 1
    return True
```

## Limitations

### ⚠️ Production Limitations

1. **Not Distributed**
   - Rate limits are per-server instance
   - Multiple instances = multiple independent rate limit counters
   - Users can bypass limits by hitting different servers

2. **Not Persistent**
   - Rate limits reset on server restart
   - No historical tracking
   - Cannot audit rate limit violations

3. **Memory Usage**
   - Grows unbounded with number of users
   - No automatic cleanup of old entries
   - Potential memory leak in high-traffic scenarios

4. **No Synchronization**
   - Race conditions possible in high-concurrency scenarios
   - Not thread-safe without additional locking

5. **Limited Observability**
   - No metrics on rate limit hits
   - Cannot monitor abuse patterns
   - No alerting on suspicious activity

## Production Recommendations

### Option 1: Redis-Based Rate Limiting (Recommended)

**Pros:**
- ✅ Distributed across all server instances
- ✅ Persistent across restarts
- ✅ Atomic operations (thread-safe)
- ✅ Automatic expiry (TTL)
- ✅ High performance
- ✅ Industry standard

**Implementation:**

```python
import redis
from datetime import datetime, timedelta

redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    db=0,
    decode_responses=True
)

def check_rate_limit_redis(user_id: str, endpoint: str, max_requests: int, window_minutes: int) -> bool:
    """Check rate limit using Redis."""
    key = f"rate_limit:{user_id}:{endpoint}"
    
    # Increment counter
    count = redis_client.incr(key)
    
    # Set expiry on first request
    if count == 1:
        redis_client.expire(key, window_minutes * 60)
    
    # Check limit
    if count > max_requests:
        ttl = redis_client.ttl(key)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Try again in {ttl} seconds."
        )
    
    return True
```

**Setup:**

```bash
# Docker Compose
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

# Environment Variables
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=<optional>
```

**See:** Issue #148 for implementation tracking

### Option 2: Database-Based Rate Limiting

**Pros:**
- ✅ No additional infrastructure
- ✅ Persistent
- ✅ Auditable

**Cons:**
- ❌ Slower than Redis
- ❌ More database load
- ❌ Requires cleanup jobs

**Implementation:**

```python
async def check_rate_limit_db(user_id: str, endpoint: str, max_requests: int, window_minutes: int):
    """Check rate limit using Firestore."""
    now = datetime.utcnow()
    window_start = now - timedelta(minutes=window_minutes)
    
    # Count requests in window
    requests_ref = db.collection('rate_limits').where('user_id', '==', user_id).where('endpoint', '==', endpoint).where('timestamp', '>=', window_start)
    
    count = len(list(requests_ref.stream()))
    
    if count >= max_requests:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    
    # Record this request
    db.collection('rate_limits').add({
        'user_id': user_id,
        'endpoint': endpoint,
        'timestamp': now
    })
```

### Option 3: Third-Party Service (e.g., Upstash)

**Pros:**
- ✅ Managed service
- ✅ No infrastructure to maintain
- ✅ Global distribution

**Cons:**
- ❌ Additional cost
- ❌ Vendor lock-in
- ❌ External dependency

## Migration Path

### Phase 1: Current (In-Memory)
- ✅ Implemented
- ⚠️ Development/staging only
- ⚠️ Not suitable for production

### Phase 2: Redis Implementation
- [ ] Add Redis to infrastructure
- [ ] Implement Redis-based rate limiting
- [ ] Add fallback to in-memory if Redis unavailable
- [ ] Add monitoring and alerting
- [ ] Deploy to production

### Phase 3: Enhanced Features
- [ ] Add rate limit metrics
- [ ] Implement adaptive rate limiting
- [ ] Add IP-based rate limiting
- [ ] Add abuse detection

## Monitoring

### Metrics to Track

1. **Rate Limit Hits**
   - Number of 429 responses per endpoint
   - Users hitting rate limits
   - Time of day patterns

2. **Usage Patterns**
   - Requests per user per endpoint
   - Peak usage times
   - Unusual activity

3. **System Health**
   - Redis connection status
   - Rate limit check latency
   - Error rates

### Alerting

Set up alerts for:
- High rate of 429 responses (potential attack)
- Redis connection failures
- Unusual spike in deletion requests
- Same user hitting limits repeatedly

## Security Considerations

### Current Risks

1. **Bypass via Multiple Instances**
   - Attacker can hit different server instances
   - Mitigation: Deploy Redis-based rate limiting

2. **No IP-Based Limiting**
   - Same IP can create multiple accounts
   - Mitigation: Add IP-based rate limiting

3. **No Abuse Detection**
   - Cannot detect coordinated attacks
   - Mitigation: Add pattern detection

### Recommendations

1. **Implement Redis Rate Limiting**
   - Priority: High
   - Timeline: Before production launch

2. **Add IP-Based Rate Limiting**
   - Priority: Medium
   - Limit requests per IP address

3. **Add Abuse Detection**
   - Priority: Medium
   - Detect suspicious patterns

4. **Add CAPTCHA for Sensitive Operations**
   - Priority: Low
   - For account deletion, add CAPTCHA

## Testing

### Current Tests

See `tests/test_gdpr_compliance.py`:
- Rate limit structure tests
- Basic rate limiting logic

### Additional Tests Needed

1. **Distributed Rate Limiting**
   - Test across multiple instances
   - Test Redis failover

2. **Concurrency Tests**
   - Test race conditions
   - Test high-concurrency scenarios

3. **Performance Tests**
   - Measure rate limit check latency
   - Test with high request volume

## Configuration

### Environment Variables

```bash
# Rate Limiting Backend
RATE_LIMIT_BACKEND=redis  # Options: memory, redis, database

# Redis Configuration (if using Redis)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=<optional>
REDIS_DB=0
REDIS_SSL=false

# Rate Limit Settings (optional overrides)
RATE_LIMIT_CONSENT_MAX=100
RATE_LIMIT_CONSENT_WINDOW=60
RATE_LIMIT_EXPORT_MAX=5
RATE_LIMIT_EXPORT_WINDOW=1440
RATE_LIMIT_DELETE_MAX=3
RATE_LIMIT_DELETE_WINDOW=1440
```

### Customization

Rate limits can be adjusted based on:
- User tier (free vs paid)
- Historical behavior (trusted users)
- Time of day (higher limits during business hours)
- Geographic location (different limits per region)

## Related Documentation

- [GDPR Implementation Guide](GDPR_IMPLEMENTATION.md)
- [Issue #148: Redis Rate Limiting](https://github.com/TEJ42000/ALLMS/issues/148)
- [PR #147: GDPR Compliance Phase 1](https://github.com/TEJ42000/ALLMS/pull/147)

## Support

For questions or issues:
- **Technical:** dev@allms.example.com
- **Security:** security@allms.example.com
- **Privacy:** privacy@allms.example.com

