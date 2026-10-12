import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import cv2
from app.detection.yolo11 import YOLO11Detector

def test_detector():
    """Test YOLO11n detector with a synthetic frame."""
    print("Testing YOLO11n detector...")
    
    # Create a synthetic frame (solid color)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    frame[:] = (128, 128, 128)  # Gray background
    
    # Initialize detector
    detector = YOLO11Detector()
    
    # Detect
    detections = detector.detect(frame)
    
    print(f"Model: {detector.get_model_name()}")
    print(f"Confidence threshold: {detector.get_confidence_threshold()}")
    print(f"Detections: {len(detections)}")
    
    for i, det in enumerate(detections):
        print(f"  Detection {i+1}:")
        print(f"    Class: {det.class_name}")
        print(f"    Confidence: {det.confidence:.3f}")
        print(f"    BBox: {det.bbox}")
        print(f"    Size: {det.width:.1f}x{det.height:.1f}")
    
    print("\nDetector test complete.")
    return detections

if __name__ == "__main__":
    test_detector()
