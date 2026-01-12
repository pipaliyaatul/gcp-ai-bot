from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel
import os
import tempfile
from typing import Optional, Dict
import logging
import urllib.parse
import json
from pathlib import Path
from google.oauth2.credentials import Credentials
import uuid as uuid_lib
from datetime import datetime

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
from config import Config as config

# Set log level - can be overridden by environment variable
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level, logging.INFO))
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
from services.base_document_service import BaseDocumentService
base_document_service = BaseDocumentService()

# In-memory job status storage (for production, use Redis or Firestore)
job_status: Dict[str, Dict] = {}

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

@app.post("/api/upload-base-document")
async def upload_base_document(
    file: UploadFile = File(...),
    x_oauth_credentials: Optional[str] = Header(None, alias="X-OAuth-Credentials")
):
    """Upload base RFP document template"""
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        file_extension = os.path.splitext(file.filename)[1].lower()
        if file_extension not in ['.pdf', '.docx', '.txt']:
            raise HTTPException(status_code=400, detail="Base document must be PDF, DOCX, or TXT")
        
        # Get user ID (for now, use a default or extract from OAuth)
        user_id = "default_user"  # TODO: Extract from OAuth credentials
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
            content = await file.read()
            tmp_file.write(content)
            tmp_file_path = tmp_file.name
        
        try:
            # Save base document and extract structure
            structure = base_document_service.save_base_document(user_id, tmp_file_path)
            
            return JSONResponse({
                "success": True,
                "message": "Base document uploaded and structure extracted successfully",
                "structure": structure,
                "sections": structure.get("sections", []),
                "total_sections": structure.get("total_sections", 0)
            })
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
                
    except Exception as e:
        logger.error(f"Error uploading base document: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/base-document/structure")
async def get_base_document_structure():
    """Get the structure of the base document"""
    try:
        user_id = "default_user"  # TODO: Extract from OAuth credentials
        structure = base_document_service.get_base_document_structure(user_id)
        
        if not structure:
            raise HTTPException(status_code=404, detail="No base document found. Please upload a base document first.")
        
        return JSONResponse({
            "success": True,
            "structure": structure,
            "sections": structure.get("sections", []),
            "total_sections": structure.get("total_sections", 0)
        })
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting base document structure: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/base-document/status")
async def get_base_document_status():
    """Check if base document is uploaded"""
    try:
        user_id = "default_user"  # TODO: Extract from OAuth credentials
        has_base_document = base_document_service.has_base_document(user_id)
        
        if has_base_document:
            structure = base_document_service.get_base_document_structure(user_id)
            return JSONResponse({
                "success": True,
                "has_base_document": True,
                "sections": structure.get("sections", []),
                "total_sections": structure.get("total_sections", 0),
                "message": "Base document is uploaded and ready to use"
            })
        else:
            return JSONResponse({
                "success": True,
                "has_base_document": False,
                "message": "No base document uploaded. Generated content may differ from expected structure.",
                "warning": "Without a base document, the system will use default sections which may not match your requirements."
            })
    except Exception as e:
        logger.error(f"Error checking base document status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/upload/status/{job_id}")
async def get_upload_status(job_id: str):
    """Get status of an upload/processing job"""
    if job_id not in job_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    status = job_status[job_id]
    return JSONResponse({
        "job_id": job_id,
        "status": status.get("status", "unknown"),
        "progress": status.get("progress", 0),
        "message": status.get("message", ""),
        "result": status.get("result"),
        "error": status.get("error"),
        "created_at": status.get("created_at"),
        "updated_at": status.get("updated_at")
    })

def update_job_progress(job_id: str, progress: int, message: str):
    """Helper to update job progress"""
    if job_id in job_status:
        job_status[job_id].update({
            "progress": progress,
            "message": message,
            "updated_at": datetime.utcnow().isoformat()
        })

