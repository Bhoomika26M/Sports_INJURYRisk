"""Engine 2.3 metrics against synthetic motion with KNOWN ground truth (docs/DECISIONS.md 2026-10-08).

Every expected number below is closed-form geometry, not a copy of what the code returned.
"""

import math

import numpy as np
import pytest

from app.modules.biomechanics.calculations import (
    LANDMARK,
    ankle_dorsiflexion_angle,
    hip_adduction_deviation,
    lower_body_extras,
)
from app.modules.biomechanics.movement_analysis import balance_metrics, landing_jump_metrics, trunk_rotation_velocity
from app.modules.biomechanics.registry import get_calculator
from app.modules.pose.processing import analyze_frames
from tests.synth import make_pose, run_frames, squat_frames

FPS = 30
LOWER_BODY = ("squatting", "landing", "running", "sprinting", "jumping", "cutting")


# ------------------------------------------------------------------ helpers
def flat_foot(pose: dict) -> dict:
    """make_pose tilts the foot 3.4 deg; level it (heel -> toe exactly horizontal) so the ground truth is exact."""
    lm = {k: list(v) for k, v in pose.items()}
    for side in ("left", "right"):
        a = np.array(lm[str(LANDMARK[f"{side}_ankle"])])
        lm[str(LANDMARK[f"{side}_heel"])] = (a + [-0.05, 0.03, 0.0]).tolist()
        lm[str(LANDMARK[f"{side}_foot_index"])] = (a + [0.12, 0.03, 0.0]).tolist()
    return lm


def frontal_pose(left_knee_x=0.1, right_knee_x=-0.1) -> dict:
    """Facing the camera: x is the lateral axis, hips +-0.1 m, thighs 0.4 m long when the knee is straight below the hip."""
    lm = {str(i): [0.0, 0.0, 0.0] for i in range(33)}
    lm.update({"11": [0.2, -0.5, 0], "12": [-0.2, -0.5, 0], "23": [0.1, 0, 0], "24": [-0.1, 0, 0],
               "25": [left_knee_x, 0.4, 0], "26": [right_knee_x, 0.4, 0], "27": [0.1, 0.8, 0], "28": [-0.1, 0.8, 0]})
    return lm


def knee_trace(*parts) -> np.ndarray:
    """Knee-flexion trace at 30 fps: ("flat", secs, deg) or ("tri", secs, base_deg, peak_deg) = ramp up then down."""
    out = []
    for p in parts:
        n = int(round(p[1] * FPS))
        out.append(np.full(n, float(p[2])) if p[0] == "flat"
                   else np.interp(np.arange(n), [0, n / 2, n - 1], [p[2], p[3], p[2]]))
    return np.concatenate(out)


def knees(trace: np.ndarray) -> dict:
    return {"knee_flexion_angle_left": trace, "knee_flexion_angle_right": trace}


# ------------------------------------------------------------------ ankle dorsiflexion (per frame)
@pytest.mark.parametrize("knee", [0, 40, 100])
def test_ankle_dorsiflexion_is_the_forward_shank_tilt_over_a_flat_foot(knee):
    lm = flat_foot(make_pose(knee, knee, 0))  # default thigh = knee/2, so the shank leans forward knee/2 from vertical
    for side in ("left", "right"):
        assert ankle_dorsiflexion_angle(lm, side) == pytest.approx(knee / 2, abs=0.2)


def test_ankle_plantarflexion_is_negative():
    lm = flat_foot(make_pose(0, 0, 0))
    ankle, heel = np.array(lm[str(LANDMARK["left_ankle"])]), np.array(lm[str(LANDMARK["left_heel"])])
    lm[str(LANDMARK["left_foot_index"])] = (heel + [0.15, 0.07, 0.0]).tolist()  # toes pointing 25 deg below the heel
    assert ankle_dorsiflexion_angle(lm, "left") == pytest.approx(-math.degrees(math.atan2(0.07, 0.15)), abs=0.5)
    assert ankle.shape == (3,)


def test_missing_degenerate_or_occluded_foot_gives_no_metric_not_a_crash_or_nan():
    lm = make_pose(30, 30, 0)
    no_foot = {k: v for k, v in lm.items() if int(k) not in (29, 30, 31, 32)}
    assert ankle_dorsiflexion_angle(no_foot, "left") is None
    assert ankle_dorsiflexion_angle({**lm, str(LANDMARK["left_heel"]): lm[str(LANDMARK["left_foot_index"])]}, "left") is None
    assert ankle_dorsiflexion_angle({**lm, str(LANDMARK["left_heel"]): [float("nan")] * 3}, "left") is None
    assert lower_body_extras(no_foot, "sagittal") == []


