import numpy as np
from typing import List, Dict, Tuple, Optional
from app.pose.estimator import Keypoint
from app.pose.keypoints import KEYPOINT_INDICES


class BiomechanicsCalculator:
    """
    Biomechanical feature calculator.
    
    Calculates:
    - Joint angles
    - Range of motion (ROM)
    - Left-right symmetry
    - Knee alignment proxy
    - Trunk lean
    - Hip stability
    - Balance indicators
    - Velocity and acceleration
    - Movement smoothness
    """
    
    def __init__(self):
        pass
    
    def calculate_joint_angle(
        self,
        point_a: Keypoint,
        point_b: Keypoint,
        point_c: Keypoint
    ) -> Optional[float]:
        """
        Calculate angle at point_b given points a-b-c.
        
        Angle is in degrees, ranging from 0 to 180.
        
        Args:
            point_a: First point (e.g., hip)
            point_b: Joint point (e.g., knee)
            point_c: Third point (e.g., ankle)
        
        Returns:
            Angle in degrees, or None if keypoints invalid
        """
        # Check confidence
        if point_a.confidence < 0.3 or point_b.confidence < 0.3 or point_c.confidence < 0.3:
            return None
        
        # Calculate vectors
        vector1 = np.array([point_a.x - point_b.x, point_a.y - point_b.y])
        vector2 = np.array([point_c.x - point_b.x, point_c.y - point_b.y])
        
        # Check for zero-length vectors
        norm1 = np.linalg.norm(vector1)
        norm2 = np.linalg.norm(vector2)
        
        if norm1 == 0 or norm2 == 0:
            return None
        
        # Calculate angle using dot product
        dot_product = np.dot(vector1, vector2)
        cosine = dot_product / (norm1 * norm2)
        
        # Clamp to [-1, 1] to handle floating-point errors
        cosine = np.clip(cosine, -1.0, 1.0)
        
        angle_rad = np.arccos(cosine)
        angle_deg = np.degrees(angle_rad)
        
        return angle_deg
    
    def calculate_knee_angle(self, keypoints: List[Keypoint], side: str = "left") -> Optional[float]:
        """
        Calculate knee angle (hip-knee-ankle).
        
        Args:
            keypoints: List of keypoints (MediaPipe has 33)
            side: "left" or "right"
        
        Returns:
            Knee angle in degrees
        """
        # Create a dictionary for quick lookup by name
        kp_dict = {kp.name: kp for kp in keypoints}
        
        if side == "left":
            hip = kp_dict.get("left_hip")
            knee = kp_dict.get("left_knee")
            ankle = kp_dict.get("left_ankle")
        else:
            hip = kp_dict.get("right_hip")
            knee = kp_dict.get("right_knee")
            ankle = kp_dict.get("right_ankle")
        
        if hip and knee and ankle:
            return self.calculate_joint_angle(hip, knee, ankle)
        return None
    
    def calculate_hip_angle(self, keypoints: List[Keypoint], side: str = "left") -> Optional[float]:
        """
        Calculate hip angle (shoulder-hip-knee).
        
        Args:
            keypoints: List of keypoints (MediaPipe has 33)
            side: "left" or "right"
        
        Returns:
            Hip angle in degrees
        """
        kp_dict = {kp.name: kp for kp in keypoints}
        
        if side == "left":
            shoulder = kp_dict.get("left_shoulder")
            hip = kp_dict.get("left_hip")
            knee = kp_dict.get("left_knee")
        else:
            shoulder = kp_dict.get("right_shoulder")
            hip = kp_dict.get("right_hip")
            knee = kp_dict.get("right_knee")
        
        if shoulder and hip and knee:
            return self.calculate_joint_angle(shoulder, hip, knee)
        return None
    
    def calculate_elbow_angle(self, keypoints: List[Keypoint], side: str = "left") -> Optional[float]:
        """
        Calculate elbow angle (shoulder-elbow-wrist).
        
        Args:
            keypoints: List of keypoints
            side: "left" or "right"
        
        Returns:
            Elbow angle in degrees
        """
        kp_dict = {kp.name: kp for kp in keypoints}
        
        if side == "left":
            shoulder = kp_dict.get("left_shoulder")
            elbow = kp_dict.get("left_elbow")
            wrist = kp_dict.get("left_wrist")
        else:
            shoulder = kp_dict.get("right_shoulder")
            elbow = kp_dict.get("right_elbow")
            wrist = kp_dict.get("right_wrist")
        
        if shoulder and elbow and wrist:
            return self.calculate_joint_angle(shoulder, elbow, wrist)
        return None
    
    def calculate_shoulder_angle(self, keypoints: List[Keypoint], side: str = "left") -> Optional[float]:
        """
        Calculate shoulder angle (elbow-shoulder-hip).
        
        Args:
            keypoints: List of keypoints
            side: "left" or "right"
        
        Returns:
            Shoulder angle in degrees
        """
        kp_dict = {kp.name: kp for kp in keypoints}
        
        if side == "left":
            elbow = kp_dict.get("left_elbow")
            shoulder = kp_dict.get("left_shoulder")
            hip = kp_dict.get("left_hip")
        else:
            elbow = kp_dict.get("right_elbow")
            shoulder = kp_dict.get("right_shoulder")
            hip = kp_dict.get("right_hip")
        
        if elbow and shoulder and hip:
            return self.calculate_joint_angle(elbow, shoulder, hip)
        return None
    
    def calculate_rom(self, angles: List[Optional[float]]) -> Dict[str, Optional[float]]:
        """
        Calculate range of motion from a sequence of angles.
        
        Args:
            angles: List of angle values (may contain None for invalid frames)
        
        Returns:
            Dictionary with min_angle, max_angle, rom
        """
        valid_angles = [a for a in angles if a is not None]
        
        if not valid_angles:
            return {"min_angle": None, "max_angle": None, "rom": None}
        
        min_angle = min(valid_angles)
        max_angle = max(valid_angles)
        rom = max_angle - min_angle
        
        return {
            "min_angle": min_angle,
            "max_angle": max_angle,
            "rom": rom
        }
    
    def calculate_asymmetry(
        self,
        left_values: List[Optional[float]],
        right_values: List[Optional[float]]
    ) -> Dict[str, float]:
        """
        Calculate left-right asymmetry.
        
        Args:
            left_values: List of left-side measurements
            right_values: List of right-side measurements
        
        Returns:
            Dictionary with asymmetry metrics
        """
        # Filter valid values
        left_valid = [v for v in left_values if v is not None]
        right_valid = [v for v in right_values if v is not None]
        
        if not left_valid or not right_valid:
            return {
                "mean_asymmetry": 0.0,
                "max_asymmetry": 0.0,
                "std_asymmetry": 0.0
            }
        
        # Calculate absolute differences (align by index)
        min_len = min(len(left_valid), len(right_valid))
        differences = [abs(left_valid[i] - right_valid[i]) for i in range(min_len)]
        
        if not differences:
            return {
                "mean_asymmetry": 0.0,
                "max_asymmetry": 0.0,
                "std_asymmetry": 0.0
            }
        
        mean_asymmetry = np.mean(differences)
        max_asymmetry = np.max(differences)
        std_asymmetry = np.std(differences)
        
        return {
            "mean_asymmetry": float(mean_asymmetry),
            "max_asymmetry": float(max_asymmetry),
            "std_asymmetry": float(std_asymmetry)
        }
    
    def calculate_knee_alignment_proxy(self, keypoints: List[Keypoint], side: str = "left") -> Optional[float]:
        """
        Calculate knee alignment / valgus proxy.
        
        This is a video-derived proxy, NOT a clinically validated measurement.
        Based on hip-knee-ankle alignment in the frontal plane.
        
        Args:
            keypoints: List of keypoints (MediaPipe has 33)
            side: "left" or "right"
        
        Returns:
            Alignment metric (deviation from vertical), or None if invalid
        """
        kp_dict = {kp.name: kp for kp in keypoints}
        
        if side == "left":
            hip = kp_dict.get("left_hip")
            knee = kp_dict.get("left_knee")
            ankle = kp_dict.get("left_ankle")
        else:
            hip = kp_dict.get("right_hip")
            knee = kp_dict.get("right_knee")
            ankle = kp_dict.get("right_ankle")
        
        if hip and knee and ankle:
            if hip.confidence < 0.3 or knee.confidence < 0.3 or ankle.confidence < 0.3:
                return None
            
            # Calculate horizontal deviation of knee from hip-ankle line
            # Simple proxy: x deviation
            hip_x = hip.x
            knee_x = knee.x
            ankle_x = ankle.x
            
            # Expected knee x position (linear interpolation between hip and ankle)
            expected_knee_x = (hip_x + ankle_x) / 2
            
            # Deviation
            deviation = knee_x - expected_knee_x
            
            return deviation
        
        return None
    
    def calculate_trunk_lean(self, keypoints: List[Keypoint]) -> Optional[float]:
        """
        Calculate trunk lean angle relative to vertical.
        
        Based on shoulder line relative to hip line.
        
        Args:
            keypoints: List of keypoints (MediaPipe has 33)
        
        Returns:
            Trunk lean angle in degrees, or None if invalid
        """
        kp_dict = {kp.name: kp for kp in keypoints}
        
        left_shoulder = kp_dict.get("left_shoulder")
        right_shoulder = kp_dict.get("right_shoulder")
        left_hip = kp_dict.get("left_hip")
        right_hip = kp_dict.get("right_hip")
        
        if (left_shoulder and right_shoulder and left_hip and right_hip and
            left_shoulder.confidence > 0.3 and right_shoulder.confidence > 0.3 and
            left_hip.confidence > 0.3 and right_hip.confidence > 0.3):
            # Calculate shoulder center
            shoulder_center_x = (left_shoulder.x + right_shoulder.x) / 2
            shoulder_center_y = (left_shoulder.y + right_shoulder.y) / 2
            
            # Calculate hip center
            hip_center_x = (left_hip.x + right_hip.x) / 2
            hip_center_y = (left_hip.y + right_hip.y) / 2
            
            # Vector from hip to shoulder
            dx = shoulder_center_x - hip_center_x
            dy = shoulder_center_y - hip_center_y
            
            # Angle from vertical (assuming vertical is negative y direction)
            angle_rad = np.arctan2(dx, -dy)
            angle_deg = np.degrees(angle_rad)
            
            return angle_deg
        
        return None
    
    def calculate_velocity(
        self,
        values: List[Optional[float]],
        timestamps: List[float]
    ) -> List[Optional[float]]:
        """
        Calculate velocity (first derivative) of a sequence.
        
        Args:
            values: List of measurements
            timestamps: List of corresponding timestamps
        
        Returns:
            List of velocities (same length as input, first element is None)
        """
        velocities = [None]  # First frame has no velocity
        
        for i in range(1, len(values)):
            if values[i] is not None and values[i-1] is not None:
                dt = timestamps[i] - timestamps[i-1]
                if dt > 0:
                    velocity = (values[i] - values[i-1]) / dt
                    velocities.append(velocity)
                else:
                    velocities.append(None)
            else:
                velocities.append(None)
        
        return velocities
    
    def calculate_acceleration(
        self,
        velocities: List[Optional[float]],
        timestamps: List[float]
    ) -> List[Optional[float]]:
        """
        Calculate acceleration (second derivative) of a sequence.
        
        Args:
            velocities: List of velocities
            timestamps: List of corresponding timestamps
        
        Returns:
            List of accelerations (first two elements are None)
        """
        accelerations = [None, None]  # First two frames have no acceleration
        
        for i in range(2, len(velocities)):
            if velocities[i] is not None and velocities[i-1] is not None:
                dt = timestamps[i] - timestamps[i-1]
                if dt > 0:
                    acceleration = (velocities[i] - velocities[i-1]) / dt
                    accelerations.append(acceleration)
                else:
                    accelerations.append(None)
            else:
                accelerations.append(None)
        
        return accelerations
