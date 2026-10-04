"""Calibration of the video-level anomaly engine, from simulated populations at realistic scale.

Replaces the per-frame calibration tests that targeted the previous (per-frame, 0-anchored) engine.
Each feature is a degrees-scale video-level extreme (e.g. knee-flexion p95) with its own spread; a
"shift k" video is one feature k baseline-SDs off the norm. Thresholds were set from measurement
(60 trials per cell; the tests below use fewer, with wider bounds, to stay fast) with stated margin:

    baseline videos | normal video scored >50 | 4-sigma caught | 6-sigma caught
    10              | 10%                     | 37%            | 72%
    30              |  2%                     | 47%            | 88%

The engine is deliberately conservative: it flags large deviations, not subtle ones. These tests pin
that behaviour (and its limits) so it cannot drift silently in either direction.
"""

import numpy as np
import pytest

from app.modules.risk_scoring.anomaly import InsufficientBaselineError, assess_video_anomaly

F = ["a.p95", "b.p95", "c.p05", "d.p95", "e.p05", "f.p95"]
MU = np.array([90, 40, 15, 25, 60, 10.0])
SD = np.array([8, 6, 5, 4, 7, 3.0])


def _rates(n_baseline: int, shift: float, trials: int = 20, seed: int = 0):
    rng = np.random.default_rng(seed)
    scores = []
    for _ in range(trials):
        base = [dict(zip(F, rng.normal(MU, SD))) for _ in range(n_baseline)]
        v = rng.normal(MU, SD)
        v[0] += shift * SD[0]
        scores.append(assess_video_anomaly(dict(zip(F, v)), base, 10)["deviation_score"])
    return np.array(scores)


@pytest.mark.parametrize("n_baseline", [10, 30])
def test_normal_videos_are_rarely_scored_as_anomalous(n_baseline):
    s = _rates(n_baseline, shift=0.0)
    assert (s > 50).mean() <= 0.30            # measured 10% / 2% over 60 trials; wide margin for 20
    assert np.median(s) == 0.0                # a typical normal video contributes nothing


def test_a_large_deviation_is_caught_most_of_the_time_given_a_decent_baseline():
    s = _rates(30, shift=6.0, trials=24)
    assert (s > 50).mean() >= 0.55            # measured 88% over 60 trials; wide margin for 24
    assert (s == 100).mean() >= 0.25


def test_score_rises_monotonically_with_how_far_off_the_video_is():
    med = [np.median(_rates(30, shift=k, trials=12)) for k in (0, 4, 8)]
    assert med == sorted(med) and med[0] < med[-1]


def test_engine_is_conservative_and_does_not_flag_moderate_deviations():
    """Pinned limit, not a goal: a 2-sigma deviation is within normal variation and must not alarm."""
    assert np.median(_rates(30, shift=2.0, trials=12)) == 0.0


def test_below_the_video_floor_it_refuses_instead_of_guessing():
    base = [dict(zip(F, MU)) for _ in range(9)]
    with pytest.raises(InsufficientBaselineError):
        assess_video_anomaly(dict(zip(F, MU)), base, 10)


def test_every_flagged_feature_is_explained():
    rng = np.random.default_rng(1)
    base = [dict(zip(F, rng.normal(MU, SD))) for _ in range(30)]
    v = dict(zip(F, MU)); v["a.p95"] = MU[0] + 7 * SD[0]
    out = assess_video_anomaly(v, base, 10)
    top = out["features"][0]
    assert top["feature"] == "a.p95" and top["flagged"] and top["direction"] == "above"


def test_score_is_a_pure_function_of_the_data_not_of_row_order():
    """REGRESSION. The baseline arrives from a GROUP BY with no ORDER BY, and the forest + cross-fit folds depend on
    row order: a perfectly normal video flipped between 0 and 100 depending only on how Postgres returned the rows
    (it also made a DB test pass alone and fail in a full run). Same data in any order must give the same score."""
    import random
    rng = np.random.default_rng(7)
    flipped = 0
    for _ in range(4):
        base = [dict(zip(F, rng.normal(MU, SD))) for _ in range(10)]
        v = dict(zip(F, rng.normal(MU, SD)))
        scores = set()
        for seed in range(4):
            b = base[:]
            random.Random(seed).shuffle(b)
            scores.add(assess_video_anomaly(v, b, 10)["deviation_score"])
        flipped += len(scores) > 1
    assert flipped == 0
