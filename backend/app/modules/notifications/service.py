"""Notification service — thin helpers, routers stay thin per backend AGENTS.md."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import Notification

logger = logging.getLogger(__name__)


async def create_notification(
    db: AsyncSession,
    user_id: str,
    type: str,
    title: str,
    body: str,
    related_athlete_id: str | None = None,
) -> Notification:
    note = Notification(
        user_id=user_id,
        type=type,
        title=title,
        body=body,
        related_athlete_id=related_athlete_id,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


async def recipients_for_athlete(db: AsyncSession, athlete) -> list[str]:
    """Users who are entitled to see this athlete's risk alerts — exactly the people who can
    open the athlete's data (mirrors `_can_access_athlete`): the athlete's own coach, the athlete
    themself, and the organisation-wide clinical/admin roles. NOT every coach in the system —
    the previous implementation broadcast every athlete's alert to all coaches."""
    from sqlalchemy import select
    from app.modules.users.models import User, UserRole

    wide = (await db.scalars(
        select(User.id).where(
            User.role.in_([UserRole.physiotherapist, UserRole.sports_scientist, UserRole.admin]),
            User.is_active.is_(True),
        )
    )).all()
    ids = {str(i) for i in wide}
    if athlete.coach_id:
        ids.add(str(athlete.coach_id))
    if athlete.user_id:
        ids.add(str(athlete.user_id))
    return sorted(ids)
