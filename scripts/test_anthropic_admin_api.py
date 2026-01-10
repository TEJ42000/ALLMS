#!/usr/bin/env python3
"""Test script to verify Anthropic Admin API configuration and connectivity.

This script checks:
1. If the Admin API key is configured in Secret Manager
2. If the API key format is correct (starts with sk-ant-admin)
3. If we can successfully call the Anthropic Admin API
4. What the actual error is if the API call fails

Usage:
    python scripts/test_anthropic_admin_api.py
"""

import asyncio
import sys
from datetime import datetime, timedelta, timezone

# Add parent directory to path
sys.path.insert(0, ".")

from app.services.gcp_service import get_secret
from app.services.anthropic_usage_api import get_anthropic_usage_client


async def test_admin_api():
    """Test Anthropic Admin API configuration and connectivity."""
    print("=" * 80)
    print("Anthropic Admin API Configuration Test")
    print("=" * 80)
    print()

    # Step 1: Check if API key exists
    print("Step 1: Checking if Admin API key is configured...")
    try:
        api_key = get_secret("anthropic-admin-api-key")
        if not api_key:
            print("❌ FAILED: Admin API key not found in Secret Manager")
            print()
            print("To fix this:")
            print("1. Create an Admin API key in Anthropic Console:")
            print("   https://console.anthropic.com/settings/keys")
            print("2. Store it in Google Cloud Secret Manager:")
            print("   gcloud secrets create anthropic-admin-api-key --data-file=-")
            print("   (then paste the key and press Ctrl+D)")
            return False
        
        print(f"✅ Admin API key found: {api_key[:8]}...{api_key[-4:] if len(api_key) > 12 else '****'}")
        print()
    except Exception as e:
        print(f"❌ FAILED: Error retrieving API key: {e}")
        return False

    # Step 2: Check API key format
    print("Step 2: Checking API key format...")
    if not api_key.startswith("sk-ant-admin"):
        print(f"⚠️  WARNING: API key does not start with 'sk-ant-admin'")
        print(f"   Current prefix: {api_key[:8]}...")
        print("   Make sure you're using an Admin API key, not a regular API key.")
        print()
    else:
        print("✅ API key format looks correct (starts with sk-ant-admin)")
        print()

    # Step 3: Test usage API call
    print("Step 3: Testing usage API call...")
    try:
        client = get_anthropic_usage_client()
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=7)
        
        print(f"   Fetching usage data from {start_date.date()} to {end_date.date()}...")
        usage_report = await client.fetch_usage_report(
            start_date=start_date,
            end_date=end_date,
            bucket_width="1d",
        )
        
        print(f"✅ Usage API call successful!")
        print(f"   Total input tokens: {usage_report.totals['input_tokens']:,}")
        print(f"   Total output tokens: {usage_report.totals['output_tokens']:,}")
        print(f"   Total cache creation tokens: {usage_report.totals['cache_creation_tokens']:,}")
        print(f"   Total cache read tokens: {usage_report.totals['cache_read_tokens']:,}")
        print()
    except Exception as e:
        print(f"❌ FAILED: Usage API call failed")
        print(f"   Error: {e}")
        print()
        return False

    # Step 4: Test cost API call
    print("Step 4: Testing cost API call...")
    try:
        cost_report = await client.fetch_cost_report(
            start_date=start_date,
            end_date=end_date,
        )
        
        total_cost_usd = float(cost_report.total_amount) / 100.0
        
        print(f"✅ Cost API call successful!")
        print(f"   Total cost: ${total_cost_usd:.4f}")
        print()
    except Exception as e:
        print(f"❌ FAILED: Cost API call failed")
        print(f"   Error: {e}")
        print()
        return False

    # All tests passed
    print("=" * 80)
    print("✅ All tests passed! Anthropic Admin API is configured correctly.")
    print("=" * 80)
    return True


if __name__ == "__main__":
    success = asyncio.run(test_admin_api())
    sys.exit(0 if success else 1)

