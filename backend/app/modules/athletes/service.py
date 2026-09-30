"""Athlete service — business logic for athlete management."""

import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.athletes.models import Athlete, InjuryHistory, TrainingLoadEntry

logger = logging.getLogger(__name__)


async def create_athlete(
    db: AsyncSession,
    coach_id: str,
    sport_type: str,
    date_of_birth: date,
    height_cm: Optional[float] = None,
    weight_kg: Optional[float] = None,
    dominant_side: Optional[str] = None,
    position: Optional[str] = None,
    user_id: Optional[str] = None,
) -> Athlete:
    """Create a new athlete profile."""
    athlete = Athlete(
        coach_id=coach_id,
        user_id=user_id,
        sport_type=sport_type,
        position=position,
        date_of_birth=date_of_birth,
        height_cm=height_cm,
        weight_kg=weight_kg,
        dominant_side=dominant_side,
    )
    db.add(athlete)
    await db.commit()
    await db.refresh(athlete)
    return athlete


async def update_athlete(
    db: AsyncSession,
    athlete_id: str,
    sport_type: Optional[str] = None,
    position: Optional[str] = None,
    date_of_birth: Optional[date] = None,
    height_cm: Optional[float] = None,
    weight_kg: Optional[float] = None,
    dominant_side: Optional[str] = None,
) -> Optional[Athlete]:
    """Update an athlete profile."""
    athlete = await db.get(Athlete, athlete_id)
    if not athlete:
        return None

    if sport_type is not None:
        athlete.sport_type = sport_type
    if position is not None:
        athlete.position = position
    if date_of_birth is not None:
        athlete.date_of_birth = date_of_birth
    if height_cm is not None:
        athlete.height_cm = height_cm
    if weight_kg is not None:
        athlete.weight_kg = weight_kg
    if dominant_side is not None:
        athlete.dominant_side = dominant_side

    await db.commit()
    await db.refresh(athlete)
    return athlete


async def delete_athlete(db: AsyncSession, athlete_id: str) -> bool:
    """Delete an athlete profile."""
    athlete = await db.get(Athlete, athlete_id)
    if not athlete:
        return False
    await db.delete(athlete)
    await db.commit()
    return True


async def list_athletes(
    db: AsyncSession,
    coach_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Athlete], int]:
    """List athletes with pagination."""
    query = select(Athlete).order_by(Athlete.created_at.desc())
    count_query = select(func.count()).select_from(Athlete)

    if coach_id:
        query = query.where(Athlete.coach_id == coach_id)
        count_query = count_query.where(Athlete.coach_id == coach_id)

    total = await db.scalar(count_query) or 0
    query = query.offset((page - 1) * page_size).limit(page_size)
    athletes = list((await db.scalars(query)).all())
    return athletes, total


async def get_athlete(db: AsyncSession, athlete_id: str) -> Optional[Athlete]:
    """Get an athlete by ID."""
    return await db.get(Athlete, athlete_id)


# Injury History
async def create_injury(
    db: AsyncSession,
    athlete_id: str,
    injury_type: str,
    body_part: str,
    injury_date: date,
    severity: Optional[str] = None,
    recovery_date: Optional[date] = None,
    notes: Optional[str] = None,
) -> InjuryHistory:
    injury = InjuryHistory(
        athlete_id=athlete_id,
        injury_type=injury_type,
        body_part=body_part,
        injury_date=injury_date,
        recovery_date=recovery_date,
        severity=severity,
        notes=notes,
    )
    db.add(injury)
    await db.commit()
    await db.refresh(injury)
    return injury


async def list_injuries(
    db: AsyncSession,
    athlete_id: str,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[InjuryHistory], int]:
    query = select(InjuryHistory).where(InjuryHistory.athlete_id == athlete_id).order_by(InjuryHistory.injury_date.desc())
    count_query = select(func.count()).select_from(InjuryHistory).where(InjuryHistory.athlete_id == athlete_id)

    total = await db.scalar(count_query) or 0
    query = query.offset((page - 1) * page_size).limit(page_size)
    injuries = list((await db.scalars(query)).all())
    return injuries, total


