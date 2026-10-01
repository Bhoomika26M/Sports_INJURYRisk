"""Anomaly detection — Isolation Forest defines "normal"; severity is measured from it.

WHAT THE SCORE MEANS (per frame, 0-100)
    0    the frame lies inside the baseline's own normal envelope
    50   the frame lies ``HALF_SATURATION_SIGMA`` (2.0) baseline robust-SDs outside it
    ->100 the frame lies far outside it (never reaches 100)

FORMULA (for one frame ``x``; baseline ``B`` is the leave-one-video-out population)
    1. Fit ``IsolationForest(random_state=42)`` on ``B``; ``s(.)`` = its decision_function
       (higher = more normal).
    2. Knee ``k`` = the 5th percentile of ``s`` over ``B`` itself. The *core* is every
       baseline frame with ``s >= k`` -- the 95% most-normal baseline frames.
    3. If ``s(x) >= k``: score = 0.
       Otherwise ``d`` = Euclidean distance from ``x`` to the nearest core frame, in units
       of the baseline's robust SD per feature (``1.4826 * MAD``; falls back to the plain SD
       when MAD is 0), and
           score = 100 * (1 - 2 ** (-d / 2.0))
       Monotone in ``d``, exactly 0 at the envelope edge, 50 at ``d = 2`` SD, 75 at 4 SD,
       87.5 at 6 SD, bounded below 100.

WHY NOT JUST RESCALE THE ISOLATION FOREST OUTPUT  (measured, see DECISIONS.md)
    * The old percentile-rank-against-baseline has no zero anchor: the baseline's own median
      frame is at the 50th percentile by construction, so an average athlete scored ~37/70.
    * Isolation Forest saturates: any point outside the training range is isolated at the same
      depth in every tree, so its decision score is the SAME for +4 SD and +8 SD (n=426:
      -0.258 vs -0.275). No transform of that output can separate "clear" from "extreme".
      The forest therefore decides *whether* a frame is outside the envelope (and copes with
      multi-modal baselines such as a squat's standing/bottom modes); geometry decides *how far*.

DIRECTION: unchanged and correct -- higher score = more anomalous. Do not invert it.

LIMITS (honest)
    * By construction ~5% of in-distribution frames register a (small) non-zero score.
    * A multi-modal baseline has a wide robust SD (it spans every mode), so distances are
      measured in units of the movement's whole range, which is lenient for within-mode
      deviations. Conservative by design; revisit with real data.
    * This is a pattern-deviation signal. It is NOT an injury probability (AGENTS.md law).
"""

import hashlib
import time
from dataclasses import dataclass

import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.neighbors import KDTree

from app.modules.risk_scoring.constants import (
    HALF_SATURATION_SIGMA,
    MAD_TO_SIGMA,
    MIN_BASELINE_FRAMES,
    NORMAL_ENVELOPE_QUANTILE,
)

_MIN_SCALE = 1e-9


class InsufficientBaselineError(Exception):
    """Raised when the baseline cannot support a score. ``unit`` names what ``have``/``need`` count."""

    def __init__(self, metric_name: str, have: int, need: int, unit: str = "frames"):
        self.metric_name, self.have, self.need, self.unit = metric_name, have, need, unit
        super().__init__(f"Need {need} baseline {unit} for '{metric_name}', have {have}")


@dataclass(frozen=True)
class _FittedBaseline:
    model: IsolationForest
    knee: float               # 5th percentile of the baseline's own decision scores
    core_tree: KDTree         # the 95% most-normal baseline frames, in scaled space
    scale: np.ndarray         # per-feature robust SD of the baseline
    n_baseline_frames: int


_model_cache: dict[str, tuple[float, _FittedBaseline]] = {}
MODEL_CACHE_TTL_SECONDS = 300
MODEL_CACHE_MAX_ENTRIES = 32


def _fingerprint(arr: np.ndarray) -> str:
    """Content hash, so a changed baseline can never be served a stale fitted model."""
    data = np.ascontiguousarray(arr, dtype=np.float64)
    h = hashlib.blake2b(digest_size=16)
    h.update(str(data.shape).encode())
    h.update(data.tobytes())
    return h.hexdigest()


