"""Video Pydantic schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator

from app.modules.biomechanics.classification import AUTO


class VideoUploadRequest(BaseModel):
    athlete_id: str
    movement_type: str = Field(min_length=1, max_length=50)
    camera_view: str = Field(pattern="^(sagittal|frontal|other|auto)$")
    original_filename: str = Field(min_length=1, max_length=255)

    @model_validator(mode="after")
    def _auto_means_both(self):
        """"auto" asks the footage to decide, and it decides both labels together: one of them alone is a client bug."""
        if (self.movement_type == AUTO) != (self.camera_view == AUTO):
            raise ValueError('movement_type and camera_view must both be "auto" or neither')
        return self


class VideoUploadResponse(BaseModel):
    video_id: str
    upload_url: str
    storage_key: str
    expires_in: int


class VideoResponse(BaseModel):
    id: str
    athlete_id: str
    uploaded_by: str
    movement_type: str
    storage_key: str
    original_filename: Optional[str] = None
    duration_seconds: Optional[float] = None
    fps: Optional[float] = None
    resolution_width: Optional[int] = None
    resolution_height: Optional[int] = None
    camera_view: str
    processing_status: str
    person_count_detected: Optional[int] = None
    detection_rate: Optional[float] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    coverage_caveat: Optional[str] = None
    job_id: Optional[str] = None
    progress_pct: int
    annotated_video_key: Optional[str] = None
    thumbnail_key: Optional[str] = None
    analysis: Optional[dict] = None
    processing_started_at: Optional[datetime] = None
    processing_completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class VideoListResponse(BaseModel):
    items: list[VideoResponse]
    total: int
    page: int
    page_size: int


# Biomechanics
class BiomechanicsSummary(BaseModel):
    metric_name: str
    peak_value: Optional[float] = None
    min_value: Optional[float] = None
    range_of_motion: Optional[float] = None


class BiomechanicsFrame(BaseModel):
    frame_number: int
    metric_name: str
    metric_value: float
    plane: str
    confidence: str
    movement_phase: Optional[str] = None

    model_config = {"from_attributes": True}


class BiomechanicsResponse(BaseModel):
    video_id: str
    detection_rate: Optional[float] = None
    limb_symmetry_index: Optional[float] = None
    summary: list[BiomechanicsSummary]
    frames: list[BiomechanicsFrame]


class MovementTypeResponse(BaseModel):
    code: str
    display_name: str
    camera_views: list[str]
    phases: Optional[list[str]] = None


class MovementMetricResponse(BaseModel):
    metric_name: str
    plane: str
    confidence: str
    unit: str
    description: Optional[str] = None