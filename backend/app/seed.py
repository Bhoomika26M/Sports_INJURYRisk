"""Seed script — idempotent demo data for Milestone 1.

Creates 5 users (one per role), 3 athletes with injury history and training load entries.

Usage:
    python -m app.seed
"""

import asyncio
import logging
import sys
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.database import async_session_factory, engine, Base
from app.modules.users.models import User, UserRole
from app.modules.athletes.models import Athlete, InjuryHistory, TrainingLoadEntry
import app.modules.videos.models  # register Video model
import app.modules.risk_scoring.models  # register Risk models
import app.modules.recommendations.models  # register Recommendation models


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Demo users — one per role
DEMO_USERS = [
    {
        "email": "athlete@demo.com",
        "password": "demo123",
        "full_name": "Alex Johnson",
        "role": UserRole.athlete,
    },
    {
        "email": "soccer.athlete@demo.com",
        "password": "demo123",
        "full_name": "Marcus Sterling",
        "role": UserRole.athlete,
    },
    {
        "email": "track.athlete@demo.com",
        "password": "demo123",
        "full_name": "Elena Rostova",
        "role": UserRole.athlete,
    },
    {
        "email": "coach@demo.com",
        "password": "demo123",
        "full_name": "Sarah Williams",
        "role": UserRole.coach,
    },
    {
        "email": "physio@demo.com",
        "password": "demo123",
        "full_name": "Dr. Michael Chen",
        "role": UserRole.physiotherapist,
    },
    {
        "email": "scientist@demo.com",
        "password": "demo123",
        "full_name": "Dr. Emily Rodriguez",
        "role": UserRole.sports_scientist,
    },
    {
        "email": "admin@demo.com",
        "password": "demo123",
        "full_name": "Admin User",
        "role": UserRole.admin,
    },
]


async def seed_users(db: AsyncSession) -> dict[str, User]:
    """Create demo users if they don't exist. Returns dict of email -> User."""
    users = {}
    for user_data in DEMO_USERS:
        result = await db.execute(select(User).where(User.email == user_data["email"]))
        existing = result.scalar_one_or_none()
        if existing:
            existing.password_hash = hash_password(user_data["password"])
            logger.info(f"Updated password for existing user: {user_data['email']}")
            users[user_data["email"]] = existing
        else:
            user = User(
                email=user_data["email"],
                password_hash=hash_password(user_data["password"]),
                full_name=user_data["full_name"],
                role=user_data["role"],
            )
            db.add(user)
            await db.flush()
            await db.refresh(user)
            users[user_data["email"]] = user
            logger.info(f"Created user: {user_data['email']} ({user_data['role'].value})")
    return users


