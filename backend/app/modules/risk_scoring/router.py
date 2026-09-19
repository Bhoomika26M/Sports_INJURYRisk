from typing import Annotated
from app.core.errors import api_error
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.deps import get_current_user, require_role
from app.database import get_db
from app.modules.users.models import User, UserRole
from app.modules.videos.models import Video, BiomechanicalMetric, VideoProcessingStatus
from app.modules.athletes.models import Athlete
from app.modules.risk_scoring.models import MovementBaseline, AnomalyScore, RiskScore
from app.modules.recommendations.models import Recommendation
from app.modules.risk_scoring.baselines import recompute_baseline_debounced, MIN_BASELINE_SAMPLES
from app.modules.risk_scoring.anomaly import compute_anomaly_scores, InsufficientBaselineError
from app.modules.risk_scoring.scoring import compute_risk_score, upsert_risk_score
from app.modules.recommendations.rules import generate_recommendations
from app.modules.risk_scoring.schemas import BaselineRecomputeRequest, ScoreBreakdown
from redis.asyncio import Redis
from app.core.deps import get_redis

router = APIRouter(prefix="/api/v1", tags=["risk_scoring"])

@router.post("/baselines/recompute")
async def recompute_baselines_endpoint(
    request: BaselineRecomputeRequest,
    current_user: Annotated[User, Depends(require_role(UserRole.admin, UserRole.sports_scientist))],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)]
):
    stmt = (
        select(BiomechanicalMetric.metric_name)
        .join(Video, Video.id == BiomechanicalMetric.video_id)
        .where(
            Video.movement_type == request.movement_type,
            BiomechanicalMetric.confidence == 'validated'
        )
        .distinct()
    )
    metric_names = (await db.scalars(stmt)).all()
    
    results = []
    from app.modules.risk_scoring.anomaly import invalidate_model_cache
    for metric_name in metric_names:
        res = await recompute_baseline_debounced(db, redis, request.movement_type, metric_name)
        results.append(res)
    invalidate_model_cache(request.movement_type)
    
    return {"message": f"Recomputed baselines for {request.movement_type}", "details": results}

def _can_access_athlete(user: User, athlete: Athlete) -> bool:
    if user.role in (UserRole.admin, UserRole.physiotherapist, UserRole.sports_scientist):
        return True
    if user.role == UserRole.coach and athlete.coach_id == user.id:
        return True
    if user.role == UserRole.athlete and athlete.user_id == user.id:
        return True
    return False

