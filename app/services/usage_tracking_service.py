"""LLM Usage Tracking Service.

Provides functionality to record and query LLM token usage and costs.
Stores data in Firestore for persistence and aggregation.

Firestore structure: llm_usage/{usage_id}
"""

import logging
import threading
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from google.cloud.firestore_v1 import aggregation
from google.cloud.firestore_v1.base_query import FieldFilter

from app.models.usage_models import (
    LLMUsageRecord,
    UsageSummary,
    UserUsageSummary,
    UserContext,
    calculate_cost,
)
from app.services.gcp_service import get_firestore_client

logger = logging.getLogger(__name__)

# Firestore collection name
USAGE_COLLECTION = "llm_usage"

# Query limits
DEFAULT_RECORD_LIMIT = 100
MAX_RECORD_LIMIT = 1000
MAX_RECORDS_USER_SUMMARY = 10_000
MAX_RECORDS_GLOBAL_SUMMARY = 50_000


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
        """Get aggregated usage summary for a user using Firestore aggregation.

        Uses Firestore aggregation API for efficient server-side calculation of totals.
        Only fetches individual records for operation breakdown.

        Args:
            user_email: User's email address
            start_date: Filter from this date
            end_date: Filter until this date

        Returns:
            Aggregated usage summary, or None if no data
        """
        if not self.db:
            return None

        try:
            # Build base query
            query = self.db.collection(USAGE_COLLECTION).where(
                "user_email", "==", user_email.lower()
            )

            if start_date:
                query = query.where("timestamp", ">=", start_date)
            if end_date:
                query = query.where("timestamp", "<=", end_date)

            # Create aggregation query for totals
            agg_query = aggregation.AggregationQuery(query)
            agg_query.count(alias="total_requests")
            agg_query.sum("input_tokens", alias="total_input")
            agg_query.sum("output_tokens", alias="total_output")
            agg_query.sum("estimated_cost_usd", alias="total_cost")

            # Execute aggregation
            results = agg_query.get()

            if not results or not results[0]:
                return None

            # Extract aggregated values
            agg_data = results[0]
            total_requests = agg_data[0].value if len(agg_data) > 0 else 0
            total_input = agg_data[1].value if len(agg_data) > 1 else 0
            total_output = agg_data[2].value if len(agg_data) > 2 else 0
            total_cost = agg_data[3].value if len(agg_data) > 3 else 0.0

            if total_requests == 0:
                return None

            # For operation breakdown and metadata, fetch a sample of records
            records = await self.get_user_usage(
                user_email=user_email,
                start_date=start_date,
                end_date=end_date,
                limit=MAX_RECORDS_USER_SUMMARY,
            )

            by_operation: Dict[str, int] = {}
            for record in records:
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
                total_requests=int(total_requests) if total_requests else 0,
                total_input_tokens=int(total_input) if total_input else 0,
                total_output_tokens=int(total_output) if total_output else 0,
                total_estimated_cost_usd=round(float(total_cost), 6) if total_cost else 0.0,
                by_operation=by_operation,
            )

        except Exception as e:
            logger.error("Failed to get user summary: %s", e)
            return None

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

        Uses Firestore aggregation API for efficient server-side calculation of totals.
        Only fetches individual records for breakdowns by operation, user, and model.

        Args:
            start_date: Filter from this date
            end_date: Filter until this date

        Returns:
            Aggregated usage summary
        """
        if not self.db:
            # Return empty summary if Firestore unavailable
            now = datetime.now(timezone.utc)
            return UsageSummary(
                start_date=start_date or now,
                end_date=end_date or now,
                total_requests=0,
                total_input_tokens=0,
                total_output_tokens=0,
                total_cache_creation_tokens=0,
                total_cache_read_tokens=0,
                total_estimated_cost_usd=0.0,
                by_operation={},
                by_user={},
                by_model={},
            )

        try:
            # Build base query
            query = self.db.collection(USAGE_COLLECTION)

            if start_date:
                query = query.where("timestamp", ">=", start_date)
            if end_date:
                query = query.where("timestamp", "<=", end_date)

            # Create aggregation query for totals
            agg_query = aggregation.AggregationQuery(query)
            agg_query.count(alias="total_requests")
            agg_query.sum("input_tokens", alias="total_input")
            agg_query.sum("output_tokens", alias="total_output")
            agg_query.sum("cache_creation_tokens", alias="total_cache_creation")
            agg_query.sum("cache_read_tokens", alias="total_cache_read")
            agg_query.sum("estimated_cost_usd", alias="total_cost")

            # Execute aggregation
            results = agg_query.get()

            if not results or not results[0]:
                now = datetime.now(timezone.utc)
                return UsageSummary(
                    start_date=start_date or now,
                    end_date=end_date or now,
                    total_requests=0,
                    total_input_tokens=0,
                    total_output_tokens=0,
                    total_cache_creation_tokens=0,
                    total_cache_read_tokens=0,
                    total_estimated_cost_usd=0.0,
                    by_operation={},
                    by_user={},
                    by_model={},
                )

            # Extract aggregated values
            agg_data = results[0]
            total_requests = agg_data[0].value if len(agg_data) > 0 else 0
            total_input = agg_data[1].value if len(agg_data) > 1 else 0
            total_output = agg_data[2].value if len(agg_data) > 2 else 0
            total_cache_creation = agg_data[3].value if len(agg_data) > 3 else 0
            total_cache_read = agg_data[4].value if len(agg_data) > 4 else 0
            total_cost = agg_data[5].value if len(agg_data) > 5 else 0.0

            # For breakdowns, fetch a sample of records
            records = await self.get_all_usage(
                start_date=start_date,
                end_date=end_date,
                limit=MAX_RECORDS_GLOBAL_SUMMARY,
            )

            by_operation: Dict[str, int] = {}
            by_user: Dict[str, int] = {}
            by_model: Dict[str, int] = {}

            for record in records:
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
                total_requests=int(total_requests) if total_requests else 0,
                total_input_tokens=int(total_input) if total_input else 0,
                total_output_tokens=int(total_output) if total_output else 0,
                total_cache_creation_tokens=int(total_cache_creation) if total_cache_creation else 0,
                total_cache_read_tokens=int(total_cache_read) if total_cache_read else 0,
                total_estimated_cost_usd=round(float(total_cost), 6) if total_cost else 0.0,
                by_operation=by_operation,
                by_user=by_user,
                by_model=by_model,
            )

        except Exception as e:
            logger.error("Failed to get usage summary: %s", e)
            now = datetime.now(timezone.utc)
            return UsageSummary(
                start_date=start_date or now,
                end_date=end_date or now,
                total_requests=0,
                total_input_tokens=0,
                total_output_tokens=0,
                total_cache_creation_tokens=0,
                total_cache_read_tokens=0,
                total_estimated_cost_usd=0.0,
                by_operation={},
                by_user={},
                by_model={},
            )


# Singleton instance with thread-safe initialization
_usage_tracking_service: Optional[UsageTrackingService] = None
_usage_tracking_service_lock = threading.Lock()


def get_usage_tracking_service() -> UsageTrackingService:
    """Get the singleton usage tracking service instance.

    Uses double-checked locking pattern for thread-safe lazy initialization.
    This ensures only one instance is created even in multi-threaded environments.

    Returns:
        The singleton UsageTrackingService instance
    """
    global _usage_tracking_service

    # First check without lock (fast path for already initialized)
    if _usage_tracking_service is None:
        # Acquire lock for initialization
        with _usage_tracking_service_lock:
            # Double-check after acquiring lock
            if _usage_tracking_service is None:
                _usage_tracking_service = UsageTrackingService()

    return _usage_tracking_service


async def track_llm_usage_from_response(
    response: Any,  # anthropic.types.Message - using Any to avoid hard dependency
    user_context: Optional[UserContext],
    operation_type: str,
    model: str,
    request_metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Helper function to track LLM usage from an Anthropic API response.

    Extracts token usage from the response and records it via the usage tracking service.
    This helper reduces code duplication across multiple LLM operation handlers.

    Args:
        response: Anthropic API response object with usage attribute
        user_context: User context containing email, user_id, and course_id
        operation_type: Type of operation (e.g., "tutor", "assessment", "quiz", "study_guide")
        model: Model identifier used for the request
        request_metadata: Optional metadata about the request (e.g., topic, parameters)

    Returns:
        None. Logs errors if tracking fails but doesn't raise exceptions.

    Example:
        >>> await track_llm_usage_from_response(
        ...     response=anthropic_response,
        ...     user_context=user_context,
        ...     operation_type="tutor",
        ...     model="claude-sonnet-4-20250514",
        ...     request_metadata={"context": "algebra"}
        ... )
    """
    if not user_context:
        return

    try:
        usage = response.usage
        await get_usage_tracking_service().record_usage(
            user_email=user_context.email,
            user_id=user_context.user_id,
            model=model,
            operation_type=operation_type,
            input_tokens=getattr(usage, "input_tokens", 0) or 0,
            output_tokens=getattr(usage, "output_tokens", 0) or 0,
            cache_creation_tokens=getattr(usage, "cache_creation_input_tokens", 0) or 0,
            cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0) or 0,
            course_id=user_context.course_id,
            request_metadata=request_metadata,
        )
    except Exception as e:
        logger.error(
            "Failed to track usage for operation %s: %s", operation_type, e
        )

