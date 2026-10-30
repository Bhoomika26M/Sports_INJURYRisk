from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.injury_risk import InjuryRiskAssessment
from app.models.video import VideoRecord
from app.schemas.injury_risk import InjuryRiskResponse

router = APIRouter(prefix="/injury_risk", tags=["Injury Risk Assessment"])

@router.get("/{video_id}", response_model=InjuryRiskResponse)
def get_injury_risk_for_video(video_id: int, db: Session = Depends(get_db)):
    assessment = db.query(InjuryRiskAssessment).join(VideoRecord, VideoRecord.id == InjuryRiskAssessment.video_id).filter(
        InjuryRiskAssessment.video_id == video_id,
        VideoRecord.status == "analyzed",
        VideoRecord.processed_video_path.isnot(None),
    ).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="Injury risk assessment not found for this video")
    return assessment

@router.get("/athlete/{athlete_id}/latest", response_model=InjuryRiskResponse)
def get_latest_athlete_risk(athlete_id: int, db: Session = Depends(get_db)):
    assessment = db.query(InjuryRiskAssessment).join(VideoRecord, VideoRecord.id == InjuryRiskAssessment.video_id).filter(
        InjuryRiskAssessment.athlete_id == athlete_id,
        VideoRecord.status == "analyzed",
        VideoRecord.processed_video_path.isnot(None),
    ).order_by(InjuryRiskAssessment.id.desc()).first()
    if not assessment:
        raise HTTPException(status_code=404, detail="No injury assessment recorded for this athlete")
    return assessment

@router.get("/athlete/{athlete_id}/trends")
def get_athlete_risk_trends(athlete_id: int, db: Session = Depends(get_db)):
    assessments = db.query(InjuryRiskAssessment).join(VideoRecord, VideoRecord.id == InjuryRiskAssessment.video_id).filter(
        InjuryRiskAssessment.athlete_id == athlete_id,
        VideoRecord.status == "analyzed",
        VideoRecord.processed_video_path.isnot(None),
    ).order_by(InjuryRiskAssessment.id.asc()).all()

    trends = []
    for idx, a in enumerate(assessments):
        trends.append({
            "session_index": idx + 1,
            "assessment_id": a.id,
            "video_id": a.video_id,
            "overall_injury_risk_score": a.overall_injury_risk_score,
            "risk_category": a.risk_category,
            "movement_quality_score": a.movement_quality_score,
            "biomechanical_deviation_score": a.biomechanical_deviation_score,
            "movement_asymmetry_score": a.movement_asymmetry_score,
            "created_at": a.created_at.strftime("%Y-%m-%d %H:%M") if a.created_at else f"Session {idx + 1}"
        })

    return {
        "athlete_id": athlete_id,
        "total_sessions": len(trends),
        "trends": trends
    }
