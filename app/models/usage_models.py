"""LLM Usage Tracking Models.

Provides data models for tracking token usage and costs for all LLM operations,
storing the data in Firestore and associating it with authenticated users.

Firestore structure: llm_usage/{usage_id}
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any

from pydantic import BaseModel, Field


class LLMUsageRecord(BaseModel):
    """Record of a single LLM API call with usage and cost data.
    
    Stored in Firestore: llm_usage/{id}
    """
    
    id: str = Field(..., description="Unique usage record ID")
    
    # User identification
    user_email: str = Field(..., description="User's email address")
    user_id: str = Field(..., description="User's IAP user ID")
    
    # Timestamp
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When the LLM call was made (UTC)"
    )
    
    # LLM details
    model: str = Field(..., description="Model used (e.g., 'claude-sonnet-4-20250514')")
    operation_type: str = Field(
        ...,
        description="Type of operation: 'tutor', 'assessment', 'study_guide', 'title_enhance', etc."
    )
    
    # Token metrics
    input_tokens: int = Field(..., description="Number of input tokens")
    output_tokens: int = Field(..., description="Number of output tokens")
    cache_creation_tokens: int = Field(default=0, description="Tokens written to cache")
    cache_read_tokens: int = Field(default=0, description="Tokens read from cache")
    
    # Cost calculation (based on Anthropic pricing)
    estimated_cost_usd: float = Field(
        ...,
        description="Estimated cost in USD based on current Anthropic pricing"
    )
    
    # Context
    course_id: Optional[str] = Field(None, description="Course ID if applicable")
    request_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional context about the request"
    )


class UsageSummary(BaseModel):
    """Aggregated usage statistics."""
    
    # Time period
    start_date: datetime
    end_date: datetime
    
    # Totals
    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_cache_creation_tokens: int = 0
    total_cache_read_tokens: int = 0
    total_estimated_cost_usd: float = 0.0
    
    # Breakdowns
    by_operation: Dict[str, int] = Field(default_factory=dict)
    by_user: Dict[str, int] = Field(default_factory=dict)
    by_model: Dict[str, int] = Field(default_factory=dict)


class UserUsageSummary(BaseModel):
    """Usage summary for a specific user."""
    
    user_email: str
    user_id: str
    
    # Time period
    start_date: datetime
    end_date: datetime
    
    # Totals
    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_estimated_cost_usd: float = 0.0
    
    # Breakdown by operation
    by_operation: Dict[str, int] = Field(default_factory=dict)


# Cost constants based on Anthropic pricing (Claude Sonnet 4 - as of Jan 2026)
# Prices per million tokens
COST_INPUT_PER_MILLION = 3.00  # $3.00 per 1M input tokens
COST_OUTPUT_PER_MILLION = 15.00  # $15.00 per 1M output tokens
COST_CACHE_WRITE_PER_MILLION = 3.75  # $3.75 per 1M cache creation tokens
COST_CACHE_READ_PER_MILLION = 0.30  # $0.30 per 1M cache read tokens


def calculate_cost(
    input_tokens: int,
    output_tokens: int,
    cache_creation_tokens: int = 0,
    cache_read_tokens: int = 0
) -> float:
    """Calculate estimated cost in USD based on token usage.
    
    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        cache_creation_tokens: Tokens written to cache
        cache_read_tokens: Tokens read from cache
        
    Returns:
        Estimated cost in USD
    """
    cost = 0.0
    cost += (input_tokens / 1_000_000) * COST_INPUT_PER_MILLION
    cost += (output_tokens / 1_000_000) * COST_OUTPUT_PER_MILLION
    cost += (cache_creation_tokens / 1_000_000) * COST_CACHE_WRITE_PER_MILLION
    cost += (cache_read_tokens / 1_000_000) * COST_CACHE_READ_PER_MILLION
    return round(cost, 6)  # Round to 6 decimal places for micro-cents

