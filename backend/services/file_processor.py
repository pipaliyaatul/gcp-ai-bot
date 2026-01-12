import os
import logging
from typing import Optional, Tuple
import PyPDF2
from docx import Document
from google.cloud import speech, documentai, storage
from google.cloud import speech_v2
from google.api_core.client_options import ClientOptions
import tempfile
import uuid
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import asyncio
from config import Config

logger = logging.getLogger(__name__)

class FileProcessor:
    """Handles file processing for text extraction and audio transcription"""
    
    def __init__(self):
        # Initialize GCP clients if credentials are available
        self.speech_client = None
        self.speech_v2_client = None  # For Vertex AI Chirp
        self.documentai_client = None
        self.storage_client = None
        self.vertex_ai_initialized = False
        self.gcs_bucket_name = os.getenv('GCS_BUCKET_NAME', os.getenv('GCP_PROJECT_ID', '') + '-speech-temp')
        
        # Thread pool executor for running blocking operations asynchronously
        # This allows us to run synchronous GCS and API calls without blocking the event loop
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="file_processor")
        
        # Initialize Vertex AI Speech-to-Text v2 (Chirp) if project ID is available
        if Config.VERTEX_AI_PROJECT_ID:
            try:
                client_options = ClientOptions(
                    api_endpoint=f"{Config.VERTEX_AI_LOCATION}-speech.googleapis.com"
                )
                self.speech_v2_client = speech_v2.SpeechClient(client_options=client_options)
                self.vertex_ai_initialized = True
                # Only log once to avoid spam during hot-reload
                if not hasattr(FileProcessor, '_chirp_logged'):
                    logger.info(f"Vertex AI Speech-to-Text v2 (Chirp) initialized for project {Config.VERTEX_AI_PROJECT_ID} in {Config.VERTEX_AI_LOCATION}")
                    FileProcessor._chirp_logged = True
            except Exception as e:
                logger.warning(f"Vertex AI Speech-to-Text v2 initialization failed: {e}. Will fallback to Speech-to-Text API v1.")
                self.vertex_ai_initialized = False
        
        # Try to initialize clients using Application Default Credentials (ADC)
        # In Cloud Run, the service account attached to the service provides credentials automatically
        # For local development, GOOGLE_APPLICATION_CREDENTIALS can point to a service account key file
        try:
            # First, try to initialize with Application Default Credentials
            # This works automatically in Cloud Run, GCE, GKE, etc.
            self.speech_client = speech.SpeechClient()
            self.documentai_client = documentai.DocumentProcessorServiceClient()
            self.storage_client = storage.Client()
            # Only log once to avoid spam during hot-reload
            if not hasattr(FileProcessor, '_gcp_logged'):
                logger.info("GCP clients initialized successfully using Application Default Credentials")
                FileProcessor._gcp_logged = True
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
    
    async def transcribe_audio(self, file_path: str, progress_callback: Optional[callable] = None) -> str:
        """Transcribe audio file to text using Vertex AI Chirp (preferred) or Speech-to-Text API (fallback)"""
        try:
            # Try using Vertex AI Chirp first (supports up to 100MB files)
            if self.vertex_ai_initialized:
                try:
                    return await self._transcribe_with_vertex_ai_chirp(file_path, progress_callback)
                except Exception as e:
                    error_msg = str(e)
                    logger.warning(f"Vertex AI Chirp failed: {error_msg}. Falling back to Speech-to-Text API.")
                    # Fall through to Speech-to-Text API
            
            # Fallback to Google Speech-to-Text API
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
            
            # No transcription service available
            # Check if we're in Cloud Run (where ADC should work automatically)
            is_cloud_run = os.getenv('K_SERVICE') is not None or os.getenv('PORT') is not None
            
            if is_cloud_run:
                error_msg = (
                    "Audio transcription requires Vertex AI or Speech-to-Text API setup. "
                    "In Cloud Run, ensure:\n"
                    "1. Vertex AI API or Speech-to-Text API is enabled in your GCP project\n"
                    "2. The service account attached to Cloud Run has proper IAM permissions\n"
                    "3. VERTEX_AI_PROJECT_ID is set (for Vertex AI Chirp)"
                )
            else:
                error_msg = (
                    "Audio transcription requires Vertex AI or Speech-to-Text API setup. "
                    "Please set GOOGLE_APPLICATION_CREDENTIALS and ensure APIs are enabled."
                )
            raise ValueError(error_msg)
        except ValueError:
            # Re-raise ValueError as-is (already has user-friendly message)
            raise
        except Exception as e:
            logger.error(f"Audio transcription error: {str(e)}")
            raise ValueError(f"Audio transcription error: {str(e)}")
    
    async def _transcribe_with_vertex_ai_chirp(self, file_path: str, progress_callback: Optional[callable] = None) -> str:
        """Transcribe audio using Vertex AI Chirp (supports up to 100MB files)"""
        try:
            if not self.speech_v2_client or not Config.VERTEX_AI_PROJECT_ID:
                raise ValueError("Vertex AI Speech-to-Text v2 client not initialized")
            
            logger.info("Using Vertex AI Chirp for transcription...")
            
            file_size = os.path.getsize(file_path)
            logger.info(f"Transcribing audio file of size: {file_size / (1024 * 1024):.2f}MB")
            
            # Always use GCS for Vertex AI Chirp (more reliable for large files)
            # Upload to GCS first (run in thread pool to avoid blocking)
            logger.info("Uploading audio file to GCS for Vertex AI Chirp...")
            if progress_callback:
                progress_callback("upload", "Starting upload...")
            
            gcs_uri, blob_name = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._upload_audio_to_gcs,
                file_path
            )
            
            if progress_callback:
                progress_callback("upload", "Upload complete")
                progress_callback("transcribe", "Starting transcription...")
            
            # Use implicit recognizer (recognizer ID = "_") - no need to create a recognizer
            # Note: Implicit recognizer uses "global" location
            from google.cloud.speech_v2 import RecognitionConfig, RecognitionFeatures, RecognizeRequest
            from google.cloud.speech_v2.types import cloud_speech
            
            # Use "global" location for implicit recognizer
            recognizer = f"projects/{Config.VERTEX_AI_PROJECT_ID}/locations/global/recognizers/_"
            
            # Create recognition config
            config = RecognitionConfig(
                auto_decoding_config=cloud_speech.AutoDetectDecodingConfig(),
                language_codes=["en-US"],
                model="chirp",  # Use Chirp model (chirp, chirp-2, or chirp-3)
                features=RecognitionFeatures(
                    enable_automatic_punctuation=True,
                    enable_word_time_offsets=False,
                )
            )
            
            # Create recognition request with GCS URI
            request = RecognizeRequest(
                recognizer=recognizer,
                config=config,
                uri=gcs_uri,
            )
            
            # Perform transcription (run in thread pool to avoid blocking)
            logger.info("Starting Vertex AI Chirp transcription...")
            if progress_callback:
                progress_callback("transcribe", "Processing audio with Vertex AI Chirp...")
            
            # Run the blocking API call in a thread pool
            response = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.speech_v2_client.recognize(request=request)
            )
            
            if progress_callback:
                progress_callback("transcribe", "Transcription complete, processing results...")
            
            # Extract transcript from response
            transcript_parts = []
            if response.results:
                for result in response.results:
                    if result.alternatives:
                        transcript_parts.append(result.alternatives[0].transcript)
            
            if not transcript_parts:
                raise ValueError("No speech detected in audio file. Please check the audio file and try again.")
            
            transcript = " ".join(transcript_parts).strip()
            logger.info(f"Vertex AI Chirp transcription completed. Transcript length: {len(transcript)} characters")
            
            return transcript
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Vertex AI Chirp error: {error_msg}")
            # Clean up GCS file if there was an error
            if 'blob_name' in locals() and blob_name:
                self._delete_gcs_file(blob_name)
            raise ValueError(f"Vertex AI Chirp transcription failed: {error_msg}")
    
            
            # Extract transcript from response
            transcript_parts = []
            if response.results:
                for result in response.results:
                    if result.alternatives:
                        transcript_parts.append(result.alternatives[0].transcript)
            
            if not transcript_parts:
                raise ValueError("No speech detected in audio file. Please check the audio file and try again.")
            
            transcript = " ".join(transcript_parts).strip()
            logger.info(f"Vertex AI Chirp transcription completed. Transcript length: {len(transcript)} characters")
            
            # Clean up GCS file if used
            if blob_name:
                self._delete_gcs_file(blob_name)
            
            return transcript
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Vertex AI Chirp error: {error_msg}")
            # Clean up GCS file if there was an error
            if 'blob_name' in locals() and blob_name:
                self._delete_gcs_file(blob_name)
            raise ValueError(f"Vertex AI Chirp transcription failed: {error_msg}")
    
    async def _transcribe_with_speech_to_text(self, file_path: str) -> str:
        """Transcribe audio using Google Speech-to-Text API"""
        try:
            # Determine audio encoding
            file_extension = os.path.splitext(file_path)[1].lower()
            encoding_map = {
                '.wav': speech.RecognitionConfig.AudioEncoding.LINEAR16,
                '.mp3': speech.RecognitionConfig.AudioEncoding.MP3,
                '.m4a': speech.RecognitionConfig.AudioEncoding.MP3,
                '.webm': speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            }
            
            encoding = encoding_map.get(file_extension, speech.RecognitionConfig.AudioEncoding.ENCODING_UNSPECIFIED)
            
            # Check file size
            file_size = os.path.getsize(file_path)
            max_size = 100 * 1024 * 1024  # 100MB limit
            
            if file_size > max_size:
                raise ValueError(
                    f"Audio file is too large ({file_size / 1024 / 1024:.1f}MB). "
                    "Maximum size is 100MB. Please use a shorter audio file or split it into smaller chunks."
                )
            
            config = speech.RecognitionConfig(
                encoding=encoding,
                sample_rate_hertz=16000,
                language_code='en-US',
                enable_automatic_punctuation=True,
            )
            
            # For files > 10MB, Speech-to-Text v1 requires GCS URI (not inline content)
            # For files < 10MB, we can use inline content
            if file_size > 10 * 1024 * 1024:
                logger.info("File is larger than 10MB, using GCS URI for Speech-to-Text v1...")
                return await self._transcribe_long_audio(file_path, config)
            
            # For smaller files, try inline content (read in thread pool to avoid blocking)
            def read_audio_file():
                with open(file_path, 'rb') as audio_file:
                    return audio_file.read()
            
            content = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                read_audio_file
            )
            
            audio = speech.RecognitionAudio(content=content)
            
            # Try synchronous recognition (run in thread pool to avoid blocking)
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    self.executor,
                    lambda: self.speech_client.recognize(config=config, audio=audio)
                )
                
                if not response.results:
                    raise ValueError("No speech detected in audio file. Please check the audio file and try again.")
                
                if progress_callback:
                    progress_callback("transcribe", "Processing transcription results...")
                
                transcript = ""
                for result in response.results:
                    if result.alternatives:
                        transcript += result.alternatives[0].transcript + " "
                
                if not transcript.strip():
                    raise ValueError("Could not extract text from audio. The audio may be too quiet or unclear.")
                
                if progress_callback:
                    progress_callback("complete", transcript)
                
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
                    return await self._transcribe_long_audio(file_path, config, progress_callback)
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
        """Upload audio file to GCS using Transfer Manager for fast parallel uploads"""
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
            
            # Get file size for upload configuration
            file_size = os.path.getsize(file_path)
            upload_start_time = time.time()
            logger.info(f"Starting upload to GCS (size: {file_size / (1024 * 1024):.2f}MB)...")
            
            blob = bucket.blob(blob_name)
            
            # Use Transfer Manager for faster parallel uploads (especially for files > 5MB)
            # Transfer Manager automatically handles:
            # - Parallel chunked uploads
            # - Automatic retries
            # - Progress tracking
            # - Optimal chunk sizing
            if file_size > 5 * 1024 * 1024:  # Use Transfer Manager for files > 5MB
                try:
                    # Import transfer_manager - requires google-cloud-storage >= 2.12.0
                    from google.cloud.storage import transfer_manager
                    
                    # Check if the function exists (for version compatibility)
                    if not hasattr(transfer_manager, 'upload_chunks_concurrently'):
                        raise AttributeError(
                            "upload_chunks_concurrently not available. "
                            "Please upgrade google-cloud-storage to version 2.12.0 or higher: "
                            "pip install --upgrade google-cloud-storage>=2.12.0"
                        )
                    
                    # Configure transfer manager for optimal performance
                    # chunk_size: Size of each chunk in bytes
                    # - For files 5-20MB: 4MB chunks
                    # - For files 20-50MB: 8MB chunks  
                    # - For files >50MB: 16MB chunks
                    if file_size < 20 * 1024 * 1024:
                        chunk_size = 4 * 1024 * 1024  # 4MB chunks
                        max_workers = 4
                    elif file_size < 50 * 1024 * 1024:
                        chunk_size = 8 * 1024 * 1024  # 8MB chunks
                        max_workers = 6
                    else:
                        chunk_size = 16 * 1024 * 1024  # 16MB chunks
                        max_workers = 8
                    
                    logger.info(f"Using Transfer Manager with {max_workers} parallel workers and {chunk_size / (1024 * 1024):.2f}MB chunks")
                    
                    # Upload with parallel chunks using transfer manager
                    # This splits the file into chunks and uploads them concurrently
                    transfer_manager.upload_chunks_concurrently(
                        filename=file_path,
                        blob=blob,
                        chunk_size=chunk_size,
                        max_workers=max_workers,
                    )
                    
                    upload_end_time = time.time()
                    upload_duration = upload_end_time - upload_start_time
                    upload_speed_mbps = (file_size / (1024 * 1024)) / upload_duration if upload_duration > 0 else 0
                    
                    gcs_uri = f"gs://{bucket_name}/{blob_name}"
                    logger.info(
                        f"Successfully uploaded audio file to GCS using Transfer Manager: {gcs_uri} "
                        f"(took {upload_duration:.2f}s, speed: {upload_speed_mbps:.2f} MB/s)"
                    )
                    return gcs_uri, blob_name
                    
                except ImportError:
                    # Transfer Manager not available (older version of google-cloud-storage)
                    # Fall back to optimized standard upload
                    logger.warning("Transfer Manager not available (requires google-cloud-storage >= 2.10.0), using optimized standard upload")
                    return self._upload_with_standard_method(blob, file_path, bucket_name, blob_name, file_size)
                except Exception as transfer_error:
                    error_msg = str(transfer_error)
                    logger.warning(f"Transfer Manager upload failed: {error_msg}. Falling back to standard upload.")
                    return self._upload_with_standard_method(blob, file_path, bucket_name, blob_name, file_size)
            else:
                # For smaller files, use standard upload (faster for small files, less overhead)
                return self._upload_with_standard_method(blob, file_path, bucket_name, blob_name, file_size)
            
        except ValueError:
            # Re-raise ValueError as-is
            raise
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to upload audio to GCS: {error_msg}")
            raise ValueError(f"Failed to upload audio file to Google Cloud Storage: {error_msg}")
    
    def _upload_with_standard_method(self, blob, file_path: str, bucket_name: str, blob_name: str, file_size: int) -> Tuple[str, str]:
        """Standard upload method with optimizations for reliability"""
        upload_start_time = time.time()
        
        # Configure chunk size for resumable uploads
        if file_size > 10 * 1024 * 1024:
            blob.chunk_size = 5 * 1024 * 1024  # 5MB chunks for large files
            logger.info("Using chunked/resumable upload for large file")
        
        # Retry configuration for upload
        max_retries = 3
        retry_delay = 2  # Start with 2 seconds
        
        for attempt in range(max_retries):
            try:
                # Use upload_from_filename which is optimized and handles resumable uploads automatically
                blob.upload_from_filename(
                    file_path,
                    timeout=300,  # 5 minute timeout
                    if_generation_match=None,  # Allow overwrites
                )
                
                upload_end_time = time.time()
                upload_duration = upload_end_time - upload_start_time
                upload_speed_mbps = (file_size / (1024 * 1024)) / upload_duration if upload_duration > 0 else 0
                
                gcs_uri = f"gs://{bucket_name}/{blob_name}"
                logger.info(
                    f"Successfully uploaded audio file to GCS: {gcs_uri} "
                    f"(took {upload_duration:.2f}s, speed: {upload_speed_mbps:.2f} MB/s)"
                )
                return gcs_uri, blob_name
                
            except (ConnectionResetError, ConnectionError, OSError) as e:
                error_msg = str(e)
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    logger.warning(
                        f"Upload attempt {attempt + 1} failed with connection error: {error_msg}. "
                        f"Retrying in {wait_time} seconds..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to upload audio to GCS after {max_retries} attempts: {error_msg}")
                    raise ValueError(f"Failed to upload audio file to Google Cloud Storage after {max_retries} attempts: {error_msg}")
            except Exception as e:
                # For non-connection errors, don't retry
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
    
    async def _transcribe_long_audio(self, file_path: str, config: speech.RecognitionConfig, progress_callback: Optional[callable] = None) -> str:
        """Transcribe long audio files (> 1 minute) using long-running recognition with GCS URI"""
        gcs_uri = None
        blob_name = None
        
        try:
            # Upload audio file to GCS (run in thread pool to avoid blocking)
            logger.info("Uploading audio file to Google Cloud Storage...")
            if progress_callback:
                progress_callback("upload", "Uploading audio file to cloud storage...")
            
            gcs_uri, blob_name = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                self._upload_audio_to_gcs,
                file_path
            )
            
            if progress_callback:
                progress_callback("upload", "Upload complete")
            
            # Create audio object with GCS URI
            audio = speech.RecognitionAudio(uri=gcs_uri)
            
            # Start long-running recognition operation (run in thread pool)
            logger.info("Starting long-running recognition with GCS URI...")
            if progress_callback:
                progress_callback("transcribe", "Starting long-running recognition operation...")
            
            # Start operation in thread pool
            operation = await asyncio.get_event_loop().run_in_executor(
                self.executor,
                lambda: self.speech_client.long_running_recognize(config=config, audio=audio)
            )
            
            logger.info("Long-running recognition started. Waiting for operation to complete...")
            if progress_callback:
                progress_callback("transcribe", "Long-running recognition operation started. Processing audio... This may take several minutes for long audio files.")
            
            # Poll operation status and update progress
            # Wait for the operation to complete (run in thread pool to avoid blocking)
            # Using a 10 minute timeout (600 seconds) - adjust if needed for very long audio files
            try:
                # Poll operation status periodically to provide progress updates
                start_time = time.time()
                last_update_time = start_time
                poll_interval = 5  # Update progress every 5 seconds
                
                def check_operation_status():
                    """Check if operation is done, return (done, response)"""
                    if operation.done():
                        return True, operation.result()
                    return False, None
                
                while True:
                    # Check operation status
                    done, response = await asyncio.get_event_loop().run_in_executor(
                        self.executor,
                        check_operation_status
                    )
                    
                    if done:
                        break
                    
                    # Update progress every poll_interval seconds
                    elapsed = time.time() - last_update_time
                    if elapsed >= poll_interval:
                        elapsed_total = time.time() - start_time
                        if progress_callback:
                            # Estimate progress based on elapsed time (rough estimate)
                            # Most operations complete within 2-5 minutes for typical audio files
                            estimated_total = 180  # 3 minutes estimate
                            progress_pct = min(95, int((elapsed_total / estimated_total) * 90))
                            progress_callback("transcribe", f"Transcribing audio... ({int(elapsed_total)}s elapsed, ~{progress_pct}% estimated)")
                        last_update_time = time.time()
                    
                    # Sleep a bit before next check
                    await asyncio.sleep(2)
                
                # Operation completed
                if progress_callback:
                    elapsed_total = time.time() - start_time
                    progress_callback("transcribe", f"Long-running recognition completed successfully! (took {int(elapsed_total)}s)")
                
                if response is None:
                    response = await asyncio.get_event_loop().run_in_executor(
                        self.executor,
                        lambda: operation.result(timeout=10)  # Short timeout since we know it's done
                    )
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

