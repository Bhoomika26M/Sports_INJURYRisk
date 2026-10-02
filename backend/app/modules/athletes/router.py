"""Athlete router — CRUD, RBAC, injury history, training load, ACWR."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_role
from app.core.errors import api_error
from app.database import get_db
from app.modules.athletes.schemas import (
    AthleteCreate,
    AthleteListResponse,
    AthleteResponse,
    AthleteUpdate,
    InjuryHistoryCreate,
    InjuryHistoryListResponse,
    InjuryHistoryResponse,
    TrainingLoadCreate,
    TrainingLoadListResponse,
    TrainingLoadResponse,
)
from app.modules.athletes.service import (
    create_athlete,
    delete_athlete,
    get_athlete,
    list_athletes,
    update_athlete,
    create_injury,
    list_injuries,
    delete_injury,
    create_training_load,
    list_training_loads,
    delete_training_load,
    compute_acwr,
)
from app.modules.users.models import User, UserRole
from app.modules.athletes.models import Athlete

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/athletes", tags=["athletes"])


def _can_access_athlete(user: User, athlete: Athlete) -> bool:
    if user.role in (UserRole.admin, UserRole.physiotherapist, UserRole.sports_scientist):
        return True
    if user.role == UserRole.coach and athlete.coach_id == user.id:
        return True
    if user.role == UserRole.athlete and athlete.user_id == user.id:
        return True
    return False


@router.post("", response_model=AthleteResponse, status_code=status.HTTP_201_CREATED)
async def create_athlete_endpoint(
    data: AthleteCreate,
    current_user: Annotated[User, Depends(require_role(UserRole.coach, UserRole.admin))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new athlete profile. Coaches create for themselves; admins can specify coach_id."""
    coach_id = current_user.id if current_user.role == UserRole.coach else None
    # Admin can optionally specify a different coach via query param in future
    athlete = await create_athlete(
        db=db,
        coach_id=coach_id,
        sport_type=data.sport_type,
        date_of_birth=data.date_of_birth,
        height_cm=data.height_cm,
        weight_kg=data.weight_kg,
        dominant_side=data.dominant_side,
        position=data.position,
    )
    return athlete


