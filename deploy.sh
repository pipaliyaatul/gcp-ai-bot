#!/bin/bash

# ZS-RFP-Demo GCP Deployment Script
# This script automates the deployment process to Google Cloud Run
# 
# Usage:
#   chmod +x deploy.sh
#   ./deploy.sh

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    print_error "gcloud CLI is not installed. Please install it first."
    exit 1
fi

# Check if user is logged in
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    print_warn "You are not logged in to gcloud. Please run: gcloud auth login"
    exit 1
fi

# Get project configuration
read -p "Enter your GCP Project ID: " PROJECT_ID
read -p "Enter your preferred region (default: us-central1): " REGION
REGION=${REGION:-us-central1}

export PROJECT_ID
export REGION
export SERVICE_NAME_BACKEND="zs-rfp-demo-backend"
export SERVICE_NAME_FRONTEND="zs-rfp-demo-frontend"
export SA_EMAIL="zs-rfp-demo-sa@${PROJECT_ID}.iam.gserviceaccount.com"

print_info "Configuration:"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  Backend Service: $SERVICE_NAME_BACKEND"
echo "  Frontend Service: $SERVICE_NAME_FRONTEND"

# Set project
print_info "Setting GCP project..."
gcloud config set project $PROJECT_ID

# Enable APIs
print_info "Enabling required APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    speech.googleapis.com \
    drive.googleapis.com \
    documentai.googleapis.com \
    --project=$PROJECT_ID

# Note: OAuth2 doesn't need to be enabled as a service
# It's automatically available when creating OAuth credentials in the Console

# Create service account
print_info "Creating service account..."
if gcloud iam service-accounts describe $SA_EMAIL --project=$PROJECT_ID &> /dev/null; then
    print_warn "Service account already exists, skipping creation..."
else
    gcloud iam service-accounts create zs-rfp-demo-sa \
        --display-name="ZS RFP Demo Service Account" \
        --description="Service account for backend operations" \
        --project=$PROJECT_ID
fi

# Grant permissions
print_info "Granting permissions to service account..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/speech.client" \
    --condition=None

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/run.invoker" \
    --condition=None

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/iam.serviceAccountUser" \
    --condition=None

# Note: Google Drive access is handled via:
# 1. OAuth scopes (configured in the application) - for user's personal Drive
# 2. Shared Drive membership - add service account to specific shared drives via Google Drive UI
#    (not via IAM roles, as Drive permissions are managed at the Drive level)

# Build and deploy backend
print_info "Building backend Docker image..."
cd backend
gcloud builds submit --tag gcr.io/${PROJECT_ID}/${SERVICE_NAME_BACKEND} --project=$PROJECT_ID

print_info "Deploying backend to Cloud Run..."
# Deploy with initial environment variables
# Note: FRONTEND_URL and OAuth vars will be updated after frontend is deployed
gcloud run deploy ${SERVICE_NAME_BACKEND} \
    --image gcr.io/${PROJECT_ID}/${SERVICE_NAME_BACKEND} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --service-account ${SA_EMAIL} \
    --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},USE_AI_FOR_RFP=true" \
    --memory=2Gi \
    --timeout=300 \
    --max-instances=10 \
    --min-instances=0 \
    --project=$PROJECT_ID

# Get backend URL
BACKEND_URL=$(gcloud run services describe ${SERVICE_NAME_BACKEND} \
    --region ${REGION} \
    --format="value(status.url)" \
    --project=$PROJECT_ID)

print_info "Backend deployed at: $BACKEND_URL"

# Build and deploy frontend
print_info "Building frontend Docker image..."
cd ../frontend

# Create .env.production if it doesn't exist
if [ ! -f .env.production ]; then
    echo "REACT_APP_API_URL=${BACKEND_URL}" > .env.production
    print_info "Created .env.production with backend URL"
fi

gcloud builds submit --tag gcr.io/${PROJECT_ID}/${SERVICE_NAME_FRONTEND} --project=$PROJECT_ID

print_info "Deploying frontend to Cloud Run..."
gcloud run deploy ${SERVICE_NAME_FRONTEND} \
    --image gcr.io/${PROJECT_ID}/${SERVICE_NAME_FRONTEND} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --port 80 \
    --memory=512Mi \
    --max-instances=10 \
    --min-instances=0 \
    --project=$PROJECT_ID

# Get frontend URL
FRONTEND_URL=$(gcloud run services describe ${SERVICE_NAME_FRONTEND} \
    --region ${REGION} \
    --format="value(status.url)" \
    --project=$PROJECT_ID)

print_info "Frontend deployed at: $FRONTEND_URL"

# Update backend with frontend URL and prompt for additional configuration
print_info "Updating backend environment variables..."
read -p "Enter Google Shared Drive ID (optional, press Enter to skip): " GOOGLE_SHARED_DRIVE_ID

# Build environment variables string
ENV_VARS="FRONTEND_URL=${FRONTEND_URL}"
if [ ! -z "$GOOGLE_SHARED_DRIVE_ID" ]; then
    ENV_VARS="${ENV_VARS},GOOGLE_SHARED_DRIVE_ID=${GOOGLE_SHARED_DRIVE_ID}"
fi

# Prompt for OAuth credentials
print_warn "OAuth Configuration Required:"
echo "You need to manually configure OAuth 2.0 credentials:"
echo "1. Go to: https://console.cloud.google.com/apis/credentials?project=${PROJECT_ID}"
echo "2. Create OAuth 2.0 Client ID (Web application)"
echo "3. Add authorized redirect URI: ${BACKEND_URL}/auth/google/callback"
echo "4. Add authorized JavaScript origin: ${FRONTEND_URL}"
echo ""
read -p "Enter your Google OAuth Client ID (or press Enter to skip): " GOOGLE_CLIENT_ID
read -p "Enter your Google OAuth Client Secret (or press Enter to skip): " GOOGLE_CLIENT_SECRET

if [ ! -z "$GOOGLE_CLIENT_ID" ] && [ ! -z "$GOOGLE_CLIENT_SECRET" ]; then
    ENV_VARS="${ENV_VARS},GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID},GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET},GOOGLE_REDIRECT_URI=${BACKEND_URL}/auth/google/callback"
    print_info "Updating backend with all environment variables..."
else
    print_warn "OAuth credentials not provided. Update them manually later."
fi

# Update all environment variables at once
gcloud run services update ${SERVICE_NAME_BACKEND} \
    --region ${REGION} \
    --update-env-vars="${ENV_VARS}" \
    --project=$PROJECT_ID

# Summary
echo ""
print_info "Deployment Summary:"
echo "===================="
echo "Backend URL:  $BACKEND_URL"
echo "Frontend URL: $FRONTEND_URL"
echo ""
echo "Next steps:"
echo "1. Test backend: curl ${BACKEND_URL}/health"
echo "2. Open frontend: ${FRONTEND_URL}"
echo "3. Configure OAuth (if not done): https://console.cloud.google.com/apis/credentials?project=${PROJECT_ID}"
echo "4. Update OAuth redirect URIs with the URLs above"
echo ""
print_info "Deployment complete! 🎉"

