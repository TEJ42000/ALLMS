#!/bin/bash
# Script to identify and delete bad usage data from dev@mgms.eu using gcloud CLI
#
# Usage:
#   # Dry run (view only)
#   ./scripts/cleanup_dev_usage_gcloud.sh
#
#   # Delete the records
#   ./scripts/cleanup_dev_usage_gcloud.sh --delete

set -e

# Configuration
PROJECT_ID="lls-study-portal"
COLLECTION="llm_usage"
DEV_EMAIL="dev@mgms.eu"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔍 Querying usage records for ${DEV_EMAIL}...${NC}"

# Query for dev@mgms.eu records
# Note: Firestore CLI doesn't support complex queries, so we'll use a Python one-liner
QUERY_SCRIPT=$(cat <<'EOF'
import sys
from google.cloud import firestore

db = firestore.Client(project="lls-study-portal")
query = db.collection("llm_usage").where("user_email", "==", "dev@mgms.eu")
docs = list(query.stream())

print(f"\n{'='*80}")
print(f"📊 Found {len(docs)} records for dev@mgms.eu")
print(f"{'='*80}\n")

if len(docs) == 0:
    print("✅ No records found")
    sys.exit(0)

# Calculate statistics
total_cost = 0
total_input = 0
total_output = 0
total_cache_creation = 0
total_cache_read = 0
operations = {}
models = {}
timestamps = []

for doc in docs:
    data = doc.to_dict()
    total_cost += data.get('estimated_cost_usd', 0)
    total_input += data.get('input_tokens', 0)
    total_output += data.get('output_tokens', 0)
    total_cache_creation += data.get('cache_creation_tokens', 0)
    total_cache_read += data.get('cache_read_tokens', 0)
    
    op = data.get('operation_type', 'unknown')
    operations[op] = operations.get(op, 0) + 1
    
    model = data.get('model', 'unknown')
    models[model] = models.get(model, 0) + 1
    
    if 'timestamp' in data:
        timestamps.append(data['timestamp'])

print(f"💰 Total Cost: ${total_cost:.2f}")
print(f"📝 Total Input Tokens: {total_input:,}")
print(f"📤 Total Output Tokens: {total_output:,}")
print(f"💾 Total Cache Creation Tokens: {total_cache_creation:,}")
print(f"📖 Total Cache Read Tokens: {total_cache_read:,}")

if timestamps:
    earliest = min(timestamps)
    latest = max(timestamps)
    print(f"\n📅 Date Range: {earliest.date()} to {latest.date()}")

print(f"\n🔧 Operations:")
for op, count in sorted(operations.items(), key=lambda x: x[1], reverse=True):
    print(f"  - {op}: {count}")

print(f"\n🤖 Models:")
for model, count in sorted(models.items(), key=lambda x: x[1], reverse=True):
    print(f"  - {model}: {count}")

print(f"\n{'='*80}")

# Print document IDs for deletion
print("\n📋 Document IDs:")
for doc in docs[:10]:  # Show first 10
    print(f"  - {doc.id}")
if len(docs) > 10:
    print(f"  ... and {len(docs) - 10} more")

# Save IDs to file for deletion
with open('/tmp/dev_usage_ids.txt', 'w') as f:
    for doc in docs:
        f.write(f"{doc.id}\n")

print(f"\n💾 Saved {len(docs)} document IDs to /tmp/dev_usage_ids.txt")
EOF
)

# Run the query
python3 -c "$QUERY_SCRIPT"

# Check if delete flag is set
if [ "$1" == "--delete" ]; then
    echo -e "\n${RED}⚠️  WARNING: This will permanently delete all records for ${DEV_EMAIL}!${NC}"
    read -p "Type 'DELETE' to confirm: " confirmation
    
    if [ "$confirmation" != "DELETE" ]; then
        echo -e "${YELLOW}❌ Deletion cancelled${NC}"
        exit 0
    fi
    
    echo -e "\n${BLUE}🗑️  Deleting records...${NC}"
    
    # Delete using Python
    DELETE_SCRIPT=$(cat <<'EOF'
from google.cloud import firestore

db = firestore.Client(project="lls-study-portal")

# Read IDs from file
with open('/tmp/dev_usage_ids.txt', 'r') as f:
    doc_ids = [line.strip() for line in f if line.strip()]

print(f"Deleting {len(doc_ids)} documents...")

deleted = 0
for doc_id in doc_ids:
    try:
        db.collection("llm_usage").document(doc_id).delete()
        deleted += 1
        if deleted % 10 == 0:
            print(f"  Deleted {deleted}/{len(doc_ids)}...")
    except Exception as e:
        print(f"❌ Error deleting {doc_id}: {e}")

print(f"\n✅ Successfully deleted {deleted} records")
EOF
)
    
    python3 -c "$DELETE_SCRIPT"
    
    echo -e "\n${GREEN}✅ Cleanup complete!${NC}"
    
    # Clean up temp file
    rm -f /tmp/dev_usage_ids.txt
else
    echo -e "\n${YELLOW}💡 To delete these records, run: $0 --delete${NC}"
fi

