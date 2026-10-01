"""Baseline computation — population-level, leave-one-video-out, sufficiency by videos and athletes.

Two rules this module enforces structurally (docs/DECISIONS.md, 2026-09-30):

1. A video is never scored against a baseline that contains itself. ``fetch_baseline`` has a
   REQUIRED keyword argument ``exclude_video_id``; there is no default to forget. ``None`` is a
   deliberate, explicit statement that no video is under evaluation (the stored, descriptive
   population baseline) and must never be used to score a member video.
2. "Enough data" is counted in distinct videos and athletes, never in frame rows. One 7-second
   clip produces hundreds of rows; it is still one video of one person.
"""

import logging
from dataclasses import dataclass

import numpy as np
from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.risk_scoring.constants import (
    MIN_BASELINE_ATHLETES,
    MIN_BASELINE_FRAMES,
    MIN_BASELINE_VIDEOS,
)
from app.modules.risk_scoring.models import MovementBaseline
from app.modules.video.models import BiomechanicalMetric, Video, VideoProcessingStatus

logger = logging.getLogger(__name__)

# (unit, need) in the order they are reported when more than one floor is unmet.
SUFFICIENCY_FLOORS: tuple[tuple[str, int], ...] = (
    ("videos", MIN_BASELINE_VIDEOS),
    ("athletes", MIN_BASELINE_ATHLETES),
    ("frames", MIN_BASELINE_FRAMES),
)


@dataclass(frozen=True)
class BaselineCoverage:
    """What a baseline is actually made of. ``frames`` counts rows for ONE metric."""

    videos: int
    athletes: int
    frames: int

    def have(self, unit: str) -> int:
        return getattr(self, unit)


@dataclass(frozen=True)
class BaselineSample:
    values: np.ndarray            # finite validated metric values, deterministic order
    coverage: BaselineCoverage
    dropped_non_finite: int


@dataclass(frozen=True)
class BaselineShortfall:
    """The first unmet floor, plus the full coverage so the caller can report honestly."""

    metric_name: str
    unit: str
    have: int
    need: int
    coverage: BaselineCoverage


def find_shortfall(metric_name: str, coverage: BaselineCoverage) -> BaselineShortfall | None:
    for unit, need in SUFFICIENCY_FLOORS:
        if coverage.have(unit) < need:
            return BaselineShortfall(metric_name, unit, coverage.have(unit), need, coverage)
    return None


def _baseline_rows_stmt(movement_type: str, metric_name: str, *, exclude_video_id: str | None) -> Select:
    stmt = (
        select(BiomechanicalMetric.metric_value, Video.id, Video.athlete_id)
        .join(Video, Video.id == BiomechanicalMetric.video_id)
        .where(
            Video.movement_type == movement_type,
            Video.processing_status == VideoProcessingStatus.completed,
            # Only clean footage defines "normal": partial-coverage and multi-person clips (identity or
            # coverage caveat) are scored for their own athlete but never contribute to a population baseline.
            Video.coverage_caveat.is_(None),
            BiomechanicalMetric.metric_name == metric_name,
            BiomechanicalMetric.confidence == "validated",
        )
    )
    if exclude_video_id is not None:
        stmt = stmt.where(Video.id != exclude_video_id)
    # Deterministic order: Isolation Forest is seeded, but it is still order-sensitive.
    return stmt.order_by(Video.id, BiomechanicalMetric.frame_number, BiomechanicalMetric.id)


def summarize_rows(rows: list[tuple]) -> BaselineSample:
    """Rows are (metric_value, video_id, athlete_id). Non-finite values are dropped BEFORE counting,
    so a video whose only rows are NaN does not count toward coverage."""
    if not rows:
        return BaselineSample(np.empty(0), BaselineCoverage(0, 0, 0), 0)
    raw = np.array([float(r[0]) for r in rows], dtype=float)
    keep = np.isfinite(raw)
    kept_rows = [r for r, k in zip(rows, keep) if k]
    coverage = BaselineCoverage(
        videos=len({r[1] for r in kept_rows}),
        athletes=len({r[2] for r in kept_rows}),
        frames=int(keep.sum()),
    )
    return BaselineSample(raw[keep], coverage, int((~keep).sum()))


async def fetch_baseline(
    db: AsyncSession, movement_type: str, metric_name: str, *, exclude_video_id: str | None
) -> BaselineSample:
    """Validated values for one metric across completed videos of ``movement_type``, EXCLUDING
    ``exclude_video_id``. Keyword-only and required on purpose -- see module docstring."""
    result = await db.execute(_baseline_rows_stmt(movement_type, metric_name, exclude_video_id=exclude_video_id))
    sample = summarize_rows([tuple(r) for r in result.all()])
    if sample.dropped_non_finite:
        logger.warning(
            "fetch_baseline(%s, %s): dropped %d non-finite value(s)",
            movement_type, metric_name, sample.dropped_non_finite,
        )
    return sample


async def upsert_baseline(
    db: AsyncSession,
    movement_type: str,
    metric_name: str,
    mean_value: float | None,
    std_dev: float | None,
    sample_size: int,
    video_count: int,
    athlete_count: int,
):
    """``mean_value``/``std_dev`` are NULL when the baseline is insufficient: NULL means "we don't
    know". A plausible-looking 0.0 +/- 0.0 would be read as a real number by every consumer."""
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
        sample_size=sample_size,
        video_count=video_count,
        athlete_count=athlete_count,
    ))
    await db.commit()


async def recompute_baseline(db: AsyncSession, movement_type: str, metric_name: str) -> dict:
    """Stored, DESCRIPTIVE population baseline (athlete_id NULL) over every completed video.

    Never used to score a member video -- scoring re-derives a leave-one-video-out baseline via
    ``fetch_baseline(..., exclude_video_id=<that video>)``.
    """
    sample = await fetch_baseline(db, movement_type, metric_name, exclude_video_id=None)
    shortfall = find_shortfall(metric_name, sample.coverage)

    if shortfall is None:
        mean_value, std_dev = float(sample.values.mean()), float(sample.values.std())
    else:
        mean_value, std_dev = None, None

    cov = sample.coverage
    await upsert_baseline(db, movement_type, metric_name, mean_value, std_dev, cov.frames, cov.videos, cov.athletes)
    return {
        "movement_type": movement_type,
        "metric_name": metric_name,
        "sufficient": shortfall is None,
        "sample_size": cov.frames,
        "sample_size_unit": "frames",
        "video_count": cov.videos,
        "athlete_count": cov.athletes,
        "unmet": None if shortfall is None else {"unit": shortfall.unit, "have": shortfall.have, "need": shortfall.need},
        "dropped_non_finite": sample.dropped_non_finite,
    }


RECOMPUTE_COOLDOWN_SECONDS = 60

async def recompute_baseline_debounced(db: AsyncSession, redis, movement_type: str, metric_name: str) -> dict:
    lock_key = f"baseline_recompute:{movement_type}:{metric_name}"
    acquired = await redis.set(lock_key, "1", nx=True, ex=RECOMPUTE_COOLDOWN_SECONDS)
    if not acquired:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=429,
            detail={"error": {"code": "RATE_LIMITED", "message": f"Baseline for '{movement_type}' was recomputed recently — try again shortly"}},
        )
    return await recompute_baseline(db, movement_type, metric_name)
