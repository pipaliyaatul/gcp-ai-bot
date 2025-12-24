# Setting Environment Variables in Cloud Run

## Overview

In Cloud Run, you **do NOT** use a `.env` file. Instead, environment variables are set directly on the Cloud Run service configuration. This guide explains how to set and manage environment variables for your deployed application.

## Required Environment Variables

Your application needs the following environment variables:

### Essential Variables

1. **`GCP_PROJECT_ID`** - Your Google Cloud Project ID
   - Example: `my-project-123456`

2. **`FRONTEND_URL`** - The URL of your frontend application
   - Example: `https://zs-rfp-demo-frontend-xxxxx.run.app`

3. **`GOOGLE_CLIENT_ID`** - OAuth 2.0 Client ID (for Google authentication)
   - Example: `123456789-abc.apps.googleusercontent.com`

4. **`GOOGLE_CLIENT_SECRET`** - OAuth 2.0 Client Secret
   - Example: `GOCSPX-xxxxxxxxxxxxx`

5. **`GOOGLE_REDIRECT_URI`** - OAuth callback URL
   - Example: `https://zs-rfp-demo-backend-xxxxx.run.app/auth/google/callback`

### Optional Variables

6. **`GOOGLE_SHARED_DRIVE_ID`** - Google Shared Drive ID (if using shared drives)
   - Only needed if you want to upload to a shared drive using service account

7. **`USE_AI_FOR_RFP`** - Enable AI for RFP generation (default: `true`)
   - Set to `false` to disable AI features

8. **`MAX_FILE_SIZE`** - Maximum file upload size in bytes (default: `10485760` = 10MB)

## Methods to Set Environment Variables

### Method 1: Using the Deployment Script (Recommended)

The `deploy.sh` script automatically sets environment variables during deployment:

```bash
./deploy.sh
```

The script will:
- Prompt you for OAuth credentials
- Automatically set `GCP_PROJECT_ID` and `FRONTEND_URL`
- Configure all necessary environment variables

### Method 2: Using gcloud CLI

#### Set Environment Variables During Deployment

```bash
gcloud run deploy zs-rfp-demo-backend \
  --image gcr.io/YOUR_PROJECT_ID/zs-rfp-demo-backend \
  --region us-central1 \
  --set-env-vars="GCP_PROJECT_ID=your-project-id,FRONTEND_URL=https://your-frontend-url.run.app,GOOGLE_CLIENT_ID=your-client-id,GOOGLE_CLIENT_SECRET=your-secret,GOOGLE_REDIRECT_URI=https://your-backend-url.run.app/auth/google/callback"
```

#### Update Environment Variables After Deployment

```bash
# Update all environment variables
gcloud run services update zs-rfp-demo-backend \
  --region us-central1 \
  --update-env-vars="GCP_PROJECT_ID=your-project-id,FRONTEND_URL=https://your-frontend-url.run.app,GOOGLE_CLIENT_ID=your-client-id,GOOGLE_CLIENT_SECRET=your-secret,GOOGLE_REDIRECT_URI=https://your-backend-url.run.app/auth/google/callback"

# Add a single environment variable
gcloud run services update zs-rfp-demo-backend \
  --region us-central1 \
  --update-env-vars="GOOGLE_SHARED_DRIVE_ID=your-drive-id"

# Remove an environment variable (set to empty)
gcloud run services update zs-rfp-demo-backend \
  --region us-central1 \
  --remove-env-vars="GOOGLE_SHARED_DRIVE_ID"
```

### Method 3: Using Google Cloud Console