@router.get("/videos/{video_id}/risk-score")
async def get_risk_score(
    video_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    recompute: bool = False,
):
    video = await db.scalar(select(Video).where(Video.id == video_id))
    if not video:
        raise api_error(404, "NOT_FOUND", "Video not found")
        
    athlete = await db.scalar(select(Athlete).where(Athlete.id == video.athlete_id))
    if not _can_access_athlete(current_user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")

    existing_score = await db.scalar(select(RiskScore).where(RiskScore.video_id == video_id))
    if existing_score and not recompute:
        return {
            "overall_score": existing_score.overall_score,
            "risk_category": existing_score.risk_category,
            "score_breakdown": existing_score.score_breakdown,
            "methodology_note": existing_score.methodology_note
        }

    # Fetch validated metrics for this video
    metrics_stmt = (
        select(BiomechanicalMetric)
        .where(BiomechanicalMetric.video_id == video_id, BiomechanicalMetric.confidence == 'validated')
    )
    metrics = (await db.scalars(metrics_stmt)).all()

    if not metrics:
        raise api_error(400, "BAD_REQUEST", "No validated metrics found for this video")

    import numpy as np
    anomaly_percentiles = []
    
    video_metric_names = set(m.metric_name for m in metrics)
    for m_name in sorted(video_metric_names):
        hist_stmt = (
            select(BiomechanicalMetric.metric_value)
            .join(Video, Video.id == BiomechanicalMetric.video_id)
            .where(
                Video.movement_type == video.movement_type,
                BiomechanicalMetric.metric_name == m_name,
                BiomechanicalMetric.confidence == 'validated',
                Video.processing_status == VideoProcessingStatus.completed
            )
        )
        hist_values = (await db.scalars(hist_stmt)).all()
        if len(hist_values) < MIN_BASELINE_SAMPLES:
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED, 
                content={"status": "insufficient_baseline_data", "metric_name": m_name, "have": len(hist_values), "need": MIN_BASELINE_SAMPLES}
            )
        
        baseline_vectors = np.array(hist_values).reshape(-1, 1)
        
        sample_values = [m.metric_value for m in metrics if m.metric_name == m_name]
        sample_vectors = np.array(sample_values).reshape(-1, 1)
        
        try:
            scores = compute_anomaly_scores(sample_vectors, baseline_vectors, MIN_BASELINE_SAMPLES, cache_key=f"{video.movement_type}:{m_name}")
            anomaly_percentiles.extend(scores)
        except InsufficientBaselineError as e:
            return JSONResponse(
                status_code=status.HTTP_202_ACCEPTED,
                content={"status": "insufficient_baseline_data", "metric_name": e.metric_name, "have": e.have, "need": e.need}
            )

    stmt = (
        select(
            BiomechanicalMetric.metric_name,
            func.max(BiomechanicalMetric.metric_value).label("peak_value")
        )
        .where(BiomechanicalMetric.video_id == video_id, BiomechanicalMetric.confidence == 'validated')
        .group_by(BiomechanicalMetric.metric_name)
    )
    result = await db.execute(stmt)
    peaks = {row.metric_name: float(row.peak_value) for row in result if row.peak_value is not None}
    
    from app.modules.biomechanics.calculations import limb_symmetry_index
    lsi = None
    if "knee_flexion_angle_left" in peaks and "knee_flexion_angle_right" in peaks:
        lsi = limb_symmetry_index(peaks["knee_flexion_angle_left"], peaks["knee_flexion_angle_right"])

    from app.modules.athletes.models import InjuryHistory
    injury_count = await db.scalar(select(func.count()).select_from(InjuryHistory).where(InjuryHistory.athlete_id == athlete.id))
    has_prior_injury = injury_count > 0

    risk_result = compute_risk_score(anomaly_percentiles, lsi, has_prior_injury)

    risk_score = await upsert_risk_score(
        db=db,
        video_id=video_id,
        athlete_id=athlete.id, # server-derived, never from request input
        overall_score=risk_result["overall_score"],
        risk_category=risk_result["risk_category"],
        score_breakdown=risk_result["score_breakdown"].model_dump()
    )

    recs = generate_recommendations(risk_result["score_breakdown"])
    
    # If we recomputed, clear old recs for this score
    if recompute:
        from sqlalchemy import delete
        await db.execute(delete(Recommendation).where(Recommendation.risk_score_id == risk_score.id))
        
    db_recs = [
        Recommendation(
            risk_score_id=risk_score.id,
            category=r["category"],
            title=r["title"],
            description=r["description"],
            priority=r["priority"]
        ) for r in recs
    ]
    db.add_all(db_recs)
    await db.commit()

    return {
        "overall_score": risk_score.overall_score,
        "risk_category": risk_score.risk_category,
        "score_breakdown": risk_score.score_breakdown,
        "methodology_note": risk_score.methodology_note
    }

@router.get("/videos/{video_id}/recommendations")
async def get_recommendations(
    video_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    video = await db.scalar(select(Video).where(Video.id == video_id))
    if not video:
        raise api_error(404, "NOT_FOUND", "Video not found")
        
    athlete = await db.scalar(select(Athlete).where(Athlete.id == video.athlete_id))
    if not _can_access_athlete(current_user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")

    risk_score = await db.scalar(select(RiskScore).where(RiskScore.video_id == video_id))
    if not risk_score:
        raise api_error(404, "NOT_FOUND", "Video not yet scored")

    recs = (await db.scalars(select(Recommendation).where(Recommendation.risk_score_id == risk_score.id))).all()
    
    return [
        {
            "category": r.category,
            "title": r.title,
            "description": r.description,
            "priority": r.priority
        } for r in recs
    ]
