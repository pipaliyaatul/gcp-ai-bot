import os
import logging
import tempfile
from datetime import datetime, timedelta
from typing import Tuple, Optional, List, Dict
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from docx import Document

logger = logging.getLogger(__name__)

class DriveService:
    """Handles Google Drive operations for uploading and sharing documents"""
    
    def __init__(self):
        # Using drive.file scope - allows access to files created by this app
        # For broader access, use 'https://www.googleapis.com/auth/drive.readonly'
        self.scopes = ['https://www.googleapis.com/auth/drive.file']
        self.credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        self.shared_drive_id = os.getenv('GOOGLE_SHARED_DRIVE_ID')  # Optional: Shared Drive ID
        self.service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Drive service with service account (for shared drives only)"""
        # Service account is only used for shared drives
        # For regular uploads, we'll use OAuth credentials
        if self.shared_drive_id:
            try:
                if not self.credentials_path:
                    logger.warning("GOOGLE_APPLICATION_CREDENTIALS not set. Shared drive upload will not work.")
                    return
                
                # Resolve relative paths
                if not os.path.isabs(self.credentials_path):
                    # Make path relative to backend directory
                    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    self.credentials_path = os.path.join(backend_dir, self.credentials_path)
                
                if not os.path.exists(self.credentials_path):
                    logger.warning(f"Service account key file not found: {self.credentials_path}.")
                    return
                
                from google.oauth2 import service_account
                credentials = service_account.Credentials.from_service_account_file(
                    self.credentials_path,
                    scopes=self.scopes
                )
                self.service = build('drive', 'v3', credentials=credentials)
                logger.info("Google Drive service initialized for shared drives")
            except Exception as e:
                logger.warning(f"Could not initialize Google Drive service: {e}")
                import traceback
                logger.debug(traceback.format_exc())
    
    def _get_drive_service(self, oauth_credentials: Optional[Credentials] = None):
        """Get Drive service using OAuth credentials or service account"""
        if oauth_credentials:
            # Use OAuth credentials (user's account)
            return build('drive', 'v3', credentials=oauth_credentials)
        elif self.service and self.shared_drive_id:
            # Use service account for shared drive
            return self.service
        else:
            raise ValueError(
                "No valid credentials available. "
                "Either provide OAuth credentials or configure GOOGLE_SHARED_DRIVE_ID with service account."
            )
    
    async def upload_document(
        self, 
        doc: Document, 
        filename: str,
        oauth_credentials: Optional[Credentials] = None
    ) -> Tuple[str, str]:
        """
        Upload a Document object to Google Drive and return file ID and shareable link
        
        Args:
            doc: Document object to upload
            filename: Name for the file
            oauth_credentials: Optional OAuth credentials from authenticated user.
                              If not provided, will use service account with shared drive.
        
        Returns:
            Tuple of (file_id, shareable_link)
        """
        try:
            # Save document to temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp_file:
                doc.save(tmp_file.name)
                tmp_file_path = tmp_file.name
            
            try:
                # Get appropriate Drive service
                drive_service = self._get_drive_service(oauth_credentials)
                
                # Upload to Google Drive
                file_metadata = {
                    'name': filename,
                    'mimeType': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                }
                
                # If using shared drive, add it to parents
                if self.shared_drive_id and not oauth_credentials:
                    file_metadata['parents'] = [self.shared_drive_id]
                
                media = MediaFileUpload(
                    tmp_file_path,
                    mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    resumable=True
                )
                
                file = drive_service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id, webViewLink, webContentLink',
                    supportsAllDrives=True  # Required for shared drives
                ).execute()
                
                file_id = file.get('id')
                
                # Make file publicly viewable (or you can use specific user permissions)
                permission = {
                    'type': 'anyone',
                    'role': 'reader'
                }
                drive_service.permissions().create(
                    fileId=file_id,
                    body=permission,
                    supportsAllDrives=True  # Required for shared drives
                ).execute()
                
                # Get shareable link
                shareable_link = f"https://drive.google.com/file/d/{file_id}/view"
                
                logger.info(f"File uploaded to Drive: {shareable_link}")
                return file_id, shareable_link
                
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
                    
        except Exception as e:
            logger.error(f"Error uploading to Drive: {str(e)}")
            raise
    
    def get_download_link(self, file_id: str) -> str:
        """Get direct download link for a file"""
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    
    async def list_recent_files(
        self,
        oauth_credentials: Optional[Credentials] = None,
        days: int = 30
    ) -> List[Dict]:
        """
        List files from Google Drive created in the last N days
        
        Args:
            oauth_credentials: OAuth credentials from authenticated user
            days: Number of days to look back (default: 30)
        
        Returns:
            List of file dictionaries with id, name, createdTime, webViewLink, etc.
        """
        try:
            drive_service = self._get_drive_service(oauth_credentials)
            
            # Calculate date threshold
            threshold_date = datetime.utcnow() - timedelta(days=days)
            threshold_time = threshold_date.isoformat() + 'Z'
            
            # Query for files created in the last N days
            # Filter for RFP summary files (files with "RFP_Summary" in name)
            # Using drive.file scope, we can only access files created by this app
            query = f"name contains 'RFP_Summary' and createdTime >= '{threshold_time}' and trashed=false"
            
            # List files
            results = drive_service.files().list(
                q=query,
                pageSize=100,
                fields="files(id, name, createdTime, modifiedTime, webViewLink, mimeType, size)",
                orderBy="modifiedTime desc",
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            files = results.get('files', [])
            
            # Format files for response
            formatted_files = []
            for file in files:
                file_id = file.get('id')
                mime_type = file.get('mimeType', '')
                
                # Determine edit link based on file type
                # For .docx files, we can open in Google Docs viewer or convert
                # For Google Docs format, use direct edit link
                if 'document' in mime_type or 'wordprocessingml' in mime_type:
                    # Try to open in Google Docs (will convert if needed)
                    edit_link = f"https://docs.google.com/document/d/{file_id}/edit"
                else:
                    # For other types, use view link
                    edit_link = file.get('webViewLink', f"https://drive.google.com/file/d/{file_id}/view")
                
                formatted_files.append({
                    'id': file_id,
                    'name': file.get('name'),
                    'createdTime': file.get('createdTime'),
                    'modifiedTime': file.get('modifiedTime'),
                    'webViewLink': file.get('webViewLink'),
                    'mimeType': mime_type,
                    'size': file.get('size'),
                    'downloadLink': self.get_download_link(file_id),
                    'editLink': edit_link
                })
            
            logger.info(f"Found {len(formatted_files)} files from the last {days} days")
            return formatted_files
            
        except Exception as e:
            logger.error(f"Error listing files from Drive: {str(e)}")
            raise

