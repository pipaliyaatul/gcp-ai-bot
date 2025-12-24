# Setup Guide for ZS-RFP-Demo

This guide will help you set up and run the ZS-RFP-Demo application locally.

## Prerequisites

1. **Node.js** (v18 or higher) and npm
2. **Python** (3.9 or higher) and pip
3. **Google Cloud Platform** account
4. **Git** (optional, for cloning)

## Step 1: Clone or Navigate to Project

```bash
cd ZS-RFP-Demo
```

## Step 2: Backend Setup

### 2.1 Create Virtual Environment (Recommended)

**Important**: On macOS with Homebrew Python, you must use a virtual environment.

```bash
cd backend

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

**Alternative**: Use the setup script:
```bash
cd backend
./setup_venv.sh
source venv/bin/activate
```

### 2.2 Install Python Dependencies

```bash
# Make sure virtual environment is activated (you should see (venv) in your prompt)
pip install -r requirements.txt
```

**Note**: If you see dependency conflicts, try:
```bash
pip install --upgrade "google-auth>=2.45.0,<3.0.0" "google-auth[requests]>=2.45.0,<3.0.0"
pip install -r requirements.txt
```

### 2.3 Set Up Google Cloud Credentials

1. Create a GCP project (or use existing)
2. Enable the following APIs:
   - Google Drive API
   - Google Speech-to-Text API
   - Google Document AI API (optional, for better PDF processing)
   - Google Cloud Storage API (optional)

3. Create a Service Account:
   ```bash
   # Using gcloud CLI
   gcloud iam service-accounts create zs-rfp-demo-sa \
     --display-name="ZS RFP Demo Service Account"
   
   # Grant necessary roles
   gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
     --member="serviceAccount:zs-rfp-demo-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
     --role="roles/drive.file"
   
   # Download key
   gcloud iam service-accounts keys create service-account-key.json \
     --iam-account=zs-rfp-demo-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com
   ```

4. Set up OAuth 2.0 Client (for Google Login):
   - Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
   - Create OAuth 2.0 Client ID
   - Add redirect URI: `http://localhost:8000/auth/google/callback`

### 2.4 Configure Environment Variables

Create a `.env` file in the `backend` directory:

```bash
# Backend .env
GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json
GCP_PROJECT_ID=your-project-id
GOOGLE_CLIENT_ID=your-oauth-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-oauth-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
FRONTEND_URL=http://localhost:3000
USE_AI_FOR_RFP=true
MAX_FILE_SIZE=10485760
```

### 2.5 Run Backend

**Important**: Make sure your virtual environment is activated before running:

```bash
# From backend directory
python app.py

# Or using uvicorn directly
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

The backend will be available at `http://localhost:8000`

## Step 3: Frontend Setup

### 3.1 Install Dependencies

```bash
cd frontend
npm install
```

### 3.2 Configure Environment Variables

Create a `.env` file in the `frontend` directory:

```bash
# Frontend .env
REACT_APP_API_URL=http://localhost:8000
```

### 3.3 Run Frontend

```bash
# From frontend directory
npm start
```

The frontend will be available at `http://localhost:3000`

## Step 4: Test the Application

1. **Open Browser**: Navigate to `http://localhost:3000`

2. **Login**:
   - Use dummy credentials:
     - Username: `admin`
     - Password: `admin123`
   - Or click "Sign in with Google" (requires OAuth setup)

3. **Upload a File**:
   - Click "Choose File" button
   - Select a PDF, DOCX, TXT, or audio file (WAV, M4A, MP3)
   - Click "Upload & Process"
   - Wait for processing (may take a few moments)
   - Download link will appear in chat

4. **Chat with AI**:
   - Type a message in the chat input
   - Press Enter or click Send
   - AI will respond

## Troubleshooting

### Backend Issues

1. **Import Errors**:
   ```bash
   # Make sure you're in the backend directory
   # Install missing packages
   pip install -r requirements.txt
   ```

2. **Google Cloud Authentication Errors**:
   - Verify `GOOGLE_APPLICATION_CREDENTIALS` points to valid service account key
   - Check that service account has required permissions
   - Ensure APIs are enabled in GCP Console

3. **Port Already in Use**:
   ```bash
   # Change port in app.py or use:
   uvicorn app:app --port 8001
   ```

### Frontend Issues

1. **Cannot Connect to Backend**:
   - Verify backend is running on port 8000
   - Check `REACT_APP_API_URL` in `.env` file
   - Check CORS settings in backend `app.py`

2. **Build Errors**:
   ```bash
   # Clear cache and reinstall
   rm -rf node_modules package-lock.json
   npm install
   ```

3. **OAuth Redirect Issues**:
   - Verify `GOOGLE_REDIRECT_URI` matches OAuth client settings
   - Check that redirect URI is added in Google Cloud Console

### File Upload Issues

1. **File Not Processing**:
   - Check file size (should be < 10MB by default)
   - Verify file is not corrupted
   - Check backend logs for errors

2. **Audio Transcription Fails**:
   - Ensure Google Speech-to-Text API is enabled
   - Check service account has Speech-to-Text permissions
   - Verify audio file format is supported

3. **Drive Upload Fails**:
   - Verify Google Drive API is enabled
   - Check service account has Drive permissions
   - Ensure `GOOGLE_APPLICATION_CREDENTIALS` is set correctly

## Development Tips

1. **Hot Reload**: Both frontend and backend support hot reload during development
2. **Logs**: Check console/terminal for detailed error messages
3. **API Testing**: Use tools like Postman or curl to test backend endpoints:
   ```bash
   curl http://localhost:8000/health
   ```

## Next Steps

- Review [DEPLOYMENT.md](./DEPLOYMENT.md) for GCP deployment instructions
- Customize RFP summary generation in `backend/services/rfp_generator.py`
- Integrate with Vertex AI or OpenAI for better AI responses
- Add more file format support

## Support

For issues:
1. Check logs in backend terminal
2. Check browser console for frontend errors
3. Verify all environment variables are set correctly
4. Ensure all GCP APIs are enabled and credentials are valid

