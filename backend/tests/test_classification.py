"""Movement / camera-view auto-identification against synthetic motion with known ground truth.

tests/synth.py has squats and runs; jumps, landings, throws, yawed cameras and heading changes are
built here from its make_pose so the rest of the suite stays untouched.
"""

import json
import math

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

from app.modules.biomechanics.classification import classify_movement, compare_labels
from app.modules.pose.analysis import build_track, clean_track
from app.modules.pose.processing import analyze_frames
from app.modules.biomechanics.calculations import LANDMARK
from tests.synth import drop_frames, make_pose, occlude_leg, run_frames, squat_frames

FPS = 30


# ------------------------------- synthetic generators -----------------------------------

def _frames(poses):
    return [{"frame_number": i, "timestamp_ms": int(round(i * 1000 / FPS)), "world_landmarks": lm,
             "visibility": [0.99] * 33} for i, lm in enumerate(poses)]


def _seg(a, b, seconds):
    n = max(2, int(seconds * FPS))
    return a + (b - a) * (1 - np.cos(np.linspace(0, np.pi, n))) / 2


def _still(seconds, knee=0.0):
    return np.full(int(seconds * FPS), float(knee))


def knee_frames(profile):
    """Both knees follow `profile` (deg flexion), standing trunk."""
    return _frames([make_pose(k, k, 8.0) for k in profile])


def jump_frames(n=3):
    """Countermovement jumps: slow crouch, fast take-off, flight, fast landing, slow recovery."""
    one = np.concatenate([_seg(0, 90, .5), _seg(90, 5, .2), _still(.4, 5), _seg(5, 70, .15), _seg(70, 0, .5), _still(.6)])
    return knee_frames(np.concatenate([_still(.5)] + [one] * n))


def landing_frames():
    """One drop landing: step off, fast flexion on impact, slow recovery."""
    return knee_frames(np.concatenate([_still(1), _still(.25, 8), _seg(8, 80, .12), _seg(80, 0, 1.2), _still(1)]))


def stride_frames(cadence_spm=170.0, seconds=6.0, kmax=90.0):
    """Running with half-wave-rectified knee flexion (each knee flexes only in its own swing): the legs are
    still in anti-phase, but - unlike synth.run_frames - the MEAN knee angle oscillates once per step, as it
    does in real running, so a repetition detector would see 'reps' in it."""
    omega = 2 * math.pi * (cadence_spm / 60.0) / 2
    poses = []
    for i in range(int(seconds * FPS)):
        th = omega * i / FPS
        poses.append(make_pose(kmax * max(0.0, math.cos(th)) ** 2, kmax * max(0.0, -math.cos(th)) ** 2, 8.0,
                               35 * math.sin(th), -35 * math.sin(th)))
    return _frames(poses)


def throw_frames(amp_deg=55.0, seconds=4.0, noise_m=0.0, seed=0):
    """Static legs; shoulders/arms/head swing about the vertical axis by +-amp_deg relative to the pelvis."""
    rng = np.random.default_rng(seed)
    poses = []
    for i in range(int(seconds * FPS)):
        lm = make_pose(0, 0, 8.0)
        p = math.radians(amp_deg * math.sin(2 * math.pi * i / (FPS * 2.0)))
        R = np.array([[math.cos(p), 0, math.sin(p)], [0, 1, 0], [-math.sin(p), 0, math.cos(p)]])
        for j in range(17):  # nose..wrists
            lm[str(j)] = (R @ np.array(lm[str(j)])).tolist()
        if noise_m:
            lm = {k: (np.array(v) + rng.normal(0, noise_m, 3)).tolist() for k, v in lm.items()}
        poses.append(lm)
    return _frames(poses)


def shuffle_feet(frames, amp_m=0.12, hz=1.4):
    """Feet scissor in anti-phase (what a stride looks like to the ankle-separation detector) while the
    knees keep doing whatever the frames already do."""
    out = []
    for i, f in enumerate(frames):
        dx = amp_m * math.sin(2 * math.pi * hz * i / FPS)
        lm = dict(f["world_landmarks"])
        for side, sign in (("left", 1), ("right", -1)):
            for part in ("ankle", "heel", "foot_index"):
                j = str(LANDMARK[f"{side}_{part}"])
                lm[j] = [lm[j][0] + sign * dx, lm[j][1], lm[j][2]]
        out.append({**f, "world_landmarks": lm})
    return out