1. Go to [Cloud Run Console](https://console.cloud.google.com/run)
2. Select your project
3. Click on your service name (`zs-rfp-demo-backend`)
4. Click **"EDIT & DEPLOY NEW REVISION"**
5. Scroll down to **"Variables & Secrets"** section
6. Click **"ADD VARIABLE"** for each environment variable
7. Enter the variable name and value
8. Click **"DEPLOY"**

### Method 4: Using a YAML File

Create a `service.yaml` file:

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: zs-rfp-demo-backend
spec:
  template:
    spec:
      containers:
      - image: gcr.io/YOUR_PROJECT_ID/zs-rfp-demo-backend
        env:
        - name: GCP_PROJECT_ID
          value: "your-project-id"
        - name: FRONTEND_URL
          value: "https://your-frontend-url.run.app"
        - name: GOOGLE_CLIENT_ID
          value: "your-client-id"
        - name: GOOGLE_CLIENT_SECRET
          value: "your-secret"
        - name: GOOGLE_REDIRECT_URI
          value: "https://your-backend-url.run.app/auth/google/callback"
```

Deploy using:

```bash
gcloud run services replace service.yaml --region us-central1
```

## Service Account Credentials

**Important:** In Cloud Run, you typically **do NOT** need to set `GOOGLE_APPLICATION_CREDENTIALS` as an environment variable pointing to a JSON key file.

Instead:
- Cloud Run automatically uses the **service account attached to the service** for authentication
- The service account credentials are available via Application Default Credentials (ADC)
- Google Cloud client libraries automatically detect and use these credentials

The service account is set during deployment:
```bash
--service-account zs-rfp-demo-sa@PROJECT_ID.iam.gserviceaccount.com
```

**Exception:** If you need to use a different service account key file (not the attached service account), you would need to:
1. Store the JSON key file as a Secret in Secret Manager
2. Mount it as a volume or read it from Secret Manager
3. Set `GOOGLE_APPLICATION_CREDENTIALS` to point to that file

For most use cases, the attached service account is sufficient.

## Verifying Environment Variables

### Check Current Environment Variables

```bash
gcloud run services describe zs-rfp-demo-backend \
  --region us-central1 \
  --format="value(spec.template.spec.containers[0].env)"
```

### Test from Inside the Container

You can check environment variables by viewing Cloud Run logs:

```bash
gcloud run services logs read zs-rfp-demo-backend \
  --region us-central1 \
  --limit 50
```

The application logs will show which environment variables were loaded.

## Common Issues

### Issue: Environment Variables Not Working

**Symptoms:**
- Application fails to start
- Missing configuration errors
- OAuth not working

**Solutions:**
1. Verify variables are set:
   ```bash
   gcloud run services describe zs-rfp-demo-backend --region us-central1
   ```

2. Check for typos in variable names (they are case-sensitive)

3. Ensure values don't have extra spaces or quotes

4. Redeploy the service after updating variables

### Issue: OAuth Redirect URI Mismatch

**Error:** `redirect_uri_mismatch`

**Solution:**
1. Ensure `GOOGLE_REDIRECT_URI` matches exactly what's configured in Google Cloud Console
2. The redirect URI must be: `https://YOUR-BACKEND-URL.run.app/auth/google/callback`
3. Update OAuth credentials in [Google Cloud Console](https://console.cloud.google.com/apis/credentials)

### Issue: CORS Errors

**Error:** CORS policy blocking requests from frontend

**Solution:**
- The application automatically adds `FRONTEND_URL` to allowed CORS origins
- Ensure `FRONTEND_URL` is set correctly
- Check Cloud Run logs to see which origins are allowed

## Best Practices

1. **Use Secret Manager for Sensitive Data**
   - Store secrets like `GOOGLE_CLIENT_SECRET` in Secret Manager
   - Reference them in Cloud Run instead of setting them directly

2. **Use Environment-Specific Values**
   - Different values for dev/staging/production
   - Use different Cloud Run services for each environment

3. **Document Your Variables**
   - Keep a list of required environment variables
   - Document what each variable does

4. **Version Control**
   - Don't commit secrets to git
   - Use `.env.example` files for documentation
   - Store actual values in Secret Manager or Cloud Run configuration

## Example: Setting All Variables at Once

```bash
# Get your URLs first
BACKEND_URL=$(gcloud run services describe zs-rfp-demo-backend \
  --region us-central1 \
  --format="value(status.url)")

FRONTEND_URL=$(gcloud run services describe zs-rfp-demo-frontend \
  --region us-central1 \
  --format="value(status.url)")

# Update all environment variables
gcloud run services update zs-rfp-demo-backend \
  --region us-central1 \
  --update-env-vars="\
GCP_PROJECT_ID=your-project-id,\
FRONTEND_URL=${FRONTEND_URL},\
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com,\
GOOGLE_CLIENT_SECRET=your-secret,\
GOOGLE_REDIRECT_URI=${BACKEND_URL}/auth/google/callback,\
USE_AI_FOR_RFP=true"
```

## Additional Resources

- [Cloud Run Environment Variables Documentation](https://cloud.google.com/run/docs/configuring/environment-variables)
- [Secret Manager Integration](https://cloud.google.com/run/docs/configuring/secrets)
- [Service Accounts in Cloud Run](https://cloud.google.com/run/docs/securing/service-identity)