async def delete_injury(db: AsyncSession, athlete_id: str, injury_id: str) -> bool:
    injury = await db.get(InjuryHistory, injury_id)
    if not injury or injury.athlete_id != athlete_id:
        return False
    await db.delete(injury)
    await db.commit()
    return True


# Training Load
async def create_training_load(
    db: AsyncSession,
    athlete_id: str,
    entry_date: date,
    session_type: Optional[str] = None,
    duration_minutes: Optional[int] = None,
    rpe: Optional[int] = None,
    notes: Optional[str] = None,
) -> TrainingLoadEntry:
    session_load = None
    if duration_minutes and rpe:
        session_load = duration_minutes * rpe

    entry = TrainingLoadEntry(
        athlete_id=athlete_id,
        entry_date=entry_date,
        session_type=session_type,
        duration_minutes=duration_minutes,
        rpe=rpe,
        session_load=session_load,
        notes=notes,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def list_training_loads(
    db: AsyncSession,
    athlete_id: str,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[TrainingLoadEntry], int]:
    query = select(TrainingLoadEntry).where(TrainingLoadEntry.athlete_id == athlete_id).order_by(TrainingLoadEntry.entry_date.desc())
    count_query = select(func.count()).select_from(TrainingLoadEntry).where(TrainingLoadEntry.athlete_id == athlete_id)

    total = await db.scalar(count_query) or 0
    query = query.offset((page - 1) * page_size).limit(page_size)
    entries = list((await db.scalars(query)).all())
    return entries, total


async def delete_training_load(db: AsyncSession, athlete_id: str, entry_id: str) -> bool:
    entry = await db.get(TrainingLoadEntry, entry_id)
    if not entry or entry.athlete_id != athlete_id:
        return False
    await db.delete(entry)
    await db.commit()
    return True


# ACWR Calculation
async def compute_acwr(db: AsyncSession, athlete_id: str) -> dict:
    """Compute Acute:Chronic Workload Ratio for an athlete."""
    # Get last 28 days of training loads
    cutoff = date.today() - timedelta(days=28)
    stmt = select(TrainingLoadEntry).where(
        TrainingLoadEntry.athlete_id == athlete_id,
        TrainingLoadEntry.entry_date >= cutoff,
        TrainingLoadEntry.session_load.is_not(None),
    ).order_by(TrainingLoadEntry.entry_date)
    entries = list((await db.scalars(stmt)).all())

    if len(entries) < 7:
        return {
            "acwr": None,
            "acute_load": None,
            "chronic_load": None,
            "flagged": False,
            "message": "Insufficient data (need at least 7 days with session_load)",
        }

    # Group by date
    daily_loads = {}
    for e in entries:
        d = e.entry_date
        daily_loads[d] = daily_loads.get(d, 0) + float(e.session_load or 0)

    # Sort dates
    sorted_dates = sorted(daily_loads.keys())

    # Acute: last 7 days
    acute_dates = [d for d in sorted_dates if d >= date.today() - timedelta(days=7)]
    acute_load = sum(daily_loads[d] for d in acute_dates) if acute_dates else 0

    # Chronic: 28-day average * 7
    chronic_avg = sum(daily_loads.values()) / max(1, len(sorted_dates))
    chronic_load = chronic_avg * 7

    acwr = acute_load / chronic_load if chronic_load > 0 else None
    flagged = acwr is not None and acwr > 1.5

    return {
        "acwr": round(acwr, 2) if acwr else None,
        "acute_load": round(acute_load, 1),
        "chronic_load": round(chronic_load, 1),
        "flagged": flagged,
        "message": "ACWR computed" if acwr else "Insufficient data",
    }