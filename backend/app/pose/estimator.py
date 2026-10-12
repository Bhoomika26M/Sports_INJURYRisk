from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import numpy as np
import cv2


class Keypoint:
    """Represents a single body keypoint."""
    
    def __init__(self, x: float, y: float, confidence: float, name: str):
        self.x = x
        self.y = y
        self.confidence = confidence
        self.name = name
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "x": self.x,
            "y": self.y,
            "confidence": self.confidence,
            "name": self.name
        }
    
    def is_valid(self, threshold: float = 0.3) -> bool:
        """Check if keypoint confidence meets threshold."""
        return self.confidence >= threshold


class PoseEstimator(ABC):
    """
    Abstract base class for pose estimators.
    
    This abstraction allows swapping between different pose models
    (MoveNet Lightning, MoveNet Thunder, MediaPipe BlazePose, etc.)
    without changing the biomechanics engine.
    """
    
    @abstractmethod
    def estimate(self, frame: np.ndarray) -> List[Keypoint]:
        """
        Estimate pose from a single frame.
        
        Args:
            frame: Input image (numpy array, BGR format for OpenCV)
        
        Returns:
            List of Keypoint objects (17 keypoints for MoveNet)
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Return the name of the pose model."""
        pass
    
    @abstractmethod
    def get_model_version(self) -> str:
        """Return the version of the pose model."""
        pass
    
    @abstractmethod
    def get_input_size(self) -> tuple:
        """Return the expected input size (width, height)."""
        pass
    
    def preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Preprocess frame for pose estimation.
        
        Default implementation can be overridden by specific estimators.
        
        Args:
            frame: Input frame
        
        Returns:
            Preprocessed frame
        """
        # Default: convert BGR to RGB for TensorFlow models
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) if frame.shape[2] == 3 else frame
