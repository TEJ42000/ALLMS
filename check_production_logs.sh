#!/bin/bash
# Check production logs for amberunal13@gmail.com authentication attempts

echo "🔍 Checking production logs for amberunal13@gmail.com..."
echo ""

gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=lls-study-portal AND textPayload=~\"amberunal13@gmail.com\"" \
  --limit 50 \
  --project=vigilant-axis-483119-r8 \
  --format="table(timestamp, severity, textPayload)" \
  --freshness=1h

echo ""
echo "─────────────────────────────────────────────────────────────────"
echo ""
echo "🔍 Checking for allow list check failures..."
echo ""

gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=lls-study-portal AND (textPayload=~\"allow list\" OR textPayload=~\"Allow list\")" \
  --limit 50 \
  --project=vigilant-axis-483119-r8 \
  --format="table(timestamp, severity, textPayload)" \
  --freshness=1h

