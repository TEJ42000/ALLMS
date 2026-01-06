"""Admin API Routes for LLM Usage Tracking.

Provides endpoints for viewing and exporting LLM usage statistics.
Requires admin privileges (@mgms.eu domain).
"""

import csv
import io
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.dependencies.auth import require_mgms_domain
from app.models.auth_models import User
from app.models.usage_models import UsageSummary, UserUsageSummary, LLMUsageRecord
from app.services.usage_tracking_service import (
    get_usage_tracking_service,
    DEFAULT_RECORD_LIMIT,
    MAX_RECORD_LIMIT,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/usage",
    tags=["Admin - Usage Tracking"],
    dependencies=[Depends(require_mgms_domain)],
)


@router.get("/summary", response_model=UsageSummary)
async def get_usage_summary(
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
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
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
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
    days: int = Query(7, ge=1, le=90, description="Number of days to include"),
    limit: int = Query(
        DEFAULT_RECORD_LIMIT,
        ge=1,
        le=MAX_RECORD_LIMIT,
        description="Max records to return",
    ),
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
    days: int = Query(30, ge=1, le=365, description="Number of days to include"),
    user: User = Depends(require_mgms_domain),
):
    """
    Export LLM usage data as CSV.
    """
    try:
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)

        service = get_usage_tracking_service()
        # Use MAX_RECORD_LIMIT for exports to prevent memory issues
        # For larger exports, consider implementing pagination
        records = await service.get_all_usage(
            start_date=start_date,
            end_date=end_date,
            limit=MAX_RECORD_LIMIT,
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
                record.timestamp.isoformat(),
                record.user_email,
                record.model,
                record.operation_type,
                record.input_tokens,
                record.output_tokens,
                record.cache_creation_tokens,
                record.cache_read_tokens,
                record.estimated_cost_usd,
                record.course_id or "",
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

