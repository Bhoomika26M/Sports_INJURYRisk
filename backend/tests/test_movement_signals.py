"""Rep outliers, literature heuristic flags, athlete trend, fatigue index (risk_scoring/movement_signals.py)."""

import json

import numpy as np
import pytest

from app.modules.recommendations.rules import generate_recommendations
from app.modules.risk_scoring import service
from app.modules.risk_scoring.injury_categories import FLAG_POINTS, assess_injury_categories
from app.modules.risk_scoring.movement_signals import (
    athlete_trend, fatigue_index, heuristic_flags, rep_outliers,
)
from app.modules.risk_scoring.scoring import CATEGORY_THRESHOLDS
from tests.conftest import auth_header
from tests.synth import squat_frames
from tests.test_risk_assessment_api import MIN, _score, _setup, _video
from tests.test_scoring_engine import _assessment, _feat


def _sets(seed=0, videos=12, reps=5, sd=2.5):
    r = np.random.default_rng(seed)
    return [(f"a{i % 4}", [float(x) for x in r.normal(100, sd, reps)]) for i in range(videos)]


def _k(hi, lo=0.0):
    return {f"knee_flexion_angle_{s}.{p}": v for s in ("left", "right") for p, v in (("p95", hi), ("p05", lo))}


def _flag(movement, key, features=None, gait=None):
    return next(f for f in heuristic_flags(movement, features or {}, gait) if f["key"] == key)


# ------------------------------------------ rep outliers ----------------------------------------

def test_rep_outliers_flag_one_bad_rep_and_leave_normal_sets_alone():
    pop = _sets()
    out = rep_outliers([101, 99, 100, 55, 102, 98], pop, 10, 3)          # rep 4 collapsed by ~45 deg
    assert out["available"] and out["flagged"] and out["score"] >= 90
    assert out["worst_rep"]["rep"] == 4 and out["worst_rep"]["from_set_median_deg"] == pytest.approx(-45, abs=2)
    ok = rep_outliers([101, 99, 100, 98, 102, 100], pop, 10, 3)
    assert ok["score"] == 0 and not ok["flagged"]


def test_rep_outliers_refuse_without_a_real_population():
    pop = _sets()
    assert "3 repetitions" in rep_outliers([100, 99], pop, 10, 3)["reason"]
    assert "found 12 from 4" in rep_outliers([100] * 5, pop, 13, 3)["reason"]      # video floor
    assert "found 12 from 4" in rep_outliers([100] * 5, pop, 10, 5)["reason"]      # athlete floor
    assert not rep_outliers([100] * 5, [], 10, 3)["available"]


def test_rep_outlier_calibration_by_simulation():
    """The rates quoted in rep_outliers' docstring, re-measured (seeded; bounds leave sampling slack)."""
    r = np.random.default_rng(7)

    def one_set(n, bad=0.0):
        p = r.normal(100.0, float(np.exp(r.normal(np.log(5.0), 0.4))), n)   # athletes differ in steadiness
        if bad:
            p[r.integers(n)] += bad
        return [float(x) for x in p]

    def score(bad):
        pop = [(f"a{i % 5}", one_set(int(r.integers(3, 11)))) for i in range(30)]
        return rep_outliers(one_set(int(r.integers(3, 11)), bad), pop, 10, 3)["score"]

    normal = np.array([score(0.0) for _ in range(200)])
    gross = np.array([score(45.0) for _ in range(100)])
    assert (normal > 50).mean() <= 0.06      # measured ~1%
    assert (gross > 50).mean() >= 0.90       # measured ~98%


# ------------------------------------------ fatigue index ---------------------------------------

def test_fatigue_index_is_direction_agnostic_and_one_bad_rep_cannot_fake_it():
    down, up = fatigue_index([100, 95, 90, 85, 80, 75]), fatigue_index([75, 80, 85, 90, 95, 100])
    assert (down["direction"], up["direction"]) == ("decrease", "increase")
    assert down["index"] == up["index"] == pytest.approx(94.9, abs=0.1) and down["total_change_deg"] == -25.0
    assert fatigue_index([100, 100, 100, 100, 100, 60])["index"] == 0.0     # first-vs-last thirds reads -20 % (-40 % at 4-5 reps)
    assert fatigue_index([100, 101, 99, 100, 102, 98])["direction"] == "stable"
    assert "5 repetitions" in fatigue_index([100, 90, 80, 70])["reason"]


