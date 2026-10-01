"""Risk scoring router — baselines, anomaly, scoring, recommendations."""

from typing import Annotated

from app.core.errors import api_error
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UuidPath, get_current_user, require_role
from app.database import get_db
from app.modules.users.models import User, UserRole
from app.modules.video.models import Video, BiomechanicalMetric, VideoProcessingStatus
from app.modules.athletes.models import Athlete, InjuryHistory
from app.modules.risk_scoring.models import MovementBaseline, AnomalyScore, RiskScore
from app.modules.recommendations.models import Recommendation
from app.modules.risk_scoring.baselines import recompute_baseline_debounced, BaselineShortfall
from app.modules.risk_scoring.service import compute_video_anomaly, insufficient_baseline_payload
from app.modules.risk_scoring.scoring import compute_risk_score, upsert_risk_score
from app.modules.recommendations.rules import generate_recommendations
from app.modules.risk_scoring.schemas import BaselineRecomputeRequest
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


def _data_quality(video: Video) -> dict:
    """What the pose pipeline could actually measure, so a score is never read as more certain than it is."""
    return {
        "detection_rate": float(video.detection_rate) if video.detection_rate is not None else None,
        "person_count_detected": video.person_count_detected,
        "caveat": video.coverage_caveat,
    }


@router.get("/videos/{video_id}/risk-score")
async def get_risk_score(
    video_id: UuidPath,
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
            "methodology_note": existing_score.methodology_note,
            "data_quality": _data_quality(video),
        }

    # Fetch validated metrics for this video
    metrics_stmt = (
        select(BiomechanicalMetric)
        .where(BiomechanicalMetric.video_id == video_id, BiomechanicalMetric.confidence == 'validated')
    )
    metrics = (await db.scalars(metrics_stmt)).all()

    if not metrics:
        raise api_error(400, "BAD_REQUEST", "No validated metrics found for this video")

    anomaly = await compute_video_anomaly(db, video, list(metrics))
    if isinstance(anomaly, BaselineShortfall):
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content=insufficient_baseline_payload(anomaly).model_dump(),
        )
    anomaly_percentiles = anomaly.frame_scores

    # LSI from biomechanics
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

    # Prior injury
    injury_count = await db.scalar(select(func.count()).select_from(InjuryHistory).where(InjuryHistory.athlete_id == athlete.id))
    has_prior_injury = injury_count > 0

    # ACWR
    acwr = None
    try:
        from app.modules.athletes.service import compute_acwr
        acwr_result = await compute_acwr(db, athlete.id)
        acwr = acwr_result.get("acwr")
    except Exception:
        pass

    # Fatigue (RPE trend)
    rpe_trend = None
    try:
        from app.modules.athletes.service import compute_acwr
        # Reuse ACWR function to get recent RPE data
        pass
    except Exception:
        pass

    risk_result = compute_risk_score(
        anomaly_percentiles, lsi, has_prior_injury, acwr, rpe_trend,
        baseline_note=f"baseline: {anomaly.baseline_videos} other videos / {anomaly.baseline_athletes} athletes, this video excluded",
    )

    risk_score = await upsert_risk_score(
        db=db,
        video_id=video_id,
        athlete_id=athlete.id,
        overall_score=risk_result["overall_score"],
        risk_category=risk_result["risk_category"],
        score_breakdown=risk_result["score_breakdown"].model_dump()
    )

    recs = generate_recommendations(risk_result["score_breakdown"])

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

    # Create notification for high/critical risk
    if risk_result["risk_category"] in ("high", "critical"):
        from app.modules.notifications.service import create_notification
        from app.modules.users.models import User as UserModel
        staff = list(
            (await db.scalars(select(UserModel).where(UserModel.role.in_(["coach", "physiotherapist", "sports_scientist", "admin"])))).all()
        )
        for member in staff:
            await create_notification(
                db,
                user_id=member.id,
                type="high_risk",
                title=f"{risk_result['risk_category'].title()} injury risk flagged",
                body=f"Video {video_id} ({video.movement_type}) scored {risk_result['overall_score']} ({risk_result['risk_category']}). Review recommended.",
                related_athlete_id=athlete.id,
            )

    return {
        "overall_score": risk_score.overall_score,
        "risk_category": risk_score.risk_category,
        "score_breakdown": risk_score.score_breakdown,
        "methodology_note": risk_score.methodology_note,
        "data_quality": _data_quality(video),
    }


@router.get("/videos/{video_id}/recommendations")
async def get_recommendations(
    video_id: UuidPath,
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