import numpy as np
from typing import List
from app.detection.base import BaseDetector, Detection
from ultralytics import YOLO


class YOLO11Detector(BaseDetector):
    """
    YOLO11n person detector.
    
    Uses Ultralytics YOLO11n nano model for fast person detection.
    Only detects the 'person' class (COCO class 0).
    """
    
    # COCO class for person
    PERSON_CLASS_ID = 0
    PERSON_CLASS_NAME = "person"
    
    def __init__(self, model_name: str = "yolo11n.pt", confidence_threshold: float = 0.5):
        """
        Initialize YOLO11n detector.
        
        Args:
            model_name: YOLO model name or path
            confidence_threshold: Minimum confidence for valid detections
        """
        self.model_name = model_name
        self.confidence_threshold = confidence_threshold
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load YOLO11n model."""
        try:
            self.model = YOLO(self.model_name)
            print(f"YOLO11n model loaded: {self.model_name}")
        except Exception as e:
            print(f"Failed to load YOLO11n model: {e}")
            self.model = None
    
    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Detect persons in a frame.
        
        Args:
            frame: Input image (numpy array, BGR format)
        
        Returns:
            List of Detection objects for persons only
        """
        if self.model is None:
            raise RuntimeError("YOLO11n model not loaded")
        
        # Run inference
        results = self.model(frame, verbose=False)
        
        detections = []
        
        # Process results
        for result in results:
            boxes = result.boxes
            if boxes is None:
                continue
            
            for box in boxes:
                # Get class
                class_id = int(box.cls[0])
                
                # Only detect persons
                if class_id != self.PERSON_CLASS_ID:
                    continue
                
                # Get confidence
                confidence = float(box.conf[0])
                
                # Filter by confidence threshold
                if confidence < self.confidence_threshold:
                    continue
                
                # Get bounding box (x1, y1, x2, y2)
                bbox = box.xyxy[0].tolist()
                bbox = tuple([float(coord) for coord in bbox])
                
                detection = Detection(
                    bbox=bbox,
                    confidence=confidence,
                    class_id=class_id,
                    class_name=self.PERSON_CLASS_NAME
                )
                detections.append(detection)
        
        return detections
    
    def get_model_name(self) -> str:
        return f"YOLO11n ({self.model_name})"
    
    def get_confidence_threshold(self) -> float:
        return self.confidence_threshold
