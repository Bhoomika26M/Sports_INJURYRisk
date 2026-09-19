import pytest
from app.modules.pose.tasks import compute_biomechanics

def test_compute_biomechanics_missing_landmarks_does_not_crash():
    # Provide a frame that is missing the "23" key entirely, simulating a severe partial detection
    mock_frames = [{
        "frame_number": 0,
        "timestamp_ms": 0,
        "world_landmarks": {
            # left_shoulder and right_shoulder exist, but no hips/knees
            "11": [0.1, 0.2, 0.3],
            "12": [0.4, 0.5, 0.6]
        }
    }]
    
    # Pre-fix, this raises KeyError. Post-fix, it should return an empty list and log a warning.
    metrics = compute_biomechanics(mock_frames, "sagittal")
    assert metrics == []
