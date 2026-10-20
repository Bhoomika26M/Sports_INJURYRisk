import numpy as np

from app.services import biomechanics as bm
from app.services.pose_estimation import JOINT_NAMES
from tests.synthetic import make_sequence


def test_angle_between_right_angle():
    a, b, c = np.array([[0.0, 1.0]]), np.array([[0.0, 0.0]]), np.array([[1.0, 0.0]])
    assert abs(bm.angle_between(a, b, c)[0] - 90.0) < 1e-6


def test_angle_between_straight_line():
    a, b, c = np.array([[0.0, 1.0]]), np.array([[0.0, 0.0]]), np.array([[0.0, -1.0]])
    # arccos is ill-conditioned near +/-1, so allow a hundredth of a degree
    assert abs(bm.angle_between(a, b, c)[0] - 180.0) < 0.01


def test_symmetry_index():
    assert bm.symmetry_index(10, 10) == 0
    assert abs(bm.symmetry_index(10, 5) - 66.666) < 0.01
    assert bm.symmetry_index(0, 0) == 0


def test_interpolate_nans_fills_gaps():
    P = make_sequence(frames=30)
    P[10:15, 3, :] = np.nan
    filled = bm.interpolate_nans(P)
    assert not np.isnan(filled).any()


def test_valgus_detected_vs_neutral():
    neutral = bm.analyze_biomechanics(make_sequence(valgus_offset=0.0), 30)
    valgus = bm.analyze_biomechanics(make_sequence(valgus_offset=0.04), 30)
    assert valgus["metrics"]["knee_valgus_peak_deg"] > neutral["metrics"]["knee_valgus_peak_deg"] + 3


def test_asymmetry_increases_symmetry_index():
    sym = bm.analyze_biomechanics(make_sequence(left_rom_scale=1.0), 30)
    asym = bm.analyze_biomechanics(make_sequence(left_rom_scale=0.4), 30)
    assert asym["symmetry"]["knee_flexion_rom_si"] > sym["symmetry"]["knee_flexion_rom_si"] + 10


def test_pelvic_drop_detected():
    flat = bm.analyze_biomechanics(make_sequence(pelvic_drop=0.0), 30)
    tilted = bm.analyze_biomechanics(make_sequence(pelvic_drop=0.04), 30)
    assert tilted["metrics"]["hip_stability_pelvic_drop_deg"] > flat["metrics"]["hip_stability_pelvic_drop_deg"] + 3


def test_repetitions_counted():
    result = bm.analyze_biomechanics(make_sequence(squat_reps=4), 30)
    assert 3 <= result["repetitions"]["count"] <= 5


def test_output_is_json_serialisable():
    import json

    result = bm.analyze_biomechanics(make_sequence(), 30, height_cm=180, weight_kg=75)
    json.dumps(result)  # raises if NaN objects or numpy types leak through
    assert result["force_estimate"] is not None


def test_missing_joints_raise_clear_error():
    P = make_sequence()
    P[:, JOINT_NAMES.index("left_knee"), :] = np.nan
    try:
        bm.analyze_biomechanics(P, 30)
    except ValueError as exc:
        assert "left knee" in str(exc) and "never clearly visible" in str(exc)
    else:
        raise AssertionError("expected ValueError")
