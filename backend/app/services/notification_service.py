"""In-app notifications. External delivery (email / push) is a logged stub:
plug SES, SendGrid or FCM into `_deliver_external` when you are ready."""

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.athlete import Athlete, AthleteAccess
from app.models.notification import Notification
from app.models.user import User
from app.models.video import Analysis, Video

logger = logging.getLogger(__name__)


def _deliver_external(user: User, title: str, message: str) -> None:
    logger.info("notify %s <%s>: %s", user.full_name, user.email, title)


def recipients_for_athlete(db: Session, athlete: Athlete) -> list[User]:
    users: dict[int, User] = {}
    if athlete.user_id:
        owner = db.get(User, athlete.user_id)
        if owner:
            users[owner.id] = owner
    for grant in db.scalars(select(AthleteAccess).where(AthleteAccess.athlete_id == athlete.id)):
        user = db.get(User, grant.user_id)
        if user and user.is_active:
            users[user.id] = user
    return list(users.values())


def notify(db: Session, users: list[User], athlete_id: int | None, type_: str, title: str, message: str) -> None:
    seen: set[int] = set()
    for user in users:
        if user.id in seen:
            continue
        seen.add(user.id)
        db.add(Notification(user_id=user.id, athlete_id=athlete_id, type=type_, title=title, message=message))
        _deliver_external(user, title, message)
    db.commit()


def notify_analysis_complete(db: Session, analysis: Analysis, athlete: Athlete, video: Video) -> None:
    everyone = recipients_for_athlete(db, athlete)
    owner = [u for u in everyone if u.id == athlete.user_id]
    uploader = db.get(User, video.uploaded_by) if video.uploaded_by else None
    name, category = athlete.full_name, analysis.risk_category

    notify(
        db, owner + ([uploader] if uploader else []), athlete.id, "assessment_complete",
        "Movement assessment complete",
        f"Analysis of {video.activity} for {name} is ready. Risk score {analysis.risk_score} ({category}).",
    )

    if category in ("moderate", "high", "critical"):
        top = analysis.injury_risks[0] if analysis.injury_risks else None
        detail = f" Highest concern: {top['category']} ({top['score']})." if top else ""
        notify(
            db, everyone, athlete.id, "injury_risk",
            f"{category.capitalize()} injury risk: {name}",
            f"Overall risk score {analysis.risk_score}.{detail}",
        )
        plan = (analysis.recommendations or {}).get("recovery_plan") or []
        if plan:
            notify(db, owner, athlete.id, "recovery", "Recovery reminder", plan[0])

    high = [d["label"] for d in analysis.deviations if d["level"] == "high"]
    if high:
        notify(
            db, everyone, athlete.id, "high_risk_movement",
            f"High-risk movement pattern: {name}",
            "Flagged: " + ", ".join(high[:4]) + ".",
        )

    load = (analysis.scores or {}).get("load_stats")
    if load and load["acwr"] > 1.5:
        notify(
            db, everyone, athlete.id, "training_load",
            f"Training load warning: {name}",
            f"Acute:chronic workload ratio is {load['acwr']}; a ratio above 1.5 is linked to higher injury risk.",
        )
