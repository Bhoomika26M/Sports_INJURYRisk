"""Movement anomaly detection — unsupervised, baseline-relative, no injury labels.

This is the honest ML component (docs/ARCHITECTURE.md §1): it compares a video to the
population of *other* videos of the same movement type. It says "this movement pattern is
unusual", never "this athlete will be injured".

Calibration note (why the score is tail-based)
----------------------------------------------
The percentile rank of a sample against its own baseline is uniformly distributed for a
perfectly normal sample — its expected value is 50, not 0. Feeding that straight into a
risk score made every normal video look "moderate". We therefore only score the *tail*:
a video must be more unusual than ANOMALY_FLOOR_PCT of the baseline before it adds
anything, reaching the maximum at the extreme. For a normal video the expected
deviation score is ~5/100 (verified by simulation in tests/test_anomaly_detection.py).
"""

from __future__ import annotations

import numpy as np
from sklearn.ensemble import IsolationForest

from app.modules.risk_scoring.features import MEASUREMENT_NOISE_DEG, split_feature_key


class InsufficientBaselineError(Exception):
    def __init__(self, metric_name: str, have: int, need: int):
        self.metric_name, self.have, self.need = metric_name, have, need
        super().__init__(f"Need {need} baseline samples for '{metric_name}', have {have}")


# Only videos more unusual than this share of the baseline start to score.
ANOMALY_FLOOR_PCT = 90.0
# Percentile at/above which a video is recorded as a flagged anomaly.
ANOMALY_FLAG_PCT = 95.0
# |robust z| at/above which an individual feature is called out as deviating.
FEATURE_Z_FLAG = 2.0
# Scale floor for robust z (deg). Half the sagittal tracking RMSE: below this a
# "deviation" is indistinguishable from pose-estimation noise.
Z_SCALE_FLOOR = MEASUREMENT_NOISE_DEG / 2


CROSSFIT_FOLDS = 5


def compute_anomaly_scores(
    sample_vectors: np.ndarray,
    baseline_vectors: np.ndarray,
    min_samples: int = 10,
    metric_name: str = "",
) -> list[float]:
    """Percentile-rank anomaly score per sample row, 0-100 (higher = more unusual).

    = % of the baseline that is MORE normal than the sample (docs/DECISIONS.md, 2026-07-11),
    but cross-fitted: the baseline is split into folds, a forest is fit on all-but-one fold,
    and the sample is ranked against the HELD-OUT fold scored by that same forest. Ranking a
    sample against the very points the forest was trained on (the previous implementation)
    makes every fresh sample look more anomalous than it is, because training points are
    always favoured by the model that saw them. Held-out ranking is exchangeable under
    "sample comes from the baseline", so a normal video's percentile is ~uniform.
    """
    base = np.asarray(baseline_vectors, dtype=float)
    x = np.asarray(sample_vectors, dtype=float)
    n = len(base)
    if n < min_samples:
        raise InsufficientBaselineError(metric_name, n, min_samples)

    order = np.random.default_rng(42).permutation(n)
    folds = np.array_split(order, min(CROSSFIT_FOLDS, n))
    more_normal = np.zeros(len(x))
    for held_idx in folds:
        train_idx = np.setdiff1d(order, held_idx)
        model = IsolationForest(n_estimators=100, contamination="auto", random_state=42)
        model.fit(base[train_idx])
        held_scores = model.decision_function(base[held_idx])
        sample_scores = model.decision_function(x)
        more_normal += (held_scores[None, :] > sample_scores[:, None]).sum(axis=1)
    return [float(100 * m / n) for m in more_normal]


def robust_z(value: float, baseline_values: np.ndarray) -> float:
    """(value - median) / (1.4826 * MAD), with the scale floored at tracking noise."""
    med = float(np.median(baseline_values))
    mad = float(np.median(np.abs(baseline_values - med)))
    scale = max(1.4826 * mad, Z_SCALE_FLOOR)
    return (value - med) / scale


