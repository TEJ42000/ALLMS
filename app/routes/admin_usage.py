"""Admin API Routes for LLM Usage Tracking.

Provides endpoints for viewing and exporting LLM usage statistics.
Includes dashboard analytics endpoints with caching.
Requires admin privileges (@mgms.eu domain).
"""

import csv
import io
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.dependencies.auth import require_mgms_domain
from app.models.auth_models import User
from app.models.usage_models import (
    UsageSummary,
    UserUsageSummary,
    LLMUsageRecord,
    COST_INPUT_PER_MILLION,
    COST_OUTPUT_PER_MILLION,
    COST_CACHE_READ_PER_MILLION,
    COST_CACHE_WRITE_PER_MILLION,
)
from app.services.usage_tracking_service import (
    get_usage_tracking_service,
    DEFAULT_QUERY_LIMIT,
    MAX_QUERY_LIMIT,
    MAX_EXPORT_RECORDS,
)

logger = logging.getLogger(__name__)

# =============================================================================
# Helper Functions
# =============================================================================


def calculate_cache_metrics(
    total_input: int,
    total_cache_reads: int,
    total_cache_writes: int,
) -> Dict[str, float]:
    """
    Calculate cache efficiency metrics.

    Args:
        total_input: Total input tokens (non-cached)
        total_cache_reads: Total tokens read from cache
        total_cache_writes: Total tokens written to cache

    Returns:
        Dictionary with cache_hit_rate, cache_savings, cache_overhead, net_benefit
    """
    # Cache hit rate: percentage of input that came from cache
    total_potential_input = total_input + total_cache_reads
    cache_hit_rate = (
        (total_cache_reads / total_potential_input * 100)
        if total_potential_input > 0
        else 0.0
    )

    # Cache cost savings: difference between cache read cost and regular input cost
    # Cache read: $0.30/M tokens, Regular input: $3.00/M tokens
    cache_savings = (total_cache_reads / 1_000_000) * (
        COST_INPUT_PER_MILLION - COST_CACHE_READ_PER_MILLION
    )

    # Cache write overhead: extra cost for writing to cache vs regular input
    # Cache write: $3.75/M tokens, Regular input: $3.00/M tokens
    cache_overhead = (total_cache_writes / 1_000_000) * (
        COST_CACHE_WRITE_PER_MILLION - COST_INPUT_PER_MILLION
    )

    # Net benefit: savings minus overhead
    net_benefit = cache_savings - cache_overhead

    return {
        "cache_hit_rate": round(cache_hit_rate, 2),
        "cache_savings": round(cache_savings, 4),
        "cache_overhead": round(cache_overhead, 4),
        "net_benefit": round(net_benefit, 4),
    }


# =============================================================================
# Query Parameter Constants
# =============================================================================

DEFAULT_DAYS = 30
MAX_DAYS = 365
DEFAULT_RECORDS_DAYS = 7
MAX_RECORDS_DAYS = 90
DEFAULT_TOP_USERS_LIMIT = 10
MIN_TOP_USERS_LIMIT = 5
MAX_TOP_USERS_LIMIT = 50


# =============================================================================
# Helper Functions
# =============================================================================

def sanitize_csv_field(value: str) -> str:
    """Sanitize a field value for CSV export to prevent CSV injection attacks.

    CSV injection occurs when a field starts with special characters like:
    =, +, -, @, which can be interpreted as formulas by spreadsheet applications.

    This function:
    1. Converts value to string
    2. Strips leading/trailing whitespace
    3. Prepends a single quote (') if the value starts with a dangerous character
    4. This forces spreadsheet apps to treat it as text, not a formula

    Args:
        value: The field value to sanitize

    Returns:
        Sanitized string safe for CSV export

    Example:
        >>> sanitize_csv_field("=SUM(A1:A10)")
        "'=SUM(A1:A10)"
        >>> sanitize_csv_field("normal text")
        "normal text"
    """
    if value is None:
        return ""

    str_value = str(value).strip()

    # Check if value starts with dangerous characters
    dangerous_chars = ("=", "+", "-", "@", "\t", "\r")
    if str_value and str_value[0] in dangerous_chars:
        # Prepend single quote to force text interpretation
        return f"'{str_value}"

    return str_value


# ============================================================================
# Response Models for Dashboard Endpoints
# ============================================================================

