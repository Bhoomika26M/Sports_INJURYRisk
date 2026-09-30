"""Analytics service — dashboard backing queries. Routers stay thin."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.athletes.models import Athlete
from app.modules.risk_scoring.models import RiskScore
from app.modules.users.models import User, UserRole
from app.modules.videos.models import Video, VideoProcessingStatus


async def scoped_athlete_ids(db: AsyncSession, user: User) -> list[str] | None:
    """Return athlete IDs visible to user, or None for unrestricted roles."""
    if user.role in (UserRole.admin, UserRole.physiotherapist, UserRole.sports_scientist):
        return None
    if user.role == UserRole.coach:
        rows = (await db.scalars(select(Athlete.id).where(Athlete.coach_id == user.id))).all()
        return list(rows)
    rows = (await db.scalars(select(Athlete.id).where(Athlete.user_id == user.id))).all()
    return list(rows)


async def team_overview(db: AsyncSession, user: User) -> dict:
    athlete_ids = await scoped_athlete_ids(db, user)

    athlete_q = select(func.count()).select_from(Athlete)
    video_q = select(func.count()).select_from(Video)
    completed_q = select(func.count()).select_from(Video).where(Video.processing_status == VideoProcessingStatus.completed)
    failed_q = select(func.count()).select_from(Video).where(Video.processing_status == VideoProcessingStatus.failed)
    processing_q = select(func.count()).select_from(Video).where(
        Video.processing_status == VideoProcessingStatus.processing
    )
    if athlete_ids is not None:
        athlete_q = athlete_q.where(Athlete.id.in_(athlete_ids)) if athlete_ids else athlete_q.where(False)
        video_q = video_q.where(Video.athlete_id.in_(athlete_ids)) if athlete_ids else video_q.where(False)
        completed_q = completed_q.where(Video.athlete_id.in_(athlete_ids)) if athlete_ids else completed_q.where(False)
        failed_q = failed_q.where(Video.athlete_id.in_(athlete_ids)) if athlete_ids else failed_q.where(False)
        processing_q = processing_q.where(Video.athlete_id.in_(athlete_ids)) if athlete_ids else processing_q.where(False)

    total_athletes = await db.scalar(athlete_q) or 0
    total_videos = await db.scalar(video_q) or 0
    videos_completed = await db.scalar(completed_q) or 0
    videos_failed = await db.scalar(failed_q) or 0
    videos_processing = await db.scalar(processing_q) or 0

    risk_q = select(RiskScore)
    if athlete_ids is not None:
        risk_q = risk_q.where(RiskScore.athlete_id.in_(athlete_ids)) if athlete_ids else risk_q.where(False)
    risks = list((await db.scalars(risk_q)).all())
    avg_risk = round(sum(float(r.overall_score) for r in risks) / len(risks), 1) if risks else None
    counts = {"low": 0, "moderate": 0, "high": 0, "critical": 0}
    for r in risks:
        if r.risk_category in counts:
            counts[r.risk_category] += 1

    return {
        "total_athletes": total_athletes,
        "total_videos": total_videos,
        "videos_completed": videos_completed,
        "videos_failed": videos_failed,
        "videos_processing": videos_processing,
        "avg_risk_score": avg_risk,
        "high_risk_count": counts["high"],
        "critical_risk_count": counts["critical"],
        "low_risk_count": counts["low"],
        "moderate_risk_count": counts["moderate"],
    }
