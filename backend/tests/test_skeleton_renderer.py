import pytest
import numpy as np
from app.visualization.skeleton_renderer import SkeletonRenderer
from app.pose.estimator import Keypoint


def test_skeleton_renderer_initialization():
    """Test skeleton renderer initialization."""
    renderer = SkeletonRenderer()
    
    assert renderer.keypoint_radius == 4
    assert renderer.confidence_threshold == 0.3


def test_skeleton_renderer_render():
    """Test skeleton rendering on frame."""
    renderer = SkeletonRenderer()
    
    # Create test frame
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Create test keypoints
    keypoints = [
        Keypoint(x=100, y=100, confidence=0.9, name="left_shoulder"),
        Keypoint(x=200, y=100, confidence=0.9, name="right_shoulder"),
        Keypoint(x=100, y=200, confidence=0.9, name="left_elbow"),
        Keypoint(x=200, y=200, confidence=0.9, name="right_elbow"),
        Keypoint(x=100, y=300, confidence=0.9, name="left_wrist"),
        Keypoint(x=200, y=300, confidence=0.9, name="right_wrist"),
    ]
    
    # Render
    annotated = renderer.render(frame, keypoints)
    
    # Check that frame is modified
    assert annotated.shape == frame.shape
    assert not np.array_equal(annotated, frame)


def test_skeleton_renderer_with_bbox():
    """Test skeleton rendering with bounding box."""
    renderer = SkeletonRenderer()
    
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    keypoints = [
        Keypoint(x=100, y=100, confidence=0.9, name="left_shoulder"),
    ]
    bbox = (50, 50, 250, 350)
    
    annotated = renderer.render(frame, keypoints, bbox=bbox, track_id=1)
    
    assert annotated.shape == frame.shape


def test_skeleton_renderer_confidence_filtering():
    """Test that low-confidence keypoints are not rendered."""
    renderer = SkeletonRenderer()
    
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    keypoints = [
        Keypoint(x=100, y=100, confidence=0.9, name="left_shoulder"),
        Keypoint(x=200, y=100, confidence=0.2, name="right_shoulder"),  # Below threshold
    ]
    
    annotated = renderer.render(frame, keypoints)
    
    assert annotated.shape == frame.shape


def test_skeleton_renderer_landmark_index_mapping():
    """Test BlazePose landmark index mapping."""
    renderer = SkeletonRenderer()
    
    # Test known mappings
    assert renderer.get_landmark_index("nose") == 0
    assert renderer.get_landmark_index("left_shoulder") == 11
    assert renderer.get_landmark_index("right_shoulder") == 12
    assert renderer.get_landmark_index("left_knee") == 25
    assert renderer.get_landmark_index("right_knee") == 26
    
    # Test reverse mapping
    assert renderer.get_landmark_name(0) == "nose"
    assert renderer.get_landmark_name(11) == "left_shoulder"
    assert renderer.get_landmark_name(25) == "left_knee"
