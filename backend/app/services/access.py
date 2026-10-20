"""Athlete-level access control on top of role-based access.

Roles decide *what kind* of action is allowed; these helpers decide *whose data*:
- administrators: all athletes
- athletes: their own profile
- coaches / physiotherapists / sports scientists: athletes who granted them access
  (coaches and physiotherapists may also write; sports scientists are read-only)
"""

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.athlete import Athlete, AthleteAccess
from app.models.user import Role, User

WRITE_ROLES = {Role.coach.value, Role.physiotherapist.value}


def can_access_athlete(db: Session, user: User, athlete: Athlete, write: bool = False) -> bool:
    if user.role == Role.administrator.value:
        return True
    if athlete.user_id == user.id:
        return True
    grant = db.scalar(
        select(AthleteAccess).where(
            AthleteAccess.athlete_id == athlete.id, AthleteAccess.user_id == user.id
        )
    )
    if grant is None:
        return False
    return grant.access_role in WRITE_ROLES if write else True


def accessible_athletes_query(user: User):
    if user.role == Role.administrator.value:
        return select(Athlete)
    granted = select(AthleteAccess.athlete_id).where(AthleteAccess.user_id == user.id)
    return select(Athlete).where(or_(Athlete.user_id == user.id, Athlete.id.in_(granted)))


def get_athlete_for(db: Session, user: User, athlete_id: int, write: bool = False) -> Athlete:
    """Fetch an athlete or raise 404. Unauthorised access also returns 404 so
    the existence of other athletes' records is not revealed."""
    athlete = db.get(Athlete, athlete_id)
    if athlete is None or not can_access_athlete(db, user, athlete, write=write):
        raise HTTPException(status_code=404, detail="Athlete not found")
    return athlete
