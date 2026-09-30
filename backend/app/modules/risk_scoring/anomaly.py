"""Anomaly detection — Isolation Forest with percentile-rank rescaling."""

import time
import numpy as np
from sklearn.ensemble import IsolationForest


class InsufficientBaselineError(Exception):
    def __init__(self, metric_name: str, have: int, need: int):
        self.metric_name, self.have, self.need = metric_name, have, need
        super().__init__(f"Need {need} baseline samples for '{metric_name}', have {have}")


_model_cache: dict[str, tuple[float, IsolationForest, np.ndarray]] = {}
MODEL_CACHE_TTL_SECONDS = 300


def _get_or_fit_model(cache_key: str, baseline_vectors: np.ndarray) -> tuple[IsolationForest, np.ndarray]:
    now = time.time()
    cached = _model_cache.get(cache_key)
    if cached and (now - cached[0]) < MODEL_CACHE_TTL_SECONDS:
        return cached[1], cached[2]
    model = IsolationForest(contamination='auto', random_state=42)
    model.fit(baseline_vectors)
    baseline_scores = model.decision_function(baseline_vectors)
    _model_cache[cache_key] = (now, model, baseline_scores)
    return model, baseline_scores


def invalidate_model_cache(movement_type: str) -> None:
    """Call after a successful baseline recompute so a stale fitted model isn't reused."""
    for key in list(_model_cache.keys()):
        if key.startswith(f"{movement_type}:"):
            _model_cache.pop(key, None)


def compute_anomaly_scores(sample_vectors: np.ndarray, baseline_vectors: np.ndarray, min_samples: int = 10, cache_key: str | None = None, metric_name: str = "") -> list[float]:
    """
    sample_vectors: this video's per-frame validated metric values, shape (n_frames, n_features)
    baseline_vectors: historical validated metric values for this movement_type, shape (n_baseline, n_features)
    Returns a percentile-rank anomaly score per frame, 0-100, self-calibrated against the
    baseline's own decision_function distribution.
    """
    if len(baseline_vectors) < min_samples:
        raise InsufficientBaselineError(metric_name, len(baseline_vectors), min_samples)

    if cache_key:
        model, baseline_scores = _get_or_fit_model(cache_key, baseline_vectors)
    else:
        model = IsolationForest(contamination='auto', random_state=42)
        model.fit(baseline_vectors)
        baseline_scores = model.decision_function(baseline_vectors)

    sample_scores = model.decision_function(sample_vectors)

    return [
        float(100 * (baseline_scores > s).mean())  # % of baseline MORE normal than this sample
        for s in sample_scores
    ]