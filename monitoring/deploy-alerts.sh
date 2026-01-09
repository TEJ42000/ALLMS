#!/bin/bash
# Deploy Cloud Monitoring Alert Policies
#
# This script deploys alert policies for the rate limiter system.
# It creates notification channels and alert policies in Google Cloud Monitoring.
#
# Prerequisites:
# - gcloud CLI installed and authenticated
# - Project: vigilant-axis-483119-r8
# - Permissions: monitoring.alertPolicies.create, monitoring.notificationChannels.create
#
# Usage:
#   ./monitoring/deploy-alerts.sh [--email EMAIL] [--dry-run]
#
# Options:
#   --email EMAIL    Email address for notifications (default: ops@mgms.eu)
#   --dry-run        Show what would be deployed without actually deploying
#   --help           Show this help message

set -e  # Exit on error

# Configuration
PROJECT_ID="vigilant-axis-483119-r8"
REGION="europe-west4"
DEFAULT_EMAIL="ops@mgms.eu"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
EMAIL="$DEFAULT_EMAIL"
DRY_RUN=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --email)
            EMAIL="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --help)
            head -n 20 "$0" | tail -n +2 | sed 's/^# //'
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}=== Deploying Rate Limiter Alert Policies ===${NC}"
echo "Project: $PROJECT_ID"
echo "Email: $EMAIL"
echo "Dry Run: $DRY_RUN"
echo ""

# Function to create notification channel
create_notification_channel() {
    local channel_name=$1
    local channel_type=$2
    local channel_email=$3
    
    echo -e "${YELLOW}Creating notification channel: $channel_name${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        echo "[DRY RUN] Would create $channel_type notification channel for $channel_email"
        echo "projects/$PROJECT_ID/notificationChannels/dry-run-$channel_name"
        return
    fi
    
    # Check if channel already exists
    existing_channel=$(gcloud alpha monitoring channels list \
        --project="$PROJECT_ID" \
        --filter="displayName='$channel_name'" \
        --format="value(name)" 2>/dev/null || true)
    
    if [ -n "$existing_channel" ]; then
        echo -e "${GREEN}✓ Channel already exists: $existing_channel${NC}"
        echo "$existing_channel"
        return
    fi
    
    # Create new channel
    case $channel_type in
        email)
            channel_id=$(gcloud alpha monitoring channels create \
                --display-name="$channel_name" \
                --type=email \
                --channel-labels=email_address="$channel_email" \
                --project="$PROJECT_ID" \
                --format="value(name)")
            ;;
        *)
            echo -e "${RED}✗ Unknown channel type: $channel_type${NC}"
            exit 1
            ;;
    esac
    
    echo -e "${GREEN}✓ Created channel: $channel_id${NC}"
    echo "$channel_id"
}

# Function to deploy alert policy
deploy_alert_policy() {
    local policy_file=$1
    local policy_name=$(basename "$policy_file" .yaml)
    local notification_channel=$2
    
    echo -e "${YELLOW}Deploying alert policy: $policy_name${NC}"
    
    if [ "$DRY_RUN" = true ]; then
        echo "[DRY RUN] Would deploy policy from $policy_file"
        echo "[DRY RUN] With notification channel: $notification_channel"
        return
    fi
    
    # Check if policy already exists
    existing_policy=$(gcloud alpha monitoring policies list \
        --project="$PROJECT_ID" \
        --filter="displayName~'$(grep "^displayName:" "$policy_file" | cut -d'"' -f2)'" \
        --format="value(name)" 2>/dev/null || true)
    
    if [ -n "$existing_policy" ]; then
        echo -e "${YELLOW}⚠ Policy already exists: $existing_policy${NC}"
        read -p "Update existing policy? (y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Skipping..."
            return
        fi
        
        # Update existing policy
        gcloud alpha monitoring policies update "$existing_policy" \
            --notification-channels="$notification_channel" \
            --policy-from-file="$policy_file" \
            --project="$PROJECT_ID"
        
        echo -e "${GREEN}✓ Updated policy: $existing_policy${NC}"
    else
        # Create new policy
        policy_id=$(gcloud alpha monitoring policies create \
            --notification-channels="$notification_channel" \
            --policy-from-file="$policy_file" \
            --project="$PROJECT_ID" \
            --format="value(name)")
        
        echo -e "${GREEN}✓ Created policy: $policy_id${NC}"
    fi
}

# Step 1: Create notification channels
echo -e "${GREEN}Step 1: Creating notification channels${NC}"
echo ""

ops_email_channel=$(create_notification_channel \
    "Ops Team Email" \
    "email" \
    "$EMAIL")

echo ""

# Step 2: Deploy alert policies
echo -e "${GREEN}Step 2: Deploying alert policies${NC}"
echo ""

# Deploy Redis connection failure alert (CRITICAL)
deploy_alert_policy \
    "monitoring/alert-redis-connection.yaml" \
    "$ops_email_channel"

echo ""

# Deploy rate limiter backend failure alert (HIGH)
deploy_alert_policy \
    "monitoring/alert-rate-limiter-failure.yaml" \
    "$ops_email_channel"

echo ""

# Deploy high rate limit hits alert (MEDIUM)
deploy_alert_policy \
    "monitoring/alert-rate-limit-capacity.yaml" \
    "$ops_email_channel"

echo ""

# Step 3: Summary
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "Alert policies deployed:"
echo "  1. Redis Connection Failure (CRITICAL)"
echo "  2. Rate Limiter Backend Failure (HIGH)"
echo "  3. High Rate Limit Hits (MEDIUM)"
echo ""
echo "Notification channel:"
echo "  Email: $EMAIL"
echo ""
echo "View alerts in Cloud Console:"
echo "  https://console.cloud.google.com/monitoring/alerting/policies?project=$PROJECT_ID"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "  1. Test alerts by simulating failures"
echo "  2. Review runbook: docs/runbooks/rate-limiter-alerts.md"
echo "  3. Configure additional channels (Slack, PagerDuty) if needed"
echo ""

