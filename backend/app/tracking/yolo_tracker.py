import cv2
import numpy as np
from typing import List
from app.tracking.base import BaseTracker, TrackedObject
from app.core.config import settings
from ultralytics import YOLO


class YOLOTracker(BaseTracker):
    """
    YOLO tracker using Ultralytics built-in ByteTrack.
    
    Combines detection and tracking in one model.
    Uses ByteTrack for stable ID assignment.
    """
    
    def __init__(
        self,
        model_name: str = "yolo11n.pt",
        confidence_threshold: float = 0.5,
        detect_max_width: int = None,
        imgsz: int = None,
    ):
        """
        Initialize YOLO tracker.
        
        Args:
            model_name: YOLO model name or path
            confidence_threshold: Minimum confidence for valid detections
            detect_max_width: Downscale frames wider than this before detection
                (person boxes are scale-invariant). None = use setting; 0 = off.
            imgsz: Inference size for YOLO. None = use setting.
        """
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.detect_max_width = (
            settings.DETECT_MAX_WIDTH if detect_max_width is None else detect_max_width
        )
        self.imgsz = settings.DETECT_IMGSZ if imgsz is None else imgsz
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

        # Detection on high-resolution frames dominates runtime on 4K footage
        # (measured ~147ms/frame). A person box is scale-invariant, so detection
        # runs on a downscaled frame and the boxes are mapped back to the
        # original coordinates. Trackers stay coherent because the same frame
        # size is used for every call within a run.
        detect_frame = frame
        scale = 1.0
        if self.detect_max_width and frame.shape[1] > self.detect_max_width:
            scale = self.detect_max_width / frame.shape[1]
            new_size = (
                self.detect_max_width,
                max(1, int(round(frame.shape[0] * scale))),
            )
            detect_frame = cv2.resize(frame, new_size, interpolation=cv2.INTER_AREA)

        # Run tracking (persist=True enables tracking across frames).
        # classes=[0] keeps only the COCO person class in NMS instead of
        # computing and then discarding boxes for all 80 classes.
        results = self.model.track(
            detect_frame,
            persist=True,
            verbose=False,
            imgsz=self.imgsz,
            classes=[0],
            conf=self.confidence_threshold,
        )
        
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
                
                # Get bounding box (x1, y1, x2, y2) and map back to the
                # original frame's coordinates when detection was downscaled.
                bbox = box.xyxy[0].tolist()
                if scale != 1.0:
                    inv = 1.0 / scale
                    bbox = [coord * inv for coord in bbox]
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
