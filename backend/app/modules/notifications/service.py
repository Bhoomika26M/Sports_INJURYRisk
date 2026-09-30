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
