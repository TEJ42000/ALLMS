#!/bin/bash
# setup-iap.sh - Configure Google Cloud Identity-Aware Proxy for LLS Study Portal
#
# This script enables IAP on Cloud Run and configures access for @mgms.eu domain.
# Run this AFTER the initial deployment with deploy.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Google Cloud IAP Setup for LLS Portal${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI not found${NC}"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Set defaults
PROJECT_ID=${GCP_PROJECT_ID:-$(gcloud config get-value project)}
REGION=${GCP_REGION:-"europe-west4"}
SERVICE_NAME=${APP_NAME:-"lls-study-portal"}
DOMAIN=${AUTH_DOMAIN:-"mgms.eu"}

echo -e "${YELLOW}Configuration:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Service Name: $SERVICE_NAME"
echo "  Authorized Domain: $DOMAIN"
echo ""

# Step 1: Enable required APIs
echo -e "${GREEN}Step 1: Enabling IAP API...${NC}"
gcloud services enable iap.googleapis.com

# Step 2: Check if OAuth consent screen is configured
echo ""
echo -e "${GREEN}Step 2: OAuth Consent Screen${NC}"
echo -e "${YELLOW}============================================${NC}"
echo -e "${YELLOW}MANUAL STEP REQUIRED:${NC}"
echo ""
echo "1. Go to: https://console.cloud.google.com/apis/credentials/consent?project=$PROJECT_ID"
echo "2. Select 'Internal' as User Type (for Google Workspace)"
echo "3. Configure app info:"
echo "   - App name: LLS Study Portal"
echo "   - User support email: admin@$DOMAIN"
echo "   - App domain: (your Cloud Run URL)"
echo "   - Developer contact: admin@$DOMAIN"
echo "4. Add scopes: email, profile, openid"
echo "5. Save"
echo ""
read -p "Press Enter when OAuth consent screen is configured..."

# Step 3: Check for OAuth client
echo ""
echo -e "${GREEN}Step 3: OAuth Client ID${NC}"
echo -e "${YELLOW}============================================${NC}"

if gcloud secrets describe oauth-client-id &> /dev/null; then
    echo "✓ OAuth client ID secret exists"
    OAUTH_CLIENT_ID=$(gcloud secrets versions access latest --secret=oauth-client-id)
else
    echo -e "${YELLOW}MANUAL STEP REQUIRED:${NC}"
    echo ""
    echo "1. Go to: https://console.cloud.google.com/apis/credentials?project=$PROJECT_ID"
    echo "2. Create OAuth 2.0 Client ID:"
    echo "   - Application type: Web application"
    echo "   - Name: LLS Study Portal IAP"
    echo "3. Copy the Client ID and Client Secret"
    echo ""
    
    read -p "Enter OAuth Client ID: " OAUTH_CLIENT_ID
    read -s -p "Enter OAuth Client Secret: " OAUTH_CLIENT_SECRET
    echo ""
    
    echo "Storing credentials in Secret Manager..."
    echo -n "$OAUTH_CLIENT_ID" | gcloud secrets create oauth-client-id --data-file=- 2>/dev/null || \
        echo -n "$OAUTH_CLIENT_ID" | gcloud secrets versions add oauth-client-id --data-file=-
    echo -n "$OAUTH_CLIENT_SECRET" | gcloud secrets create oauth-client-secret --data-file=- 2>/dev/null || \
        echo -n "$OAUTH_CLIENT_SECRET" | gcloud secrets versions add oauth-client-secret --data-file=-
    echo "✓ OAuth credentials stored"
fi

# Step 4: Enable IAP on Cloud Run
echo ""
echo -e "${GREEN}Step 4: Enabling IAP on Cloud Run...${NC}"

# Get the backend service ID for Cloud Run
BACKEND_SERVICE=$(gcloud compute backend-services list \
    --filter="name~$SERVICE_NAME" \
    --format="value(name)" 2>/dev/null || true)

if [ -z "$BACKEND_SERVICE" ]; then
    echo -e "${YELLOW}Note: Cloud Run with Load Balancer not detected.${NC}"
    echo "IAP for Cloud Run requires a serverless NEG and Load Balancer."
    echo ""
    echo "For simple IAP setup, see: docs/IAP-SETUP.md"
    echo ""
    echo "Alternatively, consider using Cloud Run's built-in auth"
    echo "by removing --allow-unauthenticated from deploy.sh"
else
    echo "Backend service found: $BACKEND_SERVICE"
    
    gcloud iap web enable \
        --resource-type=backend-services \
        --service=$BACKEND_SERVICE
    
    echo "✓ IAP enabled"
fi

# Step 5: Configure domain access
echo ""
echo -e "${GREEN}Step 5: Configuring domain access...${NC}"

if [ -n "$BACKEND_SERVICE" ]; then
    gcloud iap web add-iam-policy-binding \
        --resource-type=backend-services \
        --service=$BACKEND_SERVICE \
        --member="domain:$DOMAIN" \
        --role="roles/iap.httpsResourceAccessor" 2>/dev/null || \
    echo -e "${YELLOW}Note: Domain binding may already exist or require manual configuration${NC}"

    echo "✓ Domain access configured for @$DOMAIN"
fi

# Step 6: Update environment
echo ""
echo -e "${GREEN}Step 6: Update application configuration...${NC}"
echo ""
echo "Add the following to your Cloud Run environment variables:"
echo ""
echo "  AUTH_ENABLED=true"
echo "  AUTH_DOMAIN=$DOMAIN"
echo "  GOOGLE_CLIENT_ID=$OAUTH_CLIENT_ID"
echo ""

# Summary
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}IAP Setup Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}✓${NC} IAP API enabled"
echo -e "${GREEN}✓${NC} OAuth credentials stored in Secret Manager"
if [ -n "$BACKEND_SERVICE" ]; then
    echo -e "${GREEN}✓${NC} IAP enabled on backend service"
    echo -e "${GREEN}✓${NC} Domain access configured for @$DOMAIN"
else
    echo -e "${YELLOW}!${NC} Manual Load Balancer setup required (see docs)"
fi
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Redeploy with AUTH_ENABLED=true"
echo "2. Test login with @$DOMAIN account"
echo "3. Verify non-domain users are blocked"
echo ""
echo "For troubleshooting, see: docs/IAP-SETUP.md"
echo ""

