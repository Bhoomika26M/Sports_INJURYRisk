from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional
import os


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./test.db"
    SECRET_KEY: str = "test-secret-key-for-development"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Milestone 2: Video Processing Settings
    VIDEO_UPLOAD_DIR: str = "uploads"
    MAX_VIDEO_SIZE: int = 500 * 1024 * 1024  # 500 MB
    MAX_VIDEO_DURATION: int = 300  # 5 minutes in seconds
    TARGET_PROCESSING_WIDTH: int = 640
    POSE_FPS: int = 15  # FPS for pose estimation
    POSE_CONFIDENCE_THRESHOLD: float = 0.3
    
    model_config = ConfigDict(env_file=".env")


settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.VIDEO_UPLOAD_DIR, exist_ok=True)
