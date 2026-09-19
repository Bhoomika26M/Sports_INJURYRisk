import numpy as np
import logging
from fastapi import HTTPException
from sqlalchemy import select, delete

logger = logging.getLogger(__name__)

from app.modules.videos.models import Video, VideoProcessingStatus, BiomechanicalMetric
from app.modules.risk_scoring.models import MovementBaseline

MIN_BASELINE_SAMPLES = 10

async def upsert_baseline(db, movement_type: str, metric_name: str, mean_value: float, std_dev: float, sample_size: int):
    await db.execute(
        delete(MovementBaseline)
        .where(MovementBaseline.athlete_id.is_(None))
        .where(MovementBaseline.movement_type == movement_type)
        .where(MovementBaseline.metric_name == metric_name)
    )
    db.add(MovementBaseline(
        movement_type=movement_type,
        metric_name=metric_name,
        mean_value=mean_value,
        std_dev=std_dev,
        sample_size=sample_size
    ))
    await db.commit()

async def recompute_baseline(db, movement_type: str, metric_name: str) -> dict:
    """Population-level baseline (athlete_id NULL) from all validated-confidence metrics
    for this movement_type across every completed video. Upserts into movement_baselines."""
    stmt = (
        select(BiomechanicalMetric.metric_value)
        .join(Video, Video.id == BiomechanicalMetric.video_id)
        .where(
            Video.movement_type == movement_type,
            Video.processing_status == VideoProcessingStatus.completed,
            BiomechanicalMetric.metric_name == metric_name,
            BiomechanicalMetric.confidence == 'validated',
        )
    )
    raw_values = np.array((await db.scalars(stmt)).all(), dtype=float)
    values = raw_values[np.isfinite(raw_values)]
    dropped = len(raw_values) - len(values)
    if dropped:
        logger.warning(f"recompute_baseline({movement_type}, {metric_name}): dropped {dropped} non-finite value(s)")

    sample_size = len(values)

    if sample_size < MIN_BASELINE_SAMPLES:
        mean_value, std_dev = 0.0, 0.0
    else:
        mean_value, std_dev = float(values.mean()), float(values.std())

    await upsert_baseline(db, movement_type, metric_name, mean_value, std_dev, sample_size)
    return {"movement_type": movement_type, "metric_name": metric_name, "sample_size": sample_size, "sufficient": sample_size >= MIN_BASELINE_SAMPLES, "dropped_non_finite": dropped}

RECOMPUTE_COOLDOWN_SECONDS = 60

async def recompute_baseline_debounced(db, redis, movement_type: str, metric_name: str) -> dict:
    lock_key = f"baseline_recompute:{movement_type}:{metric_name}"
    acquired = await redis.set(lock_key, "1", nx=True, ex=RECOMPUTE_COOLDOWN_SECONDS)
    if not acquired:
        raise HTTPException(
            status_code=429,
            detail={"error": {"code": "RATE_LIMITED", "message": f"Baseline for '{movement_type}' was recomputed recently — try again shortly"}},
        )
    return await recompute_baseline(db, movement_type, metric_name)
