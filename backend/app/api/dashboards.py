"""Role-specific dashboard data. Each endpoint returns JSON ready for charts and tables."""

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.athlete import Athlete, InjuryRecord
from app.models.notification import Notification, ReportRecord
from app.models.user import Role, User
from app.models.video import Analysis, Video
from app.services.access import accessible_athletes_query, get_athlete_for

router = APIRouter(prefix="/dashboards", tags=["dashboards"])
CATEGORIES = ["low", "moderate", "high", "critical"]


def _athletes(db: Session, user: User) -> list[Athlete]:
    return db.scalars(accessible_athletes_query(user).order_by(Athlete.full_name)).all()


def _latest_by_athlete(db: Session, athlete_ids: list[int]) -> dict[int, Analysis]:
    if not athlete_ids:
        return {}
    rows = db.scalars(
        select(Analysis).where(Analysis.athlete_id.in_(athlete_ids)).order_by(Analysis.created_at.desc())
    ).all()
    latest: dict[int, Analysis] = {}
    for a in rows:
        latest.setdefault(a.athlete_id, a)
    return latest


def _team_rows(athletes: list[Athlete], latest: dict[int, Analysis]) -> list[dict]:
    rows = []
    for ath in athletes:
        a = latest.get(ath.id)
        rows.append(
            {
                "athlete_id": ath.id,
                "name": ath.full_name,
                "sport": ath.sport_type,
                "position": ath.position,
                "analysis_id": a.id if a else None,
                "risk_score": a.risk_score if a else None,
                "risk_category": a.risk_category if a else None,
                "movement_quality": a.movement_quality if a else None,
                "last_analysis": a.created_at.isoformat() if a else None,
            }
        )
    rows.sort(key=lambda r: (r["risk_score"] is None, -(r["risk_score"] or 0)))
    return rows


def _category_counts(latest: dict[int, Analysis]) -> dict[str, int]:
    counts = Counter(a.risk_category for a in latest.values())
    return {c: counts.get(c, 0) for c in CATEGORIES}


@router.get("/athlete")
def athlete_dashboard(
    athlete_id: int | None = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    if athlete_id is None:
        if user.role != Role.athlete.value:
            raise HTTPException(status_code=422, detail="athlete_id is required")
        athlete = db.scalar(select(Athlete).where(Athlete.user_id == user.id))
        if athlete is None:
            raise HTTPException(status_code=404, detail="Create your athlete profile first")
    else:
        athlete = get_athlete_for(db, user, athlete_id)

    analyses = db.scalars(
        select(Analysis).where(Analysis.athlete_id == athlete.id).order_by(Analysis.created_at.desc()).limit(30)
    ).all()
    latest = analyses[0] if analyses else None
    previous = analyses[1] if len(analyses) > 1 else None
    ordered = list(reversed(analyses))
    unread = db.scalar(
        select(func.count()).select_from(Notification).where(Notification.user_id == user.id, Notification.is_read.is_(False))
    )
    return {
        "athlete": {"id": athlete.id, "name": athlete.full_name, "sport": athlete.sport_type, "code": athlete.athlete_code},
        "latest": None if latest is None else {
            "analysis_id": latest.id,
            "risk_score": latest.risk_score,
            "risk_category": latest.risk_category,
            "movement_quality": latest.movement_quality,
            "scores": latest.scores,
            "top_risks": latest.injury_risks[:3],
            "created_at": latest.created_at.isoformat(),
        },
        "progress": None if not (latest and previous) else {
            "risk_change": round(latest.risk_score - previous.risk_score, 1),
            "quality_change": round(latest.movement_quality - previous.movement_quality, 1),
        },
        "risk_trend": [{"date": a.created_at.date().isoformat(), "risk_score": a.risk_score} for a in ordered],
        "performance_trend": [{"date": a.created_at.date().isoformat(), "movement_quality": a.movement_quality} for a in ordered],
        "recommendations": latest.recommendations if latest else None,
        "recent_reports": [
            {"analysis_id": a.id, "activity": a.activity, "risk_category": a.risk_category, "created_at": a.created_at.isoformat()}
            for a in analyses[:5]
        ],
        "unread_notifications": unread or 0,
    }


@router.get("/coach")
def coach_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.coach.value, Role.administrator.value)),
):
    athletes = _athletes(db, user)
    latest = _latest_by_athlete(db, [a.id for a in athletes])
    names = {a.id: a.full_name for a in athletes}
    quality = [a.movement_quality for a in latest.values()]
    recent = db.scalars(
        select(Analysis).where(Analysis.athlete_id.in_(names.keys() or [0])).order_by(Analysis.created_at.desc()).limit(10)
    ).all()
    return {
        "team_overview": {
            "athletes": len(athletes),
            "assessed": len(latest),
            "risk_distribution": _category_counts(latest),
            "average_movement_quality": round(sum(quality) / len(quality), 1) if quality else None,
        },
        "athletes": _team_rows(athletes, latest),
        "movement_quality_reports": [
            {"analysis_id": a.id, "athlete": names[a.athlete_id], "activity": a.activity,
             "movement_quality": a.movement_quality, "risk_category": a.risk_category, "created_at": a.created_at.isoformat()}
            for a in recent
        ],
        "training_recommendations": [
            {"athlete": names[aid], "risk_category": a.risk_category,
             "recommendation": (a.recommendations.get("training_modifications") or [""])[0]}
            for aid, a in latest.items() if a.risk_category != "low"
        ],
    }