async def process_file_background(
    job_id: str,
    tmp_file_path: str,
    file_extension: str,
    filename: str,
    oauth_credentials,
    is_audio_file: bool
):
    """Background task to process file and generate RFP"""
    try:
        user_id = "default_user"  # TODO: Extract from OAuth credentials
        
        job_status[job_id] = {
            "status": "processing",
            "progress": 5,
            "message": "Starting file processing...",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Check if base document exists
        has_base_document = base_document_service.has_base_document(user_id)
        base_structure = None
        if has_base_document:
            base_structure = base_document_service.get_base_document_structure(user_id)
            update_job_progress(job_id, 10, f"Base document found with {base_structure.get('total_sections', 0)} sections. Extracting content...")
        else:
            update_job_progress(job_id, 10, "No base document found. Extracting content from file...")
        
        # Process file based on type
        if file_extension in ['.pdf', '.docx', '.txt']:
            update_job_progress(job_id, 15, "Extracting text from document...")
            extracted_text = await file_processor.extract_text_from_document(tmp_file_path, file_extension)
            update_job_progress(job_id, 30, f"Text extracted successfully ({len(extracted_text)} characters)")
        elif file_extension in ['.wav', '.m4a', '.mp3', '.webm']:
            # Transcribe audio with detailed progress
            update_job_progress(job_id, 15, "Starting audio transcription...")
            
            # Progress callback for transcription with relative percentages
            def transcription_progress(step: str, message: str):
                if step == "upload":
                    update_job_progress(job_id, 18, f"📤 Uploading audio file to cloud storage...")
                elif step == "transcribe":
                    # Parse message to extract progress if available
                    if "estimated" in message.lower() or "%" in message:
                        # Extract percentage from message if present
                        import re
                        pct_match = re.search(r'(\d+)%', message)
                        if pct_match:
                            pct = int(pct_match.group(1))
                            # Map transcription progress (0-95%) to overall progress (20-40%)
                            overall_pct = 20 + int((pct / 95) * 20)
                            update_job_progress(job_id, overall_pct, f"🎤 {message}")
                        else:
                            update_job_progress(job_id, 25, f"🎤 {message}")
                    elif "completed successfully" in message.lower():
                        update_job_progress(job_id, 38, f"✅ {message}")
                    else:
                        update_job_progress(job_id, 25, f"🎤 {message}")
                elif step == "complete":
                    update_job_progress(job_id, 40, f"✅ Audio transcription complete! ({len(message)} characters transcribed)")
                elif step == "error":
                    update_job_progress(job_id, 20, f"❌ Transcription error: {message}")
            
            extracted_text = await file_processor.transcribe_audio(tmp_file_path, progress_callback=transcription_progress)
        else:
            raise ValueError("Unsupported file type")
        
        if not extracted_text or len(extracted_text.strip()) == 0:
            raise ValueError("Could not extract content from file")
        
        # Generate RFP summary with statistics
        if has_base_document and base_structure:
            update_job_progress(job_id, 42, f"📋 Aligning content with base document structure ({base_structure.get('total_sections', 0)} sections)...")
            
            # Progress callback for RFP generation with descriptive messages
            def progress_callback(progress, message):
                # Map internal progress (0-100) to overall progress (42-88)
                # More granular mapping for better user feedback
                if progress <= 20:
                    overall_progress = 42 + int((progress / 20) * 5)  # 42-47: Preparing
                elif progress <= 30:
                    overall_progress = 47 + int(((progress - 20) / 10) * 8)  # 47-55: Calling AI
                elif progress <= 70:
                    overall_progress = 55 + int(((progress - 30) / 40) * 15)  # 55-70: Parsing
                elif progress <= 85:
                    overall_progress = 70 + int(((progress - 70) / 15) * 10)  # 70-80: Combining sections
                else:
                    overall_progress = 80 + int(((progress - 85) / 15) * 8)  # 80-88: Finalizing
                
                # Add emoji prefix based on operation
                if "Preparing" in message or "prompt" in message.lower():
                    emoji_msg = f"📝 {message}"
                elif "Calling AI" in message or "AI model" in message.lower():
                    emoji_msg = f"🤖 {message}"
                elif "Parsing" in message or "extracting" in message.lower():
                    emoji_msg = f"🔍 {message}"
                elif "Combining" in message or "Combining" in message or "sections" in message.lower():
                    emoji_msg = f"📄 {message}"
                elif "Updating section" in message or "section" in message.lower():
                    emoji_msg = f"✏️ {message}"
                elif "complete" in message.lower() or "successfully" in message.lower():
                    emoji_msg = f"✅ {message}"
                else:
                    emoji_msg = f"⚙️ {message}"
                
                update_job_progress(job_id, overall_progress, emoji_msg)
            
            rfp_summary, statistics = await rfp_generator.generate_rfp_summary(
                extracted_text,
                base_document_structure=base_structure,
                progress_callback=progress_callback
            )
        else:
            update_job_progress(job_id, 42, "📝 Generating RFP summary with AI using default sections...")
            
            def progress_callback(progress, message):
                # Map internal progress (0-100) to overall progress (42-88)
                if progress <= 20:
                    overall_progress = 42 + int((progress / 20) * 5)  # 42-47: Preparing
                elif progress <= 30:
                    overall_progress = 47 + int(((progress - 20) / 10) * 8)  # 47-55: Calling AI
                elif progress <= 70:
                    overall_progress = 55 + int(((progress - 30) / 40) * 15)  # 55-70: Parsing
                elif progress <= 85:
                    overall_progress = 70 + int(((progress - 70) / 15) * 10)  # 70-80: Adding sections
                else:
                    overall_progress = 80 + int(((progress - 85) / 15) * 8)  # 80-88: Finalizing
                
                # Add emoji prefix based on operation
                if "Preparing" in message or "prompt" in message.lower():
                    emoji_msg = f"📝 {message}"
                elif "Calling AI" in message or "AI model" in message.lower():
                    emoji_msg = f"🤖 {message}"
                elif "Parsing" in message or "extracting" in message.lower():
                    emoji_msg = f"🔍 {message}"
                elif "Adding section" in message or "section" in message.lower():
                    emoji_msg = f"✏️ {message}"
                elif "complete" in message.lower() or "successfully" in message.lower():
                    emoji_msg = f"✅ {message}"
                else:
                    emoji_msg = f"⚙️ {message}"
                
                update_job_progress(job_id, overall_progress, emoji_msg)
            
            rfp_summary, statistics = await rfp_generator.generate_rfp_summary(
                extracted_text,
                progress_callback=progress_callback
            )
        
        update_job_progress(job_id, 90, "☁️ Uploading final document to Google Drive...")
        
        # Upload to Google Drive
        try:
            drive_file_id, drive_link = await drive_service.upload_document(
                rfp_summary,
                f"RFP_Summary_{filename}_{os.urandom(4).hex()}.docx",
                oauth_credentials=oauth_credentials
            )
        except ValueError as e:
            if "No valid credentials available" in str(e):
                error_msg = "Google Drive upload requires authentication. Please log in with Google OAuth first."
                job_status[job_id].update({
                    "status": "failed",
                    "error": error_msg,
                    "updated_at": datetime.utcnow().isoformat()
                })
                return
            raise
        
        job_status[job_id].update({
            "status": "completed",
            "progress": 100,
            "message": "File processed successfully!",
            "result": {
                "success": True,
                "message": "File processed successfully. RFP summary generated and uploaded to Google Drive.",
                "download_link": drive_link,
                "file_id": drive_file_id,
                "statistics": statistics
            },
            "updated_at": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Background processing error for job {job_id}: {str(e)}")
        job_status[job_id].update({
            "status": "failed",
            "progress": 0,
            "message": f"Error: {str(e)}",
            "error": str(e),
            "updated_at": datetime.utcnow().isoformat()
        })
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)

@app.post("/api/upload")
async def upload_file(
    file: UploadFile = File(...),
    x_oauth_credentials: Optional[str] = Header(None, alias="X-OAuth-Credentials"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    async_mode: Optional[bool] = Query(None, description="Process in background (default: true for audio files)"),
    proceed_without_base: Optional[bool] = Query(False, description="Proceed without base document (user consent)")
):
    """Upload and process file, generate RFP summary"""
    try:
        user_id = "default_user"  # TODO: Extract from OAuth credentials
        
        # Check if base document exists
        has_base_document = base_document_service.has_base_document(user_id)
        
        # If no base document and user hasn't consented, return warning
        if not has_base_document and not proceed_without_base:
            return JSONResponse({
                "success": False,
                "requires_consent": True,
                "message": "No base document uploaded",
                "warning": "A base document has not been uploaded. The generated content will use default sections which may differ from your expected structure.",
                "details": "To ensure consistent formatting and structure, please upload a base RFP document template first. You can proceed without it, but the output may not match your requirements.",
                "action_required": "user_consent"
            }, status_code=200)  # 200 because this is expected behavior, not an error
        # Validate file
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")
        
        # Check file size (not blank) - read in chunks for large files to avoid memory issues
        file_extension = os.path.splitext(file.filename)[1].lower()
        is_audio_file = file_extension in ['.wav', '.m4a', '.mp3', '.webm']
        max_size = config.MAX_AUDIO_FILE_SIZE if is_audio_file else config.MAX_FILE_SIZE
        
        # For large files, check size without loading entire file into memory
        # Read first chunk to check if file exists, then validate size
        chunk = await file.read(1024)  # Read first 1KB
        if len(chunk) == 0:
            raise HTTPException(status_code=400, detail="File is empty")
        
        # Get file size from content-length header if available, otherwise estimate
        file_size = 0
        if hasattr(file, 'size') and file.size:
            file_size = file.size
        else:
            # Need to read more to get size - but for large files, we'll check during streaming write
            # Reset file pointer
            await file.seek(0)
        
        # For files that might be large, we'll validate during the streaming write
        # But check header size first if available
        if file_size > max_size:
            max_size_mb = max_size / (1024 * 1024)
            file_size_mb = file_size / (1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail=f"File size ({file_size_mb:.1f}MB) exceeds maximum allowed size ({max_size_mb:.1f}MB) for {file_extension} files"
            )
        
        # Reset file pointer for processing
        await file.seek(0)
        
        # Parse OAuth credentials if provided
        oauth_credentials = None
        if x_oauth_credentials:
            try:
                creds_dict = json.loads(urllib.parse.unquote(x_oauth_credentials))
                oauth_credentials = auth_service.get_credentials_from_dict(creds_dict)
                logger.info("Using OAuth credentials for Drive upload")
            except Exception as e:
                logger.warning(f"Could not parse OAuth credentials: {e}. Will attempt without OAuth.")
        
        # Save to temporary file using streaming to avoid loading entire file into memory
        # This is especially important for large audio files (26MB+)
        tmp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
                tmp_file_path = tmp_file.name
                
                # Stream file content in chunks to avoid memory issues
                chunk_size = 1024 * 1024  # 1MB chunks for all files
                total_size = 0
                
                while True:
                    chunk = await file.read(chunk_size)
                    if not chunk:
                        break
                    
                    total_size += len(chunk)
                    
                    # Check size limit during streaming (for files without size header)
                    if total_size > max_size:
                        max_size_mb = max_size / (1024 * 1024)
                        file_size_mb = total_size / (1024 * 1024)
                        raise HTTPException(
                            status_code=400,
                            detail=f"File size ({file_size_mb:.1f}MB) exceeds maximum allowed size ({max_size_mb:.1f}MB) for {file_extension} files"
                        )
                    
                    tmp_file.write(chunk)
                
                logger.info(f"Streamed file to temporary location: {tmp_file_path} ({total_size / (1024 * 1024):.2f}MB)")
        except HTTPException:
            # Clean up temp file if size validation failed
            if tmp_file_path and os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
            raise
        
        # For audio files or if async_mode is explicitly enabled, process in background
        # This provides better user experience for long-running operations
        # Default: async for audio files, sync for text files
        use_async = async_mode if async_mode is not None else is_audio_file
        
        if use_async:
            job_id = str(uuid_lib.uuid4())
            job_status[job_id] = {
                "status": "queued",
                "progress": 0,
                "message": "File uploaded, processing started...",
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Start background processing
            background_tasks.add_task(
                process_file_background,
                job_id,
                tmp_file_path,
                file_extension,
                file.filename,
                oauth_credentials,
                is_audio_file
            )
            
            return JSONResponse({
                "success": True,
                "message": "File upload accepted. Processing in background.",
                "job_id": job_id,
                "status_url": f"/api/upload/status/{job_id}",
                "async": True
            })
        
        # Synchronous processing for small files (original behavior)
        try:
            # Process file based on type
            if file_extension in ['.pdf', '.docx', '.txt']:
                # Extract text from document
                extracted_text = await file_processor.extract_text_from_document(tmp_file_path, file_extension)
            elif file_extension in ['.wav', '.m4a', '.mp3', '.webm']:
                # Transcribe audio
                extracted_text = await file_processor.transcribe_audio(tmp_file_path)
            else:
                raise HTTPException(status_code=400, detail="Unsupported file type")
            
            if not extracted_text or len(extracted_text.strip()) == 0:
                raise HTTPException(status_code=400, detail="Could not extract content from file")
            
            # Check if base document exists (for synchronous path too)
            user_id = "default_user"  # TODO: Extract from OAuth credentials
            has_base_document = base_document_service.has_base_document(user_id)
            base_structure = None
            if has_base_document:
                base_structure = base_document_service.get_base_document_structure(user_id)
                logger.info(f"Base document found with {base_structure.get('total_sections', 0)} sections")
            
            # Generate RFP summary with statistics
            logger.info("Generating RFP summary...")
            if has_base_document and base_structure:
                rfp_summary, statistics = await rfp_generator.generate_rfp_summary(
                    extracted_text,
                    base_document_structure=base_structure
                )
            else:
                rfp_summary, statistics = await rfp_generator.generate_rfp_summary(extracted_text)
            
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
            
            # Log statistics
            logger.info(f"RFP generation statistics: {json.dumps(statistics, indent=2)}")
            
            return JSONResponse({
                "success": True,
                "message": "File processed successfully. RFP summary generated and uploaded to Google Drive.",
                "download_link": drive_link,
                "file_id": drive_file_id,
                "statistics": statistics  # Include LLM performance statistics
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

