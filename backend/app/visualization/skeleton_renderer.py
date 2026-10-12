import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from app.pose.estimator import Keypoint
from app.pose.keypoints import MEDIAPIPE_KEYPOINT_INDICES


class SkeletonRenderer:
    """
    Skeleton visualization renderer for BlazePose 33-point landmarks.
    
    Renders:
    - Keypoints
    - Skeletal connections
    - Bounding boxes
    - Tracker IDs
    - Confidence values
    - Frame/timestamp info
    """
    
    # BlazePose 33-point canonical mapping
    BLAZEPOSE_LANDMARKS = {
        0: "nose",
        1: "left_eye_inner",
        2: "left_eye",
        3: "left_eye_outer",
        4: "right_eye_inner",
        5: "right_eye",
        6: "right_eye_outer",
        7: "left_ear",
        8: "right_ear",
        9: "mouth_left",
        10: "mouth_right",
        11: "left_shoulder",
        12: "right_shoulder",
        13: "left_elbow",
        14: "right_elbow",
        15: "left_wrist",
        16: "right_wrist",
        17: "left_pinky",
        18: "right_pinky",
        19: "left_index",
        20: "right_index",
        21: "left_thumb",
        22: "right_thumb",
        23: "left_hip",
        24: "right_hip",
        25: "left_knee",
        26: "right_knee",
        27: "left_ankle",
        28: "right_ankle",
        29: "left_heel",
        30: "right_heel",
        31: "left_foot_index",
        32: "right_foot_index"
    }
    
    # Skeletal connections for BlazePose
    BLAZEPOSE_CONNECTIONS = [
        # Face
        (0, 1), (0, 4), (1, 2), (2, 3), (4, 5), (5, 6),
        (0, 7), (0, 8), (7, 9), (8, 10),
        # Upper body
        (11, 12),  # shoulders
        (11, 13), (13, 15),  # left arm
        (12, 14), (14, 16),  # right arm
        (11, 23), (12, 24),  # shoulders to hips
        # Hands
        (15, 17), (15, 19), (15, 21),  # left hand
        (16, 18), (16, 20), (16, 22),  # right hand
        # Lower body
        (23, 24),  # hips
        (23, 25), (25, 27),  # left leg
        (24, 26), (26, 28),  # right leg
        # Feet
        (27, 29), (27, 31),  # left foot
        (28, 30), (28, 32),  # right foot
    ]
    
    # Named landmarks for biomechanics
    BIOMECHANICS_LANDMARKS = [
        "nose",
        "left_shoulder", "right_shoulder",
        "left_elbow", "right_elbow",
        "left_wrist", "right_wrist",
        "left_hip", "right_hip",
        "left_knee", "right_knee",
        "left_ankle", "right_ankle"
    ]
    
    def __init__(
        self,
        keypoint_radius: int = 4,
        keypoint_color: Tuple[int, int, int] = (0, 255, 0),
        connection_color: Tuple[int, int, int] = (255, 255, 255),
        bbox_color: Tuple[int, int, int] = (255, 0, 0),
        text_color: Tuple[int, int, int] = (255, 255, 255),
        line_thickness: int = 2,
        confidence_threshold: float = 0.3
    ):
        """
        Initialize skeleton renderer.
        
        Args:
            keypoint_radius: Radius of keypoint circles
            keypoint_color: Color of keypoints (BGR)
            connection_color: Color of skeletal connections (BGR)
            bbox_color: Color of bounding boxes (BGR)
            text_color: Color of text (BGR)
            line_thickness: Thickness of connection lines
            confidence_threshold: Minimum confidence to render keypoint
        """
        self.keypoint_radius = keypoint_radius
        self.keypoint_color = keypoint_color
        self.connection_color = connection_color
        self.bbox_color = bbox_color
        self.text_color = text_color
        self.line_thickness = line_thickness
        self.confidence_threshold = confidence_threshold
    
    def render(
        self,
        frame: np.ndarray,
        keypoints: List[Keypoint],
        bbox: Optional[Tuple[float, float, float, float]] = None,
        track_id: Optional[int] = None,
        frame_number: Optional[int] = None,
        timestamp: Optional[float] = None,
        biomechanical_data: Optional[Dict] = None
    ) -> np.ndarray:
        """
        Render skeleton visualization on frame.
        
        Args:
            frame: Input frame (BGR format)
            keypoints: List of Keypoint objects (BlazePose 33 landmarks)
            bbox: Bounding box (x1, y1, x2, y2)
            track_id: Tracker ID
            frame_number: Frame number
            timestamp: Timestamp in seconds
            biomechanical_data: Optional biomechanical measurements to display
        
        Returns:
            Annotated frame
        """
        # Create a copy to avoid modifying original
        annotated = frame.copy()
        
        # Draw bounding box
        if bbox is not None:
            self._draw_bbox(annotated, bbox, track_id)
        
        # Draw skeletal connections
        self._draw_connections(annotated, keypoints)
        
        # Draw keypoints
        self._draw_keypoints(annotated, keypoints)
        
        # Draw frame info
        if frame_number is not None or timestamp is not None:
            self._draw_frame_info(annotated, frame_number, timestamp)
        
        # Draw biomechanical data
        if biomechanical_data is not None:
            self._draw_biomechanical_data(annotated, biomechanical_data)
        
        return annotated
    
    def _draw_bbox(
        self,
        frame: np.ndarray,
        bbox: Tuple[float, float, float, float],
        track_id: Optional[int]
    ) -> None:
        """Draw bounding box and tracker ID."""
        x1, y1, x2, y2 = [int(coord) for coord in bbox]
        
        # Draw rectangle
        cv2.rectangle(frame, (x1, y1), (x2, y2), self.bbox_color, self.line_thickness)
        
        # Draw tracker ID
        if track_id is not None:
            label = f"Athlete #{track_id}"
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(
                frame,
                (x1, y1 - label_size[1] - 10),
                (x1 + label_size[0], y1),
                self.bbox_color,
                -1
            )
            cv2.putText(
                frame,
                label,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                self.text_color,
                2
            )
    
    def _draw_connections(self, frame: np.ndarray, keypoints: List[Keypoint]) -> None:
        """Draw skeletal connections."""
        # Create a dictionary for quick lookup by name
        kp_dict = {kp.name: kp for kp in keypoints}
        
        # Also create index-based lookup for compatibility
        kp_by_index = {}
        for kp in keypoints:
            # Find index from name
            for idx, name in self.BLAZEPOSE_LANDMARKS.items():
                if name == kp.name:
                    kp_by_index[idx] = kp
                    break
        
        # Draw connections
        for idx1, idx2 in self.BLAZEPOSE_CONNECTIONS:
            kp1 = kp_by_index.get(idx1)
            kp2 = kp_by_index.get(idx2)
            
            if kp1 and kp2:
                # Check confidence
                if (kp1.confidence >= self.confidence_threshold and
                    kp2.confidence >= self.confidence_threshold):
                    pt1 = (int(kp1.x), int(kp1.y))
                    pt2 = (int(kp2.x), int(kp2.y))
                    cv2.line(frame, pt1, pt2, self.connection_color, self.line_thickness)
    
    def _draw_keypoints(self, frame: np.ndarray, keypoints: List[Keypoint]) -> None:
        """Draw keypoints."""
        for kp in keypoints:
            if kp.confidence >= self.confidence_threshold:
                pt = (int(kp.x), int(kp.y))
                
                # Color based on confidence
                if kp.confidence > 0.8:
                    color = (0, 255, 0)  # Green for high confidence
                elif kp.confidence > 0.5:
                    color = (0, 255, 255)  # Yellow for medium confidence
                else:
                    color = (0, 0, 255)  # Red for low confidence
                
                cv2.circle(frame, pt, self.keypoint_radius, color, -1)
                
                # Optional: Draw keypoint name for important landmarks
                if kp.name in self.BIOMECHANICS_LANDMARKS:
                    cv2.putText(
                        frame,
                        kp.name[:3],  # Abbreviated name
                        (pt[0] + 5, pt[1] - 5),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.3,
                        self.text_color,
                        1
                    )
    
    def _draw_frame_info(
        self,
        frame: np.ndarray,
        frame_number: Optional[int],
        timestamp: Optional[float]
    ) -> None:
        """Draw frame and timestamp info."""
        info_text = []
        if frame_number is not None:
            info_text.append(f"Frame: {frame_number}")
        if timestamp is not None:
            info_text.append(f"Time: {timestamp:.2f}s")
        
        if info_text:
            text = " | ".join(info_text)
            cv2.putText(
                frame,
                text,
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                self.text_color,
                2
            )
    
    def _draw_biomechanical_data(self, frame: np.ndarray, data: Dict) -> None:
        """Draw biomechanical measurements."""
        y_offset = 60
        line_height = 25
        
        # Common measurements to display
        measurements = [
            ("Knee Angle", data.get("knee_angle")),
            ("Hip Angle", data.get("hip_angle")),
            ("Trunk Lean", data.get("trunk_lean")),
            ("ROM", data.get("rom")),
            ("Symmetry", data.get("symmetry"))
        ]
        
        for label, value in measurements:
            if value is not None:
                if isinstance(value, dict):
                    # Handle dict values (e.g., ROM with min/max)
                    value_str = f"{value.get('mean', value)}"
                else:
                    value_str = f"{value:.1f}" if isinstance(value, float) else str(value)
                
                text = f"{label}: {value_str}"
                cv2.putText(
                    frame,
                    text,
                    (10, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    self.text_color,
                    2
                )
                y_offset += line_height
    
    def get_landmark_index(self, landmark_name: str) -> Optional[int]:
        """
        Get BlazePose index for a landmark name.
        
        Args:
            landmark_name: Name of the landmark (e.g., "left_knee")
        
        Returns:
            Index (0-32) or None if not found
        """
        for idx, name in self.BLAZEPOSE_LANDMARKS.items():
            if name == landmark_name:
                return idx
        return None
    
    def get_landmark_name(self, index: int) -> Optional[str]:
        """
        Get landmark name for a BlazePose index.
        
        Args:
            index: BlazePose index (0-32)
        
        Returns:
            Landmark name or None if not found
        """
        return self.BLAZEPOSE_LANDMARKS.get(index)