@router.get("", response_model=AthleteListResponse)
async def list_athletes_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List athletes with pagination. Role-based filtering."""
    coach_id = None
    if current_user.role == UserRole.coach:
        coach_id = current_user.id
    elif current_user.role == UserRole.athlete:
        # Athletes can only see their own profile
        athlete = await db.scalar(select(Athlete).where(Athlete.user_id == current_user.id))
        if athlete:
            return AthleteListResponse(items=[athlete], total=1, page=1, page_size=1)
        return AthleteListResponse(items=[], total=0, page=1, page_size=1)

    athletes, total = await list_athletes(db, coach_id=coach_id, page=page, page_size=page_size)
    return AthleteListResponse(items=athletes, total=total, page=page, page_size=page_size)


@router.get("/{athlete_id}", response_model=AthleteResponse)
async def get_athlete_endpoint(
    athlete_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a specific athlete by ID."""
    athlete = await get_athlete(db, athlete_id)
    if not athlete:
        raise api_error(404, "NOT_FOUND", "Athlete not found")

    if not _can_access_athlete(current_user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")

    return athlete


@router.put("/{athlete_id}", response_model=AthleteResponse)
async def update_athlete_endpoint(
    athlete_id: str,
    data: AthleteUpdate,
    current_user: Annotated[User, Depends(require_role(UserRole.coach, UserRole.admin))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update an athlete profile."""
    athlete = await get_athlete(db, athlete_id)
    if not athlete:
        raise api_error(404, "NOT_FOUND", "Athlete not found")

    if current_user.role == UserRole.coach and athlete.coach_id != current_user.id:
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")

    updated = await update_athlete(
        db=db,
        athlete_id=athlete_id,
        sport_type=data.sport_type,
        position=data.position,
        date_of_birth=data.date_of_birth,
        height_cm=data.height_cm,
        weight_kg=data.weight_kg,
        dominant_side=data.dominant_side,
    )
    return updated


@router.delete("/{athlete_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_athlete_endpoint(
    athlete_id: str,
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete an athlete profile. Admin only."""
    deleted = await delete_athlete(db, athlete_id)
    if not deleted:
        raise api_error(404, "NOT_FOUND", "Athlete not found")


# Injury History
@router.post("/{athlete_id}/injuries", response_model=InjuryHistoryResponse, status_code=status.HTTP_201_CREATED)
async def create_injury_endpoint(
    athlete_id: str,
    data: InjuryHistoryCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create an injury record for an athlete."""
    athlete = await get_athlete(db, athlete_id)
    if not athlete:
        raise api_error(404, "NOT_FOUND", "Athlete not found")

    if not _can_access_athlete(current_user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")

    injury = await create_injury(
        db=db,
        athlete_id=athlete_id,
        injury_type=data.injury_type,
        body_part=data.body_part,
        injury_date=data.injury_date,
        severity=data.severity,
        recovery_date=data.recovery_date,
        notes=data.notes,
    )
    return injury


@router.get("/{athlete_id}/injuries", response_model=InjuryHistoryListResponse)
async def list_injuries_endpoint(
    athlete_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List injury history for an athlete."""
    athlete = await get_athlete(db, athlete_id)
    if not athlete:
        raise api_error(404, "NOT_FOUND", "Athlete not found")

    if not _can_access_athlete(current_user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")

    injuries, total = await list_injuries(db, athlete_id, page, page_size)
    return InjuryHistoryListResponse(items=injuries, total=total, page=page, page_size=page_size)


@router.delete("/{athlete_id}/injuries/{injury_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_injury_endpoint(
    athlete_id: str,
    injury_id: str,
    current_user: Annotated[User, Depends(require_role(UserRole.coach, UserRole.admin))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete an injury record."""
    athlete = await get_athlete(db, athlete_id)
    if not athlete:
        raise api_error(404, "NOT_FOUND", "Athlete not found")

    if current_user.role == UserRole.coach and athlete.coach_id != current_user.id:
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")

    deleted = await delete_injury(db, athlete_id, injury_id)
    if not deleted:
        raise api_error(404, "NOT_FOUND", "Injury not found")


# Training Load
@router.post("/{athlete_id}/training-load", response_model=TrainingLoadResponse, status_code=status.HTTP_201_CREATED)
async def create_training_load_endpoint(
    athlete_id: str,
    data: TrainingLoadCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a training load entry."""
    athlete = await get_athlete(db, athlete_id)
    if not athlete:
        raise api_error(404, "NOT_FOUND", "Athlete not found")

    if not _can_access_athlete(current_user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")

    entry = await create_training_load(
        db=db,
        athlete_id=athlete_id,
        entry_date=data.entry_date,
        session_type=data.session_type,
        duration_minutes=data.duration_minutes,
        rpe=data.rpe,
        notes=data.notes,
    )
    return entry


@router.get("/{athlete_id}/training-load", response_model=TrainingLoadListResponse)
async def list_training_load_endpoint(
    athlete_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List training load entries."""
    athlete = await get_athlete(db, athlete_id)
    if not athlete:
        raise api_error(404, "NOT_FOUND", "Athlete not found")

    if not _can_access_athlete(current_user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")

    entries, total = await list_training_loads(db, athlete_id, page, page_size)
    return TrainingLoadListResponse(items=entries, total=total, page=page, page_size=page_size)


@router.delete("/{athlete_id}/training-load/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_training_load_endpoint(
    athlete_id: str,
    entry_id: str,
    current_user: Annotated[User, Depends(require_role(UserRole.coach, UserRole.admin))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a training load entry."""
    athlete = await get_athlete(db, athlete_id)
    if not athlete:
        raise api_error(404, "NOT_FOUND", "Athlete not found")

    if current_user.role == UserRole.coach and athlete.coach_id != current_user.id:
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")

    deleted = await delete_training_load(db, athlete_id, entry_id)
    if not deleted:
        raise api_error(404, "NOT_FOUND", "Training load entry not found")


# ACWR
@router.get("/{athlete_id}/acwr")
async def get_acwr_endpoint(
    athlete_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get Acute:Chronic Workload Ratio for an athlete."""
    athlete = await get_athlete(db, athlete_id)
    if not athlete:
        raise api_error(404, "NOT_FOUND", "Athlete not found")

    if not _can_access_athlete(current_user, athlete):
        raise api_error(403, "INSUFFICIENT_PERMISSIONS", "Access denied")

    return await compute_acwr(db, athlete_id)


def _can_access_athlete(user: User, athlete) -> bool:
    if user.role in (UserRole.admin, UserRole.physiotherapist, UserRole.sports_scientist):
        return True
    if user.role == UserRole.coach and athlete.coach_id == user.id:
        return True
    if user.role == UserRole.athlete and athlete.user_id == user.id:
        return True
    return False