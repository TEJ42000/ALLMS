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
from app.models.usage_models import UsageSummary, UserUsageSummary, LLMUsageRecord
from app.services.usage_tracking_service import (
    get_usage_tracking_service,
    DEFAULT_QUERY_LIMIT,
    MAX_QUERY_LIMIT,
    MAX_EXPORT_RECORDS,
)

logger = logging.getLogger(__name__)

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


class TimeSeriesResponse(BaseModel):
    """Response for time series endpoint."""
    data: List[TimeSeriesBucket]
    granularity: str
    metric: str
    total: float
    start_date: str
    end_date: str


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


class DashboardKPIs(BaseModel):
    """Key performance indicators for dashboard."""
    total_requests: int
    total_cost: float
    unique_users: int
    avg_cost_per_request: float
    total_input_tokens: int
    total_output_tokens: int
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
        avg_cost = total_cost / total_requests if total_requests > 0 else 0.0

        return DashboardKPIs(
            total_requests=total_requests,
            total_cost=round(total_cost, 4),
            unique_users=unique_users,
            avg_cost_per_request=round(avg_cost, 6),
            total_input_tokens=total_input,
            total_output_tokens=total_output,
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
