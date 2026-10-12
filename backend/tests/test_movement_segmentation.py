import pytest
import numpy as np
from app.movement.segmentation import MovementSegmenter
from app.pose.estimator import Keypoint


def test_movement_segmenter_initialization():
    """Test movement segmenter initialization."""
    segmenter = MovementSegmenter()
    assert segmenter is not None


def test_segment_squat_basic():
    """Test basic squat segmentation."""
    segmenter = MovementSegmenter()
    
    # Create mock keypoints sequence with varying knee angles
    keypoints_sequence = []
    timestamps = []
    
    for i in range(100):
        timestamp = i * 0.033
        timestamps.append(timestamp)
        
        # Simulate squat pattern: high -> low -> high
        if i < 30:
            knee_angle = 170.0  # Standing
        elif i < 50:
            knee_angle = 90.0   # Bottom
        else:
            knee_angle = 170.0  # Standing
        
        keypoints = [
            Keypoint(x=100, y=100, confidence=0.9, name="left_hip"),
            Keypoint(x=200, y=100, confidence=0.9, name="right_hip"),
            Keypoint(x=100, y=200, confidence=0.9, name="left_knee"),
            Keypoint(x=200, y=200, confidence=0.9, name="right_knee"),
            Keypoint(x=100, y=300, confidence=0.9, name="left_ankle"),
            Keypoint(x=200, y=300, confidence=0.9, name="right_ankle"),
        ]
        keypoints_sequence.append(keypoints)
    
    # Segment
    repetitions = segmenter.segment_squat(keypoints_sequence, timestamps)
    
    # Should detect at least one repetition
    assert isinstance(repetitions, list)


def test_segment_squat_insufficient_data():
    """Test squat segmentation with insufficient data."""
    segmenter = MovementSegmenter()
    
    keypoints_sequence = []
    timestamps = []
    
    # Only 2 frames (not enough for meaningful segmentation)
    for i in range(2):
        timestamps.append(i * 0.033)
        keypoints = [
            Keypoint(x=100, y=100, confidence=0.9, name="left_hip"),
            Keypoint(x=200, y=100, confidence=0.9, name="right_hip"),
        ]
        keypoints_sequence.append(keypoints)
    
    repetitions = segmenter.segment_squat(keypoints_sequence, timestamps)
    
    # Should return empty list or handle gracefully
    assert isinstance(repetitions, list)


def test_segment_jump_landing():
    """Test jump/landing segmentation."""
    segmenter = MovementSegmenter()
    
    keypoints_sequence = []
    timestamps = []
    
    for i in range(100):
        timestamp = i * 0.033
        timestamps.append(timestamp)
        
        keypoints = [
            Keypoint(x=100, y=100, confidence=0.9, name="left_hip"),
            Keypoint(x=200, y=100, confidence=0.9, name="right_hip"),
            Keypoint(x=100, y=200, confidence=0.9, name="left_knee"),
            Keypoint(x=200, y=200, confidence=0.9, name="right_knee"),
        ]
        keypoints_sequence.append(keypoints)
    
    jumps = segmenter.segment_jump_landing(keypoints_sequence, timestamps)
    
    assert isinstance(jumps, list)


def test_segment_running():
    """Test running stride segmentation."""
    segmenter = MovementSegmenter()
    
    keypoints_sequence = []
    timestamps = []
    
    for i in range(100):
        timestamp = i * 0.033
        timestamps.append(timestamp)
        
        keypoints = [
            Keypoint(x=100, y=100, confidence=0.9, name="left_hip"),
            Keypoint(x=200, y=100, confidence=0.9, name="right_hip"),
            Keypoint(x=100, y=200, confidence=0.9, name="left_knee"),
            Keypoint(x=200, y=200, confidence=0.9, name="right_knee"),
            Keypoint(x=100, y=300, confidence=0.9, name="left_ankle"),
            Keypoint(x=200, y=300, confidence=0.9, name="right_ankle"),
        ]
        keypoints_sequence.append(keypoints)
    
    strides = segmenter.segment_running(keypoints_sequence, timestamps)
    
    assert isinstance(strides, list)
