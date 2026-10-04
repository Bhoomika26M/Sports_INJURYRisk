"""Video-level feature extraction — the unit the AI engine reasons about.

Why VIDEO-level and not per-frame
---------------------------------
A frame's angle value only says where in the movement cycle that frame happened to
fall. A shallow squat and a deep squat share almost every per-frame value (both pass
through 5-25 degrees of knee flexion), so a per-frame pooled baseline cannot tell them
apart — and worse, one video already produces hundreds of "samples", which used to
satisfy the 10-sample floor on its own, so a video was scored against itself.

The unit that carries information about technique is the *extremes a whole video
reaches*: peak (95th percentile) and trough (5th percentile) of each validated metric.
Percentiles rather than max/min so a single-frame landmark glitch cannot define the
"peak". We deliberately do NOT use mean/std across frames: they depend on how long the
athlete stood still at the start/end of the clip, i.e. on clip editing, not technique.

Everything here is population-agnostic feature math. Nothing in this module makes a
medical claim — see docs/SCIENCE_CONSTRAINTS.md.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from sqlalchemy import Float, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.video.models import BiomechanicalMetric, Video, VideoProcessingStatus

# Feature statistics per validated metric.
FEATURE_STATS = {"p95": 0.95, "p05": 0.05}

# A metric needs at least this many frames in a video before its extremes mean anything.
MIN_FRAMES_FOR_FEATURE = 15

# Shared constants and pure movement math live in the biomechanics layer (see there).
from app.modules.biomechanics.movement_analysis import (  # noqa: E402,F401  (re-exported)
    MEASUREMENT_NOISE_DEG,
    MIN_MEANINGFUL_RANGE_DEG,
    MIN_REPS_FOR_DRIFT,
    analyze_reps,
    detect_reps,
    movement_dynamics,
    primary_signal,
)

def feature_key(metric_name: str, stat: str) -> str:
    return f"{metric_name}.{stat}"


def split_feature_key(key: str) -> tuple[str, str]:
    metric, _, stat = key.rpartition(".")
    return metric, stat


# --------------------------------------------------------------------------- #
# Database access
# --------------------------------------------------------------------------- #

def _feature_select():
    value = cast(BiomechanicalMetric.metric_value, Float)
    return (
        select(
            BiomechanicalMetric.video_id,
            Video.athlete_id,
            BiomechanicalMetric.metric_name,
            func.count().label("n"),
            *[
                func.percentile_cont(q).within_group(value).label(stat)
                for stat, q in FEATURE_STATS.items()
            ],
        )
        .join(Video, Video.id == BiomechanicalMetric.video_id)
        .where(
            BiomechanicalMetric.confidence == "validated",
            # excludes NaN/inf that Postgres NUMERIC can store (NaN compares greater than everything)
            value.between(-1e6, 1e6),
        )
        .group_by(BiomechanicalMetric.video_id, Video.athlete_id, BiomechanicalMetric.metric_name)
    )


def _baseline_select():
    """Feature rows eligible to be part of a POPULATION baseline.

    Videos carrying a ``coverage_caveat`` (several people in frame, or the athlete measured on too few
    frames) are excluded: their numbers may mix identities or rest on a sliver of the clip, and one such
    video would silently widen the "normal" envelope everyone else is judged against. They can still be
    scored themselves — only the reference population is filtered.
    """
    return _feature_select().where(Video.coverage_caveat.is_(None))


def _rows_to_features(rows) -> dict[str, dict[str, float]]:
    """{video_id: {feature_key: value}}, dropping metrics with too few frames."""
    out: dict[str, dict[str, float]] = {}
    for row in rows:
        if row.n < MIN_FRAMES_FOR_FEATURE:
            continue
        feats = out.setdefault(str(row.video_id), {})
        for stat in FEATURE_STATS:
            feats[feature_key(row.metric_name, stat)] = float(getattr(row, stat))
    return out


async def fetch_video_features(db: AsyncSession, video_id: str) -> dict[str, float]:
    stmt = _feature_select().where(BiomechanicalMetric.video_id == video_id)
    return _rows_to_features((await db.execute(stmt)).all()).get(str(video_id), {})


def drop_unreliable_side_features(
    features: dict[str, float], usable_pct: dict | None, floor: float
) -> tuple[dict[str, float], list[str]]:
    """Remove features computed from a leg that was not reliably visible.

    The pose pipeline already drops occluded frames, but a leg seen in only a sliver of the clip still
    yields percentile features from those few frames — and in a side-on view the far leg is routinely
    hidden behind the near one. Comparing such numbers to a population produced confident "anomalies"
    that were really occlusion (measured on real footage: a clip with the left leg visible in 13.5% of
    frames scored 63.6 "high" off three left-leg angles). Same rule ``score_asymmetry`` already applies.

    Returns (kept_features, sides_dropped). Features are named ``<metric>_<left|right>.<stat>``.
    """
    usable = usable_pct or {}
    blind = [s for s in ("left", "right") if usable.get(f"{s}_leg", 100.0) < floor]
    if not blind:
        return features, []
    kept = {k: v for k, v in features.items() if not any(k.split(".")[0].endswith(f"_{s}") for s in blind)}
    return kept, blind


@dataclass(frozen=True)
class BaselineSet:
    """The population a video is compared against, with what it is actually made of."""

    vectors: list[dict[str, float]]   # one complete feature vector per baseline VIDEO
    excluded_incomplete: int          # videos dropped for lacking one of the required features
    athletes: int                     # distinct athletes behind `vectors`

    @property
    def videos(self) -> int:
        return len(self.vectors)


async def fetch_baseline_set(
    db: AsyncSession, movement_type: str, exclude_video_id: str, required: list[str]
) -> BaselineSet:
    """Feature vectors of OTHER completed videos of this movement type.

    The scored video is always excluded — it must never be part of its own baseline. Athletes are
    counted over the videos that actually made it into the baseline: ten clips of ONE athlete is
    that athlete's personal envelope, not a population, so callers gate on this as well as on videos.
    """
    stmt = _baseline_select().where(
        Video.movement_type == movement_type,
        Video.processing_status == VideoProcessingStatus.completed,
        Video.id != exclude_video_id,
    )
    rows = (await db.execute(stmt)).all()
    athlete_of = {str(r.video_id): str(r.athlete_id) for r in rows}
    per_video = _rows_to_features(rows)
    complete, dropped, athletes = [], 0, set()
    for vid, feats in per_video.items():
        if all(k in feats for k in required):
            complete.append({k: feats[k] for k in required})
            athletes.add(athlete_of[vid])
        else:
            dropped += 1
    return BaselineSet(complete, dropped, len(athletes))


async def fetch_baseline_features(
    db: AsyncSession, movement_type: str, exclude_video_id: str, required: list[str]
) -> tuple[list[dict[str, float]], int]:
    """(complete_vectors, n_dropped_incomplete) — see ``fetch_baseline_set`` for the athlete-aware form."""
    b = await fetch_baseline_set(db, movement_type, exclude_video_id, required)
    return b.vectors, b.excluded_incomplete


async def fetch_video_athletes(db: AsyncSession, movement_type: str) -> dict[str, str]:
    """{video_id: athlete_id} for every completed video of this movement type."""
    stmt = _baseline_select().where(
        Video.movement_type == movement_type,
        Video.processing_status == VideoProcessingStatus.completed,
    )
    return {str(r.video_id): str(r.athlete_id) for r in (await db.execute(stmt)).all()}


async def fetch_all_video_features(db: AsyncSession, movement_type: str) -> dict[str, dict[str, float]]:
    """{video_id: {feature_key: value}} for every completed video of this movement type."""
    stmt = _baseline_select().where(
        Video.movement_type == movement_type,
        Video.processing_status == VideoProcessingStatus.completed,
    )
    return _rows_to_features((await db.execute(stmt)).all())


async def fetch_qualitative_extremes(db: AsyncSession, video_id: str) -> dict[str, float]:
    """95th percentile of each QUALITATIVE metric (e.g. knee valgus deviation %).

    Qualitative metrics never enter baselines or anomaly scoring — they are visual
    flags only (SCIENCE_CONSTRAINTS.md) — but the ACL category surfaces them as flags.
    """
    value = cast(BiomechanicalMetric.metric_value, Float)
    stmt = (
        select(
            BiomechanicalMetric.metric_name,
            func.count().label("n"),
            func.percentile_cont(0.95).within_group(value).label("p95"),
        )
        .where(
            BiomechanicalMetric.video_id == video_id,
            BiomechanicalMetric.confidence == "qualitative",
            value.between(-1e6, 1e6),
        )
        .group_by(BiomechanicalMetric.metric_name)
    )
    return {
        r.metric_name: float(r.p95)
        for r in (await db.execute(stmt)).all()
        if r.n >= MIN_FRAMES_FOR_FEATURE
    }


async def fetch_metric_series(db: AsyncSession, video_id: str) -> dict[str, np.ndarray]:
    """Per-frame validated series {metric_name: values ordered by frame} for rep analysis."""
    value = cast(BiomechanicalMetric.metric_value, Float)
    stmt = (
        select(BiomechanicalMetric.metric_name, BiomechanicalMetric.frame_number, value.label("v"))
        .where(
            BiomechanicalMetric.video_id == video_id,
            BiomechanicalMetric.confidence == "validated",
            value.between(-1e6, 1e6),
        )
        .order_by(BiomechanicalMetric.frame_number)
    )
    series: dict[str, list[tuple[int, float]]] = {}
    for name, frame, v in (await db.execute(stmt)).all():
        series.setdefault(name, []).append((frame, float(v)))
    return {name: _dense(pairs) for name, pairs in series.items()}


def _dense(pairs: list[tuple[int, float]]) -> np.ndarray:
    """Frames where the pose was lost leave gaps; linearly interpolate across them."""
    frames = np.array([p[0] for p in pairs])
    vals = np.array([p[1] for p in pairs])
    if len(frames) < 2:
        return vals
    grid = np.arange(frames.min(), frames.max() + 1)
    return np.interp(grid, frames, vals)
