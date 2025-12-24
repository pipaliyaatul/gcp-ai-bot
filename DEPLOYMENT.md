# GCP Deployment Guide for ZS-RFP-Demo

This guide provides step-by-step instructions for deploying the ZS-RFP-Demo application to Google Cloud Platform.

## Prerequisites

1. Google Cloud Platform account with billing enabled
2. `gcloud` CLI installed and configured
3. Node.js and npm installed (for frontend)
4. Python 3.9+ installed (for backend)

## Step 1: Create GCP Project

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
export REGION="us-central1"

# Create new project (or use existing)
gcloud projects create $PROJECT_ID --name="ZS-RFP-Demo"

# Set as default project
gcloud config set project $PROJECT_ID

# Enable billing (required for some services)
# Do this via GCP Console: https://console.cloud.google.com/billing
```

## Step 2: Enable Required APIs

```bash
# Enable required GCP APIs
gcloud services enable \
  cloudbuild.googleapis.com \
  run.googleapis.com \
  storage-component.googleapis.com \
  speech.googleapis.com \
  documentai.googleapis.com \
  drive.googleapis.com \
  cloudresourcemanager.googleapis.com

# Note: OAuth2 doesn't need to be enabled as a service
# It's automatically available when creating OAuth credentials in the Console
```

## Step 3: Set Up Authentication

### Option A: Service Account (Recommended for Backend)

```bash
# Create service account
gcloud iam service-accounts create zs-rfp-demo-sa \
  --display-name="ZS RFP Demo Service Account"

# Grant necessary permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:zs-rfp-demo-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:zs-rfp-demo-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/speech.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:zs-rfp-demo-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/documentai.apiUser"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:zs-rfp-demo-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
  --role="roles/drive.file"

# Create and download key
gcloud iam service-accounts keys create service-account-key.json \
  --iam-account=zs-rfp-demo-sa@${PROJECT_ID}.iam.gserviceaccount.com
```

### Option B: OAuth 2.0 Client (For Google Login)

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Click "Create Credentials" > "OAuth client ID"
3. Choose "Web application"
4. Add authorized redirect URI: `https://your-backend-url/auth/google/callback`
5. Save Client ID and Client Secret

## Step 4: Configure Environment Variables

### Backend Environment Variables

Create a `.env` file in the backend directory:

```bash
# Backend .env
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
GCP_PROJECT_ID=your-project-id
GOOGLE_CLIENT_ID=your-oauth-client-id
GOOGLE_CLIENT_SECRET=your-oauth-client-secret
GOOGLE_REDIRECT_URI=https://your-backend-url/auth/google/callback
USE_AI_FOR_RFP=true
MAX_FILE_SIZE=10485760
```

### Frontend Environment Variables

Create a `.env` file in the frontend directory:

```bash
# Frontend .env
REACT_APP_API_URL=https://your-backend-url
```

## Step 5: Deploy Backend to Cloud Run

### Build and Deploy

```bash
cd backend

# Create Dockerfile if not exists (see below)
# Build container image
gcloud builds submit --tag gcr.io/$PROJECT_ID/zs-rfp-demo-backend

# Deploy to Cloud Run
gcloud run deploy zs-rfp-demo-backend \
  --image gcr.io/$PROJECT_ID/zs-rfp-demo-backend \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --set-env-vars="GCP_PROJECT_ID=$PROJECT_ID,GOOGLE_CLIENT_ID=your-client-id,GOOGLE_CLIENT_SECRET=your-client-secret" \
  --service-account=zs-rfp-demo-sa@${PROJECT_ID}.iam.gserviceaccount.com \
  --memory=2Gi \
  --timeout=300
```

### Backend Dockerfile

Create `backend/Dockerfile`:

```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Step 6: Deploy Frontend to Cloud Run or App Engine

### Option A: Cloud Run (Recommended)

```bash
cd frontend

# Build React app
npm install
npm run build

# Create Dockerfile for frontend
# (see below)

# Build and deploy
gcloud builds submit --tag gcr.io/$PROJECT_ID/zs-rfp-demo-frontend

gcloud run deploy zs-rfp-demo-frontend \
  --image gcr.io/$PROJECT_ID/zs-rfp-demo-frontend \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 80
```

### Frontend Dockerfile

Create `frontend/Dockerfile`:

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

### Frontend nginx.conf

Create `frontend/nginx.conf`:

```nginx
server {
    listen 80;
    server_name _;
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://your-backend-url;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Option B: Firebase Hosting (Alternative)

```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login
firebase login

# Initialize Firebase
cd frontend
firebase init hosting

# Build and deploy
npm run build
firebase deploy --only hosting
```

## Step 7: Set Up Cloud Storage (Optional)

If you want to store uploaded files in Cloud Storage:

```bash
# Create bucket
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://zs-rfp-demo-uploads

# Set CORS (if needed)
gsutil cors set cors.json gs://zs-rfp-demo-uploads
```

## Step 8: Configure CORS

Update backend `app.py` CORS settings with your frontend URL:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://your-frontend-url",
        "http://localhost:3000"  # For local development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Step 9: Set Up Document AI (Optional)

If using Document AI for PDF processing:

```bash
# Create processor (via console or API)
# Go to: https://console.cloud.google.com/ai/document-ai
# Create a Document OCR processor
```

## Step 10: Testing

1. Test backend endpoint:
```bash
curl https://your-backend-url/health
```

2. Test frontend:
   - Navigate to your frontend URL
   - Try logging in with dummy credentials
   - Upload a test file
   - Verify RFP summary generation

## Step 11: Monitoring and Logging

```bash
# View logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Set up alerts in Cloud Console
# Go to: https://console.cloud.google.com/monitoring
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify service account has correct permissions
   - Check GOOGLE_APPLICATION_CREDENTIALS path
   - Ensure service account key is accessible

2. **CORS Errors**
   - Verify frontend URL is in CORS allow list
   - Check backend CORS configuration

3. **File Upload Failures**
   - Check MAX_FILE_SIZE setting
   - Verify Cloud Storage permissions
   - Check Cloud Run timeout settings

4. **Drive Upload Failures**
   - Verify Drive API is enabled
   - Check service account has Drive permissions
   - Ensure OAuth credentials are correct

## Cost Optimization

- Use Cloud Run (pay per request) instead of always-on VMs
- Set up Cloud Storage lifecycle policies
- Use appropriate machine types for Cloud Run
- Monitor usage with Cloud Billing alerts

## Security Best Practices

1. Never commit credentials to git
2. Use Secret Manager for sensitive data:
```bash
# Store secrets
echo -n "your-secret" | gcloud secrets create google-client-secret --data-file=-

# Use in Cloud Run
gcloud run services update zs-rfp-demo-backend \
  --update-secrets=GOOGLE_CLIENT_SECRET=google-client-secret:latest
```

3. Enable Cloud Armor for DDoS protection
4. Use IAM roles with least privilege
5. Enable audit logging

## Next Steps

- Set up CI/CD pipeline with Cloud Build
- Configure custom domain
- Set up monitoring and alerting
- Implement caching strategies
- Add rate limiting

## Support

For issues or questions, refer to:
- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [GCP API Documentation](https://cloud.google.com/apis/docs/overview)
- [Firebase Hosting Documentation](https://firebase.google.com/docs/hosting)

