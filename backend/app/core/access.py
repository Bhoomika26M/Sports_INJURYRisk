"""Central athlete-access and video-access helper — single source of truth for role scoping.

Wide roles (admin, physiotherapist, sports_scientist) see every athlete.
Coach sees only athletes linked via athlete.coach_id.
Athlete sees only the profile linked via athlete.user_id.
"""

from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import api_error
from app.modules.athletes.models import Athlete
from app.modules.users.models import User, UserRole
from app.modules.video.models import Video

WIDE_ROLES = (UserRole.admin, UserRole.physiotherapist, UserRole.sports_scientist)


def can_access_athlete(user: User, athlete: Any | None) -> bool:
    """Return True when `user` may open `athlete`'s data. Never raises on None."""
    if athlete is None:
        return False
    if user.role in WIDE_ROLES:
        return True
    if user.role == UserRole.coach and getattr(athlete, "coach_id", None) == user.id:
        return True
    if user.role == UserRole.athlete and getattr(athlete, "user_id", None) == user.id:
        return True
    return False


async def load_accessible_video(db: AsyncSession, video_id: str, user: User) -> tuple[Video, Athlete]:
    """Load a video by ID, validating that the caller has permission to access its athlete."""
    video = await db.scalar(select(Video).where(Video.id == video_id))
    if video is None:
        raise api_error(404, "NOT_FOUND", "Video not found")
    athlete = await db.scalar(select(Athlete).where(Athlete.id == video.athlete_id))
    if athlete is None or not can_access_athlete(user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")
    return video, athlete
