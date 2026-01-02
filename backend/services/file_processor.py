import os
import logging
from typing import Optional, Tuple
import PyPDF2
from docx import Document
from google.cloud import speech, documentai, storage
import tempfile
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class FileProcessor:
    """Handles file processing for text extraction and audio transcription"""
    
    def __init__(self):
        # Initialize GCP clients if credentials are available
        self.speech_client = None
        self.documentai_client = None
        self.storage_client = None
        self.gcs_bucket_name = os.getenv('GCS_BUCKET_NAME', os.getenv('GCP_PROJECT_ID', '') + '-speech-temp')
        
        # Try to initialize clients using Application Default Credentials (ADC)
        # In Cloud Run, the service account attached to the service provides credentials automatically
        # For local development, GOOGLE_APPLICATION_CREDENTIALS can point to a service account key file
        try:
            # First, try to initialize with Application Default Credentials
            # This works automatically in Cloud Run, GCE, GKE, etc.
            self.speech_client = speech.SpeechClient()
            self.documentai_client = documentai.DocumentProcessorServiceClient()
            self.storage_client = storage.Client()
            logger.info("GCP clients initialized successfully using Application Default Credentials")
        except Exception as e:
            # If ADC fails, try using GOOGLE_APPLICATION_CREDENTIALS if set (for local dev)
            creds_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            if creds_path:
                # Resolve relative paths
                if not os.path.isabs(creds_path):
                    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                    creds_path = os.path.join(backend_dir, creds_path)
                
                if os.path.exists(creds_path):
                    try:
                        # Set the environment variable explicitly for the client libraries
                        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = creds_path
                        self.speech_client = speech.SpeechClient()
                        self.documentai_client = documentai.DocumentProcessorServiceClient()
                        self.storage_client = storage.Client()
                        logger.info(f"GCP clients initialized using service account key: {creds_path}")
                    except Exception as e2:
                        logger.warning(f"GCP clients not initialized with service account key: {e2}")
                        self.speech_client = None
                        self.documentai_client = None
                        self.storage_client = None
                else:
                    logger.warning(f"Service account key file not found: {creds_path}. Speech-to-Text will not work.")
                    self.speech_client = None
                    self.documentai_client = None
                    self.storage_client = None
            else:
                # No credentials available at all
                logger.warning(f"GCP clients not initialized: {e}. No credentials available. Speech-to-Text will not work.")
                self.speech_client = None
                self.documentai_client = None
                self.storage_client = None
            # Note: In Cloud Run, ADC should work automatically, so this warning is expected
            # only if there's a real issue (like missing permissions or API not enabled)
    
    async def extract_text_from_document(self, file_path: str, file_extension: str) -> str:
        """Extract text from PDF, DOCX, or TXT files"""
        try:
            if file_extension == '.pdf':
                return await self._extract_from_pdf(file_path)
            elif file_extension == '.docx':
                return await self._extract_from_docx(file_path)
            elif file_extension == '.txt':
                return await self._extract_from_txt(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_extension}")
        except Exception as e:
            logger.error(f"Error extracting text: {str(e)}")
            raise
    
    async def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            # Try using Document AI first (if available)
            if self.documentai_client:
                try:
                    return await self._extract_pdf_with_documentai(file_path)
                except Exception as e:
                    logger.warning(f"Document AI failed, using PyPDF2: {e}")
            
            # Fallback to PyPDF2
            text = ""
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"PDF extraction error: {str(e)}")
            raise
    
    async def _extract_pdf_with_documentai(self, file_path: str) -> str:
        """Extract text using Google Document AI"""
        # This requires proper Document AI setup
        # For now, we'll use PyPDF2 as fallback
        raise NotImplementedError("Document AI setup required")
    
    async def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            doc = Document(file_path)
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            return text.strip()
        except Exception as e:
            logger.error(f"DOCX extraction error: {str(e)}")
            raise
    
    async def _extract_from_txt(self, file_path: str) -> str:
        """Extract text from TXT file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read().strip()
        except Exception as e:
            logger.error(f"TXT extraction error: {str(e)}")
            raise
    
    async def transcribe_audio(self, file_path: str) -> str:
        """Transcribe audio file to text"""
        try:
            # Try using Google Speech-to-Text first
            if self.speech_client:
                try:
                    return await self._transcribe_with_speech_to_text(file_path)
                except Exception as e:
                    error_msg = str(e)
                    # Check for common SSL/connection errors
                    if "SSL" in error_msg or "decryption" in error_msg.lower() or "stream removed" in error_msg.lower():
                        logger.error(f"Speech-to-Text connection error (SSL/network issue): {error_msg}")
                        raise ValueError(
                            "Audio transcription failed due to connection issues. "
                            "Please check your network connection and Google Cloud credentials. "
                            "Ensure GOOGLE_APPLICATION_CREDENTIALS is set correctly."
                        )
                    else:
                        logger.warning(f"Speech-to-Text API failed: {error_msg}")
                        raise ValueError(f"Audio transcription failed: {error_msg}")
            
            # No speech client available
            # Check if we're in Cloud Run (where ADC should work automatically)
            is_cloud_run = os.getenv('K_SERVICE') is not None or os.getenv('PORT') is not None
            
            if is_cloud_run:
                error_msg = (
                    "Audio transcription requires Google Speech-to-Text API setup. "
                    "In Cloud Run, ensure:\n"
                    "1. Speech-to-Text API is enabled in your GCP project\n"
                    "2. The service account attached to Cloud Run has 'Cloud Speech Client' role\n"
                    "3. The service account has proper IAM permissions"
                )
            else:
                error_msg = (
                    "Audio transcription requires Google Speech-to-Text API setup. "
                    "Please set GOOGLE_APPLICATION_CREDENTIALS and ensure Speech-to-Text API is enabled."
                )
            raise ValueError(error_msg)
        except ValueError:
            # Re-raise ValueError as-is (already has user-friendly message)
            raise
        except Exception as e:
            logger.error(f"Audio transcription error: {str(e)}")
            raise ValueError(f"Audio transcription error: {str(e)}")
    
    async def _transcribe_with_speech_to_text(self, file_path: str) -> str:
        """Transcribe audio using Google Speech-to-Text API"""
        try:
            # Determine audio encoding
            file_extension = os.path.splitext(file_path)[1].lower()
            encoding_map = {
                '.wav': speech.RecognitionConfig.AudioEncoding.LINEAR16,
                '.mp3': speech.RecognitionConfig.AudioEncoding.MP3,
                '.m4a': speech.RecognitionConfig.AudioEncoding.MP3,
            }
            
            encoding = encoding_map.get(file_extension, speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED)
            
            # Check file size (Speech-to-Text has limits)
            file_size = os.path.getsize(file_path)
            max_size = 10 * 1024 * 1024  # 10MB limit for content-based API
            
            if file_size > max_size:
                raise ValueError(
                    f"Audio file is too large ({file_size / 1024 / 1024:.1f}MB). "
                    "Maximum size is 10MB. Please use a shorter audio file or split it into smaller chunks."
                )
            
            with open(file_path, 'rb') as audio_file:
                content = audio_file.read()
            
            config = speech.RecognitionConfig(
                encoding=encoding,
                sample_rate_hertz=16000,
                language_code='en-US',
                enable_automatic_punctuation=True,
            )
            
            audio = speech.RecognitionAudio(content=content)
            
            # Try synchronous recognition first (for files < 1 minute)
            try:
                response = self.speech_client.recognize(config=config, audio=audio)
                
                if not response.results:
                    raise ValueError("No speech detected in audio file. Please check the audio file and try again.")
                
                transcript = ""
                for result in response.results:
                    if result.alternatives:
                        transcript += result.alternatives[0].transcript + " "
                
                if not transcript.strip():
                    raise ValueError("Could not extract text from audio. The audio may be too quiet or unclear.")
                
                return transcript.strip()
                
            except Exception as sync_error:
                error_msg = str(sync_error)
                
                # Check if error is due to audio being too long (> 1 minute)
                # Error messages can be:
                # - "400 Sync input too long. For audio longer than 1 min use LongRunningRecognize with a 'uri' parameter."
                # - "400 Inline audio exceeds duration limit. Please use a GCS URI."
                if ("Sync input too long" in error_msg or 
                    "Inline audio exceeds duration limit" in error_msg or
                    ("400" in error_msg and "too long" in error_msg.lower()) or
                    ("400" in error_msg and "exceeds duration limit" in error_msg.lower())):
                    logger.info("Audio file is longer than 1 minute, using long-running recognition with GCS...")
                    # Use long-running recognition for files > 1 minute (requires GCS URI)
                    return await self._transcribe_long_audio(file_path, config)
                else:
                    # Re-raise other errors
                    raise
                    
        except ValueError:
            # Re-raise ValueError as-is
            raise
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Speech-to-Text error: {error_msg}")
            # Check for specific error types
            if "SSL" in error_msg or "decryption" in error_msg.lower():
                raise ValueError("SSL/connection error with Speech-to-Text API. Check credentials and network.")
            elif "permission" in error_msg.lower() or "403" in error_msg:
                raise ValueError("Permission denied. Check service account has Speech-to-Text API access.")
            elif "quota" in error_msg.lower() or "429" in error_msg:
                raise ValueError("API quota exceeded. Please try again later.")
            else:
                raise ValueError(f"Speech-to-Text API error: {error_msg}")
    
    def _upload_audio_to_gcs(self, file_path: str) -> Tuple[str, str]:
        """Upload audio file to GCS and return the GCS URI and blob name"""
        if not self.storage_client:
            raise ValueError("Google Cloud Storage client not initialized. Cannot upload audio file.")
        
        try:
            # Get or create bucket
            bucket_name = self.gcs_bucket_name
            bucket = self.storage_client.bucket(bucket_name)
            
            # Check if bucket exists, create if it doesn't
            if not bucket.exists():
                logger.info(f"Creating GCS bucket: {bucket_name}")
                try:
                    bucket = self.storage_client.create_bucket(bucket_name)
                    logger.info(f"Created bucket: {bucket_name}")
                except Exception as e:
                    # If bucket creation fails, try to use a default bucket name
                    logger.warning(f"Failed to create bucket {bucket_name}: {e}")
                    # Try using project ID directly
                    project_id = os.getenv('GCP_PROJECT_ID')
                    if project_id:
                        bucket_name = f"{project_id}-speech-temp"
                        bucket = self.storage_client.bucket(bucket_name)
                        if not bucket.exists():
                            bucket = self.storage_client.create_bucket(bucket_name)
                            self.gcs_bucket_name = bucket_name
                            logger.info(f"Using bucket: {bucket_name}")
                    else:
                        raise ValueError(f"Cannot create or access GCS bucket. Please set GCS_BUCKET_NAME or GCP_PROJECT_ID environment variable.")
            
            # Generate unique blob name
            file_extension = os.path.splitext(file_path)[1]
            blob_name = f"speech-temp/{uuid.uuid4()}{file_extension}"
            
            # Upload file
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(file_path)
            
            gcs_uri = f"gs://{bucket_name}/{blob_name}"
            logger.info(f"Uploaded audio file to GCS: {gcs_uri}")
            
            return gcs_uri, blob_name
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to upload audio to GCS: {error_msg}")
            raise ValueError(f"Failed to upload audio file to Google Cloud Storage: {error_msg}")
    
    def _delete_gcs_file(self, blob_name: str):
        """Delete temporary file from GCS"""
        if not self.storage_client:
            return
        
        try:
            bucket = self.storage_client.bucket(self.gcs_bucket_name)
            blob = bucket.blob(blob_name)
            if blob.exists():
                blob.delete()
                logger.info(f"Deleted temporary GCS file: {blob_name}")
        except Exception as e:
            logger.warning(f"Failed to delete temporary GCS file {blob_name}: {e}")
    
    async def _transcribe_long_audio(self, file_path: str, config: speech.RecognitionConfig) -> str:
        """Transcribe long audio files (> 1 minute) using long-running recognition with GCS URI"""
        gcs_uri = None
        blob_name = None
        
        try:
            # Upload audio file to GCS
            logger.info("Uploading audio file to Google Cloud Storage...")
            gcs_uri, blob_name = self._upload_audio_to_gcs(file_path)
            
            # Create audio object with GCS URI
            audio = speech.RecognitionAudio(uri=gcs_uri)
            
            # Start long-running recognition operation
            logger.info("Starting long-running recognition with GCS URI...")
            operation = self.speech_client.long_running_recognize(config=config, audio=audio)
            
            logger.info("Long-running recognition started. Waiting for operation to complete...")
            
            # Wait for the operation to complete (this can take a while for long audio)
            # The operation.result() call will block until completion
            # Using a 10 minute timeout (600 seconds) - adjust if needed for very long audio files
            try:
                response = operation.result(timeout=600)  # 10 minute timeout
            except Exception as timeout_error:
                error_msg = str(timeout_error)
                if "timeout" in error_msg.lower() or "deadline" in error_msg.lower():
                    raise ValueError(
                        "Audio transcription timed out. The audio file may be too long. "
                        "Please try with a shorter audio file or split it into smaller chunks."
                    )
                raise
            
            if not response.results:
                raise ValueError("No speech detected in audio file. Please check the audio file and try again.")
            
            transcript = ""
            for result in response.results:
                if result.alternatives:
                    transcript += result.alternatives[0].transcript + " "
            
            if not transcript.strip():
                raise ValueError("Could not extract text from audio. The audio may be too quiet or unclear.")
            
            logger.info("Long-running recognition completed successfully.")
            return transcript.strip()
            
        except ValueError:
            # Re-raise ValueError as-is
            raise
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Long-running recognition error: {error_msg}")
            raise ValueError(f"Long audio transcription failed: {error_msg}")
        finally:
            # Clean up temporary GCS file
            if blob_name:
                self._delete_gcs_file(blob_name)

