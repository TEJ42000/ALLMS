#!/bin/bash
# Monitor deployment status and report updates

RUN_ID="20866884251"
LAST_STATUS=""

echo "🔍 Monitoring deployment run #40..."
echo "Started: 22:04:18 UTC"
echo "URL: https://github.com/TEJ42000/ALLMS/actions/runs/${RUN_ID}"
echo ""

while true; do
    # Get current status
    STATUS=$(gh api /repos/TEJ42000/ALLMS/actions/runs/${RUN_ID} --jq '.status')
    CONCLUSION=$(gh api /repos/TEJ42000/ALLMS/actions/runs/${RUN_ID} --jq '.conclusion')
    UPDATED=$(gh api /repos/TEJ42000/ALLMS/actions/runs/${RUN_ID} --jq '.updated_at')
    
    # Only report if status changed
    if [ "$STATUS" != "$LAST_STATUS" ]; then
        echo "[$(date +%H:%M:%S)] Status: $STATUS"
        LAST_STATUS="$STATUS"
    fi
    
    # Check if completed
    if [ "$STATUS" = "completed" ]; then
        echo ""
        echo "✅ DEPLOYMENT COMPLETED!"
        echo "Conclusion: $CONCLUSION"
        echo "Finished: $UPDATED"
        
        if [ "$CONCLUSION" = "success" ]; then
            echo ""
            echo "🎉 SUCCESS! The fix is now deployed to production!"
            echo ""
            echo "Next steps:"
            echo "1. Go to: https://lls-study-portal-sarfwmfd3q-ez.a.run.app/admin/users"
            echo "2. Click 'Add User'"
            echo "3. Email: amberunal13@gmail.com"
            echo "4. Reason: External student access"
            echo "5. Click 'Add'"
        else
            echo ""
            echo "❌ DEPLOYMENT FAILED!"
            echo "Check logs: https://github.com/TEJ42000/ALLMS/actions/runs/${RUN_ID}"
        fi
        
        break
    fi
    
    # Wait 30 seconds before checking again
    sleep 30
done

