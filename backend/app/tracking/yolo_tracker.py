import numpy as np
from typing import List
from app.tracking.base import BaseTracker, TrackedObject
from ultralytics import YOLO


class YOLOTracker(BaseTracker):
    """
    YOLO tracker using Ultralytics built-in ByteTrack.
    
    Combines detection and tracking in one model.
    Uses ByteTrack for stable ID assignment.
    """
    
    def __init__(self, model_name: str = "yolo11n.pt", confidence_threshold: float = 0.5):
        """
        Initialize YOLO tracker.
        
        Args:
            model_name: YOLO model name or path
            confidence_threshold: Minimum confidence for valid detections
        """
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load YOLO11n model with tracking enabled."""
        try:
            self.model = YOLO(self.model_name)
            print(f"YOLO11n tracker loaded: {self.model_name}")
        except Exception as e:
            print(f"Failed to load YOLO11n tracker: {e}")
            self.model = None
    
    def update(self, frame: np.ndarray, frame_index: int, timestamp: float) -> List[TrackedObject]:
        """
        Update tracker with new frame.
        
        Args:
            frame: Input image (numpy array, BGR format)
            frame_index: Frame number
            timestamp: Timestamp in seconds
        
        Returns:
            List of TrackedObject objects
        """
        if self.model is None:
            raise RuntimeError("YOLO11n tracker not loaded")
        
        # Run tracking (persist=True enables tracking across frames)
        results = self.model.track(frame, persist=True, verbose=False)
        
        tracked_objects = []
        
        # Process results
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            
            for box in boxes:
                # Get track ID
                track_id = int(box.id[0]) if box.id is not None else None
                
                # Skip if no track ID
                if track_id is None:
                    continue
                
                # Get class
                class_id = int(box.cls[0])
                
                # Only track persons
                if class_id != 0:  # COCO person class
                    continue
                
                # Get confidence
                confidence = float(box.conf[0])
                
                # Filter by confidence threshold
                if confidence < self.confidence_threshold:
                    continue
                
                # Get bounding box (x1, y1, x2, y2)
                bbox = box.xyxy[0].tolist()
                bbox = tuple([float(coord) for coord in bbox])
                
                tracked_object = TrackedObject(
                    track_id=track_id,
                    bbox=bbox,
                    confidence=confidence,
                    frame_index=frame_index,
                    timestamp=timestamp
                )
                tracked_objects.append(tracked_object)
        
        return tracked_objects
    
    def get_tracker_name(self) -> str:
        return f"YOLO11n+ByteTrack ({self.model_name})"
    
    def reset(self) -> None:
        """Reset tracker state."""
        # Ultralytics tracker state is reset by creating a new model instance
        self._load_model()
