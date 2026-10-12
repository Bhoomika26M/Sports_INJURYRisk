from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
from app.models.video import ProcessingStatus


class VideoBase(BaseModel):
    activity_type: str = Field(..., min_length=1, max_length=100)


class VideoCreate(VideoBase):
    pass


class VideoResponse(BaseModel):
    id: int
    athlete_id: int
    uploaded_by: int
    original_filename: str
    activity_type: str
    file_size: Optional[int] = None
    duration: Optional[float] = None
    fps: Optional[float] = None
    width: Optional[int] = None
    height: Optional[int] = None
    processing_status: ProcessingStatus
    processing_error: Optional[str] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class VideoUpdate(BaseModel):
    activity_type: Optional[str] = Field(None, min_length=1, max_length=100)
