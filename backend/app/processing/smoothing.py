import numpy as np
from scipy.signal import savgol_filter
from typing import List, Dict
from app.pose.estimator import Keypoint


class TemporalSmoother:
    """
    Temporal smoothing for pose keypoints using Savitzky-Golay filter.
    
    Smooths keypoint trajectories over time to reduce noise while
    preserving the overall movement pattern.
    """
    
    def __init__(self, window_length: int = 5, polyorder: int = 2):
        """
        Initialize smoother.
        
        Args:
            window_length: Length of the filter window (must be odd)
            polyorder: Order of the polynomial used to fit the samples
        """
        self.window_length = window_length
        self.polyorder = polyorder
    
    def smooth_keypoints(self, keypoints_sequence: List[List[Keypoint]]) -> List[List[Keypoint]]:
        """
        Smooth a sequence of keypoints across frames.
        
        Args:
            keypoints_sequence: List of frame keypoints [frame_0, frame_1, ...]
                                where each frame is a list of 17 Keypoints
        
        Returns:
            Smoothed keypoints sequence
        """
        if len(keypoints_sequence) < self.window_length:
            # Not enough frames to smooth, return original
            return keypoints_sequence
        
        # Extract x, y, confidence for each keypoint across frames
        num_frames = len(keypoints_sequence)
        num_keypoints = len(keypoints_sequence[0])
        
        # Initialize arrays for smoothing
        x_data = np.zeros((num_frames, num_keypoints))
        y_data = np.zeros((num_frames, num_keypoints))
        confidence_data = np.zeros((num_frames, num_keypoints))
        
        # Extract data
        for frame_idx, frame_keypoints in enumerate(keypoints_sequence):
            for kp_idx, keypoint in enumerate(frame_keypoints):
                x_data[frame_idx, kp_idx] = keypoint.x
                y_data[frame_idx, kp_idx] = keypoint.y
                confidence_data[frame_idx, kp_idx] = keypoint.confidence
        
        # Smooth x and y coordinates
        smoothed_x = self._apply_savgol(x_data)
        smoothed_y = self._apply_savgol(y_data)
        
        # Confidence is not smoothed - it reflects detection quality
        smoothed_confidence = confidence_data
        
        # Reconstruct keypoints
        smoothed_sequence = []
        for frame_idx in range(num_frames):
            frame_keypoints = []
            for kp_idx in range(num_keypoints):
                keypoint = Keypoint(
                    x=float(smoothed_x[frame_idx, kp_idx]),
                    y=float(smoothed_y[frame_idx, kp_idx]),
                    confidence=float(smoothed_confidence[frame_idx, kp_idx]),
                    name=keypoints_sequence[0][kp_idx].name
                )
                frame_keypoints.append(keypoint)
            smoothed_sequence.append(frame_keypoints)
        
        return smoothed_sequence
    
    def _apply_savgol(self, data: np.ndarray) -> np.ndarray:
        """
        Apply Savitzky-Golay filter to data.
        
        Args:
            data: 2D array (frames x keypoints)
        
        Returns:
            Smoothed data
        """
        smoothed = np.zeros_like(data)
        
        for kp_idx in range(data.shape[1]):
            # Handle edge cases where window_length > number of frames
            window = min(self.window_length, data.shape[0])
            if window % 2 == 0:
                window -= 1  # Must be odd
            if window < 3:
                window = 3
            
            polyorder = min(self.polyorder, window - 1)
            
            # Apply filter to each keypoint trajectory
            smoothed[:, kp_idx] = savgol_filter(
                data[:, kp_idx],
                window_length=window,
                polyorder=polyorder
            )
        
        return smoothed
