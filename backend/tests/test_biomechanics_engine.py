import pytest
from app.utils.biomechanics import (
    calculate_angle_2d,
    calculate_trunk_lean,
    calculate_lateral_trunk_lean,
    calculate_pelvic_drop,
    calculate_knee_valgus,
    calculate_stride_length,
    calculate_center_of_mass,
    calculate_cervical_posture,
    process_frame_biomechanics
)

def test_joint_angles_comprehensive():
    # 90 degree knee flexion
    hip = {"x": 0.5, "y": 0.4, "visibility": 0.9}
    knee = {"x": 0.5, "y": 0.7, "visibility": 0.9}
    ankle = {"x": 0.8, "y": 0.7, "visibility": 0.9}
    
    angle = calculate_angle_2d(hip, knee, ankle, 1000, 1000)
    assert 89.0 <= angle <= 91.0

def test_knee_valgus_and_fppa():
    l_hip = {"x": 0.45, "y": 0.5, "visibility": 0.9}
    r_hip = {"x": 0.55, "y": 0.5, "visibility": 0.9}
    # Inward collapsed knees (distance 0.04) vs wide ankles (distance 0.20)
    l_knee_valgus = {"x": 0.48, "y": 0.75, "visibility": 0.9}
    r_knee_valgus = {"x": 0.52, "y": 0.75, "visibility": 0.9}
    l_ankle = {"x": 0.40, "y": 1.0, "visibility": 0.9}
    r_ankle = {"x": 0.60, "y": 1.0, "visibility": 0.9}
    
    valgus_ratio, l_fppa, r_fppa = calculate_knee_valgus(
        l_hip, r_hip, l_knee_valgus, r_knee_valgus, l_ankle, r_ankle, 1000, 1000
    )
    assert valgus_ratio is not None
    assert valgus_ratio < 0.85 # Dynamic valgus collapse detected!

def test_hip_stability_pelvic_drop():
    # Unlevel hips: right hip dropped significantly
    l_hip = {"x": 0.4, "y": 0.50, "visibility": 0.9}
    r_hip = {"x": 0.6, "y": 0.56, "visibility": 0.9} # dropped down
    
    drop = calculate_pelvic_drop(l_hip, r_hip, 1000, 1000)
    assert drop is not None
    assert drop > 10.0 # Excessive Trendelenburg drop detected

def test_posture_and_cervical_assessment():
    l_sh = {"x": 0.4, "y": 0.3, "visibility": 0.9}
    r_sh = {"x": 0.6, "y": 0.3, "visibility": 0.9}
    l_hp = {"x": 0.4, "y": 0.7, "visibility": 0.9}
    r_hp = {"x": 0.6, "y": 0.7, "visibility": 0.9}
    
    # Forward head: nose displaced forward
    nose = {"x": 0.7, "y": 0.15, "visibility": 0.9}
    cervical = calculate_cervical_posture(nose, l_sh, r_sh, 1000, 1000)
    assert cervical is not None
    assert cervical > 20.0

def test_stride_and_center_of_mass():
    l_hp = {"x": 0.45, "y": 0.5, "visibility": 0.9}
    r_hp = {"x": 0.55, "y": 0.5, "visibility": 0.9}
    l_ak = {"x": 0.20, "y": 1.0, "visibility": 0.9}
    r_ak = {"x": 0.80, "y": 1.0, "visibility": 0.9}
    
    stride = calculate_stride_length(l_ak, r_ak, l_hp, r_hp, 1000, 1000)
    assert stride is not None
    assert stride > 1.0 # High stride extension
    
    landmarks = [
        {"name": "left_shoulder", "x": 0.45, "y": 0.2, "visibility": 0.9},
        {"name": "right_shoulder", "x": 0.55, "y": 0.2, "visibility": 0.9},
        {"name": "left_hip", "x": 0.45, "y": 0.5, "visibility": 0.9},
        {"name": "right_hip", "x": 0.55, "y": 0.5, "visibility": 0.9},
        {"name": "left_knee", "x": 0.45, "y": 0.75, "visibility": 0.9},
        {"name": "right_knee", "x": 0.55, "y": 0.75, "visibility": 0.9},
        {"name": "left_ankle", "x": 0.45, "y": 1.0, "visibility": 0.9},
        {"name": "right_ankle", "x": 0.55, "y": 1.0, "visibility": 0.9}
    ]
    com_x, com_y = calculate_center_of_mass(landmarks, 1000, 1000)
    assert com_x is not None and com_y is not None
    assert 450 <= com_x <= 550