class GranularityEnum(str, Enum):
    """Time granularity options for time series data."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


class MetricEnum(str, Enum):
    """Metric types for time series data."""
    COST = "cost"
    REQUESTS = "requests"
    TOKENS = "tokens"


class TimeSeriesBucket(BaseModel):
    """Single data point in time series."""
    bucket: str  # ISO date/datetime string
    value: float  # Cost, count, or tokens depending on metric
    count: int  # Number of requests in this bucket


class TokenBreakdownBucket(BaseModel):
    """Token breakdown for a single time bucket."""
    bucket: str  # ISO date/datetime string
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    count: int  # Number of requests in this bucket


class TimeSeriesResponse(BaseModel):
    """Response for time series endpoint."""
    data: List[TimeSeriesBucket]
    granularity: str
    metric: str
    total: float
    start_date: str
    end_date: str


class TokenBreakdownResponse(BaseModel):
    """Response for token breakdown time series."""
    data: List[TokenBreakdownBucket]
    granularity: str
    start_date: str
    end_date: str
    totals: Dict[str, int]  # Total tokens by type


class TopUserItem(BaseModel):
    """Single user in top users list."""
    email: str
    total_cost: float
    total_requests: int
    total_tokens: int
    avg_cost_per_request: float


class TopUsersResponse(BaseModel):
    """Response for top users endpoint."""
    users: List[TopUserItem]
    period: Dict[str, str]
    sort_by: str


class BreakdownItem(BaseModel):
    """Single item in breakdown response."""
    label: str
    cost: float
    requests: int
    tokens: int
    percentage: float


class BreakdownResponse(BaseModel):
    """Response for breakdown endpoint."""
    breakdown: List[BreakdownItem]
    dimension: str
    total_cost: float
    total_requests: int


class CacheAnalytics(BaseModel):
    """Detailed cache analytics."""
    cache_hit_rate: float  # Percentage
    total_cache_reads: int
    total_cache_writes: int
    total_input_tokens: int
    cache_cost_savings: float  # USD saved
    cache_write_overhead: float  # Extra cost for writing to cache
    net_cache_benefit: float  # Savings minus overhead
    operations_using_cache: int  # Number of operations that used cache
    total_operations: int


class DashboardKPIs(BaseModel):
    """Key performance indicators for dashboard."""
    total_requests: int
    total_cost: float
    unique_users: int
    avg_cost_per_request: float
    total_input_tokens: int
    total_output_tokens: int
    total_cache_creation_tokens: int
    total_cache_read_tokens: int
    cache_hit_rate: float  # Percentage of tokens from cache
    cache_cost_savings: float  # Cost saved by using cache reads vs regular input
    period_days: int

router = APIRouter(
    prefix="/api/admin/usage",
    tags=["Admin - Usage Tracking"],
    dependencies=[Depends(require_mgms_domain)],
)


@router.get("/summary", response_model=UsageSummary)
async def get_usage_summary(
    days: int = Query(DEFAULT_DAYS, ge=1, le=MAX_DAYS, description="Number of days to include"),
    user: User = Depends(require_mgms_domain),
):
    """
    Get aggregated LLM usage summary.

    Returns totals and breakdowns by operation type, user, and model.
    """
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        service = get_usage_tracking_service()
        summary = await service.get_usage_summary(
            start_date=start_date,
            end_date=end_date,
        )

        logger.info(
            "Usage summary requested by %s for last %d days",
            user.email, days
        )

        return summary

    except Exception as e:
        logger.error("Error getting usage summary: %s", e)
        raise HTTPException(500, detail=str(e)) from e


@router.get("/users/{email}", response_model=UserUsageSummary)
async def get_user_usage(
    email: str,
    days: int = Query(DEFAULT_DAYS, ge=1, le=MAX_DAYS, description="Number of days to include"),
    user: User = Depends(require_mgms_domain),
):
    """
    Get LLM usage summary for a specific user.
    """
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        service = get_usage_tracking_service()
        summary = await service.get_user_summary(
            user_email=email.lower(),
            start_date=start_date,
            end_date=end_date,
        )

        if not summary:
            raise HTTPException(404, detail=f"No usage data found for {email}")

        logger.info(
            "User usage requested by %s for %s (last %d days)",
            user.email, email, days
        )

        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting user usage: %s", e)
        raise HTTPException(500, detail=str(e)) from e


@router.get("/records")
async def list_usage_records(
    days: int = Query(DEFAULT_RECORDS_DAYS, ge=1, le=MAX_RECORDS_DAYS, description="Number of days to include"),
    limit: int = Query(DEFAULT_QUERY_LIMIT, ge=1, le=MAX_QUERY_LIMIT, description="Max records to return"),
    user: User = Depends(require_mgms_domain),
):
    """
    List individual LLM usage records.
    """
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        service = get_usage_tracking_service()
        records = await service.get_all_usage(
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

        return {
            "records": [r.model_dump() for r in records],
            "count": len(records),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        }

    except Exception as e:
        logger.error("Error listing usage records: %s", e)
        raise HTTPException(500, detail=str(e)) from e


@router.delete("/users/{email}")
async def delete_user_records(
    email: str,
    days: int = Query(
        None,
        ge=1,
        le=365,
        description="Only delete records from the last N days (optional)",
    ),
    confirm: str = Query(
        ...,
        description="Must be 'DELETE' to confirm deletion",
    ),
    user: User = Depends(require_mgms_domain),
):
    """
    Delete all LLM usage records for a specific user.

    **⚠️ WARNING: This is a destructive operation that cannot be undone!**

    Query Parameters:
    - email: User email to delete records for
    - days: Optional - only delete records from the last N days
    - confirm: Must be exactly "DELETE" to proceed

    Returns statistics about deleted records.
    """
    # Require explicit confirmation
    if confirm != "DELETE":
        raise HTTPException(
            400,
            detail="Confirmation required. Set confirm='DELETE' to proceed.",
        )

    # Prevent accidental deletion of all admin users
    if email.lower().endswith("@mgms.eu") and email.lower() != "dev@mgms.eu":
        raise HTTPException(
            403,
            detail="Cannot delete records for @mgms.eu users (except dev@mgms.eu). "
            "This is a safety measure.",
        )

    try:
        # Calculate date range if days specified
        start_date = None
        end_date = None
        if days:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)

        service = get_usage_tracking_service()
        result = await service.delete_user_records(
            user_email=email.lower(),
            start_date=start_date,
            end_date=end_date,
        )

        if not result["success"]:
            raise HTTPException(500, detail=result.get("error", "Unknown error"))

        logger.warning(
            "User %s deleted %d records for %s (cost: $%.2f)",
            user.email,
            result["deleted_count"],
            email,
            result.get("total_cost_deleted", 0),
        )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error deleting user records: %s", e)
        raise HTTPException(500, detail=str(e)) from e


@router.get("/export")
async def export_usage_csv(
    days: int = Query(DEFAULT_DAYS, ge=1, le=MAX_DAYS, description="Number of days to include"),
    user: User = Depends(require_mgms_domain),
):
    """
    Export LLM usage data as CSV.
    """
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        service = get_usage_tracking_service()
        records = await service.get_all_usage(
            start_date=start_date,
            end_date=end_date,
            limit=MAX_EXPORT_RECORDS,
        )

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "timestamp", "user_email", "model", "operation_type",
            "input_tokens", "output_tokens", "cache_creation_tokens",
            "cache_read_tokens", "estimated_cost_usd", "course_id"
        ])

        for record in records:
            writer.writerow([
                sanitize_csv_field(record.timestamp.isoformat()),
                sanitize_csv_field(record.user_email),
                sanitize_csv_field(record.model),
                sanitize_csv_field(record.operation_type),
                record.input_tokens,  # Numbers don't need sanitization
                record.output_tokens,
                record.cache_creation_tokens,
                record.cache_read_tokens,
                record.estimated_cost_usd,
                sanitize_csv_field(record.course_id or ""),
            ])

        output.seek(0)
        filename = f"llm_usage_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.csv"

        logger.info("Usage export requested by %s for last %d days", user.email, days)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except Exception as e:
        logger.error("Error exporting usage: %s", e)
        raise HTTPException(500, detail=str(e)) from e


# ============================================================================
# Dashboard Analytics Endpoints
# ============================================================================

@router.get("/dashboard/kpis", response_model=DashboardKPIs)
async def get_dashboard_kpis(
    days: int = Query(DEFAULT_DAYS, ge=1, le=MAX_DAYS, description="Number of days to include"),
    user: User = Depends(require_mgms_domain),
):
    """
    Get key performance indicators for the dashboard.

    Returns aggregated metrics for the specified time period.
    """
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        service = get_usage_tracking_service()
        records = await service.get_all_usage(
            start_date=start_date,
            end_date=end_date,
            limit=MAX_EXPORT_RECORDS,
        )

        # Calculate KPIs
        total_cost = sum(r.estimated_cost_usd for r in records)
        total_requests = len(records)
        unique_users = len(set(r.user_email for r in records))
        total_input = sum(r.input_tokens for r in records)
        total_output = sum(r.output_tokens for r in records)
        total_cache_creation = sum(r.cache_creation_tokens for r in records)
        total_cache_read = sum(r.cache_read_tokens for r in records)
        avg_cost = total_cost / total_requests if total_requests > 0 else 0.0

        # Calculate cache metrics using helper function
        cache_metrics = calculate_cache_metrics(
            total_input=total_input,
            total_cache_reads=total_cache_read,
            total_cache_writes=total_cache_creation,
        )

        return DashboardKPIs(
            total_requests=total_requests,
            total_cost=round(total_cost, 4),
            unique_users=unique_users,
            avg_cost_per_request=round(avg_cost, 6),
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_cache_creation_tokens=total_cache_creation,
            total_cache_read_tokens=total_cache_read,
            cache_hit_rate=cache_metrics["cache_hit_rate"],
            cache_cost_savings=cache_metrics["cache_savings"],
            period_days=days,
        )

    except Exception as e:
        logger.error("Error getting dashboard KPIs: %s", e)
        raise HTTPException(500, detail=str(e)) from e


@router.get("/timeseries", response_model=TimeSeriesResponse)
async def get_usage_timeseries(
    start_date: str = Query(..., description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (ISO format: YYYY-MM-DD)"),
    granularity: GranularityEnum = Query(GranularityEnum.DAILY, description="Time granularity"),
    metric: MetricEnum = Query(MetricEnum.COST, description="Metric to aggregate"),
    user: User = Depends(require_mgms_domain),
):
    """
    Get time-bucketed usage data for charts.

    Returns usage data aggregated by the specified time granularity.
    """
    try:
        # Parse dates
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)

        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)
        # Include the full end day
        end_dt = end_dt.replace(hour=23, minute=59, second=59)

        service = get_usage_tracking_service()
        records = await service.get_all_usage(
            start_date=start_dt,
            end_date=end_dt,
            limit=MAX_EXPORT_RECORDS,
        )

        # Bucket records by time
        buckets: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"value": 0.0, "count": 0, "tokens": 0}
        )

        for record in records:
            bucket_key = _get_bucket_key(record.timestamp, granularity)
            buckets[bucket_key]["count"] += 1
            buckets[bucket_key]["tokens"] += record.input_tokens + record.output_tokens
            buckets[bucket_key]["value"] += (
                record.estimated_cost_usd if metric == MetricEnum.COST
                else 1 if metric == MetricEnum.REQUESTS
                else record.input_tokens + record.output_tokens
            )

        # Convert to sorted list
        data = [
            TimeSeriesBucket(
                bucket=key,
                value=round(val["value"], 6) if metric == MetricEnum.COST else val["value"],
                count=val["count"],
            )
            for key, val in sorted(buckets.items())
        ]

        total = sum(b.value for b in data)

        return TimeSeriesResponse(
            data=data,
            granularity=granularity.value,
            metric=metric.value,
            total=round(total, 6) if metric == MetricEnum.COST else total,
            start_date=start_date,
            end_date=end_date,
        )

    except ValueError as e:
        raise HTTPException(400, detail=f"Invalid date format: {e}") from e
    except Exception as e:
        logger.error("Error getting time series: %s", e)
        raise HTTPException(500, detail=str(e)) from e


@router.get("/token-breakdown", response_model=TokenBreakdownResponse)
async def get_token_breakdown_timeseries(
    start_date: str = Query(..., description="Start date (ISO format: YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (ISO format: YYYY-MM-DD)"),
    granularity: GranularityEnum = Query(GranularityEnum.DAILY, description="Time granularity"),
    user: User = Depends(require_mgms_domain),
):
    """
    Get token breakdown over time (input, output, cache creation, cache read).

    Returns token usage broken down by type for each time bucket.
    """
    try:
        # Parse dates
        start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
        if start_dt.tzinfo is None:
            start_dt = start_dt.replace(tzinfo=timezone.utc)

        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        if end_dt.tzinfo is None:
            end_dt = end_dt.replace(tzinfo=timezone.utc)
        # Include the full end day
        end_dt = end_dt.replace(hour=23, minute=59, second=59)

        service = get_usage_tracking_service()
        records = await service.get_all_usage(
            start_date=start_dt,
            end_date=end_dt,
            limit=MAX_EXPORT_RECORDS,
        )

        # Bucket records by time
        buckets: Dict[str, Dict[str, int]] = defaultdict(
            lambda: {
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_creation_tokens": 0,
                "cache_read_tokens": 0,
                "count": 0
            }
        )

        for record in records:
            bucket_key = _get_bucket_key(record.timestamp, granularity)
            buckets[bucket_key]["input_tokens"] += record.input_tokens
            buckets[bucket_key]["output_tokens"] += record.output_tokens
            buckets[bucket_key]["cache_creation_tokens"] += record.cache_creation_tokens
            buckets[bucket_key]["cache_read_tokens"] += record.cache_read_tokens
            buckets[bucket_key]["count"] += 1

        # Convert to sorted list
        data = [
            TokenBreakdownBucket(
                bucket=key,
                input_tokens=val["input_tokens"],
                output_tokens=val["output_tokens"],
                cache_creation_tokens=val["cache_creation_tokens"],
                cache_read_tokens=val["cache_read_tokens"],
                count=val["count"],
            )
            for key, val in sorted(buckets.items())
        ]

        # Calculate totals
        totals = {
            "input_tokens": sum(b.input_tokens for b in data),
            "output_tokens": sum(b.output_tokens for b in data),
            "cache_creation_tokens": sum(b.cache_creation_tokens for b in data),
            "cache_read_tokens": sum(b.cache_read_tokens for b in data),
        }

        return TokenBreakdownResponse(
            data=data,
            granularity=granularity.value,
            start_date=start_date,
            end_date=end_date,
            totals=totals,
        )

    except ValueError as e:
        raise HTTPException(400, detail=f"Invalid date format: {e}") from e
    except Exception as e:
        logger.error("Error getting token breakdown: %s", e)
        raise HTTPException(500, detail=str(e)) from e


def _get_bucket_key(timestamp: datetime, granularity: GranularityEnum) -> str:
    """Get bucket key for a timestamp based on granularity."""
    if granularity == GranularityEnum.HOURLY:
        return timestamp.strftime("%Y-%m-%dT%H:00:00")
    elif granularity == GranularityEnum.DAILY:
        return timestamp.strftime("%Y-%m-%d")
    elif granularity == GranularityEnum.WEEKLY:
        # Get the Monday of the week
        monday = timestamp - timedelta(days=timestamp.weekday())
        return monday.strftime("%Y-%m-%d")
    elif granularity == GranularityEnum.MONTHLY:
        return timestamp.strftime("%Y-%m")
    return timestamp.strftime("%Y-%m-%d")


@router.get("/top-users", response_model=TopUsersResponse)
async def get_top_users(
    days: int = Query(DEFAULT_DAYS, ge=1, le=MAX_DAYS, description="Number of days to include"),
    limit: int = Query(DEFAULT_TOP_USERS_LIMIT, ge=MIN_TOP_USERS_LIMIT, le=MAX_TOP_USERS_LIMIT, description="Number of top users to return"),
    sort_by: str = Query("cost", description="Sort by: cost, requests, or tokens"),
    user: User = Depends(require_mgms_domain),
):
    """
    Get ranked list of users by cost/usage.

    Returns top N users sorted by the specified metric.
    """
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        service = get_usage_tracking_service()
        records = await service.get_all_usage(
            start_date=start_date,
            end_date=end_date,
            limit=MAX_EXPORT_RECORDS,
        )

        # Aggregate by user
        user_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"cost": 0.0, "requests": 0, "tokens": 0}
        )

        for record in records:
            user_stats[record.user_email]["cost"] += record.estimated_cost_usd
            user_stats[record.user_email]["requests"] += 1
            user_stats[record.user_email]["tokens"] += (
                record.input_tokens + record.output_tokens
            )

        # Sort and limit
        sort_key = "cost" if sort_by not in ["cost", "requests", "tokens"] else sort_by
        sorted_users = sorted(
            user_stats.items(),
            key=lambda x: x[1][sort_key],
            reverse=True
        )[:limit]

        users = [
            TopUserItem(
                email=email,
                total_cost=round(stats["cost"], 6),
                total_requests=stats["requests"],
                total_tokens=stats["tokens"],
                avg_cost_per_request=round(
                    stats["cost"] / stats["requests"] if stats["requests"] > 0 else 0,
                    6
                ),
            )
            for email, stats in sorted_users
        ]

        return TopUsersResponse(
            users=users,
            period={
                "start": start_date.strftime("%Y-%m-%d"),
                "end": end_date.strftime("%Y-%m-%d"),
            },
            sort_by=sort_key,
        )

    except Exception as e:
        logger.error("Error getting top users: %s", e)
        raise HTTPException(500, detail=str(e)) from e


@router.get("/breakdown", response_model=BreakdownResponse)
async def get_usage_breakdown(
    days: int = Query(DEFAULT_DAYS, ge=1, le=MAX_DAYS, description="Number of days to include"),
    dimension: str = Query("operation_type", description="Dimension: operation_type, model, course_id"),
    user: User = Depends(require_mgms_domain),
):
    """
    Get usage breakdown by dimension.

    Returns usage aggregated by operation type, model, or course.
    """
    try:
        if dimension not in ["operation_type", "model", "course_id"]:
            raise HTTPException(400, detail="Invalid dimension. Use: operation_type, model, course_id")

        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        service = get_usage_tracking_service()
        records = await service.get_all_usage(
            start_date=start_date,
            end_date=end_date,
            limit=MAX_EXPORT_RECORDS,
        )

        # Aggregate by dimension
        breakdown_stats: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"cost": 0.0, "requests": 0, "tokens": 0}
        )

        for record in records:
            label = getattr(record, dimension) or "(none)"
            breakdown_stats[label]["cost"] += record.estimated_cost_usd
            breakdown_stats[label]["requests"] += 1
            breakdown_stats[label]["tokens"] += record.input_tokens + record.output_tokens

        # Calculate totals and percentages
        total_cost = sum(s["cost"] for s in breakdown_stats.values())
        total_requests = sum(s["requests"] for s in breakdown_stats.values())

        breakdown = [
            BreakdownItem(
                label=label,
                cost=round(stats["cost"], 6),
                requests=stats["requests"],
                tokens=stats["tokens"],
                percentage=round(
                    (stats["cost"] / total_cost * 100) if total_cost > 0 else 0,
                    2
                ),
            )
            for label, stats in sorted(
                breakdown_stats.items(),
                key=lambda x: x[1]["cost"],
                reverse=True
            )
        ]

        return BreakdownResponse(
            breakdown=breakdown,
            dimension=dimension,
            total_cost=round(total_cost, 6),
            total_requests=total_requests,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error getting breakdown: %s", e)
        raise HTTPException(500, detail=str(e)) from e


@router.get("/cache-analytics", response_model=CacheAnalytics)
async def get_cache_analytics(
    days: int = Query(DEFAULT_DAYS, ge=1, le=MAX_DAYS, description="Number of days to include"),
    user: User = Depends(require_mgms_domain),
):
    """
    Get detailed cache analytics and efficiency metrics.

    Returns comprehensive cache usage statistics including hit rates,
    cost savings, and efficiency metrics.
    """
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        service = get_usage_tracking_service()
        records = await service.get_all_usage(
            start_date=start_date,
            end_date=end_date,
            limit=MAX_EXPORT_RECORDS,
        )

        # Calculate cache metrics
        total_input = sum(r.input_tokens for r in records)
        total_cache_reads = sum(r.cache_read_tokens for r in records)
        total_cache_writes = sum(r.cache_creation_tokens for r in records)

        # Use helper function for cache calculations
        cache_metrics = calculate_cache_metrics(
            total_input=total_input,
            total_cache_reads=total_cache_reads,
            total_cache_writes=total_cache_writes,
        )

        # Count operations using cache
        operations_with_cache = sum(
            1 for r in records if r.cache_read_tokens > 0 or r.cache_creation_tokens > 0
        )

        return CacheAnalytics(
            cache_hit_rate=cache_metrics["cache_hit_rate"],
            total_cache_reads=total_cache_reads,
            total_cache_writes=total_cache_writes,
            total_input_tokens=total_input,
            cache_cost_savings=cache_metrics["cache_savings"],
            cache_write_overhead=cache_metrics["cache_overhead"],
            net_cache_benefit=cache_metrics["net_benefit"],
            operations_using_cache=operations_with_cache,
            total_operations=len(records),
        )

    except Exception as e:
        logger.error("Error getting cache analytics: %s", e)
        raise HTTPException(500, detail=str(e)) from e


# =============================================================================
# Anthropic Cross-Reference Endpoints
# =============================================================================


class AnthropicUsageData(BaseModel):
    """Usage data from Anthropic Admin API."""
    total_input_tokens: int
    total_output_tokens: int
    total_cache_creation_tokens: int
    total_cache_read_tokens: int
    total_requests: int
    start_date: str
    end_date: str


class AnthropicCostData(BaseModel):
    """Cost data from Anthropic Admin API."""
    total_cost_usd: float
    start_date: str
    end_date: str


class ReconciliationReport(BaseModel):
    """Comparison between internal tracking and Anthropic's data."""
    internal_usage: Dict[str, int]
    anthropic_usage: Dict[str, int]
    internal_cost: float
    anthropic_cost: float
    variance_tokens: Dict[str, int]
    variance_cost: float
    variance_cost_percent: float
    match_status: str  # "exact", "close", "mismatch"
    start_date: str
    end_date: str


