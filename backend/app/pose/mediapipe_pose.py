import cv2
import numpy as np
from typing import List, Optional
from app.pose.estimator import PoseEstimator, Keypoint
import mediapipe as mp


class MediaPipeBlazePoseEstimator(PoseEstimator):
    """
    MediaPipe BlazePose estimator.
    
    Using MediaPipe BlazePose instead of MoveNet Lightning due to TensorFlow
    compatibility issues with Python 3.12.
    
    BlazePose provides 33 keypoints (vs MoveNet's 17) and is production-grade.
    """
    
    # MediaPipe BlazePose keypoint names (33 keypoints)
    KEYPOINT_NAMES = [
        "nose",
        "left_eye_inner", "left_eye", "left_eye_outer",
        "right_eye_inner", "right_eye", "right_eye_outer",
        "left_ear", "right_ear",
        "mouth_left", "mouth_right",
        "left_shoulder", "right_shoulder",
        "left_elbow", "right_elbow",
        "left_wrist", "right_wrist",
        "left_pinky", "right_pinky",
        "left_index", "right_index",
        "left_thumb", "right_thumb",
        "left_hip", "right_hip",
        "left_knee", "right_knee",
        "left_ankle", "right_ankle",
        "left_heel", "right_heel",
        "left_foot_index", "right_foot_index"
    ]
    
    def __init__(self, model_complexity: int = 1, min_detection_confidence: float = 0.5):
        """
        Initialize MediaPipe BlazePose estimator.
        
        Args:
            model_complexity: 0 for lite, 1 for full, 2 for heavier
            min_detection_confidence: Minimum confidence for detection
        """
        self.model_complexity = model_complexity
        self.min_detection_confidence = min_detection_confidence
        self.pose = None
        self._load_model()
    
    def _load_model(self):
        """Load MediaPipe BlazePose model."""
        try:
            self.pose = mp.solutions.pose.Pose(
                static_image_mode=False,
                model_complexity=self.model_complexity,
                smooth_landmarks=True,
                enable_segmentation=False,
                smooth_segmentation=False,
                min_detection_confidence=self.min_detection_confidence,
                min_tracking_confidence=self.min_detection_confidence
            )
            print("MediaPipe BlazePose model loaded successfully")
        except Exception as e:
            print(f"Failed to load MediaPipe BlazePose: {e}")
            self.pose = None
    
    def estimate(self, frame: np.ndarray) -> List[Keypoint]:
        """
        Estimate pose from a single frame.
        
        Args:
            frame: Input image (numpy array, BGR format)
        
        Returns:
            List of Keypoint objects (33 keypoints for BlazePose)
        """
        if self.pose is None:
            raise RuntimeError("MediaPipe BlazePose model not loaded")
        
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Run pose estimation
        results = self.pose.process(frame_rgb)
        
        if results.pose_landmarks is None:
            # No pose detected, return empty list
            return []
        
        landmarks = results.pose_landmarks.landmark
        height, width = frame.shape[:2]
        
        keypoints = []
        
        for idx, landmark in enumerate(landmarks):
            if idx < len(self.KEYPOINT_NAMES):
                # MediaPipe returns normalized coordinates (0-1)
                x = landmark.x * width
                y = landmark.y * height
                confidence = landmark.visibility  # Visibility as confidence proxy
                
                keypoint = Keypoint(
                    x=float(x),
                    y=float(y),
                    confidence=float(confidence),
                    name=self.KEYPOINT_NAMES[idx]
                )
                keypoints.append(keypoint)
        
        return keypoints
    
    def get_model_name(self) -> str:
        return "MediaPipe BlazePose"
    
    def get_model_version(self) -> str:
        return f"complexity_{self.model_complexity}"
    
    def get_input_size(self) -> tuple:
        return (None, None)  # MediaPipe handles resizing internally
    
    def preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Preprocess frame for MediaPipe.
        
        MediaPipe expects RGB format.
        
        Args:
            frame: Input frame (BGR format from OpenCV)
        
        Returns:
            Preprocessed frame (RGB format)
        """
        # Convert BGR to RGB
        if frame.shape[2] == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        return frame
