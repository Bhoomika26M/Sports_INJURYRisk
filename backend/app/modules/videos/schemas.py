from uuid import UUID
from pydantic import BaseModel, ConfigDict, field_validator
from datetime import datetime
from typing import Literal
import os
import re
from app.modules.videos.models import VideoProcessingStatus

class VideoUploadRequest(BaseModel):
    athlete_id: str
    movement_type: str
    camera_view: Literal["sagittal", "frontal", "other"]
    original_filename: str
    content_type: str

    @field_validator("original_filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        base = os.path.basename(v)
        if not re.match(r'^[\w\-. ]{1,200}\.(mp4|mov)$', base, re.IGNORECASE):
            raise ValueError("must be a simple .mp4 or .mov filename with no path separators")
        return base

    @field_validator("content_type")
    @classmethod
    def validate_content_type(cls, v: str) -> str:
        if v not in ("video/mp4", "video/quicktime"):
            raise ValueError("must be video/mp4 or video/quicktime")
        return v

class VideoUploadResponse(BaseModel):
    video_id: str
    upload_url: str
    storage_key: str
    expires_in: int

class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    athlete_id: str
    uploaded_by: str
    movement_type: str
    storage_key: str
    original_filename: str | None
    duration_seconds: float | None
    fps: float | None
    resolution_width: int | None
    resolution_height: int | None
    camera_view: str
    processing_status: VideoProcessingStatus
    person_count_detected: int | None
    detection_rate: float | None
    error_code: str | None
    error_message: str | None
    job_id: str | None
    progress_pct: int
    annotated_video_key: str | None
    thumbnail_key: str | None
    processing_started_at: datetime | None
    processing_completed_at: datetime | None
    created_at: datetime

class VideoListResponse(BaseModel):
    items: list[VideoResponse]
    total: int
    page: int
    page_size: int

class BiomechanicsSummary(BaseModel):
    metric_name: str
    peak_value: float | None
    min_value: float | None
    range_of_motion: float | None

class BiomechanicsFrame(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    frame_number: int
    metric_name: str
    metric_value: float
    plane: str
    confidence: str

class BiomechanicsResponse(BaseModel):
    video_id: str
    detection_rate: float | None
    limb_symmetry_index: float | None
    summary: list[BiomechanicsSummary]
    frames: list[BiomechanicsFrame]