# ------------------------------------------ heuristic flags -------------------------------------

@pytest.mark.parametrize("movement,key,feats,gait,expected", [
    ("landing", "stiff_landing", _k(80, 5), None, "ok"),             # 75 deg displacement
    ("landing", "stiff_landing", _k(50, 5), None, "ok"),             # exactly the LESS cut-off is not an error
    ("landing", "stiff_landing", _k(47, 5), None, "borderline"),     # 42: beyond the cut-off but inside the noise margin
    ("landing", "stiff_landing", _k(43, 5), None, "flagged"),        # 38: beyond it by more than the margin
    ("squatting", "inadequate_depth", _k(100), None, "ok"),
    ("squatting", "inadequate_depth", _k(88), None, "borderline"),
    ("squatting", "inadequate_depth", _k(80), None, "flagged"),
    ("running", "low_cadence", {}, {"cadence_spm": 170}, "ok"),
    ("running", "low_cadence", {}, {"cadence_spm": 163}, "borderline"),
    ("running", "low_cadence", {}, {"cadence_spm": 155}, "flagged"),
    ("landing", "stiff_landing", {}, None, "not_assessable"),
    ("squatting", "inadequate_depth", {}, None, "not_assessable"),
    ("running", "low_cadence", {}, None, "not_assessable"),
])
def test_flag_status_boundaries(movement, key, feats, gait, expected):
    assert _flag(movement, key, feats, gait)["status"] == expected


def test_flags_are_movement_specific_cited_and_overstride_is_never_flagged():
    assert [f["key"] for f in heuristic_flags("landing", _k(80, 5))] == ["stiff_landing"]
    assert [f["key"] for f in heuristic_flags("squatting", _k(100))] == ["inadequate_depth"]
    assert [f["key"] for f in heuristic_flags("running", {}, {"cadence_spm": 170})] == ["low_cadence", "overstride"]
    assert [f["key"] for f in heuristic_flags("sprinting", {}, {"cadence_spm": 120})] == ["overstride"]
    assert heuristic_flags("cutting", _k(30), {"cadence_spm": 120}) == [] == heuristic_flags("jumping", _k(30))
    over = _flag("running", "overstride", {}, {"cadence_spm": 100})
    assert over["status"] == "not_assessable" and over["value"] is None and over["reason"]
    assert "overstride_indicator" in over["caveat"]   # names the metric Engine 2.3 records (T2); rename one, update both
    assert all(f["evidence"] and f["caveat"] and "label" in f and "unit" in f and "threshold" in f
               for m in ("landing", "squatting", "running", "sprinting")
               for f in heuristic_flags(m, _k(40, 5), {"cadence_spm": 150}))       # one uniform shape for the UI


def _cats(flags, movement):
    return assess_injury_categories(movement_type=movement, anomaly=None, injuries=[], components={},
                                    qualitative=None, heuristic_flags=flags)


def test_flags_feed_only_the_categories_the_evidence_supports_and_are_capped():
    def flag_drivers(cats):
        return [(k, d) for k, c in cats.items() for d in c["drivers"] if d["source"] == "heuristic_flag"]

    stiff = _cats(heuristic_flags("landing", _k(43, 5)), "landing")
    (cat, drv), = flag_drivers(stiff)
    assert cat == "acl" and (drv["score"], drv["weight"]) == (66.0, 1.5) and stiff["acl"]["video_kinematics_used"]
    assert max(FLAG_POINTS.values()) <= CATEGORY_THRESHOLDS[-1]            # a flag alone can never reach "critical"
    assert _cats(None, "landing") == _cats([], "landing")                  # no flags -> nothing changes
    assert [k for k, _ in flag_drivers(_cats(heuristic_flags("running", {}, {"cadence_spm": 150}), "running"))] == ["overuse"]
    assert flag_drivers(_cats(heuristic_flags("squatting", _k(70)), "squatting")) == []          # depth feeds no category
    assert flag_drivers(_cats(heuristic_flags("landing", {}), "landing")) == []                  # not assessable adds nothing


