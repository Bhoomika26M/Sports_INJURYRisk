"""Pydantic schemas for Dual-Video Form Benchmark & Comparative Analysis."""

from typing import Any, Optional
from pydantic import BaseModel, Field


class CompareVideosRequest(BaseModel):
    video_a_id: str = Field(description="Trainer / Golden Benchmark Video ID")
    video_b_id: str = Field(description="Student / Trainee Video ID to be evaluated")
    run_gemini: bool = Field(default=True, description="Whether to invoke Gemini multimodal narrative coaching")


class VectorPostureData(BaseModel):
    landmarks: dict[str, list[float]] = Field(default_factory=dict)
    angles: dict[str, Any] = Field(default_factory=dict)
    faults: list[str] = Field(default_factory=list)
    ground_y: float = 360.0
    frame_number: Optional[int] = None
    timestamp_ms: Optional[int] = None
    movement_type: Optional[str] = None
    is_textbook_benchmark: Optional[bool] = False


class KinematicDeltaItem(BaseModel):
    metric: str
    label: str
    video_a_val: Any
    video_b_val: Any
    delta: Any
    verdict: str  # "better", "worse", "neutral"
    explanation: str


class GeminiCoachingDebrief(BaseModel):
    summary: str
    verbal_cues: list[str] = Field(default_factory=list)
    prescribed_exercises: list[dict[str, Any]] = Field(default_factory=list)


class CompareVideosResponse(BaseModel):
    status: str = "completed"
    form_match_score: float = Field(ge=0.0, le=100.0, description="0-100% kinematic agreement score")
    movement_type: str
    advisory: Optional[str] = None
    is_identical: bool = False
    suggest_swap: bool = False
    is_cross_activity: bool = False
    view_mismatch: bool = False
    video_a_info: dict[str, Any]
    video_b_info: dict[str, Any]
    deltas: list[KinematicDeltaItem] = Field(default_factory=list)
    vector_posture_a: VectorPostureData
    vector_posture_b: VectorPostureData
    gemini_coaching: Optional[GeminiCoachingDebrief] = None
