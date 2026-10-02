"""Vertical-axis audit of every biomechanics calculation.

MediaPipe WORLD landmarks: origin at the hip midpoint, +Y points DOWN (documented real data: head y~-0.6,
hip ~0, ankle ~+0.75). Poses here are built in that frame. Only trunk lean depends on the sign of the
vertical axis; every other calculation must be invariant to it (and to the frontal-plane axis choice).

Limitation: these are synthetic poses built from the documented real orientation, not stored real landmarks
(no database or clip was available when this was written).
"""

import numpy as np
import pytest

from app.modules.biomechanics.calculations import hip_flexion_angle, knee_flexion_angle, trunk_lean_angle
from app.modules.biomechanics.jumping import JumpingCalculator
from app.modules.biomechanics.running import RunningCalculator
from app.modules.biomechanics.squatting import SquattingCalculator
from app.modules.biomechanics.throwing import ThrowingCalculator


def pose(d):
    lm = {str(i): [0.0, 0.0, 0.0] for i in range(33)}
    lm.update({str(k): list(v) for k, v in d.items()})
    return lm


STANDING = pose({0: (0, -0.65, 0), 11: (0.2, -0.5, 0), 12: (-0.2, -0.5, 0), 23: (0.1, 0, 0), 24: (-0.1, 0, 0),
                 25: (0.1, 0.4, 0), 26: (-0.1, 0.4, 0), 27: (0.1, 0.78, 0), 28: (-0.1, 0.78, 0)})
SQUAT = pose({0: (0, -0.45, -0.3), 11: (0.2, -0.4, -0.2), 12: (-0.2, -0.4, -0.2), 23: (0.1, 0, 0), 24: (-0.1, 0, 0),
              25: (0.1, 0.1, -0.35), 26: (-0.1, 0.1, -0.35), 27: (0.1, 0.45, -0.05), 28: (-0.1, 0.45, -0.05)})


def flip_y(lm):
    return {k: [x, -y, z] for k, (x, y, z) in lm.items()}


def test_trunk_lean_is_zero_upright_and_modest_in_a_squat_in_the_y_down_frame():
    assert trunk_lean_angle(STANDING) == 0.0
    assert 20.0 < trunk_lean_angle(SQUAT) < 35.0          # measured 26.6


def test_trunk_lean_is_the_only_calculation_that_depends_on_the_vertical_axis_sign():
    """Flipping Y turns upright into 180 deg: the exact signature of the bug fixed in 0e7d137."""
    assert trunk_lean_angle(flip_y(STANDING)) == 180.0
    for side in ("left", "right"):
        for lm in (STANDING, SQUAT):
            assert knee_flexion_angle(flip_y(lm), side) == knee_flexion_angle(lm, side)
            assert hip_flexion_angle(flip_y(lm), side) == hip_flexion_angle(lm, side)


def test_knee_flexion_is_zero_standing_and_deep_in_a_squat():
    assert knee_flexion_angle(STANDING, "left") == 0.0
    assert 90.0 < knee_flexion_angle(SQUAT, "left") < 130.0   # measured 114.7


@pytest.mark.parametrize("calculator", [SquattingCalculator, RunningCalculator, JumpingCalculator, ThrowingCalculator])
@pytest.mark.parametrize("view", ["sagittal", "frontal"])
def test_every_calculator_output_is_finite_and_tiered_correctly(calculator, view):
    for lm in (STANDING, SQUAT):
        for m in calculator().compute_all(lm, view):
            assert np.isfinite(m["value"]), m
            assert m["confidence"] in ("validated", "qualitative")
            if m["confidence"] == "validated":
                assert m["plane"] != "frontal", f"frontal-plane metric must never be 'validated': {m}"
            if "trunk_lean" in m["name"]:
                assert 0.0 <= m["value"] <= 90.0, m


def test_knee_valgus_is_only_ever_a_qualitative_flag_never_a_precise_angle():
    for view in ("frontal", "other"):
        for m in SquattingCalculator().compute_all(SQUAT, view):
            if "valgus" in m["name"]:
                assert m["confidence"] == "qualitative" and m["plane"] == "frontal"


def test_hip_flexion_documented_convention_mismatch_is_pinned_not_hidden():
    """OPEN QUESTION (docs/DECISIONS.md 2026-09-30): this returns the interior shoulder-hip-knee angle
    (~169 standing, falling with flexion) although the docstring says 0 = extended, larger = more flexed.
    Pinned so a change is deliberate, not accidental."""
    assert hip_flexion_angle(STANDING, "left") > 150.0
    assert hip_flexion_angle(SQUAT, "left") < hip_flexion_angle(STANDING, "left")
