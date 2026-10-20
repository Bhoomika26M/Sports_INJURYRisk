"""Risk assessment API endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.db.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User
from app.models.video import Video
from app.schemas.risk import RiskAssessment
from app.services.video_service import VideoService
from app.risk.engine import InjuryRiskEngine
from app.pose.estimator import Keypoint

router = APIRouter()


@router.get("/risk/{video_id}", response_model=RiskAssessment)
def get_risk_assessment(
    video_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get explainable injury risk assessment for a video."""
    video = VideoService.get_video(video_id, current_user, db)

    # Need pose analysis with keypoints
    from app.models.pose_analysis import PoseAnalysis

    pose_analysis = db.query(PoseAnalysis).filter(PoseAnalysis.video_id == video_id).first()
    if not pose_analysis or not pose_analysis.keypoints_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pose analysis not found. Process the video first.",
        )

    engine = InjuryRiskEngine()

    # Reconstruct keypoints sequence
    keypoints_seq = []
    timestamps = []
    for frame in pose_analysis.keypoints_data:
        kps = []
        for kp in frame.get("keypoints", []):
            kps.append(
                Keypoint(
                    x=kp["x"],
                    y=kp["y"],
                    confidence=kp["confidence"],
                    name=kp["name"],
                )
            )
        keypoints_seq.append(kps)
        timestamps.append(frame.get("timestamp", 0.0))

    risk = engine.evaluate(
        keypoints_seq,
        timestamps,
        activity=video.activity_type,
        pose_quality=pose_analysis.pose_quality,
    )
    return risk