@router.get(
    "/anthropic/usage",
    response_model=AnthropicUsageData,
    summary="Get usage data from Anthropic Admin API",
    description="Fetch actual usage data from Anthropic for cross-reference",
)
async def get_anthropic_usage(
    days: int = Query(7, ge=1, le=365, description="Number of days to query"),
    _user: User = Depends(require_mgms_domain),
):
    """Get usage data from Anthropic Admin API.

    Requires Admin API key stored in Secret Manager as 'anthropic-admin-api-key'.
    """
    try:
        from app.services.anthropic_usage_api import get_anthropic_usage_client

        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        # Fetch from Anthropic
        client = get_anthropic_usage_client()
        report = await client.fetch_usage_report(
            start_date=start_date,
            end_date=end_date,
            bucket_width="1d",
        )

        return AnthropicUsageData(
            total_input_tokens=report.totals["input_tokens"],
            total_output_tokens=report.totals["output_tokens"],
            total_cache_creation_tokens=report.totals["cache_creation_tokens"],
            total_cache_read_tokens=report.totals["cache_read_tokens"],
            total_requests=sum(b.count for b in report.data),
            start_date=report.start_date,
            end_date=report.end_date,
        )

    except ValueError as e:
        # Admin API key not configured
        logger.error("Admin API key not configured: %s", e)
        raise HTTPException(
            503,
            detail="Anthropic Admin API not configured. Please add 'anthropic-admin-api-key' to Secret Manager."
        ) from e
    except Exception as e:
        logger.error("Error fetching Anthropic usage: %s", e, exc_info=True)
        raise HTTPException(500, detail=f"Error fetching Anthropic usage: {str(e)}") from e


