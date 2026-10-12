from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np


class Detection:
    """Represents a single object detection."""
    
    def __init__(
        self,
        bbox: tuple,  # (x1, y1, x2, y2)
        confidence: float,
        class_id: int,
        class_name: str
    ):
        self.bbox = bbox  # (x1, y1, x2, y2)
        self.confidence = confidence
        self.class_id = class_id
        self.class_name = class_name
    
    @property
    def x1(self) -> float:
        return self.bbox[0]
    
    @property
    def y1(self) -> float:
        return self.bbox[1]
    
    @property
    def x2(self) -> float:
        return self.bbox[2]
    
    @property
    def y2(self) -> float:
        return self.bbox[3]
    
    @property
    def width(self) -> float:
        return self.x2 - self.x1
    
    @property
    def height(self) -> float:
        return self.y2 - self.y1
    
    @property
    def center_x(self) -> float:
        return (self.x1 + self.x2) / 2
    
    @property
    def center_y(self) -> float:
        return (self.y1 + self.y2) / 2
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "bbox": self.bbox,
            "confidence": self.confidence,
            "class_id": self.class_id,
            "class_name": self.class_name,
            "width": self.width,
            "height": self.height,
            "center_x": self.center_x,
            "center_y": self.center_y
        }


class BaseDetector(ABC):
    """Abstract base class for object detectors."""
    
    @abstractmethod
    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Detect objects in a frame.
        
        Args:
            frame: Input image (numpy array, BGR format)
        
        Returns:
            List of Detection objects
        """
        pass
    
    @abstractmethod
    def get_model_name(self) -> str:
        """Return the name of the detection model."""
        pass
    
    @abstractmethod
    def get_confidence_threshold(self) -> float:
        """Return the confidence threshold for detections."""
        pass
