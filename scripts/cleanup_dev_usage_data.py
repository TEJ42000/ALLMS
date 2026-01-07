#!/usr/bin/env python3
"""Script to identify and optionally delete bad usage data from dev@mgms.eu.

This script:
1. Queries all usage records for dev@mgms.eu
2. Displays statistics about the data
3. Optionally deletes the records (with confirmation)

Usage:
    # Dry run (view only)
    python scripts/cleanup_dev_usage_data.py

    # Delete the records
    python scripts/cleanup_dev_usage_data.py --delete
"""

import argparse
import asyncio
import sys
from datetime import datetime
from typing import List

# Add parent directory to path
sys.path.insert(0, '.')

from app.services.gcp_service import get_firestore_client
from app.models.usage_models import LLMUsageRecord

USAGE_COLLECTION = "llm_usage"
DEV_EMAIL = "dev@mgms.eu"


async def get_dev_usage_records() -> List[LLMUsageRecord]:
    """Get all usage records for dev@mgms.eu."""
    db = get_firestore_client()
    if not db:
        print("❌ Error: Could not connect to Firestore")
        return []

    print(f"🔍 Querying usage records for {DEV_EMAIL}...")
    
    query = db.collection(USAGE_COLLECTION).where("user_email", "==", DEV_EMAIL)
    docs = query.stream()
    
    records = []
    for doc in docs:
        try:
            records.append(LLMUsageRecord(**doc.to_dict()))
        except Exception as e:
            print(f"⚠️  Warning: Could not parse record {doc.id}: {e}")
    
    return records


def analyze_records(records: List[LLMUsageRecord]) -> None:
    """Display statistics about the records."""
    if not records:
        print(f"✅ No records found for {DEV_EMAIL}")
        return
    
    print(f"\n📊 Found {len(records)} records for {DEV_EMAIL}")
    print("=" * 80)
    
    # Calculate totals
    total_input = sum(r.input_tokens for r in records)
    total_output = sum(r.output_tokens for r in records)
    total_cache_creation = sum(r.cache_creation_tokens for r in records)
    total_cache_read = sum(r.cache_read_tokens for r in records)
    total_cost = sum(r.estimated_cost_usd for r in records)
    
    print(f"\n💰 Total Cost: ${total_cost:.2f}")
    print(f"📝 Total Input Tokens: {total_input:,}")
    print(f"📤 Total Output Tokens: {total_output:,}")
    print(f"💾 Total Cache Creation Tokens: {total_cache_creation:,}")
    print(f"📖 Total Cache Read Tokens: {total_cache_read:,}")
    
    # Date range
    timestamps = [r.timestamp for r in records]
    earliest = min(timestamps)
    latest = max(timestamps)
    print(f"\n📅 Date Range: {earliest.date()} to {latest.date()}")
    
    # Operation breakdown
    operations = {}
    for r in records:
        operations[r.operation_type] = operations.get(r.operation_type, 0) + 1
    
    print(f"\n🔧 Operations:")
    for op, count in sorted(operations.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {op}: {count}")
    
    # Model breakdown
    models = {}
    for r in records:
        models[r.model] = models.get(r.model, 0) + 1
    
    print(f"\n🤖 Models:")
    for model, count in sorted(models.items(), key=lambda x: x[1], reverse=True):
        print(f"  - {model}: {count}")
    
    print("=" * 80)


async def delete_records(records: List[LLMUsageRecord], confirm: bool = True) -> int:
    """Delete the records from Firestore."""
    if not records:
        return 0
    
    if confirm:
        print(f"\n⚠️  WARNING: This will permanently delete {len(records)} records!")
        response = input("Type 'DELETE' to confirm: ")
        if response != "DELETE":
            print("❌ Deletion cancelled")
            return 0
    
    db = get_firestore_client()
    if not db:
        print("❌ Error: Could not connect to Firestore")
        return 0
    
    print(f"\n🗑️  Deleting {len(records)} records...")
    
    deleted_count = 0
    for record in records:
        try:
            db.collection(USAGE_COLLECTION).document(record.id).delete()
            deleted_count += 1
            if deleted_count % 10 == 0:
                print(f"  Deleted {deleted_count}/{len(records)}...")
        except Exception as e:
            print(f"❌ Error deleting record {record.id}: {e}")
    
    print(f"✅ Successfully deleted {deleted_count} records")
    return deleted_count


async def main():
    parser = argparse.ArgumentParser(description="Cleanup dev@mgms.eu usage data")
    parser.add_argument("--delete", action="store_true", help="Delete the records (requires confirmation)")
    parser.add_argument("--force", action="store_true", help="Skip confirmation prompt")
    args = parser.parse_args()
    
    # Get records
    records = await get_dev_usage_records()
    
    # Analyze
    analyze_records(records)
    
    # Delete if requested
    if args.delete:
        deleted = await delete_records(records, confirm=not args.force)
        if deleted > 0:
            print(f"\n✅ Cleanup complete! Deleted {deleted} records from {DEV_EMAIL}")
    else:
        print(f"\n💡 To delete these records, run: python {sys.argv[0]} --delete")


if __name__ == "__main__":
    asyncio.run(main())

