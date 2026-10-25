import pytest
from app.utils.biomechanics import calculate_angle_2d, calculate_trunk_lean, process_frame_biomechanics

def test_calculate_angle_2d():
    # Right angle
    a = {"x": 1.0, "y": 0.0, "visibility": 0.9}
    b = {"x": 0.0, "y": 0.0, "visibility": 0.9}
    c = {"x": 0.0, "y": 1.0, "visibility": 0.9}
    
    angle = calculate_angle_2d(a, b, c, 100, 100)
    assert 89 < angle < 91
    
    # Straight line
    a2 = {"x": -1.0, "y": 0.0, "visibility": 0.9}
    angle2 = calculate_angle_2d(a2, b, a, 100, 100)
    assert 179 < angle2 <= 180
    
    # Low visibility
    a_low = {"x": 1.0, "y": 0.0, "visibility": 0.2}
    angle3 = calculate_angle_2d(a_low, b, c, 100, 100)
    assert angle3 is None

def test_calculate_trunk_lean():
    # Vertical posture (mid shoulder at x=0.5, y=0.2; mid hip at x=0.5, y=0.8)
    l_shoulder = {"x": 0.4, "y": 0.2, "visibility": 0.9}
    r_shoulder = {"x": 0.6, "y": 0.2, "visibility": 0.9}
    l_hip = {"x": 0.4, "y": 0.8, "visibility": 0.9}
    r_hip = {"x": 0.6, "y": 0.8, "visibility": 0.9}
    
    lean = calculate_trunk_lean(l_shoulder, r_shoulder, l_hip, r_hip, 100, 100)
    assert 0 <= lean < 1  # Almost perfect 0 lean
    
    # Leaning right (mid shoulder at x=0.8, y=0.2; mid hip at x=0.5, y=0.8)
    r_shoulder_lean = {"x": 1.2, "y": 0.2, "visibility": 0.9}
    lean2 = calculate_trunk_lean(l_shoulder, r_shoulder_lean, l_hip, r_hip, 100, 100)
    assert lean2 > 10  # Significant lean

def test_process_frame_biomechanics():
    frame = {
        "timestamp_ms": 100,
        "landmarks": [
            {"name": "left_hip", "x": 0.5, "y": 0.5, "visibility": 0.9},
            {"name": "right_hip", "x": 0.5, "y": 0.5, "visibility": 0.9},
            {"name": "left_knee", "x": 0.5, "y": 0.7, "visibility": 0.9},
            {"name": "right_knee", "x": 0.5, "y": 0.7, "visibility": 0.9},
            {"name": "left_ankle", "x": 0.5, "y": 0.9, "visibility": 0.9},
            {"name": "right_ankle", "x": 0.5, "y": 0.9, "visibility": 0.9},
            {"name": "left_shoulder", "x": 0.4, "y": 0.2, "visibility": 0.9},
            {"name": "right_shoulder", "x": 0.6, "y": 0.2, "visibility": 0.9}
        ]
    }
    
    metrics = process_frame_biomechanics(frame, 100, 100)
    assert metrics["quality_flag"] == "OK"
    assert metrics["timestamp_ms"] == 100
    assert metrics["left_knee_angle"] is not None
    assert metrics["trunk_lean"] is not None
