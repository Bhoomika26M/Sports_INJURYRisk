"""Anomaly calibration tests, built from PRODUCTION-SCALE data.

Regime: a metric in degrees (baseline ~ N(90, 8)), baselines of hundreds of per-frame rows,
400-frame sample populations, every assertion repeated over several seeds. The previous spread
test used 50 baseline rows and two hand-picked points and passed by luck of the fixture while the
production calibration was wrong (an average athlete scored ~37 of 70 points).

Two kinds of "sd x k" population are used, because they mean different things physically:
  scale k  ~ N(mu, k*sd)      movement that is k times more variable than the baseline
  shift k  ~ N(mu + k*sd, sd) movement systematically k baseline-SDs off the norm
Thresholds below were set from measurement (n=426, 5 seeds) with stated margin; see comments.
"""

import numpy as np
import pytest
from sklearn.ensemble import IsolationForest

from app.modules.risk_scoring.anomaly import (
    InsufficientBaselineError,
    compute_anomaly_scores,
    invalidate_model_cache,
    severity_from_distance,
)
from app.modules.risk_scoring.scoring import compute_risk_score

MU, SD = 90.0, 8.0
SEEDS = range(5)
BASELINE_SIZES = (60, 200, 426, 1200)
N_SAMPLE = 400


def _baseline(rng, n):
    return rng.normal(MU, SD, size=(n, 1))


def _population(rng, kind, k):
    if kind == "scale":
        return rng.normal(MU, k * SD, size=(N_SAMPLE, 1))
    return rng.normal(MU + k * SD, SD, size=(N_SAMPLE, 1))


def _mean_score(kind, k, n, seed):
    rng = np.random.default_rng(seed)
    base = _baseline(rng, n)
    return float(np.mean(compute_anomaly_scores(_population(rng, kind, k), base, min_baseline_frames=10)))


# ---- zero anchor ---------------------------------------------------------------------------

@pytest.mark.parametrize("seed", SEEDS)
def test_in_distribution_frames_score_near_zero(seed):
    # Handoff requirement: < 20. Measured max across seeds is 1.2, so we pin < 5.
    score = _mean_score("scale", 1, 426, seed)
    assert score < 5.0, f"in-distribution mean anomaly {score:.1f}; the old percentile scale gave ~53"


@pytest.mark.parametrize("seed", SEEDS)
def test_normal_athlete_contributes_almost_nothing_to_the_composite(seed):
    rng = np.random.default_rng(seed)
    base = _baseline(rng, 426)
    frame_scores = compute_anomaly_scores(_population(rng, "scale", 1), base, min_baseline_frames=10)
    result = compute_risk_score(frame_scores, None, False)
    assert result["score_breakdown"].movement_anomaly.points < 5.0   # was ~37 of 70
    assert result["risk_category"] == "low"


def test_frames_at_least_as_normal_as_the_envelope_edge_score_exactly_zero():
    rng = np.random.default_rng(0)
    base = _baseline(rng, 426)
    centre = np.full((20, 1), MU)
    assert compute_anomaly_scores(centre, base, min_baseline_frames=10) == [0.0] * 20


# ---- monotone and separated ----------------------------------------------------------------

@pytest.mark.parametrize("kind,ks", [("scale", (1, 2, 4, 8)), ("shift", (0, 2, 4, 8))])
@pytest.mark.parametrize("seed", SEEDS)
def test_deviation_strength_increases_monotonically(kind, ks, seed):
    scores = [_mean_score(kind, k, 426, seed) for k in ks]
    # strict, and every step is a real step (measured minimum step ~7 points)
    for lower, higher in zip(scores, scores[1:]):
        assert higher >= lower + 5.0, f"{kind} {ks}: {[round(s, 1) for s in scores]}"


@pytest.mark.parametrize("kind", ["scale", "shift"])
@pytest.mark.parametrize("seed", SEEDS)
def test_clear_and_extreme_deviations_are_separated_by_a_meaningful_margin(kind, seed):
    # Required margin: extreme (x8) - clear (x4) >= 15 points on the 0-100 frame scale.
    # Measured: scale >= 20, shift >= 34. The old scale separated them by ~1.6 composite points.
    clear, extreme = _mean_score(kind, 4, 426, seed), _mean_score(kind, 8, 426, seed)
    assert extreme - clear >= 15.0, f"{kind}: clear={clear:.1f} extreme={extreme:.1f}"


def test_extreme_deviation_reaches_high_band_but_movement_alone_never_reaches_critical():
    rng = np.random.default_rng(0)
    base = _baseline(rng, 426)
    frames = compute_anomaly_scores(_population(rng, "shift", 8), base, min_baseline_frames=10)
    res = compute_risk_score(frames, None, False)
    assert res["risk_category"] == "high"
    assert res["score_breakdown"].movement_anomaly.points <= 70.0