@router.get(
    "/anthropic/cost",
    response_model=AnthropicCostData,
    summary="Get cost data from Anthropic Admin API",
    description="Fetch actual cost data from Anthropic for cross-reference",
)
async def get_anthropic_cost(
    days: int = Query(7, ge=1, le=365, description="Number of days to query"),
    _user: User = Depends(require_mgms_domain),
):
    """Get cost data from Anthropic Admin API.

    Requires Admin API key stored in Secret Manager as 'anthropic-admin-api-key'.
    """
    try:
        from app.services.anthropic_usage_api import get_anthropic_usage_client

        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        # Fetch from Anthropic
        client = get_anthropic_usage_client()
        report = await client.fetch_cost_report(
            start_date=start_date,
            end_date=end_date,
        )

        # Get total cost - Anthropic API returns amounts already in USD (not cents)
        total_cost_usd = report.get_total_amount()

        return AnthropicCostData(
            total_cost_usd=round(total_cost_usd, 6),
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )

    except ValueError as e:
        # Admin API key not configured
        logger.error("Admin API key not configured: %s", e)
        raise HTTPException(
            503,
            detail="Anthropic Admin API not configured. Please add 'anthropic-admin-api-key' to Secret Manager."
        ) from e
    except Exception as e:
        logger.error("Error fetching Anthropic cost: %s", e, exc_info=True)
        raise HTTPException(500, detail=f"Error fetching Anthropic cost: {str(e)}") from e


