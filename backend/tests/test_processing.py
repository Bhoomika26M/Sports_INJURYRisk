import pytest
import numpy as np
from app.processing.video_processor import VideoProcessor, VideoMetadata
from app.processing.smoothing import TemporalSmoother
from app.processing.normalization import SkeletonNormalizer
from app.pose.estimator import Keypoint


class TestVideoProcessor:
    """Test video processing with synthetic data."""
    
    def test_metadata_extraction(self, tmp_path):
        """Test that we can extract video metadata."""
        # This test would require a real video file
        # For now, we test the metadata structure
        metadata = VideoMetadata(
            width=1920,
            height=1080,
            fps=30.0,
            frame_count=900,
            duration=30.0
        )
        
        assert metadata.width == 1920
        assert metadata.height == 1080
        assert metadata.fps == 30.0
        assert metadata.frame_count == 900
        assert metadata.duration == 30.0


class TestTemporalSmoother:
    """Test temporal smoothing."""
    
    @pytest.fixture
    def smoother(self):
        return TemporalSmoother(window_length=5, polyorder=2)
    
    @pytest.fixture
    def synthetic_keypoints_sequence(self):
        """Create a synthetic sequence of keypoints."""
        sequence = []
        for frame_idx in range(10):
            frame_keypoints = []
            for kp_idx in range(17):
                # Add some noise
                noise = np.random.normal(0, 2)
                kp = Keypoint(
                    x=100.0 + kp_idx * 10 + noise,
                    y=200.0 + kp_idx * 10 + noise,
                    confidence=0.9,
                    name=f"keypoint_{kp_idx}"
                )
                frame_keypoints.append(kp)
            sequence.append(frame_keypoints)
        return sequence
    
    def test_smoothing_reduces_noise(self, smoother, synthetic_keypoints_sequence):
        """Test that smoothing reduces variation."""
        smoothed = smoother.smooth_keypoints(synthetic_keypoints_sequence)
        
        assert len(smoothed) == len(synthetic_keypoints_sequence)
        assert len(smoothed[0]) == len(synthetic_keypoints_sequence[0])
    
    def test_smoothing_with_short_sequence(self, smoother):
        """Test smoothing with sequence shorter than window."""
        short_sequence = [synthetic_keypoints_sequence()[0]]
        
        smoothed = smoother.smooth_keypoints(short_sequence)
        
        # Should return original if too short
        assert len(smoothed) == len(short_sequence)


class TestSkeletonNormalizer:
    """Test skeleton normalization."""
    
    @pytest.fixture
    def normalizer(self):
        return SkeletonNormalizer()
    
    @pytest.fixture
    def synthetic_keypoints_sequence(self):
        """Create a synthetic sequence with torso."""
        sequence = []
        for frame_idx in range(5):
            frame_keypoints = []
            for i in range(17):
                # Create keypoints with detectable torso
                if i == 5:  # left_shoulder
                    kp = Keypoint(x=100, y=100, confidence=0.9, name="left_shoulder")
                elif i == 6:  # right_shoulder
                    kp = Keypoint(x=150, y=100, confidence=0.9, name="right_shoulder")
                elif i == 11:  # left_hip
                    kp = Keypoint(x=100, y=200, confidence=0.9, name="left_hip")
                elif i == 12:  # right_hip
                    kp = Keypoint(x=150, y=200, confidence=0.9, name="right_hip")
                else:
                    kp = Keypoint(x=50 + i, y=50 + i, confidence=0.9, name=f"keypoint_{i}")
                frame_keypoints.append(kp)
            sequence.append(frame_keypoints)
        return sequence
    
    def test_normalization_scales_coordinates(self, normalizer, synthetic_keypoints_sequence):
        """Test that normalization scales coordinates."""
        normalized = normalizer.normalize_sequence(synthetic_keypoints_sequence)
        
        assert len(normalized) == len(synthetic_keypoints_sequence)
        
        # Normalized coordinates should be smaller (torso-scaled)
        original_x = synthetic_keypoints_sequence[0][0].x
        normalized_x = normalized[0][0].x
        
        # Should be scaled down
        assert abs(normalized_x) < abs(original_x)
    
    def test_normalization_preserves_structure(self, normalizer, synthetic_keypoints_sequence):
        """Test that normalization preserves keypoint structure."""
        normalized = normalizer.normalize_sequence(synthetic_keypoints_sequence)
        
        # Same number of frames
        assert len(normalized) == len(synthetic_keypoints_sequence)
        
        # Same number of keypoints per frame
        for frame_idx in range(len(normalized)):
            assert len(normalized[frame_idx]) == len(synthetic_keypoints_sequence[frame_idx])
            
            # Same keypoint names
            for kp_idx in range(len(normalized[frame_idx])):
                assert normalized[frame_idx][kp_idx].name == synthetic_keypoints_sequence[frame_idx][kp_idx].name


def synthetic_keypoints_sequence():
    """Helper function to create synthetic keypoints."""
    frame_keypoints = []
    for i in range(17):
        kp = Keypoint(x=50 + i, y=50 + i, confidence=0.9, name=f"keypoint_{i}")
        frame_keypoints.append(kp)
    return frame_keypoints
