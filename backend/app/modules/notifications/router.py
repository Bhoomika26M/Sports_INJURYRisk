"""Notifications router — list, mark read, counts."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.errors import api_error
from app.database import get_db
from app.modules.notifications.models import Notification
from app.modules.notifications.schemas import NotificationListResponse, NotificationResponse
from app.modules.users.models import User

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = False,
):
    query = select(Notification).where(Notification.user_id == current_user.id).order_by(desc(Notification.created_at))
    if unread_only:
        query = query.where(Notification.read_at.is_(None))
    total = await db.scalar(
        select(func.count()).select_from(Notification).where(Notification.user_id == current_user.id)
    )
    unread_count = await db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.user_id == current_user.id, Notification.read_at.is_(None))
    )
    items = list((await db.scalars(query.offset((page - 1) * page_size).limit(page_size))).all())
    return NotificationListResponse(
        items=items, total=total or 0, page=page, page_size=page_size, unread_count=unread_count or 0
    )


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    from datetime import datetime, timezone

    note = await db.scalar(
        select(Notification).where(Notification.id == notification_id, Notification.user_id == current_user.id)
    )
    if not note:
        raise api_error(404, "NOT_FOUND", "Notification not found")
    note.read_at = datetime.now(tz=timezone.utc)
    await db.commit()
    await db.refresh(note)
    return note
