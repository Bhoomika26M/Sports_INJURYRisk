from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.api import deps
from app.schemas.anomaly import AnomalyDetectionResponse
from app.services.anomaly_service import anomaly_service

router = APIRouter()

@router.get("/{video_id}", response_model=AnomalyDetectionResponse)
def get_video_anomalies(
    video_id: int,
    db: Session = Depends(deps.get_db)
) -> AnomalyDetectionResponse:
    """
    Detect movement anomalies in a processed video using rule-based kinematics.
    """
    response = anomaly_service.detect_anomalies(db, video_id)
    if not response:
        raise HTTPException(status_code=404, detail="Video analysis not found or not completed")
    return response
