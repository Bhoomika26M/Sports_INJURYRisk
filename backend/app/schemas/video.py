from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class VideoResponse(BaseModel):
    id: int
    athlete_id: Optional[int] = None
    title: str
    activity_type: str
    original_filename: str
    file_path: str
    processed_video_path: Optional[str] = None
    file_size: int
    duration_seconds: float
    fps: float
    frame_count: int
    resolution: str
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
