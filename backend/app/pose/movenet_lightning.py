import tensorflow as tf
import numpy as np
import cv2
from typing import List
from app.pose.estimator import PoseEstimator, Keypoint
from app.pose.keypoints import KEYPOINT_INDICES, INDEX_TO_KEYPOINT


class MoveNetLightningEstimator(PoseEstimator):
    """
    MoveNet Lightning pose estimator implementation.
    
    MoveNet Lightning is a fast, lightweight pose estimation model
    suitable for real-time applications.
    
    Model: https://tfhub.dev/google/lite-model/movenet/singlepose/lightning/3
    """
    
    def __init__(self):
        self.model = None
        self.input_size = (192, 192)  # MoveNet Lightning input size
        self._load_model()
    
    def _load_model(self):
        """Load MoveNet Lightning model from TensorFlow Hub."""
        try:
            import tensorflow_hub as hub
            
            # Load MoveNet Lightning from TensorFlow Hub
            self.model = hub.load(
                "https://tfhub.dev/google/lite-model/movenet/singlepose/lightning/3"
            )
            print("MoveNet Lightning model loaded successfully")
        except Exception as e:
            print(f"Failed to load MoveNet Lightning: {e}")
            self.model = None
    
    def estimate(self, frame: np.ndarray) -> List[Keypoint]:
        """
        Estimate pose from a single frame.
        
        Args:
            frame: Input image (numpy array, BGR format)
        
        Returns:
            List of 17 Keypoint objects
        """
        if self.model is None:
            raise RuntimeError("MoveNet model not loaded")
        
        # Preprocess frame
        processed_frame = self.preprocess_frame(frame)
        
        # Resize to model input size
        resized = tf.image.resize_with_pad(
            tf.expand_dims(processed_frame, axis=0),
            self.input_size[0],
            self.input_size[1]
        )
        
        # Cast to int32
        input_tensor = tf.cast(resized, dtype=tf.int32)
        
        # Run inference
        outputs = self.model(input_tensor)
        
        # Extract keypoints
        keypoints = self._parse_outputs(outputs, frame.shape)
        
        return keypoints
    
    def _parse_outputs(self, outputs: dict, original_shape: tuple) -> List[Keypoint]:
        """
        Parse MoveNet outputs into Keypoint objects.
        
        Args:
            outputs: Model output dictionary
            original_shape: Original frame shape (height, width, channels)
        
        Returns:
            List of 17 Keypoint objects
        """
        # MoveNet outputs: [1, 1, 17, 3] where 3 = [y, x, confidence]
        keypoints_with_scores = outputs['output_0'].numpy()
        keypoints = keypoints_with_scores[0][0]  # [17, 3]
        
        original_height, original_width = original_shape[:2]
        
        # Convert to list of Keypoint objects
        keypoint_list = []
        for idx, keypoint_data in enumerate(keypoints):
            y, x, confidence = keypoint_data
            
            # Scale to original image coordinates
            x_scaled = x * original_width
            y_scaled = y * original_height
            
            # Get keypoint name
            keypoint_name = INDEX_TO_KEYPOINT.get(idx, f"keypoint_{idx}")
            
            keypoint = Keypoint(
                x=float(x_scaled),
                y=float(y_scaled),
                confidence=float(confidence),
                name=keypoint_name
            )
            keypoint_list.append(keypoint)
        
        return keypoint_list
    
    def get_model_name(self) -> str:
        return "MoveNet Lightning"
    
    def get_model_version(self) -> str:
        return "3"
    
    def get_input_size(self) -> tuple:
        return self.input_size
    
    def preprocess_frame(self, frame: np.ndarray) -> np.ndarray:
        """
        Preprocess frame for MoveNet.
        
        MoveNet expects RGB format in range [0, 255].
        
        Args:
            frame: Input frame (BGR format from OpenCV)
        
        Returns:
            Preprocessed frame (RGB format)
        """
        # Convert BGR to RGB
        if frame.shape[2] == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        return frame