# ------------------------------------------------------------------ hip adduction (per frame, qualitative)
def test_hip_adduction_sign_and_size():
    lm = frontal_pose(left_knee_x=0.05, right_knee_x=-0.15)
    expected = 100 * 0.05 / math.hypot(0.05, 0.4)
    assert hip_adduction_deviation(lm, "left") == pytest.approx(expected, abs=0.1)    # knee toward the midline: +
    assert hip_adduction_deviation(lm, "right") == pytest.approx(-expected, abs=0.1)  # knee away from the midline: -
    assert hip_adduction_deviation(frontal_pose(), "left") == 0.0
    assert hip_adduction_deviation({**lm, "24": lm["23"]}, "left") is None            # no medial direction to measure along


@pytest.mark.parametrize("movement", LOWER_BODY)
def test_lower_body_calculators_emit_ankle_qualitative_sagittal_and_hip_qualitative_frontal(movement):
    calc = get_calculator(movement)
    sag = {m["name"]: m for m in calc.compute_all(flat_foot(make_pose(40, 40, 10)), "sagittal")}
    # qualitative, not validated: ICC < 0.5 (Russo 2026) is below what SCIENCE_CONSTRAINTS accepts, and only validated
    # per-frame metrics become anomaly features (DECISIONS 2026-10-09)
    assert sag["ankle_dorsiflexion_angle_left"]["confidence"] == "qualitative"
    assert sag["ankle_dorsiflexion_angle_right"]["plane"] == "sagittal"
    assert not [n for n in sag if "hip_adduction" in n]
    fro = {m["name"]: m for m in calc.compute_all(frontal_pose(0.05), "frontal")}
    assert fro["hip_adduction_deviation_left"]["confidence"] == "qualitative"
    assert fro["hip_adduction_deviation_left"]["plane"] == "frontal"
    assert not [n for n in fro if "ankle_dorsiflexion" in n]


def test_throwing_is_not_a_lower_body_movement():
    names = {m["name"] for m in get_calculator("throwing").compute_all(flat_foot(make_pose(40, 40, 10)), "other")}
    assert not [n for n in names if n.startswith(("ankle_", "hip_adduction"))]


# ------------------------------------------------------------------ stride length + overstride (gait)
def _yaw(frames, deg):
    r = math.radians(deg)
    R = np.array([[math.cos(r), 0, math.sin(r)], [0, 1, 0], [-math.sin(r), 0, math.cos(r)]])
    return [{**f, "world_landmarks": {k: (R @ np.array(v)).tolist() for k, v in f["world_landmarks"].items()}} for f in frames]


@pytest.mark.parametrize("yaw", [0, 40, 180])  # side-on, oblique, and running the other way (toes point -x)
def test_stride_length_and_overstride_match_straight_leg_geometry(yaw):
    """Straight legs swing +-35 deg, ankle x = 0.9 sin(phi). Feet are furthest apart at +-35 deg: one step is
    1.8 sin 35 = 1.03 m, a stride (left + right step) 2.06 m, and the leading ankle is 0.9 sin 35 = 0.516 m ahead of the pelvis."""
    frames = _yaw(run_frames(kmax=0, seconds=8), yaw)
    _, analysis = analyze_frames(frames, "running", "sagittal", FPS)
    m = analysis["movement"]["metrics"]
    stride, over = 2 * 1.8 * math.sin(math.radians(35)), 0.9 * math.sin(math.radians(35))
    # The peaks are read off a track cleaned WITHOUT the Hampel despike (it clipped them -7..-22%; DECISIONS 2026-10-09),
    # so this is now a tight band: a wrong axis, a lost sign, a x2 slip or a returning despike clip all fail it.
    assert 0.97 * stride <= m["stride_length_m"] <= 1.02 * stride
    assert 0.97 * over <= m["overstride_indicator"] <= 1.02 * over
    assert m["overstride_indicator"] > 0  # leading foot AHEAD of the pelvis, also when running toward -x (yaw 180)
    assert "stride_length_m" not in analysis["movement"]["gait"]  # moved into metrics, gait keeps its old shape
    assert analysis["movement"]["gait"]["cadence_spm"] == pytest.approx(170, rel=0.07)


def test_gait_metrics_are_not_produced_from_a_head_on_camera():
    _, analysis = analyze_frames(run_frames(kmax=0, seconds=8), "running", "frontal", FPS)
    assert analysis["movement"]["metrics"] == {}


