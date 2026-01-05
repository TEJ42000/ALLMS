#!/bin/bash
# setup-gcp-github-actions.sh
# Sets up Google Cloud Workload Identity Federation for GitHub Actions deployment
#
# Usage: ./scripts/setup-gcp-github-actions.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}======================================================${NC}"
echo -e "${BLUE}  GitHub Actions + Google Cloud Setup Script${NC}"
echo -e "${BLUE}======================================================${NC}"
echo ""

# Configuration (from .env.example)
PROJECT_ID="vigilant-axis-483119-r8"
REGION="europe-west4"
SERVICE_NAME="lls-study-portal"

# GitHub Actions specific
POOL_NAME="github-actions-pool"
PROVIDER_NAME="github-provider"
SA_NAME="github-actions-deployer"
GITHUB_REPO="TEJ42000/ALLMS"

echo -e "${YELLOW}Configuration:${NC}"
echo "  Project ID:    $PROJECT_ID"
echo "  Region:        $REGION"
echo "  Service Name:  $SERVICE_NAME"
echo "  GitHub Repo:   $GITHUB_REPO"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI not found${NC}"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n1 > /dev/null 2>&1; then
    echo -e "${RED}Error: Not authenticated with gcloud${NC}"
    echo "Run: gcloud auth login"
    exit 1
fi

# Confirm before proceeding
read -p "Proceed with setup? (y/n) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Setup cancelled"
    exit 0
fi

echo ""
echo -e "${GREEN}Step 1: Setting project...${NC}"
gcloud config set project $PROJECT_ID

echo ""
echo -e "${GREEN}Step 2: Enabling required APIs...${NC}"
gcloud services enable \
    iamcredentials.googleapis.com \
    artifactregistry.googleapis.com \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    secretmanager.googleapis.com

echo ""
echo -e "${GREEN}Step 3: Creating Artifact Registry repository...${NC}"
if gcloud artifacts repositories describe $SERVICE_NAME --location=$REGION &> /dev/null; then
    echo "  ✓ Repository '$SERVICE_NAME' already exists"
else
    gcloud artifacts repositories create $SERVICE_NAME \
        --repository-format=docker \
        --location=$REGION \
        --description="Docker images for $SERVICE_NAME"
    echo "  ✓ Repository created"
fi

echo ""
echo -e "${GREEN}Step 4: Creating service account...${NC}"
SA_EMAIL="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"
if gcloud iam service-accounts describe $SA_EMAIL &> /dev/null 2>&1; then
    echo "  ✓ Service account '$SA_NAME' already exists"
else
    gcloud iam service-accounts create $SA_NAME \
        --display-name="GitHub Actions Deployer" \
        --description="Service account for GitHub Actions to deploy to Cloud Run"
    echo "  ✓ Service account created"
fi

echo ""
echo -e "${GREEN}Step 5: Granting IAM permissions to service account...${NC}"
ROLES=(
    "roles/run.admin"
    "roles/artifactregistry.writer"
    "roles/iam.serviceAccountUser"
    "roles/secretmanager.secretAccessor"
)
for ROLE in "${ROLES[@]}"; do
    echo "  Adding $ROLE..."
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member="serviceAccount:$SA_EMAIL" \
        --role="$ROLE" \
        --condition=None \
        --quiet > /dev/null
done
echo "  ✓ Permissions granted"

echo ""
echo -e "${GREEN}Step 6: Creating Workload Identity Pool...${NC}"
if gcloud iam workload-identity-pools describe $POOL_NAME --location="global" &> /dev/null 2>&1; then
    echo "  ✓ Pool '$POOL_NAME' already exists"
else
    gcloud iam workload-identity-pools create $POOL_NAME \
        --location="global" \
        --display-name="GitHub Actions Pool" \
        --description="Workload Identity Pool for GitHub Actions"
    echo "  ✓ Pool created"
fi

echo ""
echo -e "${GREEN}Step 7: Creating OIDC Provider...${NC}"
if gcloud iam workload-identity-pools providers describe $PROVIDER_NAME \
    --location="global" \
    --workload-identity-pool=$POOL_NAME &> /dev/null 2>&1; then
    echo "  ✓ Provider '$PROVIDER_NAME' already exists"
else
    gcloud iam workload-identity-pools providers create-oidc $PROVIDER_NAME \
        --location="global" \
        --workload-identity-pool=$POOL_NAME \
        --display-name="GitHub Provider" \
        --issuer-uri="https://token.actions.githubusercontent.com" \
        --attribute-mapping="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.actor=assertion.actor,attribute.ref=assertion.ref" \
        --attribute-condition="assertion.repository=='${GITHUB_REPO}'"
    echo "  ✓ Provider created"
fi

echo ""
echo -e "${GREEN}Step 8: Allowing GitHub to impersonate service account...${NC}"
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
gcloud iam service-accounts add-iam-policy-binding $SA_EMAIL \
    --role="roles/iam.workloadIdentityUser" \
    --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL_NAME/attribute.repository/$GITHUB_REPO" \
    --quiet > /dev/null
echo "  ✓ GitHub Actions authorized"

echo ""
echo -e "${GREEN}Step 9: Checking for anthropic-api-key secret...${NC}"
if gcloud secrets describe anthropic-api-key &> /dev/null 2>&1; then
    echo "  ✓ Secret 'anthropic-api-key' already exists"
else
    echo -e "${YELLOW}  Secret 'anthropic-api-key' not found.${NC}"
    echo "  You'll need to create it manually:"
    echo "    echo -n 'YOUR_API_KEY' | gcloud secrets create anthropic-api-key --data-file=-"
fi

# Get the Workload Identity Provider value
WIF_PROVIDER=$(gcloud iam workload-identity-pools providers describe $PROVIDER_NAME \
    --location="global" \
    --workload-identity-pool=$POOL_NAME \
    --format="value(name)")

echo ""
echo -e "${BLUE}======================================================${NC}"
echo -e "${GREEN}  ✅ Setup Complete!${NC}"
echo -e "${BLUE}======================================================${NC}"
echo ""
echo -e "${YELLOW}Add these secrets to GitHub:${NC}"
echo -e "${YELLOW}(Settings → Secrets and variables → Actions → New repository secret)${NC}"
echo ""
echo -e "${GREEN}GCP_WORKLOAD_IDENTITY_PROVIDER:${NC}"
echo "$WIF_PROVIDER"
echo ""
echo -e "${GREEN}GCP_SERVICE_ACCOUNT:${NC}"
echo "$SA_EMAIL"
echo ""
echo -e "${BLUE}======================================================${NC}"
echo -e "${YELLOW}To deploy, create and push a semantic version tag:${NC}"
echo ""
echo "  git tag v1.0.0"
echo "  git push origin v1.0.0"
echo ""
echo -e "${BLUE}======================================================${NC}"

