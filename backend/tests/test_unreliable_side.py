"""A leg that was barely visible must not drive the anomaly score.

Found on REAL footage: a side-on squat clip whose left (far) leg was visible in 13.5% of frames scored
63.6 "high" because three left-leg angles, computed from those few frames, sat far outside the population.
"""
import numpy as np
import pytest

from app.modules.risk_scoring.features import drop_unreliable_side_features
from app.modules.risk_scoring.scoring import MIN_LEG_USABLE_PCT
from tests.conftest import auth_header, register_and_login
from tests.factories import make_population, make_video, normal_frames
from tests.test_risk_scoring import METRICS

F = {
    "knee_flexion_angle_left.p95": 149.0, "knee_flexion_angle_right.p95": 95.0,
    "hip_flexion_angle_left.p05": 93.0, "hip_flexion_angle_right.p05": 12.0,
    "trunk_lean_angle.p95": 20.0,
}


def test_blind_side_features_are_dropped_and_the_rest_kept():
    kept, sides = drop_unreliable_side_features(F, {"left_leg": 13.5, "right_leg": 100.0}, MIN_LEG_USABLE_PCT)
    assert sides == ["left"]
    assert set(kept) == {"knee_flexion_angle_right.p95", "hip_flexion_angle_right.p05", "trunk_lean_angle.p95"}


def test_both_legs_blind_leaves_only_trunk_features():
    kept, sides = drop_unreliable_side_features(F, {"left_leg": 20.0, "right_leg": 5.0}, MIN_LEG_USABLE_PCT)
    assert sides == ["left", "right"] and set(kept) == {"trunk_lean_angle.p95"}


@pytest.mark.parametrize("usable", [None, {}, {"left_leg": 100.0, "right_leg": 100.0}, {"left_leg": 60.0, "right_leg": 61.0}])
def test_fully_visible_or_unknown_visibility_changes_nothing(usable):
    kept, sides = drop_unreliable_side_features(F, usable, MIN_LEG_USABLE_PCT)
    assert kept == F and sides == []      # at the floor exactly (60) is still reliable; unknown is not a reason to drop


@pytest.mark.asyncio
async def test_occluded_leg_garbage_no_longer_scores_high_end_to_end(client, db_session):
    token = await register_and_login(client, "admin@occ.example.com", "admin")
    coach, people, _ = await make_population(db_session, videos=10, athletes=3, frames=200, seed=21)
    rng = np.random.default_rng(210)
    metrics = {
        "knee_flexion_angle_left": normal_frames(rng, 200, mu=90 + 8 * 8),    # absurd values from an occluded far leg
        "knee_flexion_angle_right": normal_frames(rng, 200),                  # the visible leg is perfectly normal
    }
    v = await make_video(db_session, people[0].id, coach.id, metrics=metrics)
    v.analysis = {"quality": {"grade": "fair", "usable_pct": {"left_leg": 13.5, "right_leg": 100.0, "trunk": 100.0}}}
    await db_session.commit()
    r = await client.get(f"/api/v1/videos/{v.id}/risk-score", headers=auth_header(token))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["unreliable_sides"] == ["left"]
    assert body["score_breakdown"]["biomechanical_deviations"]["score"] < 5.0
    assert body["risk_category"] == "low"
