import numpy as np
from typing import List, Dict
from app.pose.estimator import Keypoint
from app.pose.keypoints import KEYPOINT_INDICES


class SkeletonNormalizer:
    """
    Normalize skeleton coordinates to reduce sensitivity to:
    - Camera distance
    - Athlete size
    - Crop size
    - Camera framing
    
    Normalization method: Scale based on torso length (shoulder-to-hip distance).
    This provides a stable reference that is less affected by camera positioning.
    """
    
    def __init__(self):
        pass
    
    def normalize_sequence(self, keypoints_sequence: List[List[Keypoint]]) -> List[List[Keypoint]]:
        """
        Normalize a sequence of keypoints.
        
        For each frame:
        1. Calculate torso length (average of left and right shoulder-to-hip)
        2. Scale all coordinates by torso length
        3. Translate to center on a reference point (e.g., pelvis center)
        
        Args:
            keypoints_sequence: List of frame keypoints
        
        Returns:
            Normalized keypoints sequence
        """
        normalized_sequence = []
        
        for frame_keypoints in keypoints_sequence:
            # Get torso length for this frame
            torso_length = self._calculate_torso_length(frame_keypoints)
            
            if torso_length > 0:
                # Normalize by torso length
                normalized_frame = self._normalize_frame(frame_keypoints, torso_length)
            else:
                # If torso not detected, return original (shouldn't happen in valid poses)
                normalized_frame = frame_keypoints
            
            normalized_sequence.append(normalized_frame)
        
        return normalized_sequence
    
    def _calculate_torso_length(self, keypoints: List[Keypoint]) -> float:
        """
        Calculate torso length as average of left and right shoulder-to-hip distance.
        
        Args:
            keypoints: List of 17 keypoints
        
        Returns:
            Torso length in pixels
        """
        # Get keypoint indices
        left_shoulder_idx = KEYPOINT_INDICES["left_shoulder"]
        right_shoulder_idx = KEYPOINT_INDICES["right_shoulder"]
        left_hip_idx = KEYPOINT_INDICES["left_hip"]
        right_hip_idx = KEYPOINT_INDICES["right_hip"]
        
        left_shoulder = keypoints[left_shoulder_idx]
        right_shoulder = keypoints[right_shoulder_idx]
        left_hip = keypoints[left_hip_idx]
        right_hip = keypoints[right_hip_idx]
        
        # Calculate left side distance
        left_distance = 0.0
        if left_shoulder.confidence > 0.3 and left_hip.confidence > 0.3:
            left_distance = np.sqrt(
                (left_shoulder.x - left_hip.x) ** 2 +
                (left_shoulder.y - left_hip.y) ** 2
            )
        
        # Calculate right side distance
        right_distance = 0.0
        if right_shoulder.confidence > 0.3 and right_hip.confidence > 0.3:
            right_distance = np.sqrt(
                (right_shoulder.x - right_hip.x) ** 2 +
                (right_shoulder.y - right_hip.y) ** 2
            )
        
        # Average of both sides
        if left_distance > 0 and right_distance > 0:
            return (left_distance + right_distance) / 2
        elif left_distance > 0:
            return left_distance
        elif right_distance > 0:
            return right_distance
        else:
            return 0.0
    
    def _normalize_frame(self, keypoints: List[Keypoint], torso_length: float) -> List[Keypoint]:
        """
        Normalize a single frame of keypoints.
        
        Args:
            keypoints: List of 17 keypoints
            torso_length: Reference length for normalization
        
        Returns:
            Normalized keypoints
        """
        # Calculate pelvis center as reference point
        left_hip_idx = KEYPOINT_INDICES["left_hip"]
        right_hip_idx = KEYPOINT_INDICES["right_hip"]
        
        left_hip = keypoints[left_hip_idx]
        right_hip = keypoints[right_hip_idx]
        
        if left_hip.confidence > 0.3 and right_hip.confidence > 0.3:
            pelvis_center_x = (left_hip.x + right_hip.x) / 2
            pelvis_center_y = (left_hip.y + right_hip.y) / 2
        elif left_hip.confidence > 0.3:
            pelvis_center_x = left_hip.x
            pelvis_center_y = left_hip.y
        elif right_hip.confidence > 0.3:
            pelvis_center_x = right_hip.x
            pelvis_center_y = right_hip.y
        else:
            # Fallback: use nose
            nose_idx = KEYPOINT_INDICES["nose"]
            pelvis_center_x = keypoints[nose_idx].x
            pelvis_center_y = keypoints[nose_idx].y
        
        # Normalize each keypoint
        normalized_keypoints = []
        for kp in keypoints:
            # Scale by torso length
            normalized_x = (kp.x - pelvis_center_x) / torso_length
            normalized_y = (kp.y - pelvis_center_y) / torso_length
            
            normalized_kp = Keypoint(
                x=normalized_x,
                y=normalized_y,
                confidence=kp.confidence,
                name=kp.name
            )
            normalized_keypoints.append(normalized_kp)
        
        return normalized_keypoints
