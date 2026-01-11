#!/bin/bash
# Monitor v2.11.3 deployment and provide automatic updates

RUN_ID="20867532156"
CHECK_INTERVAL=30  # Check every 30 seconds

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                                                                      ║"
echo "║              🚀 MONITORING v2.11.3 DEPLOYMENT 🚀                    ║"
echo "║                                                                      ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "Deployment: v2.11.3 (Allow List Logging Enhancement)"
echo "Run ID: ${RUN_ID}"
echo "Started: 22:34:01 UTC"
echo "URL: https://github.com/TEJ42000/ALLMS/actions/runs/${RUN_ID}"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

LAST_STATUS=""
UPDATE_COUNT=0

while true; do
    # Get current status
    RESPONSE=$(gh api /repos/TEJ42000/ALLMS/actions/runs/${RUN_ID} 2>&1)
    
    if [ $? -ne 0 ]; then
        echo "⚠️  [$(date +%H:%M:%S)] Warning: Failed to fetch status"
        sleep $CHECK_INTERVAL
        continue
    fi
    
    STATUS=$(echo "$RESPONSE" | jq -r '.status')
    CONCLUSION=$(echo "$RESPONSE" | jq -r '.conclusion')
    UPDATED=$(echo "$RESPONSE" | jq -r '.updated_at')
    
    # Calculate elapsed time
    START_TIME="2026-01-09T22:34:01Z"
    CURRENT_TIME=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    
    # Only report if status changed or every 2 minutes
    UPDATE_COUNT=$((UPDATE_COUNT + 1))
    
    if [ "$STATUS" != "$LAST_STATUS" ] || [ $((UPDATE_COUNT % 4)) -eq 0 ]; then
        echo "📊 [$(date +%H:%M:%S)] Status Update #$((UPDATE_COUNT / 4 + 1))"
        echo "   Status: $STATUS"
        
        if [ "$STATUS" = "in_progress" ]; then
            echo "   ⏳ Deployment in progress..."
            echo "   🔄 Running tests, building Docker image, deploying to Cloud Run"
        fi
        
        echo ""
        LAST_STATUS="$STATUS"
    fi
    
    # Check if completed
    if [ "$STATUS" = "completed" ]; then
        echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        echo ""
        
        if [ "$CONCLUSION" = "success" ]; then
            echo "╔══════════════════════════════════════════════════════════════════════╗"
            echo "║                                                                      ║"
            echo "║                  ✅ DEPLOYMENT SUCCESSFUL! ✅                       ║"
            echo "║                                                                      ║"
            echo "╚══════════════════════════════════════════════════════════════════════╝"
            echo ""
            echo "🎉 v2.11.3 is now LIVE in production!"
            echo ""
            echo "Deployment Details:"
            echo "  • Version: v2.11.3"
            echo "  • Completed: $(date -u +%H:%M:%S) UTC"
            echo "  • Duration: ~$((UPDATE_COUNT * CHECK_INTERVAL / 60)) minutes"
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            echo "📋 NEXT STEPS:"
            echo ""
            echo "1. Have user (amberunal13@gmail.com) try to log in again"
            echo "   → Go to: https://lls-study-portal-sarfwmfd3q-ez.a.run.app"
            echo "   → Click 'Login with Google'"
            echo "   → Log in with amberunal13@gmail.com"
            echo ""
            echo "2. Check production logs for detailed error:"
            echo "   → Run: ./check_production_logs.sh"
            echo "   → Or manually check Cloud Run logs"
            echo ""
            echo "3. Look for these log messages:"
            echo "   ✅ '✅ ALLOW LIST: Service available, checking user: amberunal13@gmail.com'"
            echo "   ✅ '✅ ALLOW LIST: User amberunal13@gmail.com is ALLOWED'"
            echo "   OR"
            echo "   ❌ '❌ ALLOW LIST: Service not available (Firestore client is None)'"
            echo "   ❌ '❌ ALLOW LIST: User amberunal13@gmail.com NOT FOUND in Firestore'"
            echo "   ❌ '❌ ALLOW LIST: User found but NOT EFFECTIVE (active=...)'"
            echo ""
            echo "4. Based on logs, we'll know EXACTLY what to fix"
            echo ""
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
            echo ""
            echo "🔍 To check logs now, run:"
            echo "   gcloud logging read \"resource.type=cloud_run_revision AND resource.labels.service_name=lls-study-portal AND textPayload=~'ALLOW LIST'\" --limit 20 --project=vigilant-axis-483119-r8 --format='table(timestamp, textPayload)' --freshness=5m"
            echo ""
            
        else
            echo "╔══════════════════════════════════════════════════════════════════════╗"
            echo "║                                                                      ║"
            echo "║                   ❌ DEPLOYMENT FAILED! ❌                          ║"
            echo "║                                                                      ║"
            echo "╚══════════════════════════════════════════════════════════════════════╝"
            echo ""
            echo "Conclusion: $CONCLUSION"
            echo "Check logs: https://github.com/TEJ42000/ALLMS/actions/runs/${RUN_ID}"
            echo ""
        fi
        
        break
    fi
    
    # Wait before next check
    sleep $CHECK_INTERVAL
done

echo ""
echo "Monitoring complete."
echo ""

