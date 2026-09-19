"""
Athlete CRUD and sub-resource routes.

Access rules (enforced via _athlete_gate dependency):
  - athlete        → own record only
  - coach / physio → athletes in their coach_athlete_assignments
  - sports_scientist / admin → any athlete

Routes:
  GET    /athletes               – list with pagination + search
  POST   /athletes               – create own profile (athlete role)
  GET    /athletes/{id}          – retrieve one
  PUT    /athletes/{id}          – update
  DELETE /athletes/{id}          – soft-delete (admin/scientist only)

  GET    /athletes/{id}/injuries         – list injury history
  POST   /athletes/{id}/injuries         – add injury record

  GET    /athletes/{id}/training-profile – list training profiles
  POST   /athletes/{id}/training-profile – add training profile

  GET    /athletes/{id}/assessments      – list physical assessments
  POST   /athletes/{id}/assessments      – create assessment (physio/admin)
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db, require_roles
from app.models.assessment import PhysicalAssessment
from app.models.assignment import CoachAthleteAssignment
from app.models.athlete import Athlete
from app.models.enums import UserRole
from app.models.injury import InjuryHistory
from app.models.training import TrainingProfile
from app.models.user import User
from app.schemas.athletes import (
    AssessmentCreate,
    AssessmentRead,
    AthleteCreate,
    AthleteRead,
    AthleteUpdate,
    InjuryCreate,
    InjuryRead,
    PaginatedAthletes,
    TrainingProfileCreate,
    TrainingProfileRead,
)

router = APIRouter(prefix="/athletes", tags=["Athletes"])

# Roles that can see any athlete
_OPEN_ROLES = {UserRole.ADMIN, UserRole.SPORTS_SCIENTIST}
# Roles with restricted (assignment-based) access
_RESTRICTED_ROLES = {UserRole.COACH, UserRole.PHYSIOTHERAPIST}


# ---------------------------------------------------------------------------
# Internal gate: resolve the Athlete OR raise 403/404
# ---------------------------------------------------------------------------
async def _get_athlete_or_raise(
    athlete_id: uuid.UUID,
    current_user: User,
    db: AsyncSession,
) -> Athlete:
    """
    Fetch the Athlete and verify the caller has permission to read it.
    Returns the Athlete ORM object, or raises HTTP 403/404.
    """
    result = await db.execute(select(Athlete).where(Athlete.id == athlete_id))
    athlete: Athlete | None = result.scalar_one_or_none()
    if not athlete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Athlete not found")

    if current_user.role in _OPEN_ROLES:
        return athlete

    if current_user.role == UserRole.ATHLETE:
        if athlete.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return athlete

    # Coach / Physio – check assignment
    if current_user.role in _RESTRICTED_ROLES:
        asgn_result = await db.execute(
            select(CoachAthleteAssignment).where(
                CoachAthleteAssignment.coach_id == current_user.id,
                CoachAthleteAssignment.athlete_id == athlete_id,
                CoachAthleteAssignment.is_active.is_(True),
            )
        )
        if not asgn_result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
        return athlete

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")


# ---------------------------------------------------------------------------
# GET /athletes  – list with search + pagination
# ---------------------------------------------------------------------------
@router.get(
    "",
    response_model=PaginatedAthletes,
    summary="List athletes (paginated, searchable)",
)
async def list_athletes(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Filter by athlete name or sport"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> PaginatedAthletes:
    stmt = select(Athlete)

    # Role-based filtering
    if current_user.role == UserRole.ATHLETE:
        stmt = stmt.where(Athlete.user_id == current_user.id)
    elif current_user.role in _RESTRICTED_ROLES:
        # subquery: only athletes assigned to this user
        assigned_ids = select(CoachAthleteAssignment.athlete_id).where(
            CoachAthleteAssignment.coach_id == current_user.id,
            CoachAthleteAssignment.is_active.is_(True),
        )
        stmt = stmt.where(Athlete.id.in_(assigned_ids))
    # else ADMIN / SPORTS_SCIENTIST → no filter

    # Search filter (name via user join, or sport directly)
    if search:
        stmt = stmt.join(Athlete.user).where(
            or_(
                User.full_name.ilike(f"%{search}%"),
                Athlete.primary_sport.ilike(f"%{search}%"),
            )
        )

    count_stmt = select(Athlete.id)
    if current_user.role == UserRole.ATHLETE:
        count_stmt = count_stmt.where(Athlete.user_id == current_user.id)
    elif current_user.role in _RESTRICTED_ROLES:
        assigned_ids = select(CoachAthleteAssignment.athlete_id).where(
            CoachAthleteAssignment.coach_id == current_user.id,
            CoachAthleteAssignment.is_active.is_(True),
        )
        count_stmt = count_stmt.where(Athlete.id.in_(assigned_ids))
    if search:
        count_stmt = count_stmt.join(Athlete.user).where(
            or_(
                User.full_name.ilike(f"%{search}%"),
                Athlete.primary_sport.ilike(f"%{search}%"),
            )
        )

    total_result = await db.execute(count_stmt)
    total = len(total_result.all())

    stmt = stmt.order_by(Athlete.created_at.desc()).offset(skip).limit(limit)
    rows = await db.execute(stmt)
    athletes = rows.scalars().all()

    return PaginatedAthletes(
        total=total,
        skip=skip,
        limit=limit,
        items=[AthleteRead.model_validate(a) for a in athletes],
    )


# ---------------------------------------------------------------------------
# POST /athletes  – create own profile (athlete role only)
# ---------------------------------------------------------------------------
@router.post(
    "",
    response_model=AthleteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create athlete profile (own profile; athlete role required)",
)
async def create_athlete(
    payload: AthleteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ATHLETE, UserRole.ADMIN)),
) -> AthleteRead:
    # Determine owner
    if current_user.role == UserRole.ATHLETE:
        owner_id = current_user.id
        # Ensure they don't already have a profile
        existing = await db.execute(select(Athlete).where(Athlete.user_id == owner_id))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Athlete profile already exists for this user",
            )
    else:
        # Admin can POST on behalf of themselves or an existing user; default to self
        owner_id = current_user.id

    athlete = Athlete(user_id=owner_id, **payload.model_dump())
    db.add(athlete)
    await db.flush()
    await db.refresh(athlete)
    return AthleteRead.model_validate(athlete)


# ---------------------------------------------------------------------------
# GET /athletes/{athlete_id}
# ---------------------------------------------------------------------------
@router.get(
    "/{athlete_id}",
    response_model=AthleteRead,
    summary="Get athlete by ID",
)
async def get_athlete(
    athlete_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AthleteRead:
    athlete = await _get_athlete_or_raise(athlete_id, current_user, db)
    return AthleteRead.model_validate(athlete)


# ---------------------------------------------------------------------------
# PUT /athletes/{athlete_id}
# ---------------------------------------------------------------------------
@router.put(
    "/{athlete_id}",
    response_model=AthleteRead,
    summary="Update athlete profile",
)
async def update_athlete(
    athlete_id: uuid.UUID,
    payload: AthleteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AthleteRead:
    athlete = await _get_athlete_or_raise(athlete_id, current_user, db)

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(athlete, field, value)

    db.add(athlete)
    await db.flush()
    await db.refresh(athlete)
    return AthleteRead.model_validate(athlete)


# ---------------------------------------------------------------------------
# DELETE /athletes/{athlete_id} – admin / scientist only
# ---------------------------------------------------------------------------
@router.delete(
    "/{athlete_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete athlete profile (admin/scientist only)",
)
async def delete_athlete(
    athlete_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.SPORTS_SCIENTIST)),
) -> None:
    result = await db.execute(select(Athlete).where(Athlete.id == athlete_id))
    athlete: Athlete | None = result.scalar_one_or_none()
    if not athlete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Athlete not found")
    await db.delete(athlete)


# ===========================================================================
# Sub-resources
# ===========================================================================

# ---------------------------------------------------------------------------
# Injury history
# ---------------------------------------------------------------------------
@router.get(
    "/{athlete_id}/injuries",
    response_model=list[InjuryRead],
    summary="List injury history for an athlete",
)
async def list_injuries(
    athlete_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[InjuryRead]:
    await _get_athlete_or_raise(athlete_id, current_user, db)
    result = await db.execute(
        select(InjuryHistory)
        .where(InjuryHistory.athlete_id == athlete_id)
        .order_by(InjuryHistory.injury_date.desc())
    )
    return [InjuryRead.model_validate(i) for i in result.scalars().all()]


@router.post(
    "/{athlete_id}/injuries",
    response_model=InjuryRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record a new injury for an athlete",
)
async def create_injury(
    athlete_id: uuid.UUID,
    payload: InjuryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> InjuryRead:
    # Athletes cannot self-report injuries; only physio/coach/admin/scientist
    if current_user.role == UserRole.ATHLETE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Athletes cannot self-report injuries. Please contact your physiotherapist.",
        )
    await _get_athlete_or_raise(athlete_id, current_user, db)
    injury = InjuryHistory(athlete_id=athlete_id, **payload.model_dump())
    db.add(injury)
    await db.flush()
    await db.refresh(injury)
    return InjuryRead.model_validate(injury)


# ---------------------------------------------------------------------------
# Training profile
# ---------------------------------------------------------------------------
@router.get(
    "/{athlete_id}/training-profile",
    response_model=list[TrainingProfileRead],
    summary="List training profiles for an athlete",
)
async def list_training_profiles(
    athlete_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[TrainingProfileRead]:
    await _get_athlete_or_raise(athlete_id, current_user, db)
    result = await db.execute(
        select(TrainingProfile)
        .where(TrainingProfile.athlete_id == athlete_id)
        .order_by(TrainingProfile.effective_date.desc())
    )
    return [TrainingProfileRead.model_validate(t) for t in result.scalars().all()]


@router.post(
    "/{athlete_id}/training-profile",
    response_model=TrainingProfileRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a training profile entry for an athlete",
)
async def create_training_profile(
    athlete_id: uuid.UUID,
    payload: TrainingProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TrainingProfileRead:
    await _get_athlete_or_raise(athlete_id, current_user, db)
    profile = TrainingProfile(athlete_id=athlete_id, **payload.model_dump())
    db.add(profile)
    await db.flush()
    await db.refresh(profile)
    return TrainingProfileRead.model_validate(profile)


# ---------------------------------------------------------------------------
# Physical assessments
# ---------------------------------------------------------------------------
@router.get(
    "/{athlete_id}/assessments",
    response_model=list[AssessmentRead],
    summary="List physical assessments for an athlete",
)
async def list_assessments(
    athlete_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[AssessmentRead]:
    await _get_athlete_or_raise(athlete_id, current_user, db)
    result = await db.execute(
        select(PhysicalAssessment)
        .where(PhysicalAssessment.athlete_id == athlete_id)
        .order_by(PhysicalAssessment.assessment_date.desc())
    )
    return [AssessmentRead.model_validate(a) for a in result.scalars().all()]


@router.post(
    "/{athlete_id}/assessments",
    response_model=AssessmentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a physical assessment for an athlete (physio/coach/admin/scientist)",
)
async def create_assessment(
    athlete_id: uuid.UUID,
    payload: AssessmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_roles(
            UserRole.PHYSIOTHERAPIST,
            UserRole.COACH,
            UserRole.ADMIN,
            UserRole.SPORTS_SCIENTIST,
        )
    ),
) -> AssessmentRead:
    await _get_athlete_or_raise(athlete_id, current_user, db)
    assessment = PhysicalAssessment(
        athlete_id=athlete_id,
        assessor_id=current_user.id,
        **payload.model_dump(),
    )
    db.add(assessment)
    await db.flush()
    await db.refresh(assessment)
    return AssessmentRead.model_validate(assessment)
