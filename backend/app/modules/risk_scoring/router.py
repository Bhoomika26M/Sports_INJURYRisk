"""Risk scoring router — baselines, risk assessment, recommendations. Thin: logic is in service.py."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import UuidPath, get_current_user, get_redis, require_role
from app.core.errors import api_error
from app.database import get_db
from app.modules.athletes.models import Athlete
from app.modules.recommendations.models import Recommendation
from app.modules.risk_scoring.baselines import recompute_baseline_debounced
from app.modules.risk_scoring.models import RiskScore
from app.modules.risk_scoring.schemas import BaselineRecomputeRequest
from app.modules.risk_scoring.service import (
    InsufficientBaseline,
    NoValidatedMetrics,
    get_risk_assessment,
)
from app.modules.users.models import User, UserRole
from app.modules.video.models import Video, VideoProcessingStatus

router = APIRouter(prefix="/api/v1", tags=["risk_scoring"])


@router.post("/baselines/recompute")
async def recompute_baselines_endpoint(
    request: BaselineRecomputeRequest,
    current_user: Annotated[User, Depends(require_role(UserRole.admin, UserRole.sports_scientist))],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis: Annotated[Redis, Depends(get_redis)],
):
    result = await recompute_baseline_debounced(db, redis, request.movement_type)
    return {"message": f"Recomputed baselines for {request.movement_type}", "details": result}


def _can_access_athlete(user: User, athlete: Athlete) -> bool:
    if user.role in (UserRole.admin, UserRole.physiotherapist, UserRole.sports_scientist):
        return True
    if user.role == UserRole.coach and athlete.coach_id == user.id:
        return True
    if user.role == UserRole.athlete and athlete.user_id == user.id:
        return True
    return False


async def _load_video_and_athlete(db: AsyncSession, video_id: str, user: User) -> tuple[Video, Athlete]:
    video = await db.scalar(select(Video).where(Video.id == video_id))
    if not video:
        raise api_error(404, "NOT_FOUND", "Video not found")
    athlete = await db.scalar(select(Athlete).where(Athlete.id == video.athlete_id))
    if not _can_access_athlete(user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")
    return video, athlete


def _data_quality(video: Video) -> dict:
    """What the pose pipeline could actually measure, so a score is never read as more certain than it is."""
    return {
        "detection_rate": float(video.detection_rate) if video.detection_rate is not None else None,
        "person_count_detected": video.person_count_detected,
        "caveat": video.coverage_caveat,
    }


def _insufficient_payload(e: InsufficientBaseline) -> dict:
    """HTTP 202 body. ``unit`` says what ``have``/``need`` count (distinct videos or athletes) — never an
    unlabelled "samples". ``coverage`` reports BOTH floors."""
    what = "other completed videos" if e.unit == "videos" else "distinct athletes among them"
    return {
        "status": "insufficient_baseline_data",
        "metric_name": "video-level movement features",
        "unit": e.unit,
        "movement_type": e.movement_type,
        "have": e.have,
        "need": e.need,
        "coverage": e.coverage,
        "excluded_incomplete": e.excluded_incomplete,
        "message": (
            f"{e.have}/{e.need} {what} of '{e.movement_type}' with the same measurable metrics are needed "
            "before this video can be compared to a population baseline (this video is never counted in "
            "its own baseline)."
        ),
    }


@router.get("/videos/{video_id}/risk-score")
async def get_risk_score(
    video_id: UuidPath,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    recompute: bool = False,
):
    video, athlete = await _load_video_and_athlete(db, video_id, current_user)
    if video.processing_status != VideoProcessingStatus.completed:
        raise api_error(409, "VIDEO_NOT_READY", f"Video is {video.processing_status.value}; it can be scored once processing completes")

    try:
        assessment = await get_risk_assessment(db, video, athlete, recompute=recompute)
        return {**assessment, "data_quality": _data_quality(video)}
    except InsufficientBaseline as e:
        return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content=_insufficient_payload(e))
    except NoValidatedMetrics as e:
        raise api_error(
            422, "NO_VALIDATED_METRICS",
            f"No validated joint-angle metrics could be measured from this '{e.camera_view}'-view "
            f"{e.movement_type} video. Validated angles need a side-on (sagittal) camera with the "
            "legs and trunk visible. " + " ".join(w["message"] for w in e.warnings[:2]),
        )


@router.get("/videos/{video_id}/recommendations")
async def get_recommendations(
    video_id: UuidPath,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _load_video_and_athlete(db, video_id, current_user)
    risk_score = await db.scalar(select(RiskScore).where(RiskScore.video_id == video_id))
    if not risk_score:
        raise api_error(404, "NOT_FOUND", "Video not yet scored")

    recs = (await db.scalars(
        select(Recommendation).where(Recommendation.risk_score_id == risk_score.id).order_by(Recommendation.priority)
    )).all()
    return [{"category": r.category, "title": r.title, "description": r.description, "priority": r.priority} for r in recs]
