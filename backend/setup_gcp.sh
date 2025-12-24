#!/bin/bash
# Helper script to set up GCP credentials
# This script helps you configure GCP credentials interactively

echo "=========================================="
echo "GCP Credentials Setup Helper"
echo "=========================================="
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "⚠️  gcloud CLI not found. Installing..."
    echo "Please install gcloud CLI: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get project ID
read -p "Enter your GCP Project ID: " PROJECT_ID
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Project ID is required"
    exit 1
fi

# Set project
gcloud config set project $PROJECT_ID

echo ""
echo "📋 Step 1: Enabling required APIs..."
gcloud services enable \
  drive.googleapis.com \
  speech.googleapis.com \
  documentai.googleapis.com \
  storage-component.googleapis.com

# Note: OAuth2 doesn't need to be enabled as a service
# It's automatically available when creating OAuth credentials in the Console

echo ""
echo "📋 Step 2: Creating service account..."
SERVICE_ACCOUNT_NAME="zs-rfp-demo-backend"
SERVICE_ACCOUNT_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Check if service account exists
if gcloud iam service-accounts describe $SERVICE_ACCOUNT_EMAIL &> /dev/null; then
    echo "✅ Service account already exists: $SERVICE_ACCOUNT_EMAIL"
else
    gcloud iam service-accounts create $SERVICE_ACCOUNT_NAME \
      --display-name="ZS RFP Demo Backend" \
      --description="Service account for ZS RFP Demo backend operations"
    echo "✅ Service account created: $SERVICE_ACCOUNT_EMAIL"
fi

echo ""
echo "📋 Step 3: Granting IAM roles..."
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
  --role="roles/speech.client" \
  --quiet

echo ""
echo "📋 Step 4: Creating service account key..."
KEY_FILE="service-account-key.json"
if [ -f "$KEY_FILE" ]; then
    read -p "⚠️  $KEY_FILE already exists. Overwrite? (y/N): " overwrite
    if [[ ! $overwrite =~ ^[Yy]$ ]]; then
        echo "Skipping key creation..."
    else
        gcloud iam service-accounts keys create $KEY_FILE \
          --iam-account=$SERVICE_ACCOUNT_EMAIL
        echo "✅ Key file created: $KEY_FILE"
    fi
else
    gcloud iam service-accounts keys create $KEY_FILE \
      --iam-account=$SERVICE_ACCOUNT_EMAIL
    echo "✅ Key file created: $KEY_FILE"
fi

echo ""
echo "📋 Step 5: OAuth 2.0 Setup"
echo "⚠️  OAuth setup must be done manually in Google Cloud Console:"
echo "   1. Go to: https://console.cloud.google.com/apis/credentials"
echo "   2. Click 'Create Credentials' > 'OAuth client ID'"
echo "   3. Configure OAuth consent screen if prompted"
echo "   4. Create Web application client"
echo "   5. Add redirect URI: http://localhost:8000/auth/google/callback"
echo "   6. Save Client ID and Client Secret"

echo ""
echo "📋 Step 6: Creating .env file..."
ENV_FILE=".env"
if [ -f "$ENV_FILE" ]; then
    read -p "⚠️  .env file already exists. Overwrite? (y/N): " overwrite_env
    if [[ ! $overwrite_env =~ ^[Yy]$ ]]; then
        echo "Skipping .env creation..."
        echo ""
        echo "Please manually update .env with:"
        echo "  GCP_PROJECT_ID=$PROJECT_ID"
        echo "  GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json"
        exit 0
    fi
fi

cat > $ENV_FILE << EOF
# Google Cloud Project
GCP_PROJECT_ID=$PROJECT_ID

# Service Account Credentials
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json

# OAuth 2.0 Credentials (set these after creating OAuth client)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Frontend URL
FRONTEND_URL=http://localhost:3000

# Application Settings
USE_AI_FOR_RFP=true
MAX_FILE_SIZE=10485760
UPLOAD_FOLDER=./uploads
EOF

echo "✅ .env file created"
echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Complete OAuth 2.0 setup in Google Cloud Console"
echo "2. Update GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env"
echo "3. Test the setup by running: python app.py"
echo ""
echo "For detailed instructions, see: ../GCP_SETUP.md"

