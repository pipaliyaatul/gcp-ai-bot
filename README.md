# ZS-RFP-Demo

A comprehensive RFP (Request for Proposal) analysis application built with React frontend and Python FastAPI backend, integrated with Google Cloud Platform services.

## 🚀 Features

- **User Authentication**: 
  - Dummy username/password login (admin/admin123)
  - Google OAuth integration for production use
  - Secure session management

- **AI Chat Interface**: 
  - Interactive chat interface similar to ADK
  - Real-time messaging with AI agent
  - Message history and typing indicators

- **File Upload & Processing**: 
  - **Text Files**: PDF, DOCX, TXT
  - **Audio Files**: WAV, M4A, MP3
  - File validation (non-empty, size limits)
  - Automatic text extraction and audio transcription

- **RFP Summary Generation**: 
  - Automatically analyzes uploaded content
  - Generates structured RFP standard guidelines document
  - Includes: Executive Summary, Requirements, Technical Specs, Timeline, Budget, Compliance

- **Google Drive Integration**: 
  - Uploads generated summaries to Google Drive
  - Provides shareable download links
  - Direct download from UI

## 📁 Project Structure

```
ZS-RFP-Demo/
├── frontend/              # React application
│   ├── src/
│   │   ├── components/    # React components (Login, ChatInterface)
│   │   ├── context/       # Auth context
│   │   └── ...
│   ├── public/           # Static files
│   ├── Dockerfile         # Docker configuration
│   └── package.json       # Dependencies
│
├── backend/               # Python FastAPI backend
│   ├── services/          # Service modules
│   │   ├── file_processor.py    # File processing
│   │   ├── rfp_generator.py     # RFP generation
│   │   ├── drive_service.py     # Google Drive
│   │   └── auth_service.py      # Authentication
│   ├── app.py            # FastAPI application
│   ├── Dockerfile        # Docker configuration
│   └── requirements.txt  # Python dependencies
│
└── Documentation/
    ├── README.md         # This file
    ├── QUICK_START.md    # Quick setup guide
    ├── SETUP.md          # Detailed setup instructions
    ├── DEPLOYMENT.md     # GCP deployment guide
    └── PROJECT_STRUCTURE.md  # Architecture overview
```

## ⚡ Quick Start

### Prerequisites
- Node.js 18+
- Python 3.9+
- Google Cloud Platform account

### 1. Backend Setup

```bash
cd backend
pip install -r requirements.txt

# Create .env file with GCP credentials
# See SETUP.md for details

python app.py
```

Backend runs on `http://localhost:8000`

### 2. Frontend Setup

```bash
cd frontend
npm install

# Create .env file:
# REACT_APP_API_URL=http://localhost:8000

npm start
```

Frontend runs on `http://localhost:3000`

### 3. Test the Application

1. Navigate to `http://localhost:3000`
2. Login with:
   - Username: `admin`
   - Password: `admin123`
3. Upload a file (PDF, DOCX, TXT, or audio)
4. Wait for RFP summary generation
5. Download the generated document

## 📚 Documentation

- **[QUICK_START.md](./QUICK_START.md)** - Get started in 5 minutes
- **[SETUP.md](./SETUP.md)** - Detailed local setup instructions
- **[GCP_SETUP.md](./GCP_SETUP.md)** - **GCP Credentials Configuration Guide** ⭐
- **[DEPLOYMENT.md](./DEPLOYMENT.md)** - GCP deployment guide
- **[PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md)** - Architecture and structure

## 🔧 Configuration

### Backend Environment Variables

Create `backend/.env`:
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

### Frontend Environment Variables

Create `frontend/.env`:
```bash
REACT_APP_API_URL=http://localhost:8000
```

## 🚢 Deployment

### GCP Services Required

- **Cloud Run** (for backend and frontend)
- **Google Drive API** (for document storage)
- **Speech-to-Text API** (for audio transcription)
- **Document AI API** (optional, for enhanced PDF processing)

See [DEPLOYMENT.md](./DEPLOYMENT.md) for complete deployment instructions.

## 🛠️ Technology Stack

### Frontend
- React 18
- React Router
- Axios
- CSS3

### Backend
- Python 3.9+
- FastAPI
- Google Cloud APIs
- python-docx
- PyPDF2

### Infrastructure
- Google Cloud Run
- Docker
- Nginx

## 📋 API Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `POST /api/chat` - Chat with AI agent
- `POST /api/upload` - Upload and process files
- `GET /auth/google` - Initiate Google OAuth
- `GET /auth/google/callback` - OAuth callback

## 🔒 Security

- Service account authentication
- OAuth 2.0 for user login
- File validation
- CORS configuration
- Environment-based secrets

## 🎯 Features in Detail

### File Processing
- **PDF**: Text extraction using PyPDF2 (Document AI optional)
- **DOCX**: Text extraction using python-docx
- **TXT**: Direct text reading
- **Audio**: Transcription using Google Speech-to-Text API

### RFP Generation
- Executive Summary
- Key Requirements extraction
- Technical Specifications
- Timeline and Milestones
- Budget Considerations
- Compliance and Standards
- Recommended Next Steps

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

See LICENSE file for details.

## 🆘 Support

For issues or questions:
1. Check the documentation files
2. Review backend logs
3. Check browser console
4. Verify GCP configuration

## 🎉 Next Steps

- Integrate with Vertex AI for enhanced RFP analysis
- Add support for more file formats
- Implement batch processing
- Add user dashboard
- Enable document versioning

