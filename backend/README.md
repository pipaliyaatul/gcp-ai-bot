# Backend Setup and Run Guide

## Quick Start

### Option 1: Using the Run Script (Easiest)

```bash
cd backend
./run.sh
```

This script will:
- Create virtual environment if it doesn't exist
- Activate the virtual environment
- Install dependencies if needed
- Run the backend server

### Option 2: Manual Setup

1. **Create and activate virtual environment:**
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

3. **Set up environment variables:**
   Create a `.env` file with:
   ```bash
   GOOGLE_APPLICATION_CREDENTIALS=./service-account-key.json
   GCP_PROJECT_ID=your-project-id
   GOOGLE_CLIENT_ID=your-oauth-client-id
   GOOGLE_CLIENT_SECRET=your-oauth-client-secret
   GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
   FRONTEND_URL=http://localhost:3000
   USE_AI_FOR_RFP=true
   MAX_FILE_SIZE=10485760
   ```

4. **Run the application:**
   ```bash
   python app.py
   ```

## Important Notes

- **Always activate the virtual environment** before running the app
- You should see `(venv)` in your terminal prompt when it's activated
- The backend will run on `http://localhost:8000`

## Troubleshooting

### ModuleNotFoundError: No module named 'fastapi'

This means the virtual environment is not activated or dependencies are not installed.

**Solution:**
```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run again
python app.py
```

### Dependency Conflicts

If you see dependency conflicts:
```bash
source venv/bin/activate
pip install --upgrade "google-auth>=2.45.0,<3.0.0"
pip install -r requirements.txt
```

### Port Already in Use

If port 8000 is already in use:
```bash
# Change port in app.py or use:
uvicorn app:app --port 8001
```

### Google OAuth Not Configured

**Error:** `Google OAuth credentials not configured` or 400 error on `/auth/google`

**Solution:**
- This is expected if you haven't set up OAuth credentials
- Use the dummy login (admin/admin123) instead
- To enable OAuth, set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in your `.env` file

### Google Drive Credentials Not Found

**Warning:** `Google Drive credentials not found. Drive upload will not work.`

**Solution:**
- Set `GOOGLE_APPLICATION_CREDENTIALS` in your `.env` file
- Point it to your service account key JSON file
- Ensure the service account has Drive API permissions

### Speech-to-Text SSL/Connection Errors

**Error:** `SSL routines:OPENSSL_internal:SSLV3_ALERT_BAD_RECORD_MAC` or `Stream removed`

**Possible causes:**
1. Network/firewall issues blocking Google Cloud APIs
2. Incorrect or expired credentials
3. SSL certificate issues

**Solutions:**
1. Verify `GOOGLE_APPLICATION_CREDENTIALS` points to a valid service account key
2. Check your network connection and firewall settings
3. Ensure Speech-to-Text API is enabled in your GCP project
4. Verify service account has `Cloud Speech Client` role
5. Try using text files (PDF, DOCX, TXT) instead of audio files for testing

### Audio Transcription Fails

**Error:** `Audio transcription requires Google Speech-to-Text API setup`

**Solution:**
1. Enable Speech-to-Text API in GCP Console
2. Set `GOOGLE_APPLICATION_CREDENTIALS` environment variable
3. Ensure service account has proper permissions
4. Check audio file format is supported (WAV, M4A, MP3)
5. Verify audio file is not corrupted and is under 10MB

## API Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `POST /api/chat` - Chat with AI agent
- `POST /api/upload` - Upload and process files
- `GET /auth/google` - Initiate Google OAuth
- `GET /auth/google/callback` - OAuth callback

## Development

For development with auto-reload:
```bash
source venv/bin/activate
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

