from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.api import deps
from app.models.user import User
from app.models.video import Video
from app.services import athlete_service
from app.schemas.risk import (
    RiskScoreInput, 
    RiskScoreResponse, 
    InjuryRiskPredictionResponse,
    RiskTrendResponse
)
from app.services.risk_scoring_service import risk_scoring_service

router = APIRouter()

def _check_athlete_access(db: Session, current_user: User, athlete_id: int):
    profile = athlete_service.get_profile_by_id(db, athlete_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Athlete profile not found")
        
    if current_user.role == "athlete":
        if profile.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to view another athlete's injury predictions")
    elif current_user.role != "administrator":
        is_assigned = athlete_service.check_staff_assigned_to_athlete(db, staff_id=current_user.id, athlete_id=profile.id)
        if not is_assigned:
            raise HTTPException(status_code=403, detail="Not authorized to access this athlete's screening data")
    return profile

@router.post("/score", response_model=RiskScoreResponse)
def calculate_risk_score(
    risk_input: RiskScoreInput,
) -> RiskScoreResponse:
    """
    Calculate a preliminary risk score based on provided athlete and assessment data.
    Preserves stateless evaluation contract.
    """
    return risk_scoring_service.calculate_risk_score(risk_input)

@router.get("/athlete/{athlete_id}", response_model=InjuryRiskPredictionResponse)
def get_athlete_injury_risk_predictions(
    athlete_id: int,
    video_id: Optional[int] = Query(None, description="Optional specific video ID to analyze"),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
) -> InjuryRiskPredictionResponse:
    """
    Module 6: Injury Risk Prediction Engine
    Computes evidence-based predictions across all 6 injury categories:
    - ACL Injury Risk
    - Hamstring Strain Risk
    - Ankle Sprain Risk
    - Shoulder Impingement / Labral Risk
    - Lower Back / Lumbar Spine Risk
    - Overuse & Chronic Workload Risk
    Includes time-coded high-risk movements and personalized athlete profiling.
    """
    _check_athlete_access(db, current_user, athlete_id)
    try:
        return risk_scoring_service.predict_injury_risks(db, athlete_id=athlete_id, video_id=video_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/video/{video_id}", response_model=InjuryRiskPredictionResponse)
def get_video_injury_risk_predictions(
    video_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
) -> InjuryRiskPredictionResponse:
    """
    Evaluates injury risk probabilities specifically for a single movement capture trial.
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video recording not found")
        
    _check_athlete_access(db, current_user, video.athlete_id)
    try:
        return risk_scoring_service.predict_injury_risks(db, athlete_id=video.athlete_id, video_id=video_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/trend/{athlete_id}", response_model=RiskTrendResponse)
def get_athlete_risk_trend_history(
    athlete_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
) -> RiskTrendResponse:
    """
    Module 6: Risk Trend Monitoring
    Tracks longitudinal injury risk progression across multiple screening trials over time.
    """
    _check_athlete_access(db, current_user, athlete_id)
    return risk_scoring_service.get_risk_trend_history(db, athlete_id=athlete_id)
