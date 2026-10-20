from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.video import Analysis
from app.schemas.analysis import AnalysisOut, AnalysisSummary
from app.services.access import accessible_athletes_query, get_athlete_for

router = APIRouter(prefix="/analyses", tags=["analyses"])


@router.get("", response_model=list[AnalysisSummary])
def list_analyses(
    athlete_id: int | None = None, limit: int = 50, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    limit = max(1, min(limit, 200))
    if athlete_id is not None:
        get_athlete_for(db, user, athlete_id)
        query = select(Analysis).where(Analysis.athlete_id == athlete_id)
    else:
        ids = select(accessible_athletes_query(user).subquery().c.id)
        query = select(Analysis).where(Analysis.athlete_id.in_(ids))
    return db.scalars(query.order_by(Analysis.created_at.desc()).limit(limit)).all()


@router.get("/{analysis_id}", response_model=AnalysisOut)
def get_analysis(analysis_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    analysis = db.get(Analysis, analysis_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Analysis not found")
    get_athlete_for(db, user, analysis.athlete_id)
    return analysis


@router.get("/athlete/{athlete_id}/trend")
def risk_trend(athlete_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Risk score and movement quality over time (oldest first) for trend charts."""
    get_athlete_for(db, user, athlete_id)
    rows = db.scalars(
        select(Analysis).where(Analysis.athlete_id == athlete_id).order_by(Analysis.created_at.desc()).limit(30)
    ).all()
    return [
        {
            "analysis_id": a.id,
            "date": a.created_at.isoformat(),
            "activity": a.activity,
            "risk_score": a.risk_score,
            "risk_category": a.risk_category,
            "movement_quality": a.movement_quality,
        }
        for a in reversed(rows)
    ]