def yaw(frames, deg):
    """Rotate every pose about the vertical axis (a camera moved round the athlete); deg may be f(frame_idx)."""
    out = []
    for i, f in enumerate(frames):
        r = math.radians(deg(i) if callable(deg) else deg)
        R = np.array([[math.cos(r), 0, math.sin(r)], [0, 1, 0], [-math.sin(r), 0, math.cos(r)]])
        out.append({**f, "world_landmarks": {k: (R @ np.array(v)).tolist() for k, v in f["world_landmarks"].items()}})
    return out


def run_then_turn(turn_deg):
    frames = run_frames(cadence_spm=170, seconds=8)
    n = len(frames)

    def heading(i):
        s = min(max((i - 0.4 * n) / (0.2 * n), 0.0), 1.0)
        return turn_deg * (3 * s * s - 2 * s ** 3)

    return yaw(frames, heading)


def classify(frames):
    t = build_track(frames, FPS)
    return classify_movement(clean_track(t), {}, t.fps_eff)


def mv(c):
    return c["evidence"]["movement"]


# ------------------------------------ movement type -------------------------------------

def test_squat_is_squatting_and_side_on():
    c = classify(squat_frames())
    assert (c["movement_type"], c["camera_view"]) == ("squatting", "sagittal")
    assert c["confidence"] >= 0.9 and mv(c)["n_reps"] == 5


@pytest.mark.parametrize("cadence, expected", [(150, "running"), (170, "running"), (230, "sprinting"), (260, "sprinting")])
def test_gait_cadence_separates_running_from_sprinting(cadence, expected):
    c = classify(run_frames(cadence_spm=cadence, seconds=6))
    assert c["movement_type"] == expected and c["confidence"] >= 0.9
    assert mv(c)["cadence_spm"] == pytest.approx(cadence, rel=0.06)


def test_strides_whose_mean_knee_angle_oscillates_are_gait_not_repetitions():
    c = classify(stride_frames())
    assert c["movement_type"] == "running" and c["confidence"] >= 0.9
    assert mv(c)["n_reps"] >= 3 and mv(c)["scores"]["rep"] == 0.0  # reps exist; the anti-phase legs veto them


def test_cadence_on_the_running_sprinting_boundary_is_low_confidence():
    assert classify(run_frames(cadence_spm=200, seconds=6))["confidence"] < 0.5


def test_jump_and_landing_are_one_explosive_group_with_a_weak_exact_type():
    for frames, expected in ((jump_frames(), "jumping"), (landing_frames(), "landing")):
        c = classify(frames)
        assert c["movement_type"] == expected
        assert mv(c)["confidence"] <= 0.6 < 0.7 <= mv(c)["group_confidence"]  # exact type never certain


def test_trunk_rotation_swing_is_a_throw():
    c = classify(throw_frames())
    assert c["movement_type"] == "throwing" and c["confidence"] >= 0.9
    assert mv(c)["trunk_rotation_range_deg"] > 90


def test_a_small_trunk_swing_is_only_a_weak_throw():
    assert classify(throw_frames(amp_deg=22))["confidence"] < 0.5


def test_depth_noise_alone_is_not_a_throw():
    """White landmark noise inflates the raw shoulder-vs-pelvis yaw range; only a smooth swing may count."""
    assert classify(squat_frames(noise_m=0.06, seed=1))["movement_type"] == "squatting"
    assert classify(run_frames(seconds=6, noise_m=0.06, seed=1))["movement_type"] == "running"


def test_feet_shuffling_through_a_squat_is_not_a_run():
    """The ankle-separation detector fires, but squat knees move IN phase and stride knees in anti-phase."""
    c = classify(shuffle_feet(squat_frames()))
    assert c["movement_type"] == "squatting" and c["confidence"] >= 0.9


def test_standing_still_is_unknown():
    c = classify(squat_frames(n_reps=0, lead_s=1.5, tail_s=1.5))
    assert c["movement_type"] == "unknown" and c["confidence"] == 0.0


