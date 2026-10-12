import pytest
import numpy as np
from app.services.processing_service import VideoProcessingService
from app.pose.estimator import Keypoint


def test_movement_quality_uses_actual_data():
    """
    Test that movement quality score changes based on actual measurements.
    
    This test proves that the score is NOT a fixed default (e.g., 75.0)
    but is calculated from actual biomechanical measurements.
    """
    service = VideoProcessingService()
    
    # Create two different sets of keypoints with different characteristics
    
    # Set 1: High quality (good symmetry, low trunk lean, good ROM)
    high_quality_keypoints = []
    for _ in range(30):
        keypoints = [
            Keypoint(x=100, y=100, confidence=0.95, name="left_hip"),
            Keypoint(x=200, y=100, confidence=0.95, name="right_hip"),
            Keypoint(x=100, y=200, confidence=0.95, name="left_knee"),
            Keypoint(x=200, y=200, confidence=0.95, name="right_knee"),
            Keypoint(x=100, y=300, confidence=0.95, name="left_ankle"),
            Keypoint(x=200, y=300, confidence=0.95, name="right_ankle"),
            Keypoint(x=100, y=50, confidence=0.95, name="left_shoulder"),
            Keypoint(x=200, y=50, confidence=0.95, name="right_shoulder"),
        ]
        high_quality_keypoints.append(keypoints)
    
    # Set 2: Low quality (poor symmetry, high trunk lean, poor ROM, low confidence)
    low_quality_keypoints = []
    for _ in range(30):
        keypoints = [
            Keypoint(x=100, y=100, confidence=0.2, name="left_hip"),  # Below threshold
            Keypoint(x=250, y=100, confidence=0.2, name="right_hip"),  # Asymmetric, below threshold
            Keypoint(x=100, y=200, confidence=0.2, name="left_knee"),  # Below threshold
            Keypoint(x=250, y=200, confidence=0.2, name="right_knee"),  # Asymmetric, below threshold
            Keypoint(x=100, y=300, confidence=0.2, name="left_ankle"),  # Below threshold
            Keypoint(x=250, y=300, confidence=0.2, name="right_ankle"),  # Asymmetric, below threshold
            Keypoint(x=120, y=50, confidence=0.2, name="left_shoulder"),  # Trunk lean, below threshold
            Keypoint(x=220, y=50, confidence=0.2, name="right_shoulder"),  # Below threshold
        ]
        low_quality_keypoints.append(keypoints)
    
    # Calculate pose quality for both
    high_quality_pose = service._calculate_pose_quality(high_quality_keypoints)
    low_quality_pose = service._calculate_pose_quality(low_quality_keypoints)
    
    # Calculate movement quality for both
    high_quality_movement = service._calculate_movement_quality(
        [90.0] * 30,  # left_knee_angles (simulated - symmetric)
        [90.0] * 30,  # right_knee_angles (simulated - symmetric)
        [5.0] * 30,   # trunk_lean_angles (simulated - low lean)
        high_quality_pose
    )
    
    low_quality_movement = service._calculate_movement_quality(
        [90.0] * 30,  # left_knee_angles (simulated)
        [70.0] * 30,  # right_knee_angles (asymmetric)
        [25.0] * 30,  # trunk_lean_angles (high lean)
        low_quality_pose
    )
    
    # Assert that scores are different
    assert high_quality_movement["score"] != low_quality_movement["score"], \
        "Movement quality scores should differ based on input data"
    
    # Assert that high quality has higher score
    assert high_quality_movement["score"] > low_quality_movement["score"], \
        "High quality movement should have higher score than low quality"
    
    # Assert that component scores are different
    assert high_quality_movement["components"]["confidence"] != \
           low_quality_movement["components"]["confidence"], \
           "Confidence scores should differ"
    
    assert high_quality_movement["components"]["symmetry"] != \
           low_quality_movement["components"]["symmetry"], \
           "Symmetry scores should differ"
    
    assert high_quality_movement["components"]["alignment"] != \
           low_quality_movement["components"]["alignment"], \
           "Alignment scores should differ"
    
    # Assert that neither score is a fixed default like 75.0
    assert high_quality_movement["score"] != 75.0, \
        "High quality score should not be a fixed default"
    assert low_quality_movement["score"] != 75.0, \
        "Low quality score should not be a fixed default"
    
    # Assert that raw measurements are included
    assert "raw_measurements" in high_quality_movement
    assert "raw_measurements" in low_quality_movement
    assert high_quality_movement["raw_measurements"] != \
           low_quality_movement["raw_measurements"]
    
    print(f"High quality score: {high_quality_movement['score']}")
    print(f"Low quality score: {low_quality_movement['score']}")
    print(f"High quality components: {high_quality_movement['components']}")
    print(f"Low quality components: {low_quality_movement['components']}")


def test_movement_quality_components_are_exposed():
    """
    Test that all movement quality components are exposed.
    """
    service = VideoProcessingService()
    
    # Create sample keypoints
    keypoints_sequence = []
    for _ in range(10):
        keypoints = [
            Keypoint(x=100, y=100, confidence=0.9, name="left_hip"),
            Keypoint(x=200, y=100, confidence=0.9, name="right_hip"),
            Keypoint(x=100, y=200, confidence=0.9, name="left_knee"),
            Keypoint(x=200, y=200, confidence=0.9, name="right_knee"),
            Keypoint(x=100, y=300, confidence=0.9, name="left_ankle"),
            Keypoint(x=200, y=300, confidence=0.9, name="right_ankle"),
            Keypoint(x=100, y=50, confidence=0.9, name="left_shoulder"),
            Keypoint(x=200, y=50, confidence=0.9, name="right_shoulder"),
        ]
        keypoints_sequence.append(keypoints)
    
    pose_quality = service._calculate_pose_quality(keypoints_sequence)
    
    movement_quality = service._calculate_movement_quality(
        [90.0] * 10,
        [90.0] * 10,
        [5.0] * 10,
        pose_quality
    )
    
    # Assert all required components are present
    assert "score" in movement_quality
    assert "components" in movement_quality
    assert "weights" in movement_quality
    assert "raw_measurements" in movement_quality
    
    # Assert all component scores are present
    components = movement_quality["components"]
    assert "confidence" in components
    assert "symmetry" in components
    assert "alignment" in components
    assert "stability" in components
    assert "rom" in components
    assert "smoothness" in components
    
    # Assert all weights are present
    weights = movement_quality["weights"]
    assert "confidence" in weights
    assert "symmetry" in weights
    assert "alignment" in weights
    assert "stability" in weights
    assert "rom" in weights
    assert "smoothness" in weights
    
    # Assert weights sum to 1.0
    total_weight = sum(weights.values())
    assert abs(total_weight - 1.0) < 0.01, \
        f"Weights should sum to 1.0, got {total_weight}"