# Isolation Forest isolates points by random splits *inside* the training range, so a
# point far BEYOND that range is not reliably scored as more anomalous than one at its
# edge. A robust per-feature z-score has no such blind spot, so the two are blended:
# a video is as deviant as the worse of (multivariate pattern, single-feature extremity).
# 3 robust-sigma is the classical outlier cut; 5 maps to the maximum.
Z_TAIL_START, Z_TAIL_FULL = 3.0, 5.0


def z_tail_score(max_abs_z: float, n_baseline: int) -> float:
    """Extremity tail score. Thresholds widen by (1 + 4/n): a robust z built from a handful
    of baseline videos is noisy, and across ~10 features some will exceed 3 sigma by chance.
    Simulated (10 features, Gaussian): at n=10 this cuts normal-video false positives
    (score>50) from 16% to 4% while still catching 83% of 4-sigma deviations; at n=30,
    1% false positives vs 91% detection."""
    infl = 1.0 + 4.0 / max(n_baseline, 1)
    start, full = Z_TAIL_START * infl, Z_TAIL_FULL * infl
    return float(np.clip((max_abs_z - start) / (full - start), 0.0, 1.0) * 100.0)


def tail_score(percentile: float) -> float:
    """Map percentile rank -> 0-100 risk contribution, counting only the tail."""
    span = 100.0 - ANOMALY_FLOOR_PCT
    return float(np.clip((percentile - ANOMALY_FLOOR_PCT) / span, 0.0, 1.0) * 100.0)


def assess_video_anomaly(
    sample: dict[str, float],
    baseline: list[dict[str, float]],
    min_videos: int,
) -> dict:
    """Multivariate Isolation Forest on video-level features + per-feature explanation.

    `sample`   {feature_key: value} for the video being scored.
    `baseline` one {feature_key: value} per OTHER completed video (same keys as sample).
    """
    features = sorted(sample.keys())
    if len(baseline) < min_videos:
        raise InsufficientBaselineError("video-level features", len(baseline), min_videos)

    base = np.array([[b[f] for f in features] for b in baseline], dtype=float)
    # CANONICAL ROW ORDER. The baseline arrives from a GROUP BY with no ORDER BY, so its order follows the
    # query plan. The forest and its cross-fit folds depend on row order, so the same data could score 0 or 100
    # for a perfectly normal video depending only on how Postgres happened to return the rows (measured: 2 of 8
    # simulated populations flipped; it also made a test pass alone and fail in a full run). Sorting makes the
    # score a pure function of the data.
    base = base[np.lexsort(base.T[::-1])]
    x = np.array([[sample[f] for f in features]], dtype=float)

    percentile = compute_anomaly_scores(x, base, min_samples=min_videos)[0]

    explained = []
    for i, f in enumerate(features):
        z = robust_z(sample[f], base[:, i])
        metric, stat = split_feature_key(f)
        explained.append({
            "feature": f,
            "metric": metric,
            "stat": stat,
            "value": round(float(sample[f]), 1),
            "baseline_median": round(float(np.median(base[:, i])), 1),
            "z": round(float(z), 2),
            "direction": "above" if z > 0 else "below",
            "flagged": abs(z) >= FEATURE_Z_FLAG,
        })
    explained.sort(key=lambda e: abs(e["z"]), reverse=True)

    max_abs_z = max(abs(e["z"]) for e in explained)
    if_score = tail_score(percentile)
    z_score = z_tail_score(max_abs_z, len(baseline))
    return {
        "percentile": round(percentile, 1),
        "isolation_forest_score": round(if_score, 1),
        "extremity_score": round(z_score, 1),
        "deviation_score": round(max(if_score, z_score), 1),
        "flagged": percentile >= ANOMALY_FLAG_PCT or z_score >= 100.0,
        "n_baseline": len(baseline),
        "features": explained,
    }
