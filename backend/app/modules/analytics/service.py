"""Analytics service — dashboard backing queries. Routers stay thin."""

from datetime import date, timedelta
import numpy as np
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.athletes.models import Athlete
from app.modules.risk_scoring.models import RiskScore
from app.modules.users.models import User, UserRole
from app.modules.video.models import Video, VideoProcessingStatus


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
    processing_q = select(func.count()).select_from(Video).where(Video.processing_status == VideoProcessingStatus.processing)

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


TREND_MIN_POINTS = 4
TREND_CHANGE_POINTS = 5.0  # heuristic: mean change (0-100 scale) that counts as a real move


def risk_trend(scores_newest_first: list[float]) -> dict | None:
    """Direction of the athlete's risk over time: mean of the latest 3 scores vs. the 3 before.

    Needs >= 4 scores. Reported as improving / stable / worsening with the size of the change;
    the +/-5 point band is a heuristic noise margin, not a clinical threshold.
    """
    if len(scores_newest_first) < TREND_MIN_POINTS:
        return None
    recent = scores_newest_first[:3]
    previous = scores_newest_first[3:6]
    change = sum(recent) / len(recent) - sum(previous) / len(previous)
    direction = "worsening" if change >= TREND_CHANGE_POINTS else "improving" if change <= -TREND_CHANGE_POINTS else "stable"
    return {"direction": direction, "change": round(change, 1), "basis_points": len(recent) + len(previous)}


async def athlete_trends(db: AsyncSession, athlete_id: str, user: User, limit: int = 50) -> dict:
    """Get risk score trend for a specific athlete."""
    rows = list(
        (await db.scalars(select(RiskScore).where(RiskScore.athlete_id == athlete_id).order_by(RiskScore.created_at.desc()).limit(limit))).all()
    )
    # risk_scores.video_id is a UUID object; videos are keyed by str — normalise or every lookup misses
    videos = {str(v.id): v for v in (await db.scalars(select(Video).where(Video.athlete_id == athlete_id))).all()}
    points = [
        {
            "video_id": str(r.video_id),
            "movement_type": videos[str(r.video_id)].movement_type if str(r.video_id) in videos else "unknown",
            "overall_score": float(r.overall_score),
            "risk_category": r.risk_category,
            "created_at": r.created_at.isoformat() if r.created_at else "",
        }
        for r in rows
    ]
    return {
        "athlete_id": athlete_id, "points": points, "total": len(points),
        "trend": risk_trend([p["overall_score"] for p in points]),
    }


async def movement_type_analytics(db: AsyncSession, user: User, movement_type: str | None = None) -> dict:
    """Baseline stats and anomaly distributions per movement type."""
    athlete_ids = await scoped_athlete_ids(db, user)

    base_q = select(Video).where(Video.processing_status == VideoProcessingStatus.completed)
    if athlete_ids is not None:
        base_q = base_q.where(Video.athlete_id.in_(athlete_ids)) if athlete_ids else base_q.where(False)
    if movement_type:
        base_q = base_q.where(Video.movement_type == movement_type)

    videos = list((await db.scalars(base_q)).all())
    video_ids = [v.id for v in videos]

    if not video_ids:
        return {"movement_type": movement_type, "videos_analyzed": 0, "baselines": {}, "anomaly_distribution": {}}

    from app.modules.risk_scoring.models import MovementBaseline, AnomalyScore

    baselines = list((await db.scalars(select(MovementBaseline).where(MovementBaseline.movement_type == movement_type))).all()) if movement_type else []
    anomalies = list((await db.scalars(select(AnomalyScore).join(Video, Video.id == AnomalyScore.video_id).where(Video.id.in_(video_ids)))).all())

    baseline_data = {}
    for b in baselines:
        baseline_data[b.metric_name] = {
            "mean": b.mean_value,   # None = insufficient baseline ("unknown"), never a fabricated 0
            "std": b.std_dev,
            "sufficient": b.mean_value is not None,
            "sample_size": b.sample_size,
            "sample_size_unit": "frames",
            "video_count": b.video_count,
            "athlete_count": b.athlete_count,
        }

    anomaly_scores = [float(a.anomaly_score) for a in anomalies]
    anomaly_dist = {
        "count": len(anomaly_scores),
        "mean": round(np.mean(anomaly_scores), 1) if anomaly_scores else None,
        "p50": round(np.percentile(anomaly_scores, 50), 1) if anomaly_scores else None,
        "p90": round(np.percentile(anomaly_scores, 90), 1) if anomaly_scores else None,
        "p99": round(np.percentile(anomaly_scores, 99), 1) if anomaly_scores else None,
    }

    return {"movement_type": movement_type, "videos_analyzed": len(videos), "baselines": baseline_data, "anomaly_distribution": anomaly_dist}


async def coach_dashboard_data(db: AsyncSession, user) -> dict:
    """Coach-specific dashboard: team risk overview, athlete table, trends."""
    from app.modules.users.models import UserRole

    overview = await team_overview(db, user)

    if user.role == UserRole.coach:
        athletes = list((await db.scalars(select(Athlete).where(Athlete.coach_id == user.id))).all())
    else:
        # physio / scientist / admin see all athletes
        athletes = list((await db.scalars(select(Athlete).order_by(Athlete.created_at.desc()).limit(100))).all())
    athlete_cards = []
    for a in athletes:
        latest_risk = await db.scalar(
            select(RiskScore).where(RiskScore.athlete_id == a.id).order_by(RiskScore.created_at.desc()).limit(1)
        )
        athlete_cards.append({
            "athlete_id": a.id,
            "name": a.full_name,
            "sport": a.sport_type,
            "latest_risk_score": float(latest_risk.overall_score) if latest_risk else None,
            "latest_risk_category": latest_risk.risk_category if latest_risk else None,
            "last_assessed": latest_risk.created_at.isoformat() if latest_risk else None,
        })

    return {"overview": overview, "athletes": athlete_cards}