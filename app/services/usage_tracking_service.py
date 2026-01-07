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

from google.cloud.firestore_v1.aggregation import AggregationQuery
from google.cloud.firestore_v1 import FieldFilter

from app.models.usage_models import (
    LLMUsageRecord,
    UsageSummary,
    UserUsageSummary,
    UserContext,
    calculate_cost,
)
from app.services.gcp_service import get_firestore_client

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

# Firestore collection name
USAGE_COLLECTION = "llm_usage"

# Query limits
DEFAULT_QUERY_LIMIT = 100
MAX_QUERY_LIMIT = 1000
AGGREGATION_QUERY_LIMIT = 50000
USER_AGGREGATION_LIMIT = 10000

# Export limits
MAX_EXPORT_RECORDS = 50000


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

    async def delete_user_records(
        self,
        user_email: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Delete all usage records for a specific user.

        Args:
            user_email: User's email address
            start_date: Only delete records from this date onwards
            end_date: Only delete records until this date

        Returns:
            Dictionary with deletion statistics
        """
        if not self.db:
            logger.warning("Firestore unavailable - cannot delete records")
            return {"success": False, "error": "Firestore unavailable"}

        try:
            # Build query
            query = self.db.collection(USAGE_COLLECTION).where(
                "user_email", "==", user_email.lower()
            )

            if start_date:
                query = query.where("timestamp", ">=", start_date)
            if end_date:
                query = query.where("timestamp", "<=", end_date)

            # Get all matching documents
            docs = list(query.stream())
            total_docs = len(docs)

            if total_docs == 0:
                logger.info("No records found for user %s", user_email)
                return {
                    "success": True,
                    "deleted_count": 0,
                    "message": f"No records found for {user_email}",
                }

            # Calculate statistics before deletion
            total_cost = sum(doc.to_dict().get("estimated_cost_usd", 0) for doc in docs)
            total_tokens = sum(
                doc.to_dict().get("input_tokens", 0) + doc.to_dict().get("output_tokens", 0)
                for doc in docs
            )

            # Delete in batches (Firestore batch limit is 500)
            batch_size = 500
            deleted_count = 0

            for i in range(0, total_docs, batch_size):
                batch = self.db.batch()
                batch_docs = docs[i : i + batch_size]

                for doc in batch_docs:
                    batch.delete(doc.reference)

                batch.commit()
                deleted_count += len(batch_docs)

                logger.info(
                    "Deleted batch %d-%d of %d records for user %s",
                    i + 1,
                    min(i + batch_size, total_docs),
                    total_docs,
                    user_email,
                )

            logger.info(
                "Successfully deleted %d records for user %s (total cost: $%.2f, total tokens: %d)",
                deleted_count,
                user_email,
                total_cost,
                total_tokens,
            )

            return {
                "success": True,
                "deleted_count": deleted_count,
                "total_cost_deleted": total_cost,
                "total_tokens_deleted": total_tokens,
                "message": f"Successfully deleted {deleted_count} records for {user_email}",
            }

        except Exception as e:
            logger.error("Failed to delete user records: %s", e)
            return {"success": False, "error": str(e)}

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
            limit=USER_AGGREGATION_LIMIT,
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

    async def get_aggregated_totals(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Get aggregated totals using Firestore aggregation API.

        This is more efficient than fetching all documents for large datasets.

        Args:
            start_date: Filter from this date
            end_date: Filter until this date

        Returns:
            Dictionary with count and sum aggregations
        """
        if not self.db:
            return {"count": 0, "total_cost": 0.0, "total_input": 0, "total_output": 0}

        try:
            # Build base query with filters
            collection_ref = self.db.collection(USAGE_COLLECTION)
            query = collection_ref

            if start_date:
                query = query.where(filter=FieldFilter("timestamp", ">=", start_date))
            if end_date:
                query = query.where(filter=FieldFilter("timestamp", "<=", end_date))

            # Use Firestore aggregation API for efficient counting and summing
            from google.cloud.firestore_v1.aggregation import CountAggregation, SumAggregation

            aggregation_query = query.count(alias="total_count")

            # Execute count aggregation
            results = aggregation_query.get()
            count_result = 0
            for result in results:
                count_result = result[0].value

            # For sums, we need separate queries (Firestore limitation)
            # Fall back to sampling for cost estimate if count is large
            if count_result > AGGREGATION_QUERY_LIMIT:
                # Use sampling for large datasets
                sample_size = 1000
                sample_query = query.order_by("timestamp", direction="DESCENDING").limit(sample_size)
                sample_docs = list(sample_query.stream())

                if sample_docs:
                    sample_cost = sum(doc.to_dict().get("estimated_cost_usd", 0) for doc in sample_docs)
                    sample_input = sum(doc.to_dict().get("input_tokens", 0) for doc in sample_docs)
                    sample_output = sum(doc.to_dict().get("output_tokens", 0) for doc in sample_docs)

                    # Extrapolate
                    scale_factor = count_result / sample_size
                    return {
                        "count": count_result,
                        "total_cost": sample_cost * scale_factor,
                        "total_input": int(sample_input * scale_factor),
                        "total_output": int(sample_output * scale_factor),
                        "is_estimated": True,
                    }

            return {
                "count": count_result,
                "total_cost": 0.0,  # Will be calculated from records
                "total_input": 0,
                "total_output": 0,
                "is_estimated": False,
            }

        except Exception as e:
            logger.error("Failed to get aggregated totals: %s", e)
            return {"count": 0, "total_cost": 0.0, "total_input": 0, "total_output": 0}

    async def get_usage_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> UsageSummary:
        """Get aggregated usage summary across all users (admin only).

        Uses Firestore aggregation API for efficient counting when possible.

        Args:
            start_date: Filter from this date
            end_date: Filter until this date

        Returns:
            Aggregated usage summary
        """
        # First, get efficient count using aggregation API
        agg_totals = await self.get_aggregated_totals(
            start_date=start_date,
            end_date=end_date,
        )

        # For detailed breakdowns, we still need to fetch records
        # but limit to a reasonable number
        records = await self.get_all_usage(
            start_date=start_date,
            end_date=end_date,
            limit=AGGREGATION_QUERY_LIMIT,
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

        # Use aggregation count if available (more accurate for large datasets)
        total_requests = agg_totals.get("count", len(records)) or len(records)

        return UsageSummary(
            start_date=start_date or actual_start,
            end_date=end_date or actual_end,
            total_requests=total_requests,
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_cache_creation_tokens=total_cache_creation,
            total_cache_read_tokens=total_cache_read,
            total_estimated_cost_usd=round(total_cost, 6),
            by_operation=by_operation,
            by_user=by_user,
            by_model=by_model,
        )


# =============================================================================
# Helper Functions
# =============================================================================

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


# =============================================================================
# Singleton Instance
# =============================================================================

_usage_tracking_service: Optional[UsageTrackingService] = None
_service_lock = threading.Lock()


def get_usage_tracking_service() -> UsageTrackingService:
    """Get the singleton usage tracking service instance (thread-safe)."""
    global _usage_tracking_service
    if _usage_tracking_service is None:
        with _service_lock:
            # Double-check locking pattern
            if _usage_tracking_service is None:
                _usage_tracking_service = UsageTrackingService()
    return _usage_tracking_service
