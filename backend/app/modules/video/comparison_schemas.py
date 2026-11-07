"""Pydantic schemas for Dual-Video Form Benchmark & Comparative Analysis."""

from typing import Literal, Optional
from pydantic import BaseModel, Field


class CompareVideosRequest(BaseModel):
    video_a_id: str = Field(description="Reference video ID")
    video_b_id: str = Field(description="Comparison video ID")


class MetricDelta(BaseModel):
    metric: str
    label: str
    unit: Optional[Literal["deg", "deg_s", "m", "pct", "count", "qualitative", "s"]] = None
    video_a: Optional[float | str] = None
    video_b: Optional[float | str] = None
    delta: Optional[float] = None
    verdict: Literal["within_noise", "higher", "lower", "no_verdict", "not_comparable"]
    reason: Optional[str] = None


class VideoSummary(BaseModel):
    id: str
    filename: Optional[str] = None
    movement_type: str
    camera_view: str
    duration_seconds: Optional[float] = None
    quality_grade: Optional[str] = None
    coverage_caveat: Optional[str] = None


class PostureSnapshot(BaseModel):
    frame_number: Optional[int] = None
    timestamp_s: Optional[float] = None
    landmarks: dict[str, list[float]] = Field(default_factory=dict)
    angles: dict[str, float] = Field(default_factory=dict)
    valgus_flag: Optional[str] = None
    camera_view: Optional[str] = None
    visible_side: Optional[str] = None
    visibilities: dict[str, float] = Field(default_factory=dict)


class VectorPostureData(BaseModel):
    landmarks: dict[str, list[float]] = Field(default_factory=dict)
    angles: dict[str, float | str] = Field(default_factory=dict)
    faults: list[str] = Field(default_factory=list)
    ground_y: float = 360.0
    frame_number: Optional[int] = None
    timestamp_ms: Optional[int] = None
    movement_type: Optional[str] = None
    camera_view: Optional[str] = None
    visible_side: Optional[str] = None
    visibilities: dict[str, float] = Field(default_factory=dict)


class CompareVideosResponse(BaseModel):
    movement_type: str
    video_a_info: VideoSummary
    video_b_info: VideoSummary
    deltas: list[MetricDelta] = Field(default_factory=list)
    snapshot_a: Optional[PostureSnapshot] = None
    snapshot_b: Optional[PostureSnapshot] = None
    summary: str
    caveats: list[str] = Field(default_factory=list)
