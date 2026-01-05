from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
import os
import tempfile
from typing import Optional
import logging
import urllib.parse
import json
from pathlib import Path
from google.oauth2.credentials import Credentials

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    # Load .env file from backend directory
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        logger = logging.getLogger(__name__)
        logger.info(f"Loaded environment variables from {env_path}")
    else:
        # Try loading from current directory
        load_dotenv()
except ImportError:
    # If python-dotenv is not installed, manually load .env
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip().strip('"').strip("'")
        logger = logging.getLogger(__name__)
        logger.info(f"Loaded environment variables manually from {env_path}")

from services.file_processor import FileProcessor
from services.rfp_generator import RFPGenerator
from services.drive_service import DriveService
from services.auth_service import AuthService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ZS RFP Demo API")

# CORS configuration - allow frontend URL from environment or default to localhost
frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
cors_origins = [
    "http://localhost:3000",
    "http://localhost:3001",
]

# Add frontend URL from environment if it's different
if frontend_url not in cors_origins:
    cors_origins.append(frontend_url)

# Handle Cloud Run URLs - allow all *.run.app origins for flexibility
# This is needed because frontend and backend might be on different subdomains
from urllib.parse import urlparse
cors_origin_regex = None
if "run.app" in frontend_url or "cloudfunctions.net" in frontend_url:
    parsed = urlparse(frontend_url)
    # Allow the exact frontend URL
    if f"{parsed.scheme}://{parsed.netloc}" not in cors_origins:
        cors_origins.append(f"{parsed.scheme}://{parsed.netloc}")
    
    # Use regex to allow any *.run.app origin (for Cloud Run flexibility)
    # This allows requests from any Cloud Run service
    if "run.app" in parsed.netloc:
        cors_origin_regex = r"https://.*\.run\.app"

# Also check if we're running on Cloud Run and allow requests from the same domain
# This handles cases where the frontend URL might not be set correctly
backend_url = os.getenv("BACKEND_URL", "")
if backend_url and "run.app" in backend_url:
    parsed_backend = urlparse(backend_url)
    backend_origin = f"{parsed_backend.scheme}://{parsed_backend.netloc}"
    if backend_origin not in cors_origins:
        cors_origins.append(backend_origin)

logger.info(f"CORS allowed origins: {cors_origins}")
if cors_origin_regex:
    logger.info(f"CORS origin regex: {cors_origin_regex}")

# CORS middleware with explicit configuration
cors_middleware_kwargs = {
    "allow_origins": cors_origins,
    "allow_credentials": True,
    "allow_methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],
    "allow_headers": ["*"],
    "expose_headers": ["*"],
    "max_age": 3600,
}

# Add regex pattern if we're on Cloud Run
if cors_origin_regex:
    cors_middleware_kwargs["allow_origin_regex"] = cors_origin_regex

app.add_middleware(
    CORSMiddleware,
    **cors_middleware_kwargs
)

# Initialize services
file_processor = FileProcessor()
rfp_generator = RFPGenerator()
drive_service = DriveService()
auth_service = AuthService()

# Request models
class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