@pytest.mark.parametrize("turn, expected_cap", [(90, 0.6), (180, 0.6)])
def test_pelvis_heading_change_while_running_reads_as_cutting_with_capped_confidence(turn, expected_cap):
    c = classify(run_then_turn(turn))
    assert c["movement_type"] == "cutting" and 0 < mv(c)["confidence"] <= expected_cap
    assert mv(c)["heading_change_deg"] > 80


@pytest.mark.parametrize("name, frames, expected", [
    ("2 cm noise", squat_frames(noise_m=0.02, seed=3), "squatting"),
    ("occluded leg", occlude_leg(squat_frames(), "right"), "squatting"),
    ("dropped frames", drop_frames(squat_frames(), every=9), "squatting"),
    ("running 2 cm noise", run_frames(seconds=6, noise_m=0.02, seed=2), "running"),
    ("running dropped frames", drop_frames(run_frames(seconds=6), every=9), "running"),
    ("throw 2 cm noise", throw_frames(noise_m=0.02, seed=1), "throwing"),
])
def test_survives_recording_problems(name, frames, expected):
    assert classify(frames)["movement_type"] == expected, name


# ------------------------------------- camera view --------------------------------------

@pytest.mark.parametrize("maker", [squat_frames, lambda: run_frames(seconds=6)])
@pytest.mark.parametrize("deg, expected", [(0, "sagittal"), (45, "other"), (90, "frontal")])
def test_camera_view_from_hip_line_and_travel_axis(maker, deg, expected):
    c = classify(yaw(maker(), deg))
    assert c["camera_view"] == expected
    assert c["evidence"]["view"]["confidence"] >= 0.9


def test_view_confidence_fades_near_a_bin_boundary():
    assert classify(yaw(squat_frames(), 31))["evidence"]["view"]["confidence"] < 0.2


# ------------------------------------ robustness ----------------------------------------

def test_series_alone_still_finds_a_squat_but_not_a_view():
    knee = np.concatenate([_still(.5), _seg(0, 100, 1), _seg(100, 0, 1)] * 3)
    c = classify_movement(None, {"knee_flexion_angle_left": knee, "knee_flexion_angle_right": knee}, FPS)
    assert c["movement_type"] == "squatting" and c["camera_view"] == "unknown"
    assert c["confidence"] == 0.0  # confidence is the weaker verdict


@pytest.mark.parametrize("xyz, series, fps", [
    (None, None, 30), (np.zeros((5, 33, 3)), {}, 30), (np.full((60, 33, 3), np.nan), {}, 30),
    (np.zeros((60, 33, 3)), {}, None), (np.zeros((60, 33, 3)), {}, 0), (np.zeros((60, 5, 3)), {}, 30),
])
def test_unusable_input_is_unknown_not_a_crash(xyz, series, fps):
    c = classify_movement(xyz, series, fps)
    assert (c["movement_type"], c["camera_view"], c["confidence"]) == ("unknown", "unknown", 0.0)


@given(st.integers(0, 150), st.integers(0, 2 ** 32 - 1), st.floats(0, 0.6))
@settings(max_examples=40, deadline=None, suppress_health_check=list(HealthCheck))
def test_random_landmarks_never_crash_and_stay_bounded(n, seed, nan_frac):
    rng = np.random.default_rng(seed)
    xyz = rng.normal(0, 0.4, (n, 33, 3))
    xyz[rng.random(xyz.shape) < nan_frac] = np.nan
    c = classify_movement(xyz, {}, 30)
    assert c["movement_type"] in {"unknown", "squatting", "landing", "jumping", "running", "sprinting", "cutting", "throwing"}
    assert c["camera_view"] in {"unknown", "sagittal", "frontal", "other"}
    assert 0.0 <= c["confidence"] <= 1.0
    json.dumps(c)


# ------------------------------- label comparison (pure) --------------------------------

def test_matching_labels_agree_and_stay_quiet():
    r = compare_labels(classify(squat_frames()), "squatting", "sagittal")
    assert r["agrees"] == {"movement_type": True, "camera_view": True}
    assert r["suggested"] == {"movement_type": None, "camera_view": None} and r["warnings"] == []


def test_running_clip_labelled_squatting_warns_and_suggests_without_overriding():
    r = compare_labels(classify(run_frames(seconds=6)), "squatting", "sagittal")
    assert r["agrees"]["movement_type"] is False and r["suggested"]["movement_type"] == "running"
    assert [w["code"] for w in r["warnings"]] == ["classifier_movement_mismatch_suspected"]
    assert r["declared"]["movement_type"] == "squatting"  # the label is reported back untouched