@router.get("/physiotherapist")
def physio_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.physiotherapist.value, Role.administrator.value)),
):
    athletes = _athletes(db, user)
    ids = [a.id for a in athletes]
    names = {a.id: a.full_name for a in athletes}
    latest = _latest_by_athlete(db, ids)
    injuries = db.scalars(
        select(InjuryRecord).where(InjuryRecord.athlete_id.in_(ids or [0]), InjuryRecord.status.in_(["active", "recovering"]))
        .order_by(InjuryRecord.injury_date.desc())
    ).all()
    issue_counts: Counter = Counter()
    for a in latest.values():
        for d in a.deviations:
            if d["level"] != "normal":
                issue_counts[d["issue"]] += 1
    return {
        "injury_risk_monitoring": _team_rows(athletes, latest),
        "rehabilitation_tracking": [
            {"athlete": names[i.athlete_id], "athlete_id": i.athlete_id, "injury": i.injury_type, "body_part": i.body_part,
             "status": i.status, "injury_date": i.injury_date.isoformat(), "days_since_injury": (date.today() - i.injury_date).days}
            for i in injuries
        ],
        "movement_correction_analytics": [{"issue": k, "athletes_affected": v} for k, v in issue_counts.most_common()],
        "recovery_reports": [
            {"athlete": names[aid], "risk_category": a.risk_category,
             "referral_suggested": a.recommendations.get("clinical_referral_suggested", False),
             "recovery_plan": a.recommendations.get("recovery_plan", [])}
            for aid, a in latest.items() if a.risk_category in ("high", "critical", "moderate")
        ],
    }


@router.get("/scientist")
def scientist_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(Role.sports_scientist.value, Role.administrator.value)),
):
    athletes = _athletes(db, user)
    ids = [a.id for a in athletes]
    analyses = db.scalars(select(Analysis).where(Analysis.athlete_id.in_(ids or [0]))).all()

    def mean(values: list[float]) -> float | None:
        values = [v for v in values if v is not None]
        return round(sum(values) / len(values), 2) if values else None

    metric_keys = ["knee_valgus_peak_deg", "trunk_lean_max_deg", "hip_stability_pelvic_drop_deg", "joint_alignment_score"]
    by_activity: dict[str, list[Analysis]] = defaultdict(list)
    for a in analyses:
        by_activity[a.activity].append(a)

    def aware(dt: datetime) -> datetime:
        # SQLite returns naive datetimes, PostgreSQL returns aware ones
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    weekly: dict[str, list[float]] = defaultdict(list)
    cutoff = datetime.now(timezone.utc) - timedelta(weeks=12)
    for a in analyses:
        if aware(a.created_at) >= cutoff:
            year, week, _ = a.created_at.isocalendar()
            weekly[f"{year}-W{week:02d}"].append(a.risk_score)

    category_scores: dict[str, list[float]] = defaultdict(list)
    drivers: Counter = Counter()
    for a in analyses:
        for r in a.injury_risks:
            category_scores[r["category"]].append(r["score"])
            for d in r["drivers"]:
                drivers[d["driver"]] += 1

    return {
        "dataset": {"athletes": len(athletes), "analyses": len(analyses)},
        "biomechanical_analytics": {
            activity: {k: mean([a.biomechanics.get("metrics", {}).get(k) for a in items]) for k in metric_keys} | {"analyses": len(items)}
            for activity, items in by_activity.items()
        },
        "team_performance_trends": [
            {"week": week, "mean_risk_score": mean(vals), "analyses": len(vals)} for week, vals in sorted(weekly.items())
        ],
        "injury_prediction_insights": {
            "mean_score_by_category": {k: mean(v) for k, v in category_scores.items()},
            "most_common_drivers": [{"driver": k, "count": v} for k, v in drivers.most_common(8)],
            "risk_distribution": dict(Counter(a.risk_category for a in analyses)),
        },
    }


def _dir_size_mb(path: str) -> float:
    root = Path(path)
    if not root.exists():
        return 0.0
    return round(sum(f.stat().st_size for f in root.rglob("*") if f.is_file()) / (1024 * 1024), 2)


@router.get("/admin")
def admin_dashboard(db: Session = Depends(get_db), _: User = Depends(require_roles(Role.administrator.value))):
    def count(model) -> int:
        return db.scalar(select(func.count()).select_from(model)) or 0

    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_ok = False

    failed = db.scalars(select(Video).where(Video.status == "failed").order_by(Video.created_at.desc()).limit(10)).all()
    return {
        "users": {
            "total": count(User),
            "by_role": dict(db.execute(select(User.role, func.count()).group_by(User.role)).all()),
        },
        "platform": {
            "athletes": count(Athlete),
            "videos": count(Video),
            "videos_by_status": dict(db.execute(select(Video.status, func.count()).group_by(Video.status)).all()),
            "analyses": count(Analysis),
            "reports": count(ReportRecord),
        },
        "system": {
            "database_ok": db_ok,
            "uploads_mb": _dir_size_mb(settings.UPLOAD_DIR),
            "reports_mb": _dir_size_mb(settings.REPORT_DIR),
            "recent_failed_videos": [
                {"video_id": v.id, "athlete_id": v.athlete_id, "error": v.error, "created_at": v.created_at.isoformat()}
                for v in failed
            ],
        },
    }
