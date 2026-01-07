#!/bin/bash
# Deploy Firestore indexes for essay assessment feature
#
# This script creates the required composite indexes for the assessmentAttempts collection
# These indexes are needed for querying user history with sorting

set -e

PROJECT_ID="vigilant-axis-483119-r8"
DATABASE="(default)"

echo "🔥 Deploying Firestore Indexes for Essay Assessment"
echo "Project: $PROJECT_ID"
echo "Database: $DATABASE"
echo ""

# Index 1: assessmentId + submittedAt (for getting attempts by assessment)
echo "Creating index: assessmentAttempts (assessmentId ASC, submittedAt DESC)..."
gcloud firestore indexes composite create \
  --project="$PROJECT_ID" \
  --database="$DATABASE" \
  --collection-group=assessmentAttempts \
  --field-config field-path=assessmentId,order=ascending \
  --field-config field-path=submittedAt,order=descending \
  --quiet || echo "Index may already exist"

# Index 2: userId + submittedAt (for getting user history)
echo "Creating index: assessmentAttempts (userId ASC, submittedAt DESC)..."
gcloud firestore indexes composite create \
  --project="$PROJECT_ID" \
  --database="$DATABASE" \
  --collection-group=assessmentAttempts \
  --field-config field-path=userId,order=ascending \
  --field-config field-path=submittedAt,order=descending \
  --quiet || echo "Index may already exist"

# Index 3: userId + courseId + submittedAt (for getting user history filtered by course)
echo "Creating index: assessmentAttempts (userId ASC, courseId ASC, submittedAt DESC)..."
gcloud firestore indexes composite create \
  --project="$PROJECT_ID" \
  --database="$DATABASE" \
  --collection-group=assessmentAttempts \
  --field-config field-path=userId,order=ascending \
  --field-config field-path=courseId,order=ascending \
  --field-config field-path=submittedAt,order=descending \
  --quiet || echo "Index may already exist"

# Index 4: assessments createdAt (for listing assessments)
echo "Creating index: assessments (createdAt DESC)..."
gcloud firestore indexes composite create \
  --project="$PROJECT_ID" \
  --database="$DATABASE" \
  --collection-group=assessments \
  --field-config field-path=createdAt,order=descending \
  --quiet || echo "Index may already exist"

# Index 5: assessments topic + createdAt (for filtering by topic)
echo "Creating index: assessments (topic ASC, createdAt DESC)..."
gcloud firestore indexes composite create \
  --project="$PROJECT_ID" \
  --database="$DATABASE" \
  --collection-group=assessments \
  --field-config field-path=topic,order=ascending \
  --field-config field-path=createdAt,order=descending \
  --quiet || echo "Index may already exist"

echo ""
echo "✅ Index creation commands submitted!"
echo ""
echo "⏳ Note: Indexes take 5-15 minutes to build."
echo "   Check status at: https://console.cloud.google.com/firestore/indexes?project=$PROJECT_ID"
echo ""
echo "   Or run: gcloud firestore indexes composite list --project=$PROJECT_ID --database=$DATABASE"