async def seed_athletes(db: AsyncSession, users: dict[str, User]) -> list[Athlete]:
    """Create demo athletes if they don't exist."""
    athlete_user = users["athlete@demo.com"]
    soccer_user = users.get("soccer.athlete@demo.com")
    track_user = users.get("track.athlete@demo.com")
    coach_user = users["coach@demo.com"]

    athlete_defs = [
        {
            "user_id": athlete_user.id,
            "coach_id": coach_user.id,
            "sport_type": "basketball",
            "position": "point guard",
            "date_of_birth": date(2000, 3, 15),
            "height_cm": 185.5,
            "weight_kg": 82.0,
            "dominant_side": "right",
        },
        {
            "user_id": soccer_user.id if soccer_user else None,
            "coach_id": coach_user.id,
            "sport_type": "soccer",
            "position": "midfielder",
            "date_of_birth": date(1999, 8, 22),
            "height_cm": 178.0,
            "weight_kg": 75.5,
            "dominant_side": "left",
        },
        {
            "user_id": track_user.id if track_user else None,
            "coach_id": coach_user.id,
            "sport_type": "track and field",
            "position": "sprinter",
            "date_of_birth": date(2001, 11, 5),
            "height_cm": 175.0,
            "weight_kg": 68.0,
            "dominant_side": "right",
        },
    ]

    athletes = []
    for i, athlete_data in enumerate(athlete_defs):
        # Check if athlete with this user_id or sport_type + date_of_birth exists
        result = await db.execute(
            select(Athlete).where(
                Athlete.sport_type == athlete_data["sport_type"],
                Athlete.date_of_birth == athlete_data["date_of_birth"],
                Athlete.coach_id == athlete_data["coach_id"],
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            if existing.user_id is None and athlete_data.get("user_id"):
                existing.user_id = athlete_data["user_id"]
                await db.flush()
                await db.refresh(existing)
            logger.info(f"Athlete already exists: {athlete_data['sport_type']}")
            athletes.append(existing)
        else:
            athlete = Athlete(**athlete_data)
            db.add(athlete)
            await db.flush()
            await db.refresh(athlete)
            athletes.append(athlete)
            logger.info(f"Created athlete: {athlete_data['sport_type']} ({athlete_data['position']})")

    return athletes


async def seed_injury_history(db: AsyncSession, athletes: list[Athlete]) -> None:
    """Create demo injury records if they don't exist."""
    injuries_data = [
        # Athlete 0 — basketball player
        {
            "athlete_idx": 0,
            "injury_type": "ACL sprain",
            "body_part": "right knee",
            "injury_date": date(2024, 11, 15),
            "recovery_date": date(2025, 2, 1),
            "severity": "moderate",
            "notes": "Non-contact injury during practice",
        },
        {
            "athlete_idx": 0,
            "injury_type": "Ankle sprain",
            "body_part": "left ankle",
            "injury_date": date(2025, 4, 10),
            "recovery_date": date(2025, 4, 25),
            "severity": "minor",
            "notes": "Rolled ankle on landing",
        },
        # Athlete 1 — soccer player
        {
            "athlete_idx": 1,
            "injury_type": "Hamstring strain",
            "body_part": "right hamstring",
            "injury_date": date(2025, 1, 20),
            "recovery_date": date(2025, 3, 1),
            "severity": "moderate",
            "notes": "During sprint training",
        },
        # Athlete 2 — track athlete
        {
            "athlete_idx": 2,
            "injury_type": "Shin splints",
            "body_part": "bilateral shins",
            "injury_date": date(2025, 5, 1),
            "recovery_date": None,
            "severity": "minor",
            "notes": "Gradually worsening over training block",
        },
    ]

    for injury_data in injuries_data:
        athlete = athletes[injury_data["athlete_idx"]]
        result = await db.execute(
            select(InjuryHistory).where(
                InjuryHistory.athlete_id == athlete.id,
                InjuryHistory.injury_type == injury_data["injury_type"],
                InjuryHistory.injury_date == injury_data["injury_date"],
            )
        )
        if result.scalar_one_or_none():
            logger.info(f"Injury already exists: {injury_data['injury_type']} for athlete {injury_data['athlete_idx']}")
            continue

        injury = InjuryHistory(
            athlete_id=athlete.id,
            injury_type=injury_data["injury_type"],
            body_part=injury_data["body_part"],
            injury_date=injury_data["injury_date"],
            recovery_date=injury_data["recovery_date"],
            severity=injury_data["severity"],
            notes=injury_data["notes"],
        )
        db.add(injury)
        logger.info(f"Created injury: {injury_data['injury_type']}")

    await db.flush()


async def seed_training_loads(db: AsyncSession, athletes: list[Athlete]) -> None:
    """Create demo training load entries if they don't exist."""
    load_data = [
        # Athlete 0 — basketball
        {"athlete_idx": 0, "entry_date": date(2025, 7, 1), "session_type": "strength", "duration_minutes": 60, "rpe": 7, "notes": "Upper body focus"},
        {"athlete_idx": 0, "entry_date": date(2025, 7, 2), "session_type": "practice", "duration_minutes": 120, "rpe": 8, "notes": "Full team practice"},
        {"athlete_idx": 0, "entry_date": date(2025, 7, 3), "session_type": "conditioning", "duration_minutes": 45, "rpe": 6, "notes": "Light conditioning"},
        # Athlete 1 — soccer
        {"athlete_idx": 1, "entry_date": date(2025, 7, 1), "session_type": "practice", "duration_minutes": 90, "rpe": 7, "notes": "Tactical session"},
        {"athlete_idx": 1, "entry_date": date(2025, 7, 2), "session_type": "match", "duration_minutes": 90, "rpe": 9, "notes": "Full match"},
        # Athlete 2 — track
        {"athlete_idx": 2, "entry_date": date(2025, 7, 1), "session_type": "track workout", "duration_minutes": 75, "rpe": 8, "notes": "200m repeats x 8"},
        {"athlete_idx": 2, "entry_date": date(2025, 7, 3), "session_type": "recovery", "duration_minutes": 30, "rpe": 3, "notes": "Easy jog + stretching"},
    ]

    for entry_data in load_data:
        athlete = athletes[entry_data["athlete_idx"]]
        result = await db.execute(
            select(TrainingLoadEntry).where(
                TrainingLoadEntry.athlete_id == athlete.id,
                TrainingLoadEntry.entry_date == entry_data["entry_date"],
                TrainingLoadEntry.session_type == entry_data["session_type"],
            )
        )
        if result.scalar_one_or_none():
            logger.info(f"Training load already exists: {entry_data['session_type']} on {entry_data['entry_date']}")
            continue

        entry = TrainingLoadEntry(
            athlete_id=athlete.id,
            entry_date=entry_data["entry_date"],
            session_type=entry_data["session_type"],
            duration_minutes=entry_data["duration_minutes"],
            rpe=entry_data["rpe"],
            notes=entry_data["notes"],
        )
        db.add(entry)
        logger.info(f"Created training load: {entry_data['session_type']} on {entry_data['entry_date']}")

    await db.flush()


async def run_seed():
    """Main seed function — creates all demo data."""
    logger.info("=" * 60)
    logger.info("SEEDING DATABASE")
    logger.info("=" * 60)

    async with async_session_factory() as db:
        try:
            users = await seed_users(db)
            athletes = await seed_athletes(db, users)
            await seed_injury_history(db, athletes)
            await seed_training_loads(db, athletes)
            await db.commit()
            logger.info("=" * 60)
            logger.info("SEEDING COMPLETE")
            logger.info("=" * 60)
        except Exception as e:
            await db.rollback()
            logger.error(f"Seeding failed: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(run_seed())
