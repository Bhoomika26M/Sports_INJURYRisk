from abc import ABC, abstractmethod
from typing import List, Optional
import numpy as np


class TrackedObject:
    """Represents a tracked object across frames."""
    
    def __init__(
        self,
        track_id: int,
        bbox: tuple,  # (x1, y1, x2, y2)
        confidence: float,
        frame_index: int,
        timestamp: float
    ):
        self.track_id = track_id
        self.bbox = bbox
        self.confidence = confidence
        self.frame_index = frame_index
        self.timestamp = timestamp
    
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
            "track_id": self.track_id,
            "bbox": self.bbox,
            "confidence": self.confidence,
            "frame_index": self.frame_index,
            "timestamp": self.timestamp,
            "width": self.width,
            "height": self.height,
            "center_x": self.center_x,
            "center_y": self.center_y
        }


class BaseTracker(ABC):
    """Abstract base class for object trackers."""
    
    @abstractmethod
    def update(self, frame: np.ndarray, frame_index: int, timestamp: float) -> List[TrackedObject]:
        """
        Update tracker with new frame.
        
        Args:
            frame: Input image
            frame_index: Frame number
            timestamp: Timestamp in seconds
        
        Returns:
            List of TrackedObject objects
        """
        pass
    
    @abstractmethod
    def get_tracker_name(self) -> str:
        """Return the name of the tracker."""
        pass
    
    @abstractmethod
    def reset(self) -> None:
        """Reset tracker state."""
        pass
