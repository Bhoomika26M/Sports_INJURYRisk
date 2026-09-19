"""Athlete router — CRUD for athletes, injury history, training load.

RBAC rules:
- POST /athletes: coach, physiotherapist, sports_scientist, admin
- GET /athletes: all authenticated users
- GET /athletes/{id}: owner (athlete), their coach, or admin/physio/sports_scientist
- PUT /athletes/{id}: owner or admin
- DELETE /athletes/{id}: admin only
- Sub-resources (injury history, training load): same access as parent athlete
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_role
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
    create_injury,
    create_training_load,
    delete_athlete,
    delete_injury,
    delete_training_load,
    get_athlete,
    list_athletes,
    list_injuries,
    list_training_loads,
    update_athlete,
)
from app.modules.users.models import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/athletes", tags=["athletes"])


def _can_access_athlete(user: User, athlete) -> bool:
    """Check if the current user can access this athlete's data."""
    # Admin, physio, sports_scientist can see all
    if user.role in (UserRole.admin, UserRole.physiotherapist, UserRole.sports_scientist):
        return True
    # Coach can see their own athletes
    if user.role == UserRole.coach and athlete.coach_id == user.id:
        return True
    # Athlete can see their own record
    if user.role == UserRole.athlete and athlete.user_id == user.id:
        return True
    return False


# --- Athlete CRUD ---

@router.post("", response_model=AthleteResponse, status_code=status.HTTP_201_CREATED)
async def create_athlete_endpoint(
    data: AthleteCreate,
    current_user: Annotated[
        User,
        Depends(require_role(UserRole.coach, UserRole.physiotherapist, UserRole.sports_scientist, UserRole.admin)),
    ],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Create a new athlete profile. Athletes cannot create their own profiles."""
    if current_user.role == UserRole.coach and not data.coach_id:
        data.coach_id = current_user.id
    athlete = await create_athlete(db, data)
    return athlete


@router.get("", response_model=AthleteListResponse)
async def list_athletes_endpoint(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List athletes. Coaches see their own athletes. Admin/physio/sci see all. Athletes see their own."""
    coach_filter = None
    if current_user.role == UserRole.coach:
        coach_filter = current_user.id
    elif current_user.role == UserRole.athlete:
        # Athletes see only themselves — handled via filtering
        # For simplicity, return all and filter (small dataset in M1)
        pass

    athletes, total = await list_athletes(db, page=page, page_size=page_size, coach_id=coach_filter)

    # If athlete role, filter to only their own record
    if current_user.role == UserRole.athlete:
        athletes = [a for a in athletes if a.user_id == current_user.id]
        total = len(athletes)

    return AthleteListResponse(items=athletes, total=total, page=page, page_size=page_size)


@router.get("/{athlete_id}", response_model=AthleteResponse)
async def get_athlete_endpoint(
    athlete_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Get a single athlete by ID."""
    athlete = await get_athlete(db, athlete_id)
    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Athlete not found", "details": {}}},
        )
    if not _can_access_athlete(current_user, athlete):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "INSUFFICIENT_PERMISSIONS", "message": "Access denied to this athlete", "details": {}}},
        )
    return athlete


@router.put("/{athlete_id}", response_model=AthleteResponse)
async def update_athlete_endpoint(
    athlete_id: str,
    data: AthleteUpdate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Update an athlete profile."""
    athlete = await get_athlete(db, athlete_id)
    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Athlete not found", "details": {}}},
        )
    # Only admin or the athlete themselves can update
    if not (current_user.role == UserRole.admin or athlete.user_id == current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "INSUFFICIENT_PERMISSIONS", "message": "Only admin or the athlete can update this profile", "details": {}}},
        )
    updated = await update_athlete(db, athlete, data)
    return updated


@router.delete("/{athlete_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_athlete_endpoint(
    athlete_id: str,
    current_user: Annotated[User, Depends(require_role(UserRole.admin))],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete an athlete profile. Admin only."""
    athlete = await get_athlete(db, athlete_id)
    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Athlete not found", "details": {}}},
        )
    await delete_athlete(db, athlete)


# --- Injury History ---

@router.post("/{athlete_id}/injuries", response_model=InjuryHistoryResponse, status_code=status.HTTP_201_CREATED)
async def create_injury_endpoint(
    athlete_id: str,
    data: InjuryHistoryCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Add an injury to an athlete's history."""
    athlete = await get_athlete(db, athlete_id)
    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Athlete not found", "details": {}}},
        )
    if not _can_access_athlete(current_user, athlete):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "INSUFFICIENT_PERMISSIONS", "message": "Access denied", "details": {}}},
        )
    injury = await create_injury(db, athlete_id, data)
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
    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Athlete not found", "details": {}}},
        )
    if not _can_access_athlete(current_user, athlete):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "INSUFFICIENT_PERMISSIONS", "message": "Access denied", "details": {}}},
        )
    injuries, total = await list_injuries(db, athlete_id, page=page, page_size=page_size)
    return InjuryHistoryListResponse(items=injuries, total=total, page=page, page_size=page_size)


@router.delete("/{athlete_id}/injuries/{injury_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_injury_endpoint(
    athlete_id: str,
    injury_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete an injury record."""
    athlete = await get_athlete(db, athlete_id)
    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Athlete not found", "details": {}}},
        )
    if not _can_access_athlete(current_user, athlete):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "INSUFFICIENT_PERMISSIONS", "message": "Access denied", "details": {}}},
        )
    deleted = await delete_injury(db, injury_id, athlete_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Injury record not found", "details": {}}},
        )


# --- Training Load ---

@router.post("/{athlete_id}/training-load", response_model=TrainingLoadResponse, status_code=status.HTTP_201_CREATED)
async def create_training_load_endpoint(
    athlete_id: str,
    data: TrainingLoadCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Add a training load entry for an athlete."""
    athlete = await get_athlete(db, athlete_id)
    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Athlete not found", "details": {}}},
        )
    if not _can_access_athlete(current_user, athlete):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "INSUFFICIENT_PERMISSIONS", "message": "Access denied", "details": {}}},
        )
    entry = await create_training_load(db, athlete_id, data)
    return entry


@router.get("/{athlete_id}/training-load", response_model=TrainingLoadListResponse)
async def list_training_loads_endpoint(
    athlete_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List training load entries for an athlete."""
    athlete = await get_athlete(db, athlete_id)
    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Athlete not found", "details": {}}},
        )
    if not _can_access_athlete(current_user, athlete):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "INSUFFICIENT_PERMISSIONS", "message": "Access denied", "details": {}}},
        )
    entries, total = await list_training_loads(db, athlete_id, page=page, page_size=page_size)
    return TrainingLoadListResponse(items=entries, total=total, page=page, page_size=page_size)


@router.delete("/{athlete_id}/training-load/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_training_load_endpoint(
    athlete_id: str,
    entry_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Delete a training load entry."""
    athlete = await get_athlete(db, athlete_id)
    if athlete is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Athlete not found", "details": {}}},
        )
    if not _can_access_athlete(current_user, athlete):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "INSUFFICIENT_PERMISSIONS", "message": "Access denied", "details": {}}},
        )
    deleted = await delete_training_load(db, entry_id, athlete_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": {"code": "NOT_FOUND", "message": "Training load entry not found", "details": {}}},
        )
