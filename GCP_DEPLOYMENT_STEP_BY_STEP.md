# Step-by-Step GCP Deployment Guide for ZS-RFP-Demo

This is a comprehensive, beginner-friendly guide to deploy the ZS-RFP-Demo application to Google Cloud Platform (GCP) Cloud Run.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Step 1: Install and Configure gcloud CLI](#step-1-install-and-configure-gcloud-cli)
3. [Step 2: Create GCP Project](#step-2-create-gcp-project)
4. [Step 3: Enable Required APIs](#step-3-enable-required-apis)
5. [Step 4: Create Service Account](#step-4-create-service-account)
6. [Step 5: Set Up OAuth 2.0](#step-5-set-up-oauth-20)
7. [Step 6: Prepare Application for Deployment](#step-6-prepare-application-for-deployment)
8. [Step 7: Build and Deploy Backend](#step-7-build-and-deploy-backend)
9. [Step 8: Build and Deploy Frontend](#step-8-build-and-deploy-frontend)
10. [Step 9: Configure Environment Variables](#step-9-configure-environment-variables)
11. [Step 10: Test the Deployment](#step-10-test-the-deployment)
12. [Step 11: Set Up Custom Domain (Optional)](#step-11-set-up-custom-domain-optional)
13. [Troubleshooting](#troubleshooting)
14. [Cost Optimization Tips](#cost-optimization-tips)

---

## Prerequisites

Before starting, ensure you have:

- ✅ Google Cloud Platform account with billing enabled
- ✅ `gcloud` CLI installed (we'll install it in Step 1)
- ✅ Docker installed (for local testing, optional)
- ✅ Git installed
- ✅ Basic knowledge of command line

**Estimated Time**: 1-2 hours for first-time deployment

**Estimated Cost**: ~$0-5/month for low traffic (Cloud Run free tier includes 2 million requests/month)

---

## Step 1: Install and Configure gcloud CLI

### 1.1 Install gcloud CLI

**On macOS:**
```bash
# Download and install
curl https://sdk.cloud.google.com | bash

# Restart your shell or run:
exec -l $SHELL
```

**On Linux:**
```bash
# Download and install
curl https://sdk.cloud.google.com | bash

# Restart your shell or run:
exec -l $SHELL
```

**On Windows:**
Download and run the installer from: https://cloud.google.com/sdk/docs/install

### 1.2 Initialize gcloud

```bash
# Login to your Google account
gcloud auth login

# Set default region and zone
gcloud config set compute/region us-central1
gcloud config set compute/zone us-central1-a
```

### 1.3 Verify Installation

```bash
gcloud --version
# Should show: Google Cloud SDK version and components
```

---

## Step 2: Create GCP Project

### 2.1 Create a New Project

```bash
# Set your project ID (must be globally unique)
export PROJECT_ID="zs-rfp-demo-$(date +%s)"
# Or use a custom name (must be lowercase, no spaces)
# export PROJECT_ID="your-unique-project-id"

# Create the project
gcloud projects create $PROJECT_ID --name="ZS RFP Demo"

# Set it as the default project
gcloud config set project $PROJECT_ID

# Verify project creation
gcloud projects describe $PROJECT_ID
```

**Note**: Save your `PROJECT_ID` - you'll need it throughout the deployment!

### 2.2 Enable Billing

1. Go to [GCP Console Billing](https://console.cloud.google.com/billing)
2. Select your project
3. Link a billing account (or create one)
4. **Important**: Cloud Run has a free tier, but some APIs may require billing

### 2.3 Set Project Variables

```bash
# Set these for easy reference (run in each new terminal session)
export PROJECT_ID="your-project-id"  # Replace with your actual project ID
export REGION="us-central1"          # Choose your preferred region
export SERVICE_NAME_BACKEND="zs-rfp-demo-backend"
export SERVICE_NAME_FRONTEND="zs-rfp-demo-frontend"
```

---

## Step 3: Enable Required APIs

Enable all APIs needed for the application:

```bash
# Enable Cloud Run API (required for deployment)
gcloud services enable run.googleapis.com

# Enable Cloud Build API (for building Docker images)
gcloud services enable cloudbuild.googleapis.com

# Enable Container Registry API (for storing Docker images)
gcloud services enable containerregistry.googleapis.com

# Enable Artifact Registry API (newer, recommended)
gcloud services enable artifactregistry.googleapis.com

# Enable Speech-to-Text API
gcloud services enable speech.googleapis.com

# Enable Google Drive API
gcloud services enable drive.googleapis.com

# Enable Document AI API (optional, for enhanced PDF processing)
gcloud services enable documentai.googleapis.com

# Note: OAuth2 doesn't need to be enabled as a service
# It's automatically available when creating OAuth credentials in the Console

# Verify APIs are enabled
gcloud services list --enabled
```

**Expected Output**: You should see all the APIs listed above in the enabled services.

---

## Step 4: Create Service Account

### 4.1 Create Service Account

```bash
# Create service account for backend
gcloud iam service-accounts create zs-rfp-demo-sa \
  --display-name="ZS RFP Demo Service Account" \
  --description="Service account for backend operations"

# Get the service account email
export SA_EMAIL="zs-rfp-demo-sa@${PROJECT_ID}.iam.gserviceaccount.com"
echo "Service Account Email: $SA_EMAIL"
```

### 4.2 Grant Required Permissions

```bash
# Grant Cloud Run Invoker role (to allow Cloud Run to run)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/run.invoker"

# Grant Speech-to-Text Client role
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/speech.client"

# Grant Document AI User role (if using Document AI)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/documentai.apiUser"

# Grant Storage Object Admin (if using Cloud Storage)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin"

# Grant Service Account User role (for Cloud Run)
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/iam.serviceAccountUser"
```

### 4.3 Create and Download Service Account Key

```bash
# Create key file
gcloud iam service-accounts keys create service-account-key.json \
  --iam-account=${SA_EMAIL}

# Move to backend directory
mv service-account-key.json backend/

# Verify file exists
ls -la backend/service-account-key.json
```

**⚠️ Security Note**: This key file contains sensitive credentials. Never commit it to git!

---

## Step 5: Set Up OAuth 2.0

### 5.1 Configure OAuth Consent Screen

1. Go to [APIs & Services > OAuth consent screen](https://console.cloud.google.com/apis/credentials/consent)
2. Select **External** (unless you have Google Workspace)
3. Click **Create**
4. Fill in the form:
   - **App name**: `ZS RFP Demo`
   - **User support email**: Your email
   - **Developer contact information**: Your email
5. Click **Save and Continue**
6. **Scopes** (Step 2):
   - Click **Add or Remove Scopes**
   - Add these scopes:
     - `.../auth/userinfo.email`
     - `.../auth/userinfo.profile`
     - `.../auth/drive.file`
   - Click **Update** then **Save and Continue**
7. **Test users** (Step 3):
   - Add your email address
   - Click **Save and Continue**
8. **Summary**: Review and click **Back to Dashboard**

### 5.2 Create OAuth 2.0 Client ID

1. Go to [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials)
2. Click **+ CREATE CREDENTIALS** > **OAuth client ID**
3. Choose **Web application**
4. Configure:
   - **Name**: `ZS RFP Demo Web Client`
   - **Authorized JavaScript origins**:
     - `http://localhost:3000` (for local development)
     - `https://your-frontend-url.run.app` (we'll add this after deployment)
   - **Authorized redirect URIs**:
     - `http://localhost:8000/auth/google/callback` (for local development)
     - `https://your-backend-url.run.app/auth/google/callback` (we'll add this after deployment)
5. Click **Create**
6. **IMPORTANT**: Copy the **Client ID** and **Client Secret** - save them securely!

```bash
# Save these for later (replace with your actual values)
export GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your-client-secret"
```

---

## Step 6: Prepare Application for Deployment

### 6.1 Verify Dockerfiles Exist

Check that both Dockerfiles exist:

```bash
# Check backend Dockerfile
cat backend/Dockerfile

# Check frontend Dockerfile
cat frontend/Dockerfile
```

If they don't exist or need updates, they should be:

**backend/Dockerfile** (should already exist):
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directory for uploads
RUN mkdir -p /tmp/uploads

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

**frontend/Dockerfile** (should already exist):
```dockerfile
FROM node:18-alpine as build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Build app
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built app
COPY --from=build /app/build /usr/share/nginx/html

# Copy nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### 6.2 Verify .dockerignore Files

Create `.dockerignore` files to exclude unnecessary files:

**backend/.dockerignore**:
```
__pycache__
*.pyc
*.pyo
*.pyd
.Python
venv/
env/
.env
*.log
.git
.gitignore
README.md
*.md
service-account-key.json
```

**frontend/.dockerignore**:
```
node_modules
npm-debug.log
.git
.gitignore
.env
.env.local
.env.development.local
.env.test.local
.env.production.local
README.md
*.md
build
```

### 6.3 Update CORS Settings

Update `backend/app.py` to allow your Cloud Run frontend URL:

```python
# In app.py, update CORS middleware:
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://your-frontend-url.run.app",  # Add your Cloud Run frontend URL
        "https://your-custom-domain.com"      # Add if using custom domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## Step 7: Build and Deploy Backend

### 7.1 Build Backend Docker Image

```bash
# Navigate to backend directory
cd backend

# Build using Cloud Build
gcloud builds submit --tag gcr.io/${PROJECT_ID}/${SERVICE_NAME_BACKEND}

# This will take 5-10 minutes. Wait for "SUCCESS" message.
```

**Alternative: Build locally and push** (if you have Docker installed):
```bash
# Build locally
docker build -t gcr.io/${PROJECT_ID}/${SERVICE_NAME_BACKEND} .

# Push to Google Container Registry
docker push gcr.io/${PROJECT_ID}/${SERVICE_NAME_BACKEND}
```

### 7.2 Deploy Backend to Cloud Run

```bash
# Deploy backend service
gcloud run deploy ${SERVICE_NAME_BACKEND} \
  --image gcr.io/${PROJECT_ID}/${SERVICE_NAME_BACKEND} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --service-account ${SA_EMAIL} \
  --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID}" \
  --memory=2Gi \
  --timeout=300 \
  --max-instances=10 \
  --min-instances=0

# Wait for deployment to complete (2-3 minutes)
```

**Note the service URL** from the output - it will look like:
```
Service URL: https://zs-rfp-demo-backend-xxxxx-uc.a.run.app
```

```bash
# Save backend URL
export BACKEND_URL="https://zs-rfp-demo-backend-xxxxx-uc.a.run.app"
echo "Backend URL: $BACKEND_URL"
```

### 7.3 Update OAuth Redirect URI

Now that you have the backend URL, update OAuth settings:

1. Go to [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials)
2. Click on your OAuth 2.0 Client ID
3. Add to **Authorized redirect URIs**:
   - `${BACKEND_URL}/auth/google/callback`
4. Click **Save**

### 7.4 Set Backend Environment Variables

```bash
# Update backend service with all environment variables
gcloud run services update ${SERVICE_NAME_BACKEND} \
  --region ${REGION} \
  --update-env-vars="GCP_PROJECT_ID=${PROJECT_ID},GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID},GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET},GOOGLE_REDIRECT_URI=${BACKEND_URL}/auth/google/callback,FRONTEND_URL=https://your-frontend-url.run.app,USE_AI_FOR_RFP=true,MAX_FILE_SIZE=10485760"

# Note: Replace "your-frontend-url.run.app" with actual frontend URL after Step 8
```

**⚠️ Security Best Practice**: For production, use Secret Manager instead:

```bash
# Create secrets
echo -n "${GOOGLE_CLIENT_SECRET}" | gcloud secrets create google-client-secret --data-file=-

# Update service to use secrets
gcloud run services update ${SERVICE_NAME_BACKEND} \
  --region ${REGION} \
  --update-secrets="GOOGLE_CLIENT_SECRET=google-client-secret:latest"
```

---

## Step 8: Build and Deploy Frontend

### 8.1 Update Frontend Environment Variables

Before building, update the frontend to use the backend URL:

```bash
# Navigate to frontend directory
cd frontend

# Create or update .env.production file
cat > .env.production << EOF
REACT_APP_API_URL=${BACKEND_URL}
EOF

# Verify
cat .env.production
```

### 8.2 Build Frontend Docker Image

```bash
# Build using Cloud Build
gcloud builds submit --tag gcr.io/${PROJECT_ID}/${SERVICE_NAME_FRONTEND}

# Wait for build to complete (5-10 minutes)
```

### 8.3 Deploy Frontend to Cloud Run

```bash
# Deploy frontend service
gcloud run deploy ${SERVICE_NAME_FRONTEND} \
  --image gcr.io/${PROJECT_ID}/${SERVICE_NAME_FRONTEND} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --port 80 \
  --memory=512Mi \
  --max-instances=10 \
  --min-instances=0

# Wait for deployment (2-3 minutes)
```

**Note the service URL**:
```bash
# Save frontend URL
export FRONTEND_URL="https://zs-rfp-demo-frontend-xxxxx-uc.a.run.app"
echo "Frontend URL: $FRONTEND_URL"
```

### 8.4 Update Backend with Frontend URL

```bash
# Update backend CORS and environment variables
gcloud run services update ${SERVICE_NAME_BACKEND} \
  --region ${REGION} \
  --update-env-vars="FRONTEND_URL=${FRONTEND_URL}"

# Also update the CORS in app.py and redeploy if needed
```

### 8.5 Update OAuth Settings with Frontend URL

1. Go to [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials)
2. Click on your OAuth 2.0 Client ID
3. Add to **Authorized JavaScript origins**:
   - `${FRONTEND_URL}`
4. Click **Save**

---

## Step 9: Configure Environment Variables

### 9.1 Verify All Environment Variables

Check that all backend environment variables are set:

```bash
# View current environment variables
gcloud run services describe ${SERVICE_NAME_BACKEND} \
  --region ${REGION} \
  --format="value(spec.template.spec.containers[0].env)"
```

### 9.2 Set Missing Variables

If any are missing, set them:

```bash
gcloud run services update ${SERVICE_NAME_BACKEND} \
  --region ${REGION} \
  --update-env-vars="GCP_PROJECT_ID=${PROJECT_ID},GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID},GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET},GOOGLE_REDIRECT_URI=${BACKEND_URL}/auth/google/callback,FRONTEND_URL=${FRONTEND_URL},USE_AI_FOR_RFP=true,MAX_FILE_SIZE=10485760"
```

### 9.3 Optional: Configure Shared Drive

If using Google Workspace Shared Drive:

```bash
# Get your Shared Drive ID from Google Drive URL
# Format: https://drive.google.com/drive/folders/DRIVE_ID

export GOOGLE_SHARED_DRIVE_ID="your-drive-id"

# Update backend
gcloud run services update ${SERVICE_NAME_BACKEND} \
  --region ${REGION} \
  --update-env-vars="GOOGLE_SHARED_DRIVE_ID=${GOOGLE_SHARED_DRIVE_ID}"
```

---

## Step 10: Test the Deployment

### 10.1 Test Backend Health Endpoint

```bash
# Test backend health
curl ${BACKEND_URL}/health

# Expected: {"status":"healthy"}
```

### 10.2 Test Backend Root Endpoint

```bash
# Test backend root
curl ${BACKEND_URL}/

# Expected: {"message":"ZS RFP Demo API"}
```

### 10.3 Test Frontend

1. Open your browser and navigate to: `${FRONTEND_URL}`
2. You should see the login page
3. Try logging in with dummy credentials: `admin` / `admin123`
4. Test file upload functionality
5. Test Google OAuth login (if configured)

### 10.4 Test File Upload

1. Log in to the application
2. Upload a test file (PDF, DOCX, or TXT)
3. Wait for processing
4. Verify RFP summary is generated
5. Check download link works

### 10.5 Check Logs

```bash
# View backend logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME_BACKEND}" --limit 50

# View frontend logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME_FRONTEND}" --limit 50
```

---

## Step 11: Set Up Custom Domain (Optional)

### 11.1 Map Custom Domain to Cloud Run

```bash
# Map domain to backend
gcloud run domain-mappings create \
  --service ${SERVICE_NAME_BACKEND} \
  --domain api.yourdomain.com \
  --region ${REGION}

# Map domain to frontend
gcloud run domain-mappings create \
  --service ${SERVICE_NAME_FRONTEND} \
  --domain yourdomain.com \
  --region ${REGION}
```

### 11.2 Update DNS Records

Follow the instructions provided by the domain mapping command to update your DNS records.

---

## Troubleshooting

### Issue: Build Fails

**Symptoms**: `gcloud builds submit` fails

**Solutions**:
- Check Dockerfile syntax
- Verify all files are present
- Check Cloud Build logs: `gcloud builds list`
- View detailed logs: `gcloud builds log <BUILD_ID>`

### Issue: OAuth2 API Enable Error

**Symptoms**: Error when trying to enable `oauth2.googleapis.com`:
```
ERROR: Service 'oauth2.googleapis.com' is an internal service
Service oauth2.googleapis.com is not available to this consumer
```

**Solution**:
- **OAuth2 doesn't need to be enabled as a service** - it's automatically available
- Remove `oauth2.googleapis.com` from your API enablement commands
- OAuth functionality is available when you create OAuth credentials in the Google Cloud Console
- Simply create OAuth 2.0 Client ID in [APIs & Services > Credentials](https://console.cloud.google.com/apis/credentials)

### Issue: Deployment Fails

**Symptoms**: `gcloud run deploy` fails

**Solutions**:
- Check service account permissions
- Verify image exists: `gcloud container images list`
- Check quotas: `gcloud compute project-info describe`
- Review deployment logs

### Issue: Service Returns 500 Error

**Symptoms**: Service deployed but returns errors

**Solutions**:
- Check logs: `gcloud logging read "resource.type=cloud_run_revision" --limit 50`
- Verify environment variables are set correctly
- Check service account has required permissions
- Verify APIs are enabled

### Issue: CORS Errors

**Symptoms**: Frontend can't connect to backend

**Solutions**:
- Verify `FRONTEND_URL` is set correctly in backend
- Check CORS settings in `app.py`
- Ensure frontend URL is in `allow_origins` list
- Redeploy backend after CORS changes

### Issue: OAuth Not Working

**Symptoms**: Google login fails

**Solutions**:
- Verify OAuth redirect URI matches exactly
- Check `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are set
- Verify OAuth consent screen is configured
- Check OAuth scopes include `drive.file`
- Review OAuth logs in Cloud Console

### Issue: Drive Upload Fails

**Symptoms**: "No valid credentials available" error

**Solutions**:
- Verify `GOOGLE_SHARED_DRIVE_ID` is set (if using service account)
- Or ensure OAuth credentials are passed with upload request
- Check Drive API is enabled
- Verify service account has Drive permissions
- Check OAuth scopes include Drive access

### Issue: Speech-to-Text Fails

**Symptoms**: Audio transcription errors

**Solutions**:
- Verify Speech-to-Text API is enabled
- Check service account has `roles/speech.client` role
- Verify `GOOGLE_APPLICATION_CREDENTIALS` is accessible
- Check audio file format and size limits
- Review Speech-to-Text quotas

### Common Commands for Debugging

```bash
# View service details
gcloud run services describe ${SERVICE_NAME_BACKEND} --region ${REGION}

# View service logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME_BACKEND}" --limit 100 --format json

# Test service locally (if Docker is installed)
docker run -p 8000:8000 -e GCP_PROJECT_ID=${PROJECT_ID} gcr.io/${PROJECT_ID}/${SERVICE_NAME_BACKEND}

# Check IAM permissions
gcloud projects get-iam-policy ${PROJECT_ID}

# List all Cloud Run services
gcloud run services list --region ${REGION}
```

---

## Cost Optimization Tips

### 1. Use Cloud Run Free Tier

- Cloud Run free tier: 2 million requests/month
- 400,000 GB-seconds of memory
- 200,000 vCPU-seconds

### 2. Set Minimum Instances to 0

```bash
# Update to scale to zero when not in use
gcloud run services update ${SERVICE_NAME_BACKEND} \
  --region ${REGION} \
  --min-instances=0
```

### 3. Optimize Memory Allocation

```bash
# Reduce memory if not needed (default is 2Gi for backend)
gcloud run services update ${SERVICE_NAME_BACKEND} \
  --region ${REGION} \
  --memory=1Gi
```

### 4. Set Up Billing Alerts

1. Go to [Billing > Budgets & alerts](https://console.cloud.google.com/billing/budgets)
2. Create a budget with alerts
3. Set threshold (e.g., $10/month)

### 5. Monitor Usage

```bash
# View Cloud Run usage
gcloud billing accounts list
gcloud billing projects describe ${PROJECT_ID}
```

---

## Quick Reference: All Commands in One Place

```bash
# Set variables (run first)
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export SERVICE_NAME_BACKEND="zs-rfp-demo-backend"
export SERVICE_NAME_FRONTEND="zs-rfp-demo-frontend"
export SA_EMAIL="zs-rfp-demo-sa@${PROJECT_ID}.iam.gserviceaccount.com"
export GOOGLE_CLIENT_ID="your-client-id"
export GOOGLE_CLIENT_SECRET="your-client-secret"

# Create project
gcloud projects create $PROJECT_ID --name="ZS RFP Demo"
gcloud config set project $PROJECT_ID

# Enable APIs
gcloud services enable run.googleapis.com cloudbuild.googleapis.com \
  speech.googleapis.com drive.googleapis.com

# Create service account
gcloud iam service-accounts create zs-rfp-demo-sa --display-name="ZS RFP Demo Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/speech.client"

# Build and deploy backend
cd backend
gcloud builds submit --tag gcr.io/${PROJECT_ID}/${SERVICE_NAME_BACKEND}
gcloud run deploy ${SERVICE_NAME_BACKEND} \
  --image gcr.io/${PROJECT_ID}/${SERVICE_NAME_BACKEND} \
  --platform managed --region ${REGION} --allow-unauthenticated \
  --service-account ${SA_EMAIL} --memory=2Gi

# Build and deploy frontend
cd ../frontend
gcloud builds submit --tag gcr.io/${PROJECT_ID}/${SERVICE_NAME_FRONTEND}
gcloud run deploy ${SERVICE_NAME_FRONTEND} \
  --image gcr.io/${PROJECT_ID}/${SERVICE_NAME_FRONTEND} \
  --platform managed --region ${REGION} --allow-unauthenticated --port 80
```

---

## Next Steps

After successful deployment:

1. ✅ Set up monitoring and alerting
2. ✅ Configure custom domain (if needed)
3. ✅ Set up CI/CD pipeline with Cloud Build
4. ✅ Implement backup strategies
5. ✅ Review and optimize costs
6. ✅ Set up staging environment
7. ✅ Document your deployment process

---

## Support Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Build Documentation](https://cloud.google.com/build/docs)
- [GCP Pricing Calculator](https://cloud.google.com/products/calculator)
- [Cloud Run Troubleshooting](https://cloud.google.com/run/docs/troubleshooting)

---

## Checklist

Use this checklist to track your deployment progress:

- [ ] gcloud CLI installed and configured
- [ ] GCP project created
- [ ] Billing enabled
- [ ] All APIs enabled
- [ ] Service account created and permissions granted
- [ ] Service account key downloaded
- [ ] OAuth consent screen configured
- [ ] OAuth client ID created
- [ ] Backend Docker image built
- [ ] Backend deployed to Cloud Run
- [ ] Frontend Docker image built
- [ ] Frontend deployed to Cloud Run
- [ ] Environment variables configured
- [ ] OAuth redirect URIs updated
- [ ] Backend health check passes
- [ ] Frontend loads correctly
- [ ] File upload tested
- [ ] OAuth login tested
- [ ] Drive upload tested
- [ ] Logs reviewed
- [ ] Cost monitoring set up

---

**Congratulations!** 🎉 Your ZS-RFP-Demo application should now be deployed and running on Google Cloud Platform!

