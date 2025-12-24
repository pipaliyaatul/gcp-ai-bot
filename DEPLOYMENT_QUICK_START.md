# Quick Start: Deploy to GCP

This is a condensed version of the deployment guide. For detailed instructions, see [GCP_DEPLOYMENT_STEP_BY_STEP.md](./GCP_DEPLOYMENT_STEP_BY_STEP.md).

## 🚀 Automated Deployment (Recommended)

Use the provided script for automated deployment:

```bash
# Make script executable (if not already)
chmod +x deploy.sh

# Run deployment script
./deploy.sh
```

The script will:
- ✅ Enable required APIs
- ✅ Create service account
- ✅ Build and deploy backend
- ✅ Build and deploy frontend
- ✅ Configure environment variables

**You'll still need to manually:**
- Configure OAuth 2.0 credentials in GCP Console
- Update OAuth redirect URIs with the deployed URLs

## 📝 Manual Deployment (Step-by-Step)

### 1. Prerequisites

```bash
# Install gcloud CLI (if not installed)
# macOS: curl https://sdk.cloud.google.com | bash
# Then: exec -l $SHELL

# Login
gcloud auth login
```

### 2. Set Variables

```bash
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export SERVICE_NAME_BACKEND="zs-rfp-demo-backend"
export SERVICE_NAME_FRONTEND="zs-rfp-demo-frontend"
```

### 3. Create Project & Enable APIs

```bash
gcloud projects create $PROJECT_ID --name="ZS RFP Demo"
gcloud config set project $PROJECT_ID

gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  speech.googleapis.com \
  drive.googleapis.com

# Note: OAuth2 doesn't need to be enabled as a service
# It's automatically available when creating OAuth credentials in the Console
```

### 4. Create Service Account

```bash
gcloud iam service-accounts create zs-rfp-demo-sa \
  --display-name="ZS RFP Demo Service Account"

export SA_EMAIL="zs-rfp-demo-sa@${PROJECT_ID}.iam.gserviceaccount.com"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/speech.client"
```

### 5. Deploy Backend

```bash
cd backend
gcloud builds submit --tag gcr.io/${PROJECT_ID}/${SERVICE_NAME_BACKEND}

gcloud run deploy ${SERVICE_NAME_BACKEND} \
  --image gcr.io/${PROJECT_ID}/${SERVICE_NAME_BACKEND} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --service-account ${SA_EMAIL} \
  --memory=2Gi

# Save backend URL
export BACKEND_URL=$(gcloud run services describe ${SERVICE_NAME_BACKEND} \
  --region ${REGION} \
  --format="value(status.url)")
```

### 6. Deploy Frontend

```bash
cd ../frontend

# Create .env.production
echo "REACT_APP_API_URL=${BACKEND_URL}" > .env.production

gcloud builds submit --tag gcr.io/${PROJECT_ID}/${SERVICE_NAME_FRONTEND}

gcloud run deploy ${SERVICE_NAME_FRONTEND} \
  --image gcr.io/${PROJECT_ID}/${SERVICE_NAME_FRONTEND} \
  --platform managed \
  --region ${REGION} \
  --allow-unauthenticated \
  --port 80

# Save frontend URL
export FRONTEND_URL=$(gcloud run services describe ${SERVICE_NAME_FRONTEND} \
  --region ${REGION} \
  --format="value(status.url)")
```

### 7. Configure OAuth

1. Go to: https://console.cloud.google.com/apis/credentials?project=${PROJECT_ID}
2. Create OAuth 2.0 Client ID (Web application)
3. Add redirect URI: `${BACKEND_URL}/auth/google/callback`
4. Add JavaScript origin: `${FRONTEND_URL}`
5. Update backend with credentials:

```bash
gcloud run services update ${SERVICE_NAME_BACKEND} \
  --region ${REGION} \
  --update-env-vars="GOOGLE_CLIENT_ID=your-client-id,GOOGLE_CLIENT_SECRET=your-secret,GOOGLE_REDIRECT_URI=${BACKEND_URL}/auth/google/callback,FRONTEND_URL=${FRONTEND_URL}"
```

### 8. Test

```bash
# Test backend
curl ${BACKEND_URL}/health

# Open frontend
open ${FRONTEND_URL}  # macOS
# or visit in browser
```

## 🔧 Common Issues

### Build Fails
- Check Dockerfile exists
- Verify all files are present
- Check Cloud Build logs: `gcloud builds list`

### Service Returns 500
- Check logs: `gcloud logging read "resource.type=cloud_run_revision" --limit 50`
- Verify environment variables
- Check service account permissions

### CORS Errors
- Verify `FRONTEND_URL` is set in backend
- Check CORS settings in `app.py`
- Redeploy backend after changes

## 📚 Full Documentation

- **Detailed Guide**: [GCP_DEPLOYMENT_STEP_BY_STEP.md](./GCP_DEPLOYMENT_STEP_BY_STEP.md)
- **GCP Setup**: [GCP_SETUP.md](./GCP_SETUP.md)
- **General Deployment**: [DEPLOYMENT.md](./DEPLOYMENT.md)

## 💰 Cost Estimate

- **Cloud Run**: Free tier includes 2M requests/month
- **Cloud Build**: ~$0.003 per build minute
- **Storage**: Minimal (images stored in Container Registry)
- **APIs**: Pay-per-use (Speech-to-Text, Drive API)

**Estimated**: $0-5/month for low traffic

## ✅ Deployment Checklist

- [ ] gcloud CLI installed
- [ ] GCP project created
- [ ] Billing enabled
- [ ] APIs enabled
- [ ] Service account created
- [ ] Backend deployed
- [ ] Frontend deployed
- [ ] OAuth configured
- [ ] Environment variables set
- [ ] Health check passes
- [ ] Frontend loads
- [ ] File upload tested

---

**Need help?** See the detailed guide: [GCP_DEPLOYMENT_STEP_BY_STEP.md](./GCP_DEPLOYMENT_STEP_BY_STEP.md)

