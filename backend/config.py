import os
from typing import Optional

class Config:
    """Application configuration"""
    
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Google Cloud
    GOOGLE_APPLICATION_CREDENTIALS: Optional[str] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    GCP_PROJECT_ID: Optional[str] = os.getenv("GCP_PROJECT_ID")
    
    # Google OAuth
    GOOGLE_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_CLIENT_ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = os.getenv("GOOGLE_CLIENT_SECRET")
    GOOGLE_REDIRECT_URI: str = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/google/callback")
    
    # AI Service
    USE_AI_FOR_RFP: bool = os.getenv("USE_AI_FOR_RFP", "true").lower() == "true"
    
    # File upload
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "10485760"))  # 10MB default for documents
    MAX_AUDIO_FILE_SIZE: int = int(os.getenv("MAX_AUDIO_FILE_SIZE", "104857600"))  # 100MB default for audio files
    UPLOAD_FOLDER: str = os.getenv("UPLOAD_FOLDER", "/tmp")
    
    # Vertex AI Configuration
    VERTEX_AI_PROJECT_ID: Optional[str] = os.getenv("VERTEX_AI_PROJECT_ID") or os.getenv("GCP_PROJECT_ID")
    VERTEX_AI_LOCATION: str = os.getenv("VERTEX_AI_LOCATION", "us-south1")
    # Default to gemini-1.5-flash which is more widely available, or gemini-pro as fallback
    VERTEX_AI_MODEL_NAME: str = os.getenv("VERTEX_AI_MODEL_NAME", "gemini-2.5-flash")
    
    @staticmethod
    def get_fallback_models() -> list:
        """Get list of fallback models to try if primary model fails"""
        fallback_env = os.getenv("VERTEX_AI_FALLBACK_MODELS", "gemini-2.5-flash")
        if fallback_env:
            return [m.strip() for m in fallback_env.split(",")]
        return [
            "gemini-1.5-flash",
            "gemini-pro",
            "gemini-1.5-pro",
            "gemini-2.5-flash"
        ]

