from pydantic import BaseModel, ConfigDict
from typing import List, Dict, Any, Optional
from datetime import datetime


class MetricsSummary(BaseModel):
    peak_knee_valgus_left: float
    peak_knee_valgus_right: float
    peak_valgus_overall: float
    avg_valgus_overall: float
    peak_knee_flexion_left: float
    peak_knee_flexion_right: float
    peak_flexion_overall: float
    mean_asymmetry_index: float
    peak_asymmetry_index: float
    mean_trunk_lean: float
    peak_trunk_lean: float


class QualityReport(BaseModel):
    overall_score: float
    grade: str
    valgus_stability_score: float
    symmetry_score: float
    rom_score: float
    posture_score: float
    metrics_summary: MetricsSummary
    anomalies: List[str]


class FrameSample(BaseModel):
    frame_index: int
    timestamp: float
    left_knee_angle: float
    right_knee_angle: float
    left_knee_flexion: float
    right_knee_flexion: float
    left_hip_angle: float
    right_hip_angle: float
    left_valgus_angle: float
    right_valgus_angle: float
    trunk_lean: float
    lateral_lean: float
    knee_symmetry_index: float
    valgus_symmetry_index: float


class VideoAnalysisResponse(BaseModel):
    video_name: str
    movement_type: str
    athlete_id: Optional[str] = None
    total_frames: int
    fps: float
    duration: float
    quality_report: QualityReport
    sampled_frames: List[FrameSample]


class AnalysisRecordOut(BaseModel):
    id: int
    video_name: str
    movement_type: str
    athlete_id: Optional[str]
    overall_score: float
    grade: str
    peak_valgus: float
    mean_asymmetry: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
