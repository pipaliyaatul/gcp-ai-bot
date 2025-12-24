import os
import logging
from typing import Optional
import PyPDF2
from docx import Document
from google.cloud import speech, documentai
import tempfile

logger = logging.getLogger(__name__)

class FileProcessor:
    """Handles file processing for text extraction and audio transcription"""
    
    def __init__(self):
        # Initialize GCP clients if credentials are available
        self.speech_client = None
        self.documentai_client = None
        
        # Try to initialize clients using Application Default Credentials (ADC)
        # In Cloud Run, the service account attached to the service provides credentials automatically
        # For local development, GOOGLE_APPLICATION_CREDENTIALS can point to a service account key file
        try:
            # First, try to initialize with Application Default Credentials
            # This works automatically in Cloud Run, GCE, GKE, etc.
            self.speech_client = speech.SpeechClient()
            self.documentai_client = documentai.DocumentProcessorServiceClient()
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
                        logger.info(f"GCP clients initialized using service account key: {creds_path}")
                    except Exception as e2:
                        logger.warning(f"GCP clients not initialized with service account key: {e2}")
                        self.speech_client = None
                        self.documentai_client = None
                else:
                    logger.warning(f"Service account key file not found: {creds_path}. Speech-to-Text will not work.")
                    self.speech_client = None
                    self.documentai_client = None
            else:
                # No credentials available at all
                logger.warning(f"GCP clients not initialized: {e}. No credentials available. Speech-to-Text will not work.")
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
            max_size = 10 * 1024 * 1024  # 10MB limit for synchronous API
            
            if file_size > max_size:
                raise ValueError(
                    f"Audio file is too large ({file_size / 1024 / 1024:.1f}MB). "
                    "Maximum size is 10MB for synchronous transcription. "
                    "Please use a shorter audio file or split it into smaller chunks."
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