def _robust_scale(baseline: np.ndarray) -> np.ndarray:
    median = np.median(baseline, axis=0)
    scale = MAD_TO_SIGMA * np.median(np.abs(baseline - median), axis=0)
    fallback = baseline.std(axis=0)
    scale = np.where(scale < _MIN_SCALE, fallback, scale)
    return np.maximum(scale, _MIN_SCALE)


def _fit_baseline(baseline: np.ndarray) -> _FittedBaseline:
    model = IsolationForest(contamination="auto", random_state=42)
    model.fit(baseline)
    baseline_scores = model.decision_function(baseline)
    knee = float(np.quantile(baseline_scores, NORMAL_ENVELOPE_QUANTILE))
    scale = _robust_scale(baseline)
    core = baseline[baseline_scores >= knee]
    return _FittedBaseline(
        model=model,
        knee=knee,
        core_tree=KDTree(core / scale),
        scale=scale,
        n_baseline_frames=len(baseline),
    )


def _get_or_fit(cache_key: str, baseline: np.ndarray) -> _FittedBaseline:
    now = time.time()
    full_key = f"{cache_key}:{_fingerprint(baseline)}"
    cached = _model_cache.get(full_key)
    if cached and (now - cached[0]) < MODEL_CACHE_TTL_SECONDS:
        return cached[1]
    fitted = _fit_baseline(baseline)
    for key in [k for k, (ts, _) in _model_cache.items() if now - ts >= MODEL_CACHE_TTL_SECONDS]:
        _model_cache.pop(key, None)
    while len(_model_cache) >= MODEL_CACHE_MAX_ENTRIES:
        _model_cache.pop(min(_model_cache, key=lambda k: _model_cache[k][0]), None)
    _model_cache[full_key] = (now, fitted)
    return fitted


def invalidate_model_cache(movement_type: str) -> None:
    """Call after a successful baseline recompute so a stale fitted model isn't reused."""
    for key in list(_model_cache.keys()):
        if key.startswith(f"{movement_type}:"):
            _model_cache.pop(key, None)


def severity_from_distance(distance_sd: np.ndarray | float) -> np.ndarray:
    """Monotone, bounded map from distance-outside-the-envelope (baseline robust SDs) to 0-100."""
    d = np.maximum(np.asarray(distance_sd, dtype=float), 0.0)
    return 100.0 * (1.0 - np.power(2.0, -d / HALF_SATURATION_SIGMA))


def compute_anomaly_scores(
    sample_vectors: np.ndarray,
    baseline_vectors: np.ndarray,
    min_baseline_frames: int = MIN_BASELINE_FRAMES,
    cache_key: str | None = None,
    metric_name: str = "",
) -> list[float]:
    """
    sample_vectors: this video's per-frame validated metric values, shape (n_frames, n_features)
    baseline_vectors: the leave-one-video-out baseline for this movement_type, (n_baseline, n_features)
    Returns one anomaly score per sample frame, 0-100 (see module docstring for the definition).

    ``min_baseline_frames`` is only the ESTIMATOR floor (unit: frames). Whether the baseline is a
    real population -- distinct videos and athletes -- is decided upstream in baselines.py.
    """
    if len(baseline_vectors) < min_baseline_frames:
        raise InsufficientBaselineError(metric_name, len(baseline_vectors), min_baseline_frames, unit="frames")
    if not (np.isfinite(baseline_vectors).all() and np.isfinite(sample_vectors).all()):
        raise ValueError("compute_anomaly_scores requires finite inputs; filter NaN/inf upstream")
    if len(sample_vectors) == 0:
        return []

    fitted = _get_or_fit(cache_key, baseline_vectors) if cache_key else _fit_baseline(baseline_vectors)

    sample_scores = fitted.model.decision_function(sample_vectors)
    distance = np.zeros(len(sample_vectors))
    outside = sample_scores < fitted.knee
    if outside.any():
        dist, _ = fitted.core_tree.query(sample_vectors[outside] / fitted.scale, k=1)
        distance[outside] = dist[:, 0]
    return [float(v) for v in severity_from_distance(distance)]