def test_jump_clip_labelled_squatting_warns_at_group_level():
    r = compare_labels(classify(jump_frames()), "squatting", "sagittal")
    assert r["agrees"]["movement_type"] is False
    assert [w["code"] for w in r["warnings"]] == ["classifier_movement_mismatch_suspected"]


def test_a_different_label_inside_the_same_group_suggests_but_does_not_warn():
    r = compare_labels(classify(run_frames(cadence_spm=170, seconds=6)), "sprinting", "sagittal")
    assert r["suggested"]["movement_type"] == "running"
    assert r["agrees"]["movement_type"] is None and r["warnings"] == []


def test_wrong_camera_label_warns_and_suggests_the_detected_view():
    r = compare_labels(classify(squat_frames()), "squatting", "frontal")
    assert r["agrees"]["camera_view"] is False and r["suggested"]["camera_view"] == "sagittal"
    assert [w["code"] for w in r["warnings"]] == ["classifier_camera_view_mismatch_suspected"]


def test_other_view_label_claims_nothing_to_contradict_and_unknown_movements_are_not_judged():
    r = compare_labels(classify(yaw(squat_frames(), 90)), "sport_specific", "other")
    assert r["agrees"] == {"movement_type": None, "camera_view": None} and r["warnings"] == []


# ----------------------------- wired into analyze_frames --------------------------------

def _codes(analysis):
    return [w["code"] for w in analysis["quality"]["warnings"]]


def test_analyze_frames_reports_classification_and_correct_labels_stay_quiet():
    _, a = analyze_frames(squat_frames(), "squatting", "sagittal", 30)
    c = a["classification"]
    assert c["version"] == 1 and (c["movement_type"], c["camera_view"]) == ("squatting", "sagittal")
    assert c["agrees"] == {"movement_type": True, "camera_view": True}
    assert not [x for x in _codes(a) if x.startswith("classifier_")] and a["quality"]["grade"] == "good"
    json.loads(json.dumps(a))


def test_the_verdict_does_not_depend_on_the_label_it_checks():
    frames = run_frames(seconds=6)
    verdicts = []
    for label, view in (("running", "sagittal"), ("squatting", "sagittal"), ("throwing", "frontal"), ("sport_specific", "other")):
        _, a = analyze_frames(frames, label, view, 30)
        c = a["classification"]
        verdicts.append((c["movement_type"], c["camera_view"], c["confidence"], c["evidence"]))
    assert all(v == verdicts[0] for v in verdicts) and verdicts[0][0] == "running"


def test_mislabelled_run_gets_one_movement_warning_not_two_and_keeps_its_label():
    metrics, a = analyze_frames(run_frames(seconds=6), "squatting", "sagittal", 30)
    assert _codes(a).count("movement_type_mismatch_suspected") == 1  # the older stride-in-a-rep-clip warning
    assert "classifier_movement_mismatch_suspected" not in _codes(a)  # not repeated
    assert a["classification"]["agrees"]["movement_type"] is False
    assert a["classification"]["suggested"]["movement_type"] == "running"
    assert a["movement"]["movement_type"] == "squatting" and metrics  # analysed as labelled


def test_mislabelled_jump_gets_the_classifier_warning_and_is_still_analysed_as_labelled():
    metrics, a = analyze_frames(jump_frames(), "squatting", "sagittal", 30)
    assert "classifier_movement_mismatch_suspected" in _codes(a)
    assert a["movement"]["movement_type"] == "squatting" and metrics


def test_wrong_camera_label_warns_but_the_label_still_drives_the_metrics():
    metrics, a = analyze_frames(squat_frames(), "squatting", "frontal", 30)
    assert "classifier_camera_view_mismatch_suspected" in _codes(a)
    assert a["classification"]["suggested"]["camera_view"] == "sagittal"
    assert not [m for m in metrics if m["confidence"] == "validated"]  # frontal label: no sagittal angles, as before


def test_no_pose_data_has_no_classification():
    _, a = analyze_frames([], "squatting", "sagittal", 30)
    assert "classification" not in a
