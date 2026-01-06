"""LLM Usage Tracking Service.

Provides functionality to record and query LLM token usage and costs.
Stores data in Firestore for persistence and aggregation.

Firestore structure: llm_usage/{usage_id}
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from app.models.usage_models import (
    LLMUsageRecord,
    UsageSummary,
    UserUsageSummary,
    calculate_cost,
)
from app.services.gcp_service import get_firestore_client

logger = logging.getLogger(__name__)

# Firestore collection name
USAGE_COLLECTION = "llm_usage"


class UsageTrackingService:
    """Service for tracking and querying LLM usage."""

    def __init__(self):
        """Initialize the usage tracking service."""
        self._db = None

    @property
    def db(self):
        """Lazy-load Firestore client."""
        if self._db is None:
            self._db = get_firestore_client()
        return self._db

    async def record_usage(
        self,
        user_email: str,
        user_id: str,
        model: str,
        operation_type: str,
        input_tokens: int,
        output_tokens: int,
        cache_creation_tokens: int = 0,
        cache_read_tokens: int = 0,
        course_id: Optional[str] = None,
        request_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[LLMUsageRecord]:
        """Record a single LLM usage event.

        Args:
            user_email: User's email address
            user_id: User's IAP user ID
            model: Model used (e.g., 'claude-sonnet-4-20250514')
            operation_type: Type of operation ('tutor', 'assessment', etc.)
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cache_creation_tokens: Tokens written to cache
            cache_read_tokens: Tokens read from cache
            course_id: Course ID if applicable
            request_metadata: Additional context

        Returns:
            The created LLMUsageRecord, or None if Firestore unavailable
        """
        if not self.db:
            logger.warning("Firestore unavailable - usage not recorded")
            return None

        try:
            # Calculate cost
            estimated_cost = calculate_cost(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_creation_tokens=cache_creation_tokens,
                cache_read_tokens=cache_read_tokens,
            )

            # Create record
            record = LLMUsageRecord(
                id=str(uuid.uuid4()),
                user_email=user_email,
                user_id=user_id,
                timestamp=datetime.now(timezone.utc),
                model=model,
                operation_type=operation_type,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_creation_tokens=cache_creation_tokens,
                cache_read_tokens=cache_read_tokens,
                estimated_cost_usd=estimated_cost,
                course_id=course_id,
                request_metadata=request_metadata,
            )

            # Store in Firestore
            doc_ref = self.db.collection(USAGE_COLLECTION).document(record.id)
            doc_ref.set(record.model_dump())

            logger.info(
                "Recorded LLM usage: user=%s, op=%s, tokens=%d/%d, cost=$%.6f",
                user_email,
                operation_type,
                input_tokens,
                output_tokens,
                estimated_cost,
            )

            return record

        except Exception as e:
            logger.error("Failed to record LLM usage: %s", e)
            return None

    async def get_user_usage(
        self,
        user_email: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[LLMUsageRecord]:
        """Get usage records for a specific user.

        Args:
            user_email: User's email address
            start_date: Filter from this date
            end_date: Filter until this date
            limit: Maximum records to return

        Returns:
            List of usage records
        """
        if not self.db:
            return []

        try:
            query = self.db.collection(USAGE_COLLECTION).where(
                "user_email", "==", user_email.lower()
            )

            if start_date:
                query = query.where("timestamp", ">=", start_date)
            if end_date:
                query = query.where("timestamp", "<=", end_date)

            query = query.order_by("timestamp", direction="DESCENDING").limit(limit)

            docs = query.stream()
            return [LLMUsageRecord(**doc.to_dict()) for doc in docs]

        except Exception as e:
            logger.error("Failed to get user usage: %s", e)
            return []

    async def get_user_summary(
        self,
        user_email: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Optional[UserUsageSummary]:
        """Get aggregated usage summary for a user.

        Args:
            user_email: User's email address
            start_date: Filter from this date
            end_date: Filter until this date

        Returns:
            Aggregated usage summary, or None if no data
        """
        records = await self.get_user_usage(
            user_email=user_email,
            start_date=start_date,
            end_date=end_date,
            limit=10000,  # Get all for aggregation
        )

        if not records:
            return None

        # Calculate aggregates
        by_operation: Dict[str, int] = {}
        total_input = 0
        total_output = 0
        total_cost = 0.0

        for record in records:
            total_input += record.input_tokens
            total_output += record.output_tokens
            total_cost += record.estimated_cost_usd
            by_operation[record.operation_type] = (
                by_operation.get(record.operation_type, 0) + 1
            )

        # Determine date range
        timestamps = [r.timestamp for r in records]
        actual_start = min(timestamps) if timestamps else datetime.now(timezone.utc)
        actual_end = max(timestamps) if timestamps else datetime.now(timezone.utc)

        return UserUsageSummary(
            user_email=user_email,
            user_id=records[0].user_id if records else "",
            start_date=start_date or actual_start,
            end_date=end_date or actual_end,
            total_requests=len(records),
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_estimated_cost_usd=round(total_cost, 6),
            by_operation=by_operation,
        )

    async def get_all_usage(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[LLMUsageRecord]:
        """Get all usage records (admin only).

        Args:
            start_date: Filter from this date
            end_date: Filter until this date
            limit: Maximum records to return

        Returns:
            List of usage records
        """
        if not self.db:
            return []

        try:
            query = self.db.collection(USAGE_COLLECTION)

            if start_date:
                query = query.where("timestamp", ">=", start_date)
            if end_date:
                query = query.where("timestamp", "<=", end_date)

            query = query.order_by("timestamp", direction="DESCENDING").limit(limit)

            docs = query.stream()
            return [LLMUsageRecord(**doc.to_dict()) for doc in docs]

        except Exception as e:
            logger.error("Failed to get all usage: %s", e)
            return []

    async def get_usage_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> UsageSummary:
        """Get aggregated usage summary across all users (admin only).

        Args:
            start_date: Filter from this date
            end_date: Filter until this date

        Returns:
            Aggregated usage summary
        """
        records = await self.get_all_usage(
            start_date=start_date,
            end_date=end_date,
            limit=50000,  # Get all for aggregation
        )

        # Initialize aggregates
        by_operation: Dict[str, int] = {}
        by_user: Dict[str, int] = {}
        by_model: Dict[str, int] = {}
        total_input = 0
        total_output = 0
        total_cache_creation = 0
        total_cache_read = 0
        total_cost = 0.0

        for record in records:
            total_input += record.input_tokens
            total_output += record.output_tokens
            total_cache_creation += record.cache_creation_tokens
            total_cache_read += record.cache_read_tokens
            total_cost += record.estimated_cost_usd

            by_operation[record.operation_type] = (
                by_operation.get(record.operation_type, 0) + 1
            )
            by_user[record.user_email] = by_user.get(record.user_email, 0) + 1
            by_model[record.model] = by_model.get(record.model, 0) + 1

        # Determine date range
        now = datetime.now(timezone.utc)
        timestamps = [r.timestamp for r in records]
        actual_start = min(timestamps) if timestamps else now
        actual_end = max(timestamps) if timestamps else now

        return UsageSummary(
            start_date=start_date or actual_start,
            end_date=end_date or actual_end,
            total_requests=len(records),
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_cache_creation_tokens=total_cache_creation,
            total_cache_read_tokens=total_cache_read,
            total_estimated_cost_usd=round(total_cost, 6),
            by_operation=by_operation,
            by_user=by_user,
            by_model=by_model,
        )


# Singleton instance
_usage_tracking_service: Optional[UsageTrackingService] = None


def get_usage_tracking_service() -> UsageTrackingService:
    """Get the singleton usage tracking service instance."""
    global _usage_tracking_service
    if _usage_tracking_service is None:
        _usage_tracking_service = UsageTrackingService()
    return _usage_tracking_service

