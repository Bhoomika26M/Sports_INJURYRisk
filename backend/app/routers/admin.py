"""
Admin-only routes:
  POST /admin/users                         – create a user with any role
  POST /admin/assignments                   – assign athlete to coach/physio
  DELETE /admin/assignments/{assignment_id} – deactivate an assignment
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.deps import get_db, require_roles
from app.models.assignment import CoachAthleteAssignment
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.athletes import AssignmentCreate, AssignmentRead
from app.schemas.auth import AdminUserCreate, UserRead

router = APIRouter(prefix="/admin", tags=["Admin"])

_admin_only = require_roles(UserRole.ADMIN)


# ---------------------------------------------------------------------------
# POST /admin/users
# ---------------------------------------------------------------------------
@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="[Admin] Create a user with any role",
)
async def admin_create_user(
    payload: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_admin_only),
) -> UserRead:
    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        phone_number=payload.phone_number,
        is_active=True,
        is_verified=True,  # admin-created accounts are pre-verified
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return UserRead.model_validate(user)


# ---------------------------------------------------------------------------
# POST /admin/assignments
# ---------------------------------------------------------------------------
@router.post(
    "/assignments",
    response_model=AssignmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="[Admin] Assign an athlete to a coach or physiotherapist",
)
async def admin_assign_athlete(
    payload: AssignmentCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_admin_only),
) -> AssignmentRead:
    # Validate coach exists and has an appropriate role
    coach_result = await db.execute(select(User).where(User.id == payload.coach_id))
    coach: User | None = coach_result.scalar_one_or_none()
    if not coach:
        raise HTTPException(status_code=404, detail="Coach/physio user not found")
    if coach.role not in {UserRole.COACH, UserRole.PHYSIOTHERAPIST, UserRole.ADMIN}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Target user must have role coach, physiotherapist, or admin",
        )

    # Check for duplicate active assignment
    dup_result = await db.execute(
        select(CoachAthleteAssignment).where(
            CoachAthleteAssignment.coach_id == payload.coach_id,
            CoachAthleteAssignment.athlete_id == payload.athlete_id,
            CoachAthleteAssignment.assignment_role == payload.assignment_role,
            CoachAthleteAssignment.is_active.is_(True),
        )
    )
    if dup_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This assignment already exists and is active",
        )

    assignment = CoachAthleteAssignment(
        coach_id=payload.coach_id,
        athlete_id=payload.athlete_id,
        assignment_role=payload.assignment_role,
        is_active=True,
    )
    db.add(assignment)
    await db.flush()
    await db.refresh(assignment)
    return AssignmentRead.model_validate(assignment)


# ---------------------------------------------------------------------------
# DELETE /admin/assignments/{assignment_id}
# ---------------------------------------------------------------------------
@router.delete(
    "/assignments/{assignment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="[Admin] Deactivate a coach-athlete assignment",
)
async def admin_deactivate_assignment(
    assignment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_admin_only),
) -> None:
    result = await db.execute(
        select(CoachAthleteAssignment).where(CoachAthleteAssignment.id == assignment_id)
    )
    assignment: CoachAthleteAssignment | None = result.scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    assignment.is_active = False
    db.add(assignment)