def test_isolation_forest_alone_cannot_separate_clear_from_extreme_which_is_why_geometry_is_used():
    """Regression evidence for the design: the forest's own decision score SATURATES."""
    rng = np.random.default_rng(0)
    base = _baseline(rng, 426)
    forest = IsolationForest(contamination="auto", random_state=42).fit(base)
    clear = float(np.median(forest.decision_function(_population(rng, "shift", 4))))
    extreme = float(np.median(forest.decision_function(_population(rng, "shift", 8))))
    assert abs(clear - extreme) < 0.05          # measured: -0.275 vs -0.275
    assert _mean_score("shift", 8, 426, 0) - _mean_score("shift", 4, 426, 0) >= 15.0


# ---- stable across baseline size -----------------------------------------------------------

@pytest.mark.parametrize("kind,k", [("scale", 1), ("scale", 2), ("scale", 4), ("scale", 8),
                                    ("shift", 2), ("shift", 4), ("shift", 8)])
def test_score_is_stable_across_baseline_size(kind, k):
    # Same population, baselines of 60 / 200 / 426 / 1200 frames, mean over 5 seeds.
    # Required: spread <= 10 points. Measured: worst case 7.5 (shift x4), in-distribution 0.7.
    # (The old percentile scale moved by ~29-43 points here.)
    means = [np.mean([_mean_score(kind, k, n, s) for s in SEEDS]) for n in BASELINE_SIZES]
    assert max(means) - min(means) <= 10.0, f"{kind} x{k}: {[round(m, 1) for m in means]}"


def test_in_distribution_score_is_tightly_stable_across_baseline_size():
    means = [np.mean([_mean_score("scale", 1, n, s) for s in SEEDS]) for n in BASELINE_SIZES]
    assert max(means) - min(means) <= 2.0, [round(m, 2) for m in means]


# ---- behaviour that must not regress -------------------------------------------------------

def test_direction_is_higher_score_means_more_anomalous_on_both_sides():
    rng = np.random.default_rng(0)
    base = _baseline(rng, 426)
    normal = compute_anomaly_scores(np.array([[MU]]), base, min_baseline_frames=10)[0]
    high = compute_anomaly_scores(np.array([[MU + 6 * SD]]), base, min_baseline_frames=10)[0]
    low = compute_anomaly_scores(np.array([[MU - 6 * SD]]), base, min_baseline_frames=10)[0]
    assert normal < 1.0 and high > 50.0 and low > 50.0


def test_multimodal_baseline_modes_are_normal():
    """A squat's per-frame knee flexion is bimodal (standing / bottom). Both modes must read as
    normal; a median/MAD z-score on the raw metric would call them anomalous."""
    rng = np.random.default_rng(1)
    baseline = np.concatenate([
        rng.normal(5, 3, size=(200, 1)), rng.normal(100, 4, size=(200, 1)), rng.uniform(5, 100, size=(60, 1)),
    ])
    at_modes = compute_anomaly_scores(np.array([[5.0], [100.0]]), baseline, min_baseline_frames=10)
    beyond = compute_anomaly_scores(np.array([[175.0]]), baseline, min_baseline_frames=10)[0]
    assert max(at_modes) < 5.0 and beyond > 15.0


def test_severity_mapping_anchors():
    assert float(severity_from_distance(0.0)) == 0.0
    assert float(severity_from_distance(2.0)) == pytest.approx(50.0)   # half-saturation = 2 robust SD
    assert float(severity_from_distance(4.0)) == pytest.approx(75.0)
    d = np.linspace(0, 50, 200)
    s = severity_from_distance(d)
    assert np.all(np.diff(s) > 0) and s.max() < 100.0
    assert float(severity_from_distance(-3.0)) == 0.0


def test_model_cache_never_serves_a_model_fitted_on_a_different_baseline():
    rng = np.random.default_rng(0)
    base_a = _baseline(rng, 300)
    base_b = base_a + 40.0   # a different population under the SAME cache key
    x = np.array([[MU + 40.0]])
    key = "squatting:knee_flexion_angle_left:cache-test"
    try:
        a = compute_anomaly_scores(x, base_a, min_baseline_frames=10, cache_key=key)[0]
        b = compute_anomaly_scores(x, base_b, min_baseline_frames=10, cache_key=key)[0]
    finally:
        invalidate_model_cache("squatting")
    assert a > 50.0 and b < 1.0


def test_insufficient_baseline_raises_with_unit():
    tiny = np.random.default_rng(0).normal(MU, SD, size=(3, 1))
    with pytest.raises(InsufficientBaselineError) as exc:
        compute_anomaly_scores(np.array([[90.0]]), tiny, min_baseline_frames=10)
    assert exc.value.unit == "frames" and exc.value.have == 3 and exc.value.need == 10


def test_non_finite_input_is_rejected_not_silently_scored():
    base = _baseline(np.random.default_rng(0), 200)
    with pytest.raises(ValueError):
        compute_anomaly_scores(np.array([[np.nan]]), base, min_baseline_frames=10)
