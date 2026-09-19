"""Athlete service — business logic for athlete CRUD, injury history, training load."""

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.athletes.models import Athlete, InjuryHistory, TrainingLoadEntry
from app.modules.athletes.schemas import (
    AthleteCreate,
    AthleteUpdate,
    InjuryHistoryCreate,
    TrainingLoadCreate,
)

logger = logging.getLogger(__name__)


# --- Athlete CRUD ---

async def create_athlete(db: AsyncSession, data: AthleteCreate) -> Athlete:
    """Create a new athlete profile."""
    athlete = Athlete(
        user_id=data.user_id,
        coach_id=data.coach_id,
        sport_type=data.sport_type,
        position=data.position,
        date_of_birth=data.date_of_birth,
        height_cm=data.height_cm,
        weight_kg=data.weight_kg,
        dominant_side=data.dominant_side,
    )
    db.add(athlete)
    await db.flush()
    await db.refresh(athlete)
    return athlete


async def get_athlete(db: AsyncSession, athlete_id: str) -> Athlete | None:
    """Get an athlete by ID."""
    result = await db.execute(select(Athlete).where(Athlete.id == athlete_id))
    return result.scalar_one_or_none()


async def list_athletes(
    db: AsyncSession, page: int = 1, page_size: int = 20, coach_id: str | None = None
) -> tuple[list[Athlete], int]:
    """List athletes with pagination. Optionally filter by coach_id."""
    query = select(Athlete)
    count_query = select(func.count()).select_from(Athlete)

    if coach_id:
        query = query.where(Athlete.coach_id == coach_id)
        count_query = count_query.where(Athlete.coach_id == coach_id)

    # Total count
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginated results
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    athletes = list(result.scalars().all())

    return athletes, total


async def update_athlete(db: AsyncSession, athlete: Athlete, data: AthleteUpdate) -> Athlete:
    """Update an athlete's fields (only those provided)."""
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(athlete, field, value)
    await db.flush()
    await db.refresh(athlete)
    return athlete


async def delete_athlete(db: AsyncSession, athlete: Athlete) -> None:
    """Delete an athlete profile."""
    await db.delete(athlete)
    await db.flush()


# --- Injury History ---

async def create_injury(db: AsyncSession, athlete_id: str, data: InjuryHistoryCreate) -> InjuryHistory:
    """Add an injury to an athlete's history."""
    injury = InjuryHistory(
        athlete_id=athlete_id,
        injury_type=data.injury_type,
        body_part=data.body_part,
        injury_date=data.injury_date,
        recovery_date=data.recovery_date,
        severity=data.severity,
        notes=data.notes,
    )
    db.add(injury)
    await db.flush()
    await db.refresh(injury)
    return injury


async def list_injuries(
    db: AsyncSession, athlete_id: str, page: int = 1, page_size: int = 20
) -> tuple[list[InjuryHistory], int]:
    """List injury history for an athlete."""
    query = select(InjuryHistory).where(InjuryHistory.athlete_id == athlete_id)
    count_query = select(func.count()).select_from(InjuryHistory).where(InjuryHistory.athlete_id == athlete_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    injuries = list(result.scalars().all())

    return injuries, total


async def delete_injury(db: AsyncSession, injury_id: str, athlete_id: str) -> bool:
    """Delete an injury record. Returns True if found and deleted."""
    result = await db.execute(
        select(InjuryHistory).where(InjuryHistory.id == injury_id, InjuryHistory.athlete_id == athlete_id)
    )
    injury = result.scalar_one_or_none()
    if injury is None:
        return False
    await db.delete(injury)
    await db.flush()
    return True


# --- Training Load ---

async def create_training_load(db: AsyncSession, athlete_id: str, data: TrainingLoadCreate) -> TrainingLoadEntry:
    """Add a training load entry for an athlete."""
    entry = TrainingLoadEntry(
        athlete_id=athlete_id,
        entry_date=data.entry_date,
        session_type=data.session_type,
        duration_minutes=data.duration_minutes,
        rpe=data.rpe,
        notes=data.notes,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)
    return entry


async def list_training_loads(
    db: AsyncSession, athlete_id: str, page: int = 1, page_size: int = 20
) -> tuple[list[TrainingLoadEntry], int]:
    """List training load entries for an athlete."""
    query = select(TrainingLoadEntry).where(TrainingLoadEntry.athlete_id == athlete_id)
    count_query = select(func.count()).select_from(TrainingLoadEntry).where(
        TrainingLoadEntry.athlete_id == athlete_id
    )

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    entries = list(result.scalars().all())

    return entries, total


async def delete_training_load(db: AsyncSession, entry_id: str, athlete_id: str) -> bool:
    """Delete a training load entry. Returns True if found and deleted."""
    result = await db.execute(
        select(TrainingLoadEntry).where(
            TrainingLoadEntry.id == entry_id, TrainingLoadEntry.athlete_id == athlete_id
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        return False
    await db.delete(entry)
    await db.flush()
    return True
