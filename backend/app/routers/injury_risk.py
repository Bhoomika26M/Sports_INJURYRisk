from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.injury_risk import InjuryRiskAssessment
from app.schemas.injury_risk import InjuryRiskResponse

router = APIRouter(prefix="/injury_risk", tags=["Injury Risk Assessment"])

@router.get("/{video_id}", response_model=InjuryRiskResponse)
def get_injury_risk_for_video(video_id: int, db: Session = Depends(get_db)):
    assessment = db.query(InjuryRiskAssessment).filter(InjuryRiskAssessment.video_id == video_id).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Injury risk assessment not found for this video")
    return assessment

@router.get("/athlete/{athlete_id}/latest", response_model=InjuryRiskResponse)
def get_latest_athlete_risk(athlete_id: int, db: Session = Depends(get_db)):
    assessment = db.query(InjuryRiskAssessment).filter(InjuryRiskAssessment.athlete_id == athlete_id).order_by(InjuryRiskAssessment.id.desc()).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="No injury assessment recorded for this athlete")
    return assessment