def test_flagged_flags_recommend_with_their_evidence_and_replace_the_generic_advice():
    a = _assessment(feats=[_feat("knee_flexion_angle_left", "p95", 62, 101, -3.0)])   # the generic finding fires too
    a["heuristic_flags"] = heuristic_flags("landing", _k(43, 5))
    recs = [r for r in generate_recommendations(a, "landing") if r["title"] == "Soft-landing and depth-control drills"]
    assert len(recs) == 1 and "Padua 2009" in recs[0]["description"] and "38°" in recs[0]["description"]

    b = _assessment()
    b["heuristic_flags"] = heuristic_flags("running", {}, {"cadence_spm": 150})
    assert any(r["title"] == "Gradually raise running step rate" for r in generate_recommendations(b, "running"))
    b["heuristic_flags"] = heuristic_flags("running", {}, {"cadence_spm": 163})       # borderline: no recommendation
    assert all("step rate" not in r["title"] for r in generate_recommendations(b, "running"))


# ------------------------------------------ athlete trend ---------------------------------------

def test_athlete_trend_is_bounded_labelled_and_needs_priors():
    priors = [{"knee_flexion_angle_left.p95": 100.0 + d} for d in (-1, 0, 1, 0, 2)]
    t = athlete_trend({"knee_flexion_angle_left.p95": 60.0}, priors)
    assert t["available"] and t["notable"] and t["changes"][0]["z"] <= -2 and t["changes"][0]["change_deg"] < -35
    assert "Not a risk score" in t["label"]
    assert not athlete_trend({"knee_flexion_angle_left.p95": 101.0}, priors)["notable"]
    assert "3 earlier videos" in athlete_trend({"knee_flexion_angle_left.p95": 60.0}, priors[:2])["reason"]
    many = [{"x": 100.0}] * 5 + [{"x": 0.0}] * 10                    # only the newest 10 count
    assert athlete_trend({"x": 0.0}, many)["n_priors"] == 10 and not athlete_trend({"x": 0.0}, many)["notable"]
    assert athlete_trend({"x": 1e9}, many)["changes"][0]["z"] == 10.0   # clipped


def test_outputs_are_json_serialisable():
    json.dumps([rep_outliers([100, 99, 55], _sets(), 10, 3), fatigue_index([1, 2, 3, 4, 5, 6]),
                heuristic_flags("running", {}, {"cadence_spm": 150}), athlete_trend({"x": 1.0}, [{"x": 1.0}] * 3)])


# ------------------------------------------ end to end ------------------------------------------

@pytest.mark.asyncio
async def test_signals_are_wired_through_the_api_and_never_touch_the_composite(client, db_session, monkeypatch):
    token, coach, ath = await _setup(client, db_session)
    v = await _video(db_session, coach.id, ath.id,
                     squat_frames(n_reps=6, depth=60, depth_drift=-0.3, noise_m=0.004, seed=3))
    j = (await _score(client, token, v.id)).json()

    assert {f["key"]: f["status"] for f in j["heuristic_flags"]} == {"inadequate_depth": "flagged"}
    assert j["fatigue_index"]["available"] and j["fatigue_index"]["direction"] == "decrease" and j["fatigue_index"]["index"] > 40
    assert j["rep_outliers"]["available"] and j["rep_outliers"]["population"]["videos"] >= MIN
    assert j["athlete_trend"]["available"] and j["athlete_trend"]["notable"] and j["athlete_trend"]["n_priors"] >= 3
    recs = (await client.get(f"/api/v1/videos/{v.id}/recommendations", headers=auth_header(token))).json()
    assert sum(r["title"] == "Depth progression (tempo / box squat)" for r in recs) == 1
    assert any("Pallarés" in r["description"] for r in recs)

    async def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(service, "_extras", boom)          # a failing extra must not take the assessment down
    j2 = (await _score(client, token, v.id, recompute="true")).json()
    assert (j2["overall_score"], j2["risk_category"]) == (j["overall_score"], j["risk_category"])
    assert "heuristic_flags" not in j2
