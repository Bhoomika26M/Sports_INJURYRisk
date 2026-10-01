"""Risk-scoring service — leave-one-video-out anomaly scoring for a single video."""

import logging
from dataclasses import dataclass

import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.risk_scoring.anomaly import InsufficientBaselineError, compute_anomaly_scores
from app.modules.risk_scoring.baselines import (
    BaselineCoverage,
    BaselineShortfall,
    fetch_baseline,
    SUFFICIENCY_FLOORS,
    find_shortfall,
)
from app.modules.risk_scoring.constants import MIN_BASELINE_FRAMES
from app.modules.risk_scoring.schemas import BaselineUnitCoverage, InsufficientBaselineResponse
from app.modules.video.models import BiomechanicalMetric, Video

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class VideoAnomaly:
    frame_scores: list[float]        # pooled across this video's validated metrics, 0-100 each
    baseline_videos: int             # distinct videos in the binding (smallest) per-metric baseline
    baseline_athletes: int


async def compute_video_anomaly(
    db: AsyncSession, video: Video, sample_metrics: list[BiomechanicalMetric]
) -> VideoAnomaly | BaselineShortfall:
    """Score ``video`` against a baseline that EXCLUDES ``video`` itself.

    Returns a ``BaselineShortfall`` (never a score) when any metric's baseline is not a real
    population: too few distinct videos, too few distinct athletes, or too few frames.
    """
    by_metric: dict[str, list[float]] = {}
    for m in sample_metrics:
        by_metric.setdefault(m.metric_name, []).append(float(m.metric_value))

    pooled: list[float] = []
    binding: BaselineCoverage | None = None

    for name in sorted(by_metric):
        baseline = await fetch_baseline(db, video.movement_type, name, exclude_video_id=video.id)
        shortfall = find_shortfall(name, baseline.coverage)
        if shortfall is not None:
            return shortfall

        sample = np.array(by_metric[name], dtype=float)
        sample = sample[np.isfinite(sample)]
        if sample.size == 0:
            continue
        try:
            scores = compute_anomaly_scores(
                sample.reshape(-1, 1),
                baseline.values.reshape(-1, 1),
                MIN_BASELINE_FRAMES,
                cache_key=f"{video.movement_type}:{name}:{video.id}",
                metric_name=name,
            )
        except InsufficientBaselineError as e:
            return BaselineShortfall(e.metric_name, e.unit, e.have, e.need, baseline.coverage)
        pooled.extend(scores)
        if binding is None or baseline.coverage.videos < binding.videos:
            binding = baseline.coverage

    assert binding is not None or not pooled
    return VideoAnomaly(
        frame_scores=pooled,
        baseline_videos=binding.videos if binding else 0,
        baseline_athletes=binding.athletes if binding else 0,
    )


def insufficient_baseline_payload(shortfall: BaselineShortfall) -> InsufficientBaselineResponse:
    cov = shortfall.coverage
    return InsufficientBaselineResponse(
        metric_name=shortfall.metric_name,
        unit=shortfall.unit,
        have=shortfall.have,
        need=shortfall.need,
        coverage={unit: BaselineUnitCoverage(have=cov.have(unit), need=need) for unit, need in SUFFICIENCY_FLOORS},
        message=(
            f"Not enough reference data to score this video: {shortfall.have} of {shortfall.need} "
            f"{shortfall.unit} for '{shortfall.metric_name}' (this video is never counted in its own baseline)."
        ),
    )