@app.get("/")
async def root():
    return {"message": "ZS RFP Demo API"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Handle chat messages with AI agent"""
    try:
        response = await rfp_generator.chat_with_agent(request.message)
        return ChatResponse(response=response)
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    x_oauth_credentials: Optional[str] = Header(None, alias="X-OAuth-Credentials")
):
    """Upload and process file, generate RFP summary"""
    try:
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file size (not blank)
        file_content = await file.read()
        if len(file_content) == 0:
            raise HTTPException(status_code=400, detail="File is empty")
        
        # Parse OAuth credentials if provided
        oauth_credentials = None
        if x_oauth_credentials:
            try:
                creds_dict = json.loads(urllib.parse.unquote(x_oauth_credentials))
                oauth_credentials = auth_service.get_credentials_from_dict(creds_dict)
                logger.info("Using OAuth credentials for Drive upload")
            except Exception as e:
                logger.warning(f"Could not parse OAuth credentials: {e}. Will attempt without OAuth.")
        
        # Save to temporary file
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            tmp_file.write(file_content)
            tmp_file_path = tmp_file.name
        
        try:
            # Process file based on type
            if file_extension in ['.pdf', '.docx', '.txt']:
                # Extract text from document
                extracted_text = await file_processor.extract_text_from_document(tmp_file_path, file_extension)
            elif file_extension in ['.wav', '.m4a', '.mp3']:
                # Transcribe audio
                extracted_text = await file_processor.transcribe_audio(tmp_file_path)
            else:
                raise HTTPException(status_code=400, detail="Unsupported file type")
            
            if not extracted_text or len(extracted_text.strip()) == 0:
                raise HTTPException(status_code=400, detail="Could not extract content from file")
            
            # Generate RFP summary
            logger.info("Generating RFP summary...")
            rfp_summary = await rfp_generator.generate_rfp_summary(extracted_text)
            
            # Upload to Google Drive
            logger.info("Uploading to Google Drive...")
            try:
                drive_file_id, drive_link = await drive_service.upload_document(
                    rfp_summary,
                    f"RFP_Summary_{file.filename}_{os.urandom(4).hex()}.docx",
                    oauth_credentials=oauth_credentials
                )
            except ValueError as e:
                # If OAuth is required but not provided, give helpful error
                if "No valid credentials available" in str(e):
                    raise HTTPException(
                        status_code=401,
                        detail="Google Drive upload requires authentication. Please log in with Google OAuth first."
                    )
                raise
            
            return JSONResponse({
                "success": True,
                "message": "File processed successfully. RFP summary generated and uploaded to Google Drive.",
                "download_link": drive_link,
                "file_id": drive_file_id
            })
            
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
                
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.get("/api/documents")
async def list_documents(
    x_oauth_credentials: Optional[str] = Header(None, alias="X-OAuth-Credentials"),
    days: int = 30
):
    """List documents from Google Drive created in the last N days"""
    try:
        # Parse OAuth credentials if provided
        oauth_credentials = None
        if x_oauth_credentials:
            try:
                creds_dict = json.loads(urllib.parse.unquote(x_oauth_credentials))
                oauth_credentials = auth_service.get_credentials_from_dict(creds_dict)
                logger.info("Using OAuth credentials for Drive file listing")
            except Exception as e:
                logger.warning(f"Could not parse OAuth credentials: {e}")
                raise HTTPException(
                    status_code=401,
                    detail="Google Drive access requires authentication. Please log in with Google OAuth first."
                )
        else:
            raise HTTPException(
                status_code=401,
                detail="Google Drive access requires authentication. Please log in with Google OAuth first."
            )
        
        # List files from Drive
        try:
            files = await drive_service.list_recent_files(
                oauth_credentials=oauth_credentials,
                days=days
            )
        except Exception as drive_error:
            logger.error(f"Drive API error: {str(drive_error)}")
            # Check if it's a scope/permission error
            error_str = str(drive_error).lower()
            if 'insufficient' in error_str or 'permission' in error_str or 'scope' in error_str:
                raise HTTPException(
                    status_code=403,
                    detail="Insufficient permissions to access Google Drive. Please ensure you granted Drive access during login."
                )
            elif 'invalid' in error_str or 'expired' in error_str or 'token' in error_str:
                raise HTTPException(
                    status_code=401,
                    detail="Authentication expired. Please log out and log in again with Google OAuth."
                )
            else:
                raise HTTPException(
                    status_code=500,
                    detail=f"Error accessing Google Drive: {str(drive_error)}"
                )
        
        return JSONResponse({
            "success": True,
            "files": files,
            "count": len(files)
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")

@app.get("/auth/google")
async def google_auth():
    """Initiate Google OAuth flow"""
    try:
        auth_url = auth_service.get_google_auth_url()
        return {"auth_url": auth_url}
    except ValueError as e:
        # OAuth not configured - return helpful error message
        logger.warning(f"OAuth not configured: {str(e)}")
        raise HTTPException(
            status_code=400, 
            detail="Google OAuth is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables, or use the dummy login (admin/admin123)."
        )
    except Exception as e:
        logger.error(f"Auth error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Authentication error: {str(e)}")

@app.get("/auth/google/callback")
async def google_auth_callback(code: str):
    """Handle Google OAuth callback and redirect to frontend"""
    try:
        user_info = await auth_service.handle_google_callback(code)
        # Redirect to frontend with user info as query params
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        import json
        user_info_json = json.dumps(user_info)
        redirect_url = f"{frontend_url}/auth/callback?auth=success&user={urllib.parse.quote(user_info_json)}"
        return RedirectResponse(url=redirect_url)
    except Exception as e:
        logger.error(f"Callback error: {str(e)}")
        frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")
        error_url = f"{frontend_url}/login?error=auth_failed"
        return RedirectResponse(url=error_url)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

