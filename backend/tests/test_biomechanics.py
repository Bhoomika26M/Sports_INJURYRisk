import math
import numpy as np

from app.modules.biomechanics.calculations import (
    joint_angle,
    limb_symmetry_index,
    knee_flexion_angle,
    trunk_lean_angle,
    knee_valgus_flag,
    LANDMARK
)

def test_joint_angle_collinear():
    """Test near-collinear points that could cause acos(>1) without np.clip."""
    a = np.array([1.0000001, 0.0, 0.0])
    b = np.array([0.0, 0.0, 0.0])
    c = np.array([-1.0000001, 0.0, 0.0])
    
    angle = joint_angle(a, b, c)
    assert not math.isnan(angle), "Angle should not be NaN"
    assert math.isclose(angle, 180.0, abs_tol=1e-5), f"Expected ~180, got {angle}"

    # Another test specifically simulating floating point inaccuracy
    # where cos_theta could theoretically be 1.0000000000000002
    a = np.array([1.0, 1.0, 1.0])
    b = np.array([0.0, 0.0, 0.0])
    c = np.array([2.0, 2.0, 2.0])
    # a and c are in exactly the same direction from b, angle should be 0
    angle2 = joint_angle(a, b, c)
    assert not math.isnan(angle2), "Angle should not be NaN"
    assert math.isclose(angle2, 0.0, abs_tol=1e-5), f"Expected ~0, got {angle2}"

def test_limb_symmetry_index():
    """Test limb symmetry index calculations."""
    # Perfect symmetry
    assert limb_symmetry_index(100.0, 100.0) == 100.0
    
    # Left weaker
    assert limb_symmetry_index(80.0, 100.0) == 80.0
    
    # Right weaker
    assert limb_symmetry_index(100.0, 75.0) == 75.0
    
    # Zero edge case
    assert limb_symmetry_index(0.0, 0.0) == 100.0
    assert limb_symmetry_index(0.0, 50.0) == 0.0

def test_trunk_lean_angle_handles_degenerate_zero_norm():
    from app.modules.biomechanics.calculations import trunk_lean_angle
    degenerate = {"11": [0.0, 0.5, 0.0], "12": [0.0, 0.5, 0.0], "23": [0.0, 0.5, 0.0], "24": [0.0, 0.5, 0.0]}
    assert trunk_lean_angle(degenerate) is None  # must not raise, must not return NaN
