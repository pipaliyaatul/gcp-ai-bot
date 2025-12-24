# GCP Credentials Setup Guide

This guide will walk you through setting up all Google Cloud Platform credentials needed for the ZS-RFP-Demo project.

## Prerequisites

1. Google Cloud Platform account (sign up at https://cloud.google.com)
2. Billing enabled on your GCP account (some APIs require billing)
3. `gcloud` CLI installed (optional but recommended)

## Step 1: Create a GCP Project

### Option A: Using Google Cloud Console

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click on the project dropdown at the top
3. Click "New Project"
4. Enter project name: `zs-rfp-demo` (or your preferred name)
5. Click "Create"
6. Wait for project creation, then select it

### Option B: Using gcloud CLI

```bash
# Set your project ID (choose a unique ID)
export PROJECT_ID="zs-rfp-demo-$(date +%s)"

# Create project
gcloud projects create $PROJECT_ID --name="ZS RFP Demo"

# Set as default project
gcloud config set project $PROJECT_ID

# Enable billing (you'll need to do this in console if not using CLI)
```

## Step 2: Enable Required APIs

Enable the following APIs in your GCP project:

### Using Google Cloud Console

1. Go to [APIs & Services > Library](https://console.cloud.google.com/apis/library)
2. Search for and enable each API:
   - **Google Drive API** (required for document storage)
   - **Cloud Speech-to-Text API** (required for audio transcription)
   - **Cloud Document AI API** (optional, for enhanced PDF processing)
   - **Cloud Storage API** (optional, if using GCS)

### Using gcloud CLI

```bash
# Enable all required APIs
gcloud services enable \
  drive.googleapis.com \
  speech.googleapis.com \
  documentai.googleapis.com \
  storage-component.googleapis.com

# Note: OAuth2 doesn't need to be enabled as a service
# It's automatically available when creating OAuth credentials in the Console
```

## Step 3: Create Service Account

A service account is needed for backend operations (Drive uploads, Speech-to-Text, etc.)

### Using Google Cloud Console

1. Go to [IAM & Admin > Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Click "Create Service Account"
3. Enter details:
   - **Name**: `zs-rfp-demo-backend`
   - **Description**: "Service account for ZS RFP Demo backend"
4. Click "Create and Continue"
5. Grant roles:
   - **Cloud Speech Client** (for audio transcription)
   - **Storage Object Admin** (if using Cloud Storage)
   - **Document AI API User** (if using Document AI)
6. Click "Continue" then "Done"

### Using gcloud CLI

```bash
# Create service account
gcloud iam service-accounts create zs-rfp-demo-backend \
  --display-name="ZS RFP Demo Backend Service Account" \
  --description="Service account for backend operations"

# Grant necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:zs-rfp-demo-backend@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/speech.client"

# For Google Drive, we need to grant Drive API access
# Note: Service accounts can't directly access Drive files owned by users
# We'll use domain-wide delegation or OAuth for Drive access
```

## Step 4: Create and Download Service Account Key

### Using Google Cloud Console

1. Go to [IAM & Admin > Service Accounts](https://console.cloud.google.com/iam-admin/serviceaccounts)
2. Click on your service account (`zs-rfp-demo-backend`)
3. Go to "Keys" tab
4. Click "Add Key" > "Create new key"
5. Choose "JSON" format
6. Click "Create"
7. The JSON file will download automatically
8. **Save this file securely** - you'll need it for `GOOGLE_APPLICATION_CREDENTIALS`

### Using gcloud CLI

```bash
# Create and download key
gcloud iam service-accounts keys create service-account-key.json \
  --iam-account=zs-rfp-demo-backend@${PROJECT_ID}.iam.gserviceaccount.com

# Move to backend directory
mv service-account-key.json backend/
```

## Step 5: Configure Google Drive Access

Google Drive requires special setup because service accounts can't directly access user files.

### Option A: Domain-Wide Delegation (for Workspace/Google Workspace)

If you're using Google Workspace:

1. In Service Account settings, enable "Domain-wide delegation"
2. Note the Client ID
3. In Google Workspace Admin Console, grant API scopes:
   - `https://www.googleapis.com/auth/drive.file`

### Option B: OAuth 2.0 (Recommended for Personal Use)

We'll set this up in Step 6 for user authentication, which also works for Drive.

## Step 6: Set Up OAuth 2.0 for User Login

OAuth is needed for Google login and can also be used for Drive access.

### Using Google Cloud Console

1. Go to [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials)
2. Click "Create Credentials" > "OAuth client ID"
3. If prompted, configure OAuth consent screen first:
   - **User Type**: External (or Internal if using Workspace)
   - **App name**: ZS RFP Demo
   - **User support email**: Your email
   - **Developer contact**: Your email
   - Click "Save and Continue"
   - **Scopes**: Add `https://www.googleapis.com/auth/drive.file`
   - Click "Save and Continue"
   - **Test users**: Add your email (for testing)
   - Click "Save and Continue"
4. Back to Credentials, click "Create Credentials" > "OAuth client ID"
5. Choose "Web application"
6. Configure:
   - **Name**: ZS RFP Demo Web Client
   - **Authorized JavaScript origins**: 
     - `http://localhost:3000` (for local dev)
     - `https://your-domain.com` (for production)
   - **Authorized redirect URIs**:
     - `http://localhost:8000/auth/google/callback` (for local dev)
     - `https://your-backend-url/auth/google/callback` (for production)
7. Click "Create"
8. **Save the Client ID and Client Secret** - you'll need these for environment variables

## Step 7: Configure Environment Variables

### Backend Configuration

Create or update `backend/.env` file:

```bash
# Google Cloud Project
GCP_PROJECT_ID=your-project-id

# Service Account Credentials (path to JSON key file)
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json

# OAuth 2.0 Credentials (from Step 6)
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Frontend URL
FRONTEND_URL=http://localhost:3000

# Application Settings
USE_AI_FOR_RFP=true
MAX_FILE_SIZE=10485760
UPLOAD_FOLDER=./uploads
```

### Frontend Configuration

Create or update `frontend/.env` file:

```bash
REACT_APP_API_URL=http://localhost:8000
```

## Step 8: Verify Setup

### Test Service Account

```bash
# Activate virtual environment
cd backend
source venv/bin/activate

# Set credentials
export GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json

# Test Speech-to-Text API
python -c "from google.cloud import speech; print('Speech-to-Text API accessible')"

# Test Drive API (if configured)
python -c "from googleapiclient.discovery import build; from google.oauth2 import service_account; print('Drive API accessible')"
```

### Test OAuth Setup

1. Start the backend server
2. Try accessing `/auth/google` endpoint
3. You should get an auth URL (not an error)

## Step 9: Grant Drive Permissions (Important!)

For the service account to upload files to Drive, you need to:

### Option 1: Share a Drive Folder with Service Account

1. Create a folder in Google Drive
2. Right-click > Share
3. Add the service account email: `zs-rfp-demo-backend@your-project-id.iam.gserviceaccount.com`
4. Give it "Editor" permission
5. Use this folder ID in your code (optional)

### Option 2: Use OAuth for Drive (Recommended)

The OAuth flow (Step 6) allows the app to access the user's Drive on their behalf, which is better for user files.

## Step 10: Production Deployment

For production deployment:

1. **Store credentials securely**:
   - Use Google Secret Manager
   - Or environment variables in Cloud Run
   - Never commit credentials to git

2. **Update OAuth redirect URIs**:
   - Add production URLs to authorized redirect URIs
   - Update `GOOGLE_REDIRECT_URI` in production environment

3. **Service Account in Cloud Run**:
   - Cloud Run can use the service account automatically
   - Set service account in Cloud Run deployment settings

## Troubleshooting

### "Permission denied" errors

- Verify service account has correct IAM roles
- Check API is enabled
- Verify service account key is correct

### "OAuth credentials not configured"

- Check `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set
- Verify OAuth consent screen is configured
- Check redirect URI matches exactly

### "Drive service not initialized"

- Verify `GOOGLE_APPLICATION_CREDENTIALS` points to valid JSON file
- Check service account has Drive API access
- For user files, use OAuth instead of service account

### SSL/Connection errors

- Check network/firewall settings
- Verify credentials are not expired
- Try regenerating service account key

## Security Best Practices

1. **Never commit credentials to git**
   - Add `*.json` to `.gitignore`
   - Use environment variables
   - Use Secret Manager in production

2. **Rotate keys regularly**
   - Regenerate service account keys periodically
   - Update OAuth secrets if compromised

3. **Use least privilege**
   - Only grant necessary IAM roles
   - Limit OAuth scopes

4. **Monitor usage**
   - Set up billing alerts
   - Review API usage in Cloud Console

## Quick Reference

### Required Environment Variables

**Backend:**
```bash
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json
GCP_PROJECT_ID=your-project-id
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
```

**Frontend:**
```bash
REACT_APP_API_URL=http://localhost:8000
```

### Required APIs

- ✅ Google Drive API
- ✅ Cloud Speech-to-Text API
- ⚪ Cloud Document AI API (optional)
- ⚪ Cloud Storage API (optional)

### Required IAM Roles

- `roles/speech.client` - For Speech-to-Text
- `roles/storage.objectAdmin` - For Cloud Storage (if used)
- `roles/documentai.apiUser` - For Document AI (if used)

## Next Steps

After completing this setup:

1. Test file upload with a text file (PDF, DOCX, TXT)
2. Test audio transcription (if Speech-to-Text is configured)
3. Test Google login (if OAuth is configured)
4. Verify Drive upload works (if configured)

For deployment instructions, see [DEPLOYMENT.md](./DEPLOYMENT.md)

