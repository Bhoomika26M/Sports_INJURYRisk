"""Athlete service — business logic for athlete management."""

import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

import uuid
from app.modules.athletes.models import Athlete, InjuryHistory, TrainingLoadEntry
from app.modules.users.models import NotificationPreference, User, UserRole

logger = logging.getLogger(__name__)


async def create_athlete(
    db: AsyncSession,
    coach_id: Optional[str],
    sport_type: str,
    date_of_birth: date,
    height_cm: Optional[float] = None,
    weight_kg: Optional[float] = None,
    dominant_side: Optional[str] = None,
    position: Optional[str] = None,
    user_id: Optional[str] = None,
    full_name: Optional[str] = None,
    email: Optional[str] = None,
) -> Athlete:
    """Create a new athlete profile and link/create their user profile."""
    clean_email = email.strip().lower() if email and email.strip() else None
    clean_name = full_name.strip() if full_name and full_name.strip() else None

    linked_user_id = user_id

    if clean_email:
        # Check if a user with this email already exists
        existing_user = await db.scalar(select(User).where(User.email == clean_email))
        if existing_user:
            # Check if this user already has an athlete profile
            existing_athlete = await db.scalar(select(Athlete).where(Athlete.user_id == existing_user.id))
            if existing_athlete:
                if existing_athlete.coach_id and coach_id and existing_athlete.coach_id != coach_id:
                    raise ValueError("An athlete with this email is already registered with another coach.")
                # Update existing athlete profile and coach link
                if coach_id:
                    existing_athlete.coach_id = coach_id
                existing_athlete.sport_type = sport_type
                existing_athlete.position = position
                existing_athlete.date_of_birth = date_of_birth
                if height_cm is not None:
                    existing_athlete.height_cm = height_cm
                if weight_kg is not None:
                    existing_athlete.weight_kg = weight_kg
                if dominant_side is not None:
                    existing_athlete.dominant_side = dominant_side
                if clean_name:
                    existing_user.full_name = clean_name
                await db.commit()
                await db.refresh(existing_athlete)
                return existing_athlete
            else:
                if clean_name and (not existing_user.full_name or existing_user.full_name == "Athlete"):
                    existing_user.full_name = clean_name
                linked_user_id = existing_user.id
        else:
            # Create a user placeholder for this email
            user_full_name = clean_name or clean_email.split("@")[0]
            new_user = User(
                email=clean_email,
                password_hash="",
                full_name=user_full_name,
                role=UserRole.athlete,
                is_active=True,
            )
            db.add(new_user)
            await db.flush()
            for ntype in ["high_risk_flag", "insufficient_baseline", "processing_failed", "training_load_spike", "assessment_due"]:
                db.add(NotificationPreference(user_id=new_user.id, notification_type=ntype))
            linked_user_id = new_user.id
    elif not linked_user_id:
        # No email provided: create local placeholder user so full_name resolves everywhere
        placeholder_name = clean_name or "Athlete"
        placeholder_email = f"athlete_{uuid.uuid4().hex[:12]}@local.athlete"
        new_user = User(
            email=placeholder_email,
            password_hash="",
            full_name=placeholder_name,
            role=UserRole.athlete,
            is_active=True,
        )
        db.add(new_user)
        await db.flush()
        for ntype in ["high_risk_flag", "insufficient_baseline", "processing_failed", "training_load_spike", "assessment_due"]:
            db.add(NotificationPreference(user_id=new_user.id, notification_type=ntype))
        linked_user_id = new_user.id
    elif linked_user_id and clean_name:
        u = await db.get(User, linked_user_id)
        if u:
            u.full_name = clean_name

    athlete = Athlete(
        coach_id=coach_id,
        user_id=linked_user_id,
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
    full_name: Optional[str] = None,
    email: Optional[str] = None,
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

    clean_name = full_name.strip() if full_name is not None and full_name.strip() else None
    clean_email = email.strip().lower() if email is not None and email.strip() else None

    # Handle full_name update
    if clean_name:
        if athlete.user:
            athlete.user.full_name = clean_name
        else:
            placeholder_email = f"athlete_{uuid.uuid4().hex[:12]}@local.athlete"
            new_user = User(
                email=placeholder_email,
                password_hash="",
                full_name=clean_name,
                role=UserRole.athlete,
                is_active=True,
            )
            db.add(new_user)
            await db.flush()
            athlete.user_id = new_user.id

    # Handle email update
    if email is not None:
        if clean_email:
            existing_user = await db.scalar(select(User).where(User.email == clean_email))
            if existing_user and existing_user.id != athlete.user_id:
                existing_athlete = await db.scalar(select(Athlete).where(Athlete.user_id == existing_user.id))
                if existing_athlete and existing_athlete.id != athlete.id:
                    raise ValueError("Another athlete profile is already linked to this email address.")
                old_user = athlete.user
                athlete.user_id = existing_user.id
                if clean_name:
                    existing_user.full_name = clean_name
                if old_user and old_user.email.endswith("@local.athlete"):
                    await db.delete(old_user)
            elif athlete.user:
                athlete.user.email = clean_email
            else:
                user_name = clean_name or clean_email.split("@")[0]
                new_user = User(
                    email=clean_email,
                    password_hash="",
                    full_name=user_name,
                    role=UserRole.athlete,
                    is_active=True,
                )
                db.add(new_user)
                await db.flush()
                athlete.user_id = new_user.id
        elif athlete.user and not athlete.user.email.endswith("@local.athlete"):
            # Email cleared by user: switch back to a local placeholder
            athlete.user.email = f"athlete_{uuid.uuid4().hex[:12]}@local.athlete"

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


# ---------------------------------------------------------------------------
# Training-load indicators (ACWR + RPE trend)
#
# ACWR follows the standard rolling-average formulation: daily loads are summed
# per calendar day, days with no session count as ZERO load, the acute load is the
# 7-day mean and the chronic load the 28-day mean, ACWR = acute / chronic
# (Gabbett 2016; zone conventions: 0.8-1.3 "sweet spot", >=1.5 elevated).
# Known limitation, kept visible on purpose: ACWR is criticised as a statistical
# artefact-prone metric (Impellizzeri et al. 2020, Sports Med 51:581) and is very
# sensitive to missing data, so we refuse to compute it until a full chronic
# window of monitoring history exists. It is a bounded input, never a verdict.
# ---------------------------------------------------------------------------

ACWR_ACUTE_DAYS = 7
ACWR_CHRONIC_DAYS = 28
ACWR_ELEVATED_THRESHOLD = 1.5


def compute_acwr_from_loads(
    daily_loads: dict[date, float],
    today: date,
    first_entry_date: Optional[date],
) -> dict:
    """Pure ACWR calculation. `daily_loads` = {date: summed session_load}."""
    if first_entry_date is None or (today - first_entry_date).days < ACWR_CHRONIC_DAYS - 1:
        return {
            "acwr": None, "acute_load": None, "chronic_load": None, "flagged": False,
            "message": (
                f"Insufficient history: ACWR needs a full {ACWR_CHRONIC_DAYS}-day chronic window "
                "of logged training (rest days are counted as zero load)."
            ),
        }

    acute_start = today - timedelta(days=ACWR_ACUTE_DAYS - 1)
    chronic_start = today - timedelta(days=ACWR_CHRONIC_DAYS - 1)

    acute_sum = sum(v for d, v in daily_loads.items() if acute_start <= d <= today)
    chronic_sum = sum(v for d, v in daily_loads.items() if chronic_start <= d <= today)

    acute_mean = acute_sum / ACWR_ACUTE_DAYS
    chronic_mean = chronic_sum / ACWR_CHRONIC_DAYS

    if chronic_mean <= 0:
        return {
            "acwr": None, "acute_load": round(acute_sum, 1), "chronic_load": 0.0, "flagged": False,
            "message": "No load logged in the chronic window; ratio undefined.",
        }

    acwr = acute_mean / chronic_mean
    return {
        "acwr": round(acwr, 2),
        # weekly-equivalent loads (chronic mean x 7) so the two numbers are comparable
        "acute_load": round(acute_sum, 1),
        "chronic_load": round(chronic_mean * ACWR_ACUTE_DAYS, 1),
        "flagged": acwr > ACWR_ELEVATED_THRESHOLD,
        "message": "ACWR computed (7-day mean / 28-day mean, rest days = 0)",
    }


async def compute_acwr(db: AsyncSession, athlete_id: str, today: Optional[date] = None) -> dict:
    """Compute Acute:Chronic Workload Ratio for an athlete."""
    today = today or date.today()
    chronic_start = today - timedelta(days=ACWR_CHRONIC_DAYS - 1)

    first_entry = await db.scalar(
        select(func.min(TrainingLoadEntry.entry_date)).where(
            TrainingLoadEntry.athlete_id == athlete_id,
            TrainingLoadEntry.session_load.is_not(None),
        )
    )
    rows = (await db.execute(
        select(TrainingLoadEntry.entry_date, TrainingLoadEntry.session_load).where(
            TrainingLoadEntry.athlete_id == athlete_id,
            TrainingLoadEntry.entry_date >= chronic_start,
            TrainingLoadEntry.entry_date <= today,
            TrainingLoadEntry.session_load.is_not(None),
        )
    )).all()

    daily_loads: dict[date, float] = {}
    for entry_date, session_load in rows:
        daily_loads[entry_date] = daily_loads.get(entry_date, 0.0) + float(session_load)

    return compute_acwr_from_loads(daily_loads, today, first_entry)


RPE_RECENT_DAYS = 7
RPE_BASELINE_DAYS = 21
RPE_MIN_ENTRIES_PER_WINDOW = 3


def compute_rpe_trend_from_entries(entries: list[tuple[date, int]], today: date) -> Optional[dict]:
    """Recent-week mean RPE minus the mean RPE of the preceding three weeks.

    Positive = sessions are feeling harder than the athlete's own recent norm
    (a fatigue-accumulation indicator). Returns None when either window has fewer
    than RPE_MIN_ENTRIES_PER_WINDOW rated sessions — a trend from one or two points
    is noise.
    """
    recent_start = today - timedelta(days=RPE_RECENT_DAYS - 1)
    base_start = recent_start - timedelta(days=RPE_BASELINE_DAYS)
    recent = [r for d, r in entries if recent_start <= d <= today]
    baseline = [r for d, r in entries if base_start <= d < recent_start]
    if len(recent) < RPE_MIN_ENTRIES_PER_WINDOW or len(baseline) < RPE_MIN_ENTRIES_PER_WINDOW:
        return None
    recent_mean = sum(recent) / len(recent)
    baseline_mean = sum(baseline) / len(baseline)
    return {
        "rpe_trend": round(recent_mean - baseline_mean, 2),
        "recent_mean_rpe": round(recent_mean, 2),
        "baseline_mean_rpe": round(baseline_mean, 2),
        "n_recent": len(recent),
        "n_baseline": len(baseline),
    }


async def compute_rpe_trend(db: AsyncSession, athlete_id: str, today: Optional[date] = None) -> Optional[dict]:
    today = today or date.today()
    start = today - timedelta(days=RPE_RECENT_DAYS + RPE_BASELINE_DAYS)
    rows = (await db.execute(
        select(TrainingLoadEntry.entry_date, TrainingLoadEntry.rpe).where(
            TrainingLoadEntry.athlete_id == athlete_id,
            TrainingLoadEntry.entry_date >= start,
            TrainingLoadEntry.entry_date <= today,
            TrainingLoadEntry.rpe.is_not(None),
        )
    )).all()
    return compute_rpe_trend_from_entries([(d, int(r)) for d, r in rows], today)
