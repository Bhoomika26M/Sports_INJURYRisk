"""Central athlete-access helper — single source of truth for role scoping.

Wide roles (admin, physiotherapist, sports_scientist) see every athlete.
Coach sees only athletes linked via athlete.coach_id.
Athlete sees only the profile linked via athlete.user_id.

Routers stay thin: import this instead of copy-pasting the same 8 lines.
`athletes/router.py` keeps its local copy for now (other agent is working that
lane) — it must stay logically identical to this.
"""

from typing import Any

from app.modules.users.models import User, UserRole

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