# ------------------------------------------------------------------ landing mechanics
def test_stiff_landing_scores_higher_than_soft_and_both_follow_the_less_thresholds():
    soft = landing_jump_metrics(knees(knee_trace(("flat", 1, 35), ("tri", 0.8, 35, 100), ("flat", 1, 35))), None, FPS, "landing")
    stiff = landing_jump_metrics(knees(knee_trace(("flat", 1, 10), ("tri", 0.8, 10, 40), ("flat", 1, 10))), None, FPS, "landing")
    assert soft["contact_flexion"] == pytest.approx(35, abs=4) and soft["stiff_landing_index"] < 0.05  # >30 at contact, 65 deg displacement
    assert stiff["contact_flexion"] == pytest.approx(10, abs=4)
    assert stiff["stiff_landing_index"] == pytest.approx(0.5, abs=0.12)  # 1 - 10/30 = 0.67 and 1 - 30/45 = 0.33 -> mean 0.5
    assert 0.0 <= stiff["stiff_landing_index"] <= 1.0


def test_flight_time_is_the_extended_gap_between_two_landings():
    trace = knee_trace(("flat", 0.6, 5), ("tri", 0.8, 5, 70), ("flat", 0.4, 5), ("tri", 0.8, 5, 70), ("flat", 0.6, 5))
    out = landing_jump_metrics(knees(trace), None, FPS, "landing")
    assert out["flight_time"] == pytest.approx(0.4, abs=0.1)  # resolution is 1/fps; the 5%-of-range valley edges add < 2 frames


def test_flight_outside_the_physical_window_is_not_reported():
    long_pause = knee_trace(("flat", 0.6, 5), ("tri", 0.8, 5, 70), ("flat", 2.0, 5), ("tri", 0.8, 5, 70), ("flat", 0.6, 5))
    assert "flight_time" not in landing_jump_metrics(knees(long_pause), None, FPS, "landing")  # 2 s pause is standing, not a 2 s jump
    back_to_back = knee_trace(("flat", 0.6, 5), ("tri", 0.8, 5, 70), ("tri", 0.8, 5, 70), ("flat", 0.6, 5))
    assert "flight_time" not in landing_jump_metrics(knees(back_to_back), None, FPS, "landing")  # no extended gap at all
    # continuous smooth reps: the knee is "near its minimum" for ~0.28 s at every valley, which is NOT a flight
    cosine = 100 * (1 - np.cos(2 * np.pi * np.arange(4 * 60) / 60)) / 2  # 4 squats of 2 s
    out = landing_jump_metrics(knees(np.concatenate([np.zeros(20), cosine, np.zeros(20)])), None, FPS, "landing")
    assert out["contact_flexion"] is not None and "flight_time" not in out


def test_jumping_counts_only_landings_that_follow_a_flight_and_measures_countermovement_depth():
    trace = knee_trace(("flat", 0.6, 3), ("tri", 0.8, 3, 80), ("flat", 0.4, 3), ("tri", 0.6, 3, 70), ("flat", 0.6, 3))
    xyz = np.zeros((len(trace), 33, 3))
    hip_height = 0.9 - 0.25 * (trace - 3) / 77  # hip sinks 0.25 m at the countermovement bottom (80 deg)
    xyz[:, [LANDMARK["left_ankle"], LANDMARK["right_ankle"]], 1] = hip_height[:, None]  # hips sit at y = 0, +Y is DOWN
    out = landing_jump_metrics(knees(trace), xyz, FPS, "jumping")
    assert out["flight_time"] == pytest.approx(0.4, abs=0.1)
    assert out["countermovement_depth"] == pytest.approx(0.25, abs=0.02)
    assert "contact_flexion" in out
    # one dip and nothing after it: a countermovement with no landing, so no landing metrics for "jumping" ...
    assert landing_jump_metrics(knees(knee_trace(("flat", 1, 3), ("tri", 0.8, 3, 80), ("flat", 1, 3))), None, FPS, "jumping") == {}
    # ... but a "landing" clip with one dip IS a landing
    assert "contact_flexion" in landing_jump_metrics(knees(knee_trace(("flat", 1, 3), ("tri", 0.8, 3, 80), ("flat", 1, 3))), None, FPS, "landing")


def test_landing_metrics_need_a_real_movement_not_noise():
    rng = np.random.default_rng(0)
    assert landing_jump_metrics(knees(10 + rng.normal(0, 1.0, 120)), None, FPS, "landing") == {}
    assert landing_jump_metrics({}, None, FPS, "landing") == {}


# ------------------------------------------------------------------ balance: stance time + COM sway
def single_leg_clip(raised="left", lift=(1.0, 5.0), seconds=6.0, amp=0.02, hz=0.5) -> np.ndarray:
    t = np.arange(int(seconds * FPS)) / FPS
    xyz = np.zeros((len(t), 33, 3))
    stance, free = ("right_ankle", "left_ankle") if raised == "left" else ("left_ankle", "right_ankle")
    xyz[:, [LANDMARK["left_ankle"], LANDMARK["right_ankle"]], 1] = 0.85
    xyz[(t >= lift[0]) & (t < lift[1]), LANDMARK[free], 1] = 0.65  # free foot 20 cm above the stance foot
    xyz[:, LANDMARK[stance], 0] = -amp * np.sin(2 * np.pi * hz * (t - lift[0]))  # body sways over the planted foot
    for n in ("left_shoulder", "right_shoulder"):
        xyz[:, LANDMARK[n], 1] = -0.5
    return xyz


