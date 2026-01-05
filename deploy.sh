#!/bin/bash
# deploy.sh - Deploy LLS Study Portal to Google Cloud Run

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Parse command line arguments
ENABLE_IAP=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --with-iap)
            ENABLE_IAP=true
            shift
            ;;
        --help|-h)
            echo "Usage: ./deploy.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --with-iap    Enable IAP authentication (blocks public access)"
            echo "  --help, -h    Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./deploy.sh              # Deploy with public access"
            echo "  ./deploy.sh --with-iap   # Deploy with IAP authentication"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}LLS Study Portal - Cloud Run Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
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
else
    echo -e "${YELLOW}Warning: .env file not found${NC}"
    echo "Using default values..."
fi

# Set default values if not in .env
PROJECT_ID=${GCP_PROJECT_ID:-"your-project-id"}
REGION=${GCP_REGION:-"us-central1"}
SERVICE_NAME=${APP_NAME:-"lls-study-portal"}

echo -e "${YELLOW}Configuration:${NC}"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Service Name: $SERVICE_NAME"
if [ "$ENABLE_IAP" = true ]; then
    echo -e "  Authentication: ${BLUE}IAP Enabled${NC}"
else
    echo -e "  Authentication: ${YELLOW}Public Access${NC}"
fi
echo ""

# Confirm deployment
if [ "$ENABLE_IAP" = true ]; then
    echo -e "${YELLOW}⚠️  IAP mode: Service will require Google login${NC}"
fi
read -p "Deploy to Google Cloud Run? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled"
    exit 0
fi

echo -e "${GREEN}Step 1: Setting project...${NC}"
gcloud config set project $PROJECT_ID

echo -e "${GREEN}Step 2: Enabling required APIs...${NC}"
gcloud services enable run.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable cloudbuild.googleapis.com

echo -e "${GREEN}Step 3: Checking API key in Secret Manager...${NC}"
if gcloud secrets describe anthropic-api-key &> /dev/null; then
    echo "✓ Secret 'anthropic-api-key' exists"
else
    echo -e "${YELLOW}Creating secret 'anthropic-api-key'...${NC}"
    echo -n "Enter your Anthropic API key: "
    read -s API_KEY
    echo ""
    echo -n "$API_KEY" | gcloud secrets create anthropic-api-key --data-file=-
    echo "✓ Secret created"
fi

echo -e "${GREEN}Step 4: Deploying to Cloud Run...${NC}"

# Build deployment command
DEPLOY_CMD="gcloud run deploy $SERVICE_NAME \
    --source . \
    --region $REGION \
    --platform managed \
    --set-secrets=ANTHROPIC_API_KEY=anthropic-api-key:latest \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 10 \
    --timeout 300 \
    --port 8080"

if [ "$ENABLE_IAP" = true ]; then
    # IAP mode: require authentication, enable auth in app
    DEPLOY_CMD="$DEPLOY_CMD \
        --no-allow-unauthenticated \
        --set-env-vars=AUTH_ENABLED=true,AUTH_DOMAIN=mgms.eu"
else
    # Public mode: allow unauthenticated, disable auth in app
    DEPLOY_CMD="$DEPLOY_CMD \
        --allow-unauthenticated \
        --set-env-vars=AUTH_ENABLED=false"
fi

eval $DEPLOY_CMD

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)')
echo ""
echo -e "${GREEN}Service URL:${NC} $SERVICE_URL"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
if [ "$ENABLE_IAP" = true ]; then
    echo "  1. Run: ./scripts/setup-iap.sh"
    echo "  2. Configure OAuth consent screen (see docs/IAP-SETUP.md)"
    echo "  3. Access via Load Balancer URL (not Cloud Run URL directly)"
else
    echo "  1. Visit your app at: $SERVICE_URL"
    echo "  2. Test the API docs: $SERVICE_URL/api/docs"
fi
echo "  📊 Monitor logs: gcloud run services logs read $SERVICE_NAME --region $REGION"
echo ""
if [ "$ENABLE_IAP" = true ]; then
    echo -e "${BLUE}📖 For IAP setup, see: docs/IAP-SETUP.md${NC}"
    echo ""
fi
