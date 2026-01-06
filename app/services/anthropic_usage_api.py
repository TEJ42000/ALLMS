"""Anthropic Usage & Cost Admin API Client.

This service fetches actual usage and cost data from Anthropic's Admin API
for reconciliation with internal tracking.

Requires an Admin API key (starts with sk-ant-admin...) stored in Secret Manager
as 'anthropic-admin-api-key'. The Cloud Run service account must have the
'roles/secretmanager.secretAccessor' role for this secret.

API Documentation: https://docs.anthropic.com/en/api/admin-api
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from urllib.parse import urlencode

import httpx
from pydantic import BaseModel

from app.services.gcp_service import get_secret

logger = logging.getLogger(__name__)

# Anthropic Admin API base URL
ANTHROPIC_ADMIN_API_BASE = "https://api.anthropic.com/v1/organizations"
ANTHROPIC_API_VERSION = "2023-06-01"


class AnthropicUsageBucket(BaseModel):
    """Usage data for a time bucket."""
    bucket: str  # ISO datetime
    input_tokens: int
    output_tokens: int
    cache_creation_tokens: int
    cache_read_tokens: int
    count: int  # Number of requests


class AnthropicUsageReport(BaseModel):
    """Response from usage_report/messages endpoint."""
    data: List[AnthropicUsageBucket]
    granularity: str
    start_date: str
    end_date: str
    totals: Dict[str, int]


class AnthropicCostBucket(BaseModel):
    """Cost data for a time bucket."""
    bucket: str  # ISO datetime
    amount: str  # USD in cents (decimal string)
    description: Optional[str] = None


class AnthropicCostReport(BaseModel):
    """Response from cost_report endpoint."""
    data: List[AnthropicCostBucket]
    start_date: str
    end_date: str
    total_amount: str  # USD in cents


class AnthropicUsageAPIError(Exception):
    """Error communicating with Anthropic Admin API."""
    pass


class AnthropicUsageAPIClient:
    """Client for Anthropic Usage & Cost Admin API."""

    def __init__(self):
        """Initialize the client with Admin API key."""
        self.admin_api_key = self._get_admin_api_key()
        self.base_url = ANTHROPIC_ADMIN_API_BASE
        self.headers = {
            "anthropic-version": ANTHROPIC_API_VERSION,
            "x-api-key": self.admin_api_key,
            "User-Agent": "ALLMS-LLS-Portal/2.8.0 (https://lls-study-portal.com)",
        }

    def _get_admin_api_key(self) -> str:
        """Get Admin API key from Secret Manager.
        
        Returns:
            Admin API key string
            
        Raises:
            ValueError: If admin API key is not found
        """
        api_key = get_secret("anthropic-admin-api-key")
        
        if not api_key:
            raise ValueError(
                "Anthropic Admin API key not found. Please:\n"
                "1. Create an Admin API key in Anthropic Console (Settings → API Keys)\n"
                "2. Store it in Secret Manager as 'anthropic-admin-api-key'\n"
                "Note: Admin API keys start with 'sk-ant-admin...'"
            )
        
        if not api_key.startswith("sk-ant-admin"):
            logger.warning(
                "API key does not start with 'sk-ant-admin'. "
                "Make sure you're using an Admin API key, not a regular API key."
            )
        
        return api_key

    async def fetch_usage_report(
        self,
        start_date: datetime,
        end_date: datetime,
        bucket_width: str = "1d",
        group_by: Optional[List[str]] = None,
    ) -> AnthropicUsageReport:
        """Fetch usage report from Anthropic.
        
        Args:
            start_date: Start of time range (inclusive)
            end_date: End of time range (inclusive)
            bucket_width: Time bucket size: "1m", "1h", or "1d"
            group_by: Optional list of dimensions to group by
                     (e.g., ["model", "workspace_id"])
        
        Returns:
            Usage report with token counts
            
        Raises:
            AnthropicUsageAPIError: If API request fails
        """
        # Build query parameters
        params = {
            "starting_at": start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ending_at": end_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "bucket_width": bucket_width,
        }
        
        # Add group_by parameters
        if group_by:
            for dimension in group_by:
                params[f"group_by[]"] = dimension
        
        url = f"{self.base_url}/usage_report/messages?{urlencode(params, doseq=True)}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                
                # Calculate totals
                totals = {
                    "input_tokens": sum(b.get("input_tokens", 0) for b in data.get("data", [])),
                    "output_tokens": sum(b.get("output_tokens", 0) for b in data.get("data", [])),
                    "cache_creation_tokens": sum(b.get("cache_creation_tokens", 0) for b in data.get("data", [])),
                    "cache_read_tokens": sum(b.get("cache_read_tokens", 0) for b in data.get("data", [])),
                }
                
                return AnthropicUsageReport(
                    data=[AnthropicUsageBucket(**b) for b in data.get("data", [])],
                    granularity=bucket_width,
                    start_date=params["starting_at"],
                    end_date=params["ending_at"],
                    totals=totals,
                )
        except httpx.HTTPStatusError as e:
            logger.error(f"Anthropic API error: {e.response.status_code} - {e.response.text}")
            raise AnthropicUsageAPIError(
                f"Failed to fetch usage report: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            logger.error(f"Error fetching usage report: {str(e)}")
            raise AnthropicUsageAPIError(f"Failed to fetch usage report: {str(e)}")

    async def fetch_cost_report(
        self,
        start_date: datetime,
        end_date: datetime,
        group_by: Optional[List[str]] = None,
    ) -> AnthropicCostReport:
        """Fetch cost report from Anthropic.

        Args:
            start_date: Start of time range (inclusive)
            end_date: End of time range (inclusive)
            group_by: Optional list of dimensions to group by
                     (e.g., ["workspace_id", "description"])

        Returns:
            Cost report with actual USD amounts

        Raises:
            AnthropicUsageAPIError: If API request fails
        """
        # Build query parameters
        params = {
            "starting_at": start_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ending_at": end_date.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        # Add group_by parameters
        if group_by:
            for dimension in group_by:
                params[f"group_by[]"] = dimension

        url = f"{self.base_url}/cost_report?{urlencode(params, doseq=True)}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=self.headers)
                response.raise_for_status()
                data = response.json()

                # Calculate total amount with validation
                try:
                    total_amount = sum(
                        float(b.get("amount", "0")) for b in data.get("data", [])
                    )
                except (ValueError, TypeError) as e:
                    logger.error(f"Invalid amount format in cost report: {e}")
                    raise AnthropicUsageAPIError(f"Invalid cost data format: {e}")

                return AnthropicCostReport(
                    data=[AnthropicCostBucket(**b) for b in data.get("data", [])],
                    start_date=params["starting_at"],
                    end_date=params["ending_at"],
                    total_amount=str(total_amount),
                )
        except httpx.HTTPStatusError as e:
            logger.error(f"Anthropic API error: {e.response.status_code} - {e.response.text}")
            raise AnthropicUsageAPIError(
                f"Failed to fetch cost report: {e.response.status_code} - {e.response.text}"
            )
        except Exception as e:
            logger.error(f"Error fetching cost report: {str(e)}")
            raise AnthropicUsageAPIError(f"Failed to fetch cost report: {str(e)}")


# Singleton instance
_client: Optional[AnthropicUsageAPIClient] = None


def get_anthropic_usage_client() -> AnthropicUsageAPIClient:
    """Get singleton instance of Anthropic Usage API client.

    Returns:
        AnthropicUsageAPIClient instance
    """
    global _client
    if _client is None:
        _client = AnthropicUsageAPIClient()
    return _client

