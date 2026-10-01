"""DB factories for baseline / scoring tests. Real rows in real Postgres, no mocks."""

from datetime import date

import numpy as np
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.modules.athletes.models import Athlete
from app.modules.users.models import User, UserRole
from app.modules.video.models import BiomechanicalMetric, Video, VideoProcessingStatus


async def make_user(db: AsyncSession, email: str, role: UserRole = UserRole.coach) -> User:
    user = User(email=email, password_hash=hash_password("testpassword123"), full_name=email.split("@")[0], role=role)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def make_athlete(db: AsyncSession, coach_id: str) -> Athlete:
    athlete = Athlete(coach_id=coach_id, sport_type="soccer", date_of_birth=date(2001, 5, 17))
    db.add(athlete)
    await db.commit()
    await db.refresh(athlete)
    return athlete


async def make_video(
    db: AsyncSession,
    athlete_id: str,
    uploaded_by: str,
    movement_type: str = "squatting",
    status: VideoProcessingStatus = VideoProcessingStatus.completed,
    metrics: dict[str, list[float]] | None = None,
    confidence: str = "validated",
) -> Video:
    """One video with ``metrics`` = {metric_name: [value per frame]} stored as BiomechanicalMetric rows."""
    video = Video(
        athlete_id=athlete_id, uploaded_by=uploaded_by, movement_type=movement_type,
        storage_key=f"test_{np.random.default_rng().integers(1 << 30)}.mp4",
        camera_view="sagittal", processing_status=status,
    )
    db.add(video)
    await db.commit()
    await db.refresh(video)
    if metrics:
        rows = [
            {
                "video_id": video.id, "frame_number": i, "metric_name": name, "metric_value": round(float(v), 3),
                "plane": "sagittal", "confidence": confidence,
            }
            for name, values in metrics.items() for i, v in enumerate(values)
        ]
        await db.execute(insert(BiomechanicalMetric), rows)
        await db.commit()
    return video


def normal_frames(rng: np.random.Generator, n: int, mu: float = 90.0, sd: float = 8.0) -> list[float]:
    return [float(v) for v in rng.normal(mu, sd, size=n)]


async def make_population(
    db: AsyncSession, *, videos: int, athletes: int, frames: int = 150, movement_type: str = "squatting",
    metric_names: tuple[str, ...] = ("knee_flexion_angle_left", "knee_flexion_angle_right"), seed: int = 0,
) -> tuple[User, list[Athlete], list[Video]]:
    """``videos`` completed videos spread round-robin over ``athletes`` distinct athletes."""
    rng = np.random.default_rng(seed)
    coach = await make_user(db, f"coach{seed}@pop.example.com")
    people = [await make_athlete(db, coach.id) for _ in range(athletes)]
    made = []
    for i in range(videos):
        made.append(await make_video(
            db, people[i % athletes].id, coach.id, movement_type,
            metrics={m: normal_frames(rng, frames) for m in metric_names},
        ))
    return coach, people, made