@pytest.mark.parametrize("raised", ["left", "right"])
def test_stance_time_and_com_sway_of_a_single_leg_stance(raised):
    out = balance_metrics(single_leg_clip(raised), FPS)
    assert out["stance_time"] == pytest.approx(4.0, abs=0.07)
    assert out["com_sway"] == pytest.approx(0.02 / math.sqrt(2), abs=0.0005)  # SD of a +-2 cm sinusoid over whole cycles


def test_no_balance_metrics_without_a_real_single_leg_stance():
    assert balance_metrics(single_leg_clip(lift=(1.0, 1.5)), FPS) == {}  # 0.5 s is a step, not a stance
    assert balance_metrics(single_leg_clip(lift=(9.0, 10.0)), FPS) == {}  # never lifted inside the clip
    assert balance_metrics(None, FPS) == {}


# ------------------------------------------------------------------ trunk rotation velocity (throwing)
def test_trunk_rotation_velocity_is_the_peak_rate_of_change():
    ramp = np.concatenate([np.zeros(30), np.linspace(0, 90, 15), np.full(45, 90.0)])  # 90 deg in 14 intervals
    out = trunk_rotation_velocity({"trunk_rotation": ramp}, FPS)
    assert out["trunk_rotation_velocity"] == pytest.approx(90 / 14 * FPS, abs=8)  # 193 deg/s
    assert trunk_rotation_velocity({"trunk_rotation": np.full(60, 40.0)}, FPS)["trunk_rotation_velocity"] == 0
    assert trunk_rotation_velocity({}, FPS) == {} and trunk_rotation_velocity({"trunk_rotation": ramp[:5]}, FPS) == {}


# ------------------------------------------------------------------ wiring: everything emitted is registered
@pytest.mark.parametrize("view", ["sagittal", "frontal", "other"])
@pytest.mark.parametrize("movement", [*LOWER_BODY, "throwing"])
def test_every_emitted_metric_is_registered_in_the_seed_for_that_movement(movement, view):
    from app.seed import MOVEMENT_METRICS

    frames = run_frames(kmax=0, seconds=8) if movement in ("running", "sprinting", "cutting") else squat_frames(n_reps=3)
    metrics, analysis = analyze_frames(frames, movement, view, FPS)
    emitted = {m["name"] for m in metrics} | set(analysis["movement"]["metrics"])
    registered = {name for mv, name, *_ in MOVEMENT_METRICS if mv == movement}
    assert emitted <= registered, emitted - registered


async def test_seeded_registry_has_units_and_descriptions_and_reseeding_adds_nothing(db_session):
    from sqlalchemy import func, select

    from app.modules.video.models import MovementMetric
    from app.seed import MOVEMENT_METRICS, seed_movements

    rows = {(r.movement_type, r.metric_name): r for r in (await db_session.scalars(select(MovementMetric))).all()}
    assert len(rows) == len({(m, n) for m, n, *_ in MOVEMENT_METRICS})
    assert rows[("running", "stride_length_m")].unit == "m"
    assert rows[("landing", "stiff_landing_index")].unit == "index"
    assert rows[("throwing", "trunk_rotation_velocity")].unit == "deg/s"
    assert rows[("squatting", "knee_flexion_angle_left")].unit == "degrees"  # old 4-tuple rows keep the default
    assert rows[("squatting", "hip_adduction_deviation_left")].confidence == "qualitative"
    assert rows[("cutting", "ankle_dorsiflexion_angle_left")].description
    await seed_movements(db_session)
    await db_session.commit()
    assert await db_session.scalar(select(func.count()).select_from(MovementMetric)) == len(rows)


async def test_reseeding_converges_a_registry_seeded_by_an_older_version(db_session):
    """The registry rows follow the code: a DB seeded before a tier / description change is corrected by the next seed."""
    from sqlalchemy import select

    from app.modules.video.models import MovementMetric
    from app.seed import seed_movements

    row = await db_session.scalar(select(MovementMetric).where(
        MovementMetric.movement_type == "running", MovementMetric.metric_name == "ankle_dorsiflexion_angle_left"))
    assert row.confidence == "qualitative"
    row.confidence, row.description = "validated", "stale"
    await db_session.commit()
    await seed_movements(db_session)
    await db_session.commit()
    await db_session.refresh(row)
    assert row.confidence == "qualitative" and "Qualitative" in row.description
