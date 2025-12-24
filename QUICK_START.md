# Quick Start Guide

Get up and running with ZS-RFP-Demo in 5 minutes!

## Prerequisites Check

- [ ] Node.js 18+ installed (`node --version`)
- [ ] Python 3.9+ installed (`python --version`)
- [ ] Google Cloud account with billing enabled
- [ ] `gcloud` CLI installed (optional, for GCP setup)

## Quick Setup (5 Steps)

### 1. Backend Setup (2 minutes)

```bash
cd backend

# Create and activate virtual environment (required on macOS)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create .env file (copy from .env.example)
# Add your GCP credentials

python app.py
```

**Note**: Always activate the virtual environment before running the backend!

Backend runs on `http://localhost:8000`

### 2. Frontend Setup (2 minutes)

```bash
cd frontend
npm install

# Create .env file with:
# REACT_APP_API_URL=http://localhost:8000

npm start
```

Frontend runs on `http://localhost:3000`

### 3. GCP Setup (1 minute)

**Minimum required:**
1. Enable Google Drive API
2. Create Service Account
3. Download service account key JSON
4. Set `GOOGLE_APPLICATION_CREDENTIALS` in backend `.env`

**For full features:**
- Enable Speech-to-Text API (for audio files)
- Enable Document AI API (for better PDF processing)
- Set up OAuth 2.0 Client (for Google login)

### 4. Test Login

- Username: `admin`
- Password: `admin123`

### 5. Upload a File

- Click "Choose File"
- Select a PDF, DOCX, TXT, or audio file
- Click "Upload & Process"
- Wait for RFP summary generation
- Download from the link provided

## Common Issues & Quick Fixes

| Issue | Quick Fix |
|-------|-----------|
| Backend won't start | Check Python version (3.9+), use virtual environment, install requirements |
| Dependency conflicts | Upgrade google-auth: `pip install --upgrade "google-auth>=2.45.0"` |
| Frontend can't connect | Verify `REACT_APP_API_URL` matches backend URL |
| File upload fails | Check GCP credentials and API enablement |
| OAuth not working | Verify OAuth client ID/secret in `.env` |
| Drive upload fails | Ensure service account has Drive permissions |

## Next Steps

- Read [SETUP.md](./SETUP.md) for detailed setup
- Read [DEPLOYMENT.md](./DEPLOYMENT.md) for GCP deployment
- Read [PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md) for architecture

## Need Help?

1. Check backend logs in terminal
2. Check browser console for frontend errors
3. Verify all environment variables are set
4. Ensure GCP APIs are enabled

Happy coding! 🚀

