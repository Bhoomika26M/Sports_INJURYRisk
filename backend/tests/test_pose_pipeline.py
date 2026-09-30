"""Pose pipeline biomechanics tests — movement calculators never crash on partial data."""

from app.modules.biomechanics.registry import get_calculator
from app.modules.pose.tasks import compute_biomechanics


def test_compute_biomechanics_missing_landmarks_does_not_crash():
    mock_frames = [{
        "frame_number": 0,
        "timestamp_ms": 0,
        "world_landmarks": {
            "11": [0.1, 0.2, 0.3],
            "12": [0.4, 0.5, 0.6],
        },
    }]
    metrics = compute_biomechanics(mock_frames, get_calculator("squatting"), "sagittal")
    assert metrics == []


def test_every_movement_calculator_handles_minimal_landmarks():
    minimal = {
        "11": [0.1, 0.2, 0.3], "12": [0.4, 0.5, 0.6],
        "23": [0.1, 0.0, 0.0], "24": [0.4, 0.0, 0.0],
        "25": [0.1, -0.4, 0.0], "26": [0.4, -0.4, 0.0],
        "27": [0.1, -0.8, 0.0], "28": [0.4, -0.8, 0.0],
    }
    frames = [{"frame_number": 0, "timestamp_ms": 0, "world_landmarks": minimal}]
    for movement in ["squatting", "landing", "running", "sprinting", "jumping", "throwing", "cutting"]:
        metrics = compute_biomechanics(frames, get_calculator(movement), "sagittal")
        assert isinstance(metrics, list)
        assert len(metrics) > 0, f"{movement} produced no metrics"
        for m in metrics:
            assert m["confidence"] in ("validated", "qualitative")
