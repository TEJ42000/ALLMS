#!/bin/bash
# Automatically diagnose the allow list issue and start working on the fix

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                      ║"
echo "║           🔍 AUTO-DIAGNOSE ALLOW LIST ISSUE 🔍                      ║"
echo "║                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Wait for deployment to complete
echo "⏳ Waiting for v2.11.3 deployment to complete..."
echo ""

RUN_ID="20867532156"

while true; do
    STATUS=$(gh api /repos/TEJ42000/ALLMS/actions/runs/${RUN_ID} --jq '.status' 2>/dev/null)
    
    if [ "$STATUS" = "completed" ]; then
        CONCLUSION=$(gh api /repos/TEJ42000/ALLMS/actions/runs/${RUN_ID} --jq '.conclusion' 2>/dev/null)
        
        if [ "$CONCLUSION" = "success" ]; then
            echo "✅ Deployment completed successfully!"
            echo ""
            break
        else
            echo "❌ Deployment failed with conclusion: $CONCLUSION"
            echo "Cannot proceed with diagnosis."
            exit 1
        fi
    fi
    
    echo "   Status: $STATUS - waiting..."
    sleep 30
done

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔍 STEP 1: Checking production logs for allow list errors..."
echo ""

# Check logs for the user's login attempts
LOGS=$(gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=lls-study-portal AND (textPayload=~'amberunal13@gmail.com' OR textPayload=~'ALLOW LIST')" \
  --limit 50 \
  --project=vigilant-axis-483119-r8 \
  --format=json \
  --freshness=10m 2>&1)

if [ $? -ne 0 ]; then
    echo "⚠️  Warning: Could not fetch logs. Error:"
    echo "$LOGS"
    echo ""
    echo "Please check logs manually:"
    echo "gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=lls-study-portal AND textPayload=~'ALLOW LIST'\" --limit 20 --project=vigilant-axis-483119-r8 --format='table(timestamp, textPayload)' --freshness=10m"
    exit 1
fi

echo "📋 Recent logs retrieved. Analyzing..."
echo ""

# Parse logs to find the issue
SERVICE_NOT_AVAILABLE=$(echo "$LOGS" | grep -c "Service not available")
USER_NOT_FOUND=$(echo "$LOGS" | grep -c "NOT FOUND in Firestore")
USER_NOT_EFFECTIVE=$(echo "$LOGS" | grep -c "found but NOT EFFECTIVE")
USER_ALLOWED=$(echo "$LOGS" | grep -c "is ALLOWED")

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 DIAGNOSIS RESULTS:"
echo ""

if [ $USER_ALLOWED -gt 0 ]; then
    echo "✅ User IS ALLOWED according to logs!"
    echo "   Found $USER_ALLOWED log entries showing user is allowed."
    echo ""
    echo "🤔 If user still can't access, the issue is likely:"
    echo "   1. Browser cache (user needs incognito window)"
    echo "   2. OAuth session issue"
    echo "   3. Different authentication path being used"
    echo ""
    echo "RECOMMENDATION: Have user try in incognito window again."
    exit 0
fi

if [ $SERVICE_NOT_AVAILABLE -gt 0 ]; then
    echo "❌ ISSUE FOUND: Allow List Service Not Available"
    echo "   Firestore client is returning None in production"
    echo ""
    echo "🔧 ROOT CAUSE: Firestore initialization issue"
    echo ""
    echo "POSSIBLE FIXES:"
    echo "1. Check GCP_PROJECT_ID environment variable in Cloud Run"
    echo "2. Check service account permissions for Firestore"
    echo "3. Check if Firestore is enabled in the project"
    echo ""
    echo "Creating fix script..."
    
    cat > fix_firestore_init.md << 'EOF'
# Fix: Firestore Service Not Available

## Issue
Allow list service reports "Service not available (Firestore client is None)"

## Root Cause
Firestore client is not initializing in production Cloud Run environment.

## Fixes to Try

### Fix 1: Check Environment Variables
```bash
gcloud run services describe lls-study-portal \
  --region=europe-west4 \
  --project=vigilant-axis-483119-r8 \
  --format='value(spec.template.spec.containers[0].env)'
```

Ensure GCP_PROJECT_ID is set to: vigilant-axis-483119-r8

### Fix 2: Check Service Account Permissions
```bash
gcloud run services describe lls-study-portal \
  --region=europe-west4 \
  --project=vigilant-axis-483119-r8 \
  --format='value(spec.template.spec.serviceAccountName)'
```

Service account needs: roles/datastore.user

### Fix 3: Add Explicit Project ID to Firestore Client
In app/services/gcp_service.py, change:
```python
db = firestore.Client()
```
to:
```python
db = firestore.Client(project='vigilant-axis-483119-r8')
```
EOF
    
    echo "✅ Fix guide created: fix_firestore_init.md"
    exit 0
fi

if [ $USER_NOT_FOUND -gt 0 ]; then
    echo "❌ ISSUE FOUND: User Not Found in Firestore"
    echo "   User amberunal13@gmail.com does not exist in 'allowed_users' collection"
    echo ""
    echo "🔧 ROOT CAUSE: User was not actually added to Firestore"
    echo ""
    echo "FIX: Add user directly to Firestore"
    echo ""
    echo "Running fix script..."
    
    # Create Python script to add user
    cat > add_user_to_firestore.py << 'EOF'
from google.cloud import firestore
from datetime import datetime, timezone

db = firestore.Client(project='vigilant-axis-483119-r8')
doc_id = 'amberunal13%40gmail.com'

user_data = {
    'email': 'amberunal13@gmail.com',
    'active': True,
    'added_by': 'matej@mgms.eu',
    'added_at': datetime.now(timezone.utc),
    'updated_at': datetime.now(timezone.utc),
    'reason': 'External student access - auto-added by diagnostic script',
    'expires_at': None,
    'notes': None
}

print(f"Adding user to Firestore...")
db.collection('allowed_users').document(doc_id).set(user_data)
print(f"✅ User added successfully!")
print(f"User can now try logging in again.")
EOF
    
    echo "Running: python add_user_to_firestore.py"
    python add_user_to_firestore.py
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ User added to Firestore!"
        echo "Have user try logging in again."
    else
        echo ""
        echo "❌ Failed to add user. Try manually in Firestore Console."
    fi
    
    exit 0
fi

if [ $USER_NOT_EFFECTIVE -gt 0 ]; then
    echo "❌ ISSUE FOUND: User Found But Not Effective"
    echo "   User exists in Firestore but active=false or expired=true"
    echo ""
    
    # Extract the actual values from logs
    DETAILS=$(echo "$LOGS" | grep "found but NOT EFFECTIVE" | head -1)
    echo "Details: $DETAILS"
    echo ""
    
    echo "🔧 ROOT CAUSE: User's active flag is false or user is expired"
    echo ""
    echo "FIX: Update user's active status"
    echo ""
    echo "Running fix script..."
    
    cat > fix_user_active.py << 'EOF'
from google.cloud import firestore
from datetime import datetime, timezone

db = firestore.Client(project='vigilant-axis-483119-r8')
doc_id = 'amberunal13%40gmail.com'

print(f"Updating user in Firestore...")
db.collection('allowed_users').document(doc_id).update({
    'active': True,
    'expires_at': None,
    'updated_at': datetime.now(timezone.utc)
})
print(f"✅ User updated successfully!")
print(f"User can now try logging in again.")
EOF
    
    echo "Running: python fix_user_active.py"
    python fix_user_active.py
    
    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ User updated in Firestore!"
        echo "Have user try logging in again."
    else
        echo ""
        echo "❌ Failed to update user. Try manually in Firestore Console."
    fi
    
    exit 0
fi

echo "⚠️  NO SPECIFIC ISSUE FOUND IN LOGS"
echo ""
echo "This could mean:"
echo "1. User hasn't tried to log in since deployment"
echo "2. Logs haven't propagated yet (wait 1-2 minutes)"
echo "3. User is using a different authentication path"
echo ""
echo "NEXT STEPS:"
echo "1. Have user try to log in NOW"
echo "2. Wait 1 minute"
echo "3. Run this script again"
echo ""
echo "Or check logs manually:"
echo "gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=lls-study-portal AND textPayload=~'ALLOW LIST'\" --limit 20 --project=vigilant-axis-483119-r8 --format='table(timestamp, textPayload)' --freshness=5m"
echo ""

