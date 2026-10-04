"""Population baselines — computed over VIDEOS, one feature vector per video.

`movement_baselines` rows summarise, for each video-level feature (e.g.
`knee_flexion_angle_left.p95`), the mean/std across completed videos of a movement type, with
`sample_size` = number of VIDEOS. (Previously the table pooled every per-frame value, so a
single clip counted as hundreds of samples and the 10-sample floor meant nothing.)

The scoring path computes its baseline directly from the same features at request time, so
these rows are a reporting/inspection aid, not a cache the score depends on.
"""

import logging

import numpy as np
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.modules.risk_scoring.features import fetch_all_video_features, fetch_video_athletes
from app.modules.risk_scoring.models import MovementBaseline

logger = logging.getLogger(__name__)


def min_baseline_videos() -> int:
    return settings.min_baseline_videos


def min_baseline_athletes() -> int:
    return settings.min_baseline_athletes


# Backwards-compatible name for callers that import the constant.
MIN_BASELINE_SAMPLES = settings.min_baseline_videos


async def recompute_movement_baselines(db: AsyncSession, movement_type: str) -> dict:
    per_video = await fetch_all_video_features(db, movement_type)
    athlete_of = await fetch_video_athletes(db, movement_type)
    names = sorted({k for feats in per_video.values() for k in feats})
    need = min_baseline_videos()
    need_athletes = min_baseline_athletes()

    await db.execute(
        delete(MovementBaseline).where(
            MovementBaseline.athlete_id.is_(None), MovementBaseline.movement_type == movement_type
        )
    )
    details = []
    for name in names:
        with_name = [(vid, f[name]) for vid, f in per_video.items() if name in f]
        with_name = [(vid, v) for vid, v in with_name if np.isfinite(v)]
        vals = np.array([v for _, v in with_name], dtype=float)
        n = len(vals)
        n_athletes = len({athlete_of.get(vid) for vid, _ in with_name})
        sufficient = n >= need and n_athletes >= need_athletes
        # NULL means "we don't know" — never store a plausible-looking fabricated 0.0 +/- 0.0.
        mean, std = (float(vals.mean()), float(vals.std())) if sufficient else (None, None)
        db.add(MovementBaseline(movement_type=movement_type, metric_name=name, mean_value=mean, std_dev=std,
                                sample_size=n, video_count=n, athlete_count=n_athletes))
        details.append({"feature": name, "sample_size": n, "athletes": n_athletes, "sufficient": sufficient,
                        "mean": round(mean, 2) if sufficient else None,
                        "std": round(std, 2) if sufficient else None})
    await db.commit()
    return {"movement_type": movement_type, "videos": len(per_video), "need": need,
            "need_athletes": need_athletes, "features": details}


RECOMPUTE_COOLDOWN_SECONDS = 60


async def recompute_baseline_debounced(db: AsyncSession, redis, movement_type: str) -> dict:
    lock_key = f"baseline_recompute:{movement_type}"
    acquired = await redis.set(lock_key, "1", nx=True, ex=RECOMPUTE_COOLDOWN_SECONDS)
    if not acquired:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=429,
            detail={"error": {"code": "RATE_LIMITED", "message": f"Baseline for '{movement_type}' was recomputed recently — try again shortly"}},
        )
    return await recompute_movement_baselines(db, movement_type)