@router.get(
    "/reconciliation",
    response_model=ReconciliationReport,
    summary="Compare internal tracking with Anthropic's data",
    description="Cross-reference internal usage tracking with Anthropic's actual billing data",
)
async def get_reconciliation_report(
    days: int = Query(7, ge=1, le=365, description="Number of days to query"),
    _user: User = Depends(require_mgms_domain),
):
    """Generate reconciliation report comparing internal vs Anthropic data.

    Compares:
    - Token counts (input, output, cache creation, cache read)
    - Total costs
    - Identifies discrepancies

    Requires Admin API key stored in Secret Manager as 'anthropic-admin-api-key'.
    """
    try:
        from app.services.anthropic_usage_api import get_anthropic_usage_client

        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        # Fetch internal data
        service = get_usage_tracking_service()
        records = await service.get_all_usage(
            start_date=start_date,
            end_date=end_date,
            limit=MAX_EXPORT_RECORDS,  # Get all records for accurate comparison
        )

        # Calculate internal totals
        internal_input = sum(r.input_tokens for r in records)
        internal_output = sum(r.output_tokens for r in records)
        internal_cache_creation = sum(r.cache_creation_tokens for r in records)
        internal_cache_read = sum(r.cache_read_tokens for r in records)
        internal_cost = sum(r.estimated_cost_usd for r in records)

        # Fetch Anthropic data
        client = get_anthropic_usage_client()

        usage_report = await client.fetch_usage_report(
            start_date=start_date,
            end_date=end_date,
            bucket_width="1d",
        )

        cost_report = await client.fetch_cost_report(
            start_date=start_date,
            end_date=end_date,
        )

        # Anthropic totals
        totals = usage_report.get_totals()
        anthropic_input = totals["input_tokens"]
        anthropic_output = totals["output_tokens"]
        anthropic_cache_creation = totals["cache_creation_tokens"]
        anthropic_cache_read = totals["cache_read_tokens"]
        anthropic_cost = cost_report.get_total_amount()  # Already in USD

        # Calculate variances
        variance_input = internal_input - anthropic_input
        variance_output = internal_output - anthropic_output
        variance_cache_creation = internal_cache_creation - anthropic_cache_creation
        variance_cache_read = internal_cache_read - anthropic_cache_read
        variance_cost = internal_cost - anthropic_cost
        variance_cost_percent = (
            (variance_cost / anthropic_cost * 100) if anthropic_cost != 0 else 0.0
        )

        # Determine match status
        # Consider "close" if within 1% variance
        if abs(variance_cost_percent) < 0.01:
            match_status = "exact"
        elif abs(variance_cost_percent) < 1.0:
            match_status = "close"
        else:
            match_status = "mismatch"

        return ReconciliationReport(
            internal_usage={
                "input_tokens": internal_input,
                "output_tokens": internal_output,
                "cache_creation_tokens": internal_cache_creation,
                "cache_read_tokens": internal_cache_read,
            },
            anthropic_usage={
                "input_tokens": anthropic_input,
                "output_tokens": anthropic_output,
                "cache_creation_tokens": anthropic_cache_creation,
                "cache_read_tokens": anthropic_cache_read,
            },
            internal_cost=round(internal_cost, 6),
            anthropic_cost=round(anthropic_cost, 6),
            variance_tokens={
                "input_tokens": variance_input,
                "output_tokens": variance_output,
                "cache_creation_tokens": variance_cache_creation,
                "cache_read_tokens": variance_cache_read,
            },
            variance_cost=round(variance_cost, 6),
            variance_cost_percent=round(variance_cost_percent, 2),
            match_status=match_status,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
        )

    except ValueError as e:
        # Admin API key not configured
        logger.error("Admin API key not configured: %s", e)
        raise HTTPException(
            503,
            detail="Anthropic Admin API not configured. Please add 'anthropic-admin-api-key' to Secret Manager."
        ) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error generating reconciliation report: %s", e, exc_info=True)
        raise HTTPException(500, detail=f"Error generating reconciliation report: {str(e)}") from e
