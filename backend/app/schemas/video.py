from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class VideoBase(BaseModel):
    athlete_id: int
    movement_type: Optional[str] = "general"

class VideoCreate(VideoBase):
    pass

class VideoResponse(VideoBase):
    id: int
    uploader_id: int
    filename: str
    original_filename: str
    format: str
    size_bytes: int
    duration_sec: Optional[float] = None
    fps: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    status: str
    error_message: Optional[str] = None
    processing_progress: Optional[int] = 0
    quality_score: Optional[float] = None
    quality_issues: Optional[str] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}

class VideoStatusResponse(BaseModel):
    id: int
    status: str
    processing_progress: int
    quality_score: Optional[float] = None
    quality_issues: Optional[str] = None
    error_message: Optional[str] = None
