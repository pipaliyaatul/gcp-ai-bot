# ZS-RFP-Demo Project Structure

## Overview

This project is structured as a full-stack application with separate frontend and backend components, designed to be deployed on Google Cloud Platform.

```
ZS-RFP-Demo/
├── frontend/                 # React frontend application
│   ├── public/              # Static files
│   │   └── index.html       # HTML template
│   ├── src/                 # Source code
│   │   ├── components/      # React components
│   │   │   ├── Login.js     # Login component
│   │   │   ├── Login.css    # Login styles
│   │   │   ├── ChatInterface.js  # Main chat UI
│   │   │   └── ChatInterface.css # Chat styles
│   │   ├── context/         # React context
│   │   │   └── AuthContext.js # Authentication context
│   │   ├── App.js           # Main app component
│   │   ├── App.css          # App styles
│   │   ├── index.js         # Entry point
│   │   └── index.css        # Global styles
│   ├── package.json         # Node dependencies
│   ├── Dockerfile           # Docker image for frontend
│   ├── nginx.conf           # Nginx configuration
│   └── .gitignore           # Git ignore rules
│
├── backend/                 # Python FastAPI backend
│   ├── services/            # Service modules
│   │   ├── __init__.py
│   │   ├── file_processor.py    # File processing (text extraction, transcription)
│   │   ├── rfp_generator.py      # RFP summary generation
│   │   ├── drive_service.py      # Google Drive integration
│   │   └── auth_service.py       # Authentication service
│   ├── app.py               # FastAPI application
│   ├── config.py            # Configuration settings
│   ├── requirements.txt     # Python dependencies
│   ├── Dockerfile           # Docker image for backend
│   └── .gitignore           # Git ignore rules
│
├── README.md                # Project overview
├── SETUP.md                 # Local setup instructions
├── DEPLOYMENT.md            # GCP deployment guide
├── PROJECT_STRUCTURE.md     # This file
└── .gitignore               # Root git ignore

```

## Frontend Structure

### Components

- **Login.js**: Handles user authentication
  - Dummy username/password login
  - Google OAuth integration
  - Form validation

- **ChatInterface.js**: Main application interface
  - Chat messages display
  - File upload functionality
  - AI agent interaction
  - Download links for generated documents

### Context

- **AuthContext.js**: Manages authentication state
  - User session management
  - Login/logout functions
  - Persistent authentication (localStorage)

## Backend Structure

### Services

- **file_processor.py**: Handles file processing
  - Text extraction from PDF, DOCX, TXT
  - Audio transcription (WAV, M4A, MP3)
  - Integration with GCP services (Speech-to-Text, Document AI)

- **rfp_generator.py**: Generates RFP summaries
  - Document creation using python-docx
  - Content analysis and extraction
  - Structured RFP document generation

- **drive_service.py**: Google Drive operations
  - Document upload
  - Shareable link generation
  - File management

- **auth_service.py**: Authentication handling
  - Google OAuth flow
  - User information retrieval

### API Endpoints

- `GET /`: API information
- `GET /health`: Health check
- `POST /api/chat`: Chat with AI agent
- `POST /api/upload`: Upload and process files
- `GET /auth/google`: Initiate Google OAuth
- `GET /auth/google/callback`: OAuth callback handler

## Key Features

1. **File Upload & Processing**
   - Supports multiple file formats
   - Validates file size and content
   - Extracts text or transcribes audio

2. **RFP Summary Generation**
   - Analyzes uploaded content
   - Generates structured RFP document
   - Includes requirements, specs, timeline, etc.

3. **Google Drive Integration**
   - Uploads generated documents
   - Provides shareable download links
   - Manages file permissions

4. **Authentication**
   - Dummy credentials for testing
   - Google OAuth for production
   - Session management

## Technology Stack

### Frontend
- React 18
- React Router
- Axios for API calls
- CSS3 for styling

### Backend
- Python 3.9+
- FastAPI
- Google Cloud APIs
  - Drive API
  - Speech-to-Text API
  - Document AI API
- python-docx for document generation
- PyPDF2 for PDF processing

### Deployment
- Google Cloud Run (recommended)
- Docker containers
- Nginx for frontend serving

## Environment Variables

### Backend
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account key
- `GCP_PROJECT_ID`: GCP project ID
- `GOOGLE_CLIENT_ID`: OAuth client ID
- `GOOGLE_CLIENT_SECRET`: OAuth client secret
- `GOOGLE_REDIRECT_URI`: OAuth redirect URI
- `FRONTEND_URL`: Frontend application URL
- `USE_AI_FOR_RFP`: Enable AI features
- `MAX_FILE_SIZE`: Maximum upload size

### Frontend
- `REACT_APP_API_URL`: Backend API URL

## Development Workflow

1. **Local Development**
   - Run backend: `cd backend && python app.py`
   - Run frontend: `cd frontend && npm start`
   - Access at `http://localhost:3000`

2. **Testing**
   - Test file uploads
   - Verify RFP generation
   - Check Drive integration
   - Test authentication flows

3. **Deployment**
   - Build Docker images
   - Deploy to Cloud Run
   - Configure environment variables
   - Set up monitoring

## File Flow

1. User uploads file → Frontend
2. Frontend sends to → Backend `/api/upload`
3. Backend processes file → `file_processor.py`
4. Backend generates RFP → `rfp_generator.py`
5. Backend uploads to Drive → `drive_service.py`
6. Backend returns download link → Frontend
7. User downloads document → Google Drive

## Security Considerations

- Service account credentials stored securely
- OAuth tokens handled properly
- File validation on upload
- CORS configuration
- Environment variables for secrets
- No credentials in code

## Future Enhancements

- Integration with Vertex AI for better RFP analysis
- Support for more file formats
- Batch file processing
- User dashboard
- Document versioning
- Advanced search capabilities
- Multi-user collaboration

