import numpy as np
from typing import List, Dict, Optional, Tuple
from app.pose.estimator import Keypoint
from app.biomechanics.calculator import BiomechanicsCalculator


class MovementSegmenter:
    """
    Movement window detection and segmentation.
    
    Supports:
    - Squat (descent-ascent cycles)
    - Jump/Landing (takeoff-flight-landing-stabilization)
    - Running/Sprinting (stride cycles)
    """
    
    def __init__(self):
        self.biomechanics = BiomechanicsCalculator()
    
    def segment_squat(
        self,
        keypoints_sequence: List[List[Keypoint]],
        timestamps: List[float]
    ) -> List[Dict]:
        """
        Detect squat repetitions from knee angle and hip trajectory.
        
        Phases:
        - START: Standing position
        - DESCENT: Going down
        - BOTTOM: Deepest point
        - ASCENT: Coming up
        - COMPLETION: Return to standing
        
        Args:
            keypoints_sequence: Sequence of keypoints across frames
            timestamps: Frame timestamps
        
        Returns:
            List of repetition dictionaries with timing and metrics
        """
        repetitions = []
        
        # Calculate knee angles across frames
        left_knee_angles = []
        right_knee_angles = []
        
        for frame_keypoints in keypoints_sequence:
            left_angle = self.biomechanics.calculate_knee_angle(frame_keypoints, "left")
            right_angle = self.biomechanics.calculate_knee_angle(frame_keypoints, "right")
            left_knee_angles.append(left_angle)
            right_knee_angles.append(right_angle)
        
        # Use average of left and right for detection
        avg_knee_angles = []
        for i in range(len(left_knee_angles)):
            if left_knee_angles[i] is not None and right_knee_angles[i] is not None:
                avg_knee_angles.append((left_knee_angles[i] + right_knee_angles[i]) / 2)
            elif left_knee_angles[i] is not None:
                avg_knee_angles.append(left_knee_angles[i])
            elif right_knee_angles[i] is not None:
                avg_knee_angles.append(right_knee_angles[i])
            else:
                avg_knee_angles.append(None)
        
        # Detect repetitions using knee angle peaks and valleys
        # Squat: high angle (standing) -> low angle (bottom) -> high angle (standing)
        
        # Find local minima (bottom of squat)
        minima = self._find_local_minima(avg_knee_angles, window=5)
        
        # Find local maxima (standing positions)
        maxima = self._find_local_maxima(avg_knee_angles, window=5)
        
        # Pair maxima with minima to identify repetitions
        rep_num = 1
        for i, min_idx in enumerate(minima):
            # Find preceding maximum (start)
            start_idx = None
            for max_idx in maxima:
                if max_idx < min_idx:
                    start_idx = max_idx
                else:
                    break
            
            # Find following maximum (completion)
            end_idx = None
            for max_idx in maxima:
                if max_idx > min_idx:
                    end_idx = max_idx
                    break
            
            if start_idx is not None and end_idx is not None:
                # Valid repetition
                rep_data = {
                    "phase": "squat",
                    "repetition_number": rep_num,
                    "start_frame": start_idx,
                    "end_frame": end_idx,
                    "start_time": timestamps[start_idx] if start_idx < len(timestamps) else None,
                    "end_time": timestamps[end_idx] if end_idx < len(timestamps) else None,
                    "metrics": {
                        "bottom_frame": min_idx,
                        "bottom_time": timestamps[min_idx] if min_idx < len(timestamps) else None,
                        "duration": (timestamps[end_idx] - timestamps[start_idx]) if end_idx < len(timestamps) and start_idx < len(timestamps) else None,
                        "minimum_knee_angle": avg_knee_angles[min_idx] if min_idx < len(avg_knee_angles) else None,
                        "maximum_knee_angle": avg_knee_angles[start_idx] if start_idx < len(avg_knee_angles) else None
                    }
                }
                repetitions.append(rep_data)
                rep_num += 1
        
        return repetitions
    
    def segment_jump_landing(
        self,
        keypoints_sequence: List[List[Keypoint]],
        timestamps: List[float]
    ) -> List[Dict]:
        """
        Detect jump and landing phases.
        
        Phases:
        - PREPARATION: Crouch before jump
        - TAKEOFF: Leaving ground
        - FLIGHT: In air
        - LANDING: Contact with ground
        - STABILIZATION: Regaining balance
        
        Args:
            keypoints_sequence: Sequence of keypoints across frames
            timestamps: Frame timestamps
        
        Returns:
            List of jump dictionaries with timing and metrics
        """
        jumps = []
        
        # Calculate vertical hip position (using y coordinate)
        hip_y_positions = []
        for frame_keypoints in keypoints_sequence:
            kp_dict = {kp.name: kp for kp in frame_keypoints}
            left_hip = kp_dict.get("left_hip")
            right_hip = kp_dict.get("right_hip")
            
            if left_hip and right_hip:
                avg_y = (left_hip.y + right_hip.y) / 2
                hip_y_positions.append(avg_y)
            elif left_hip:
                hip_y_positions.append(left_hip.y)
            elif right_hip:
                hip_y_positions.append(right_hip.y)
            else:
                hip_y_positions.append(None)
        
        # Calculate knee angles
        knee_angles = []
        for frame_keypoints in keypoints_sequence:
            left_angle = self.biomechanics.calculate_knee_angle(frame_keypoints, "left")
            right_angle = self.biomechanics.calculate_knee_angle(frame_keypoints, "right")
            
            if left_angle is not None and right_angle is not None:
                knee_angles.append((left_angle + right_angle) / 2)
            elif left_angle is not None:
                knee_angles.append(left_angle)
            elif right_angle is not None:
                knee_angles.append(right_angle)
            else:
                knee_angles.append(None)
        
        # Detect takeoff: rapid increase in hip y (going up)
        # Detect landing: rapid decrease in hip y (coming down)
        
        # Calculate velocity of hip movement
        hip_velocity = self._calculate_velocity(hip_y_positions, timestamps)
        
        # Find takeoff (positive velocity peak)
        takeoff_indices = self._find_velocity_peaks(hip_velocity, direction="positive", threshold=50.0)
        
        # Find landing (negative velocity peak)
        landing_indices = self._find_velocity_peaks(hip_velocity, direction="negative", threshold=-50.0)
        
        # Pair takeoffs with landings
        jump_num = 1
        for takeoff_idx in takeoff_indices:
            # Find landing after takeoff
            landing_idx = None
            for land_idx in landing_indices:
                if land_idx > takeoff_idx:
                    landing_idx = land_idx
                    break
            
            if landing_idx is not None:
                # Calculate landing knee angle
                landing_knee_angle = knee_angles[landing_idx] if landing_idx < len(knee_angles) else None
                
                jump_data = {
                    "phase": "jump_landing",
                    "jump_number": jump_num,
                    "start_frame": takeoff_idx,
                    "end_frame": landing_idx,
                    "start_time": timestamps[takeoff_idx] if takeoff_idx < len(timestamps) else None,
                    "end_time": timestamps[landing_idx] if landing_idx < len(timestamps) else None,
                    "metrics": {
                        "takeoff_frame": takeoff_idx,
                        "landing_frame": landing_idx,
                        "takeoff_time": timestamps[takeoff_idx] if takeoff_idx < len(timestamps) else None,
                        "landing_time": timestamps[landing_idx] if landing_idx < len(timestamps) else None,
                        "flight_duration": (timestamps[landing_idx] - timestamps[takeoff_idx]) if landing_idx < len(timestamps) and takeoff_idx < len(timestamps) else None,
                        "landing_knee_angle": landing_knee_angle
                    }
                }
                jumps.append(jump_data)
                jump_num += 1
        
        return jumps
    
    def segment_running(
        self,
        keypoints_sequence: List[List[Keypoint]],
        timestamps: List[float]
    ) -> List[Dict]:
        """
        Detect running stride cycles from ankle/hip/knee trajectories.
        
        Args:
            keypoints_sequence: Sequence of keypoints across frames
            timestamps: Frame timestamps
        
        Returns:
            List of stride dictionaries with timing and metrics
        """
        strides = []
        
        # Calculate ankle vertical positions (both left and right)
        left_ankle_y = []
        right_ankle_y = []
        
        for frame_keypoints in keypoints_sequence:
            kp_dict = {kp.name: kp for kp in frame_keypoints}
            left_ankle = kp_dict.get("left_ankle")
            right_ankle = kp_dict.get("right_ankle")
            
            left_ankle_y.append(left_ankle.y if left_ankle else None)
            right_ankle_y.append(right_ankle.y if right_ankle else None)
        
        # Detect stride cycles from alternating ankle peaks
        # Left ankle peaks = left foot forward phase
        # Right ankle peaks = right foot forward phase
        
        left_peaks = self._find_local_maxima(left_ankle_y, window=3)
        right_peaks = self._find_local_maxima(right_ankle_y, window=3)
        
        # Combine and sort all peaks
        all_peaks = []
        for peak in left_peaks:
            all_peaks.append({"frame": peak, "side": "left"})
        for peak in right_peaks:
            all_peaks.append({"frame": peak, "side": "right"})
        
        all_peaks.sort(key=lambda x: x["frame"])
        
        # Group into stride cycles (alternating left-right)
        stride_num = 1
        for i in range(len(all_peaks) - 1):
            if all_peaks[i]["side"] != all_peaks[i+1]["side"]:
                # Alternating - this is a stride
                start_frame = all_peaks[i]["frame"]
                end_frame = all_peaks[i+1]["frame"]
                
                stride_data = {
                    "phase": "running",
                    "stride_number": stride_num,
                    "start_frame": start_frame,
                    "end_frame": end_frame,
                    "start_time": timestamps[start_frame] if start_frame < len(timestamps) else None,
                    "end_time": timestamps[end_frame] if end_frame < len(timestamps) else None,
                    "metrics": {
                        "duration": (timestamps[end_frame] - timestamps[start_frame]) if end_frame < len(timestamps) and start_frame < len(timestamps) else None,
                        "side": all_peaks[i]["side"]
                    }
                }
                strides.append(stride_data)
                stride_num += 1
        
        return strides
    
    def _find_local_minima(
        self,
        values: List[Optional[float]],
        window: int = 5
    ) -> List[int]:
        """Find indices of local minima in a sequence."""
        minima = []
        
        for i in range(window, len(values) - window):
            if values[i] is None:
                continue
            
            # Check if this is a local minimum
            is_minimum = True
            for j in range(i - window, i + window + 1):
                if j == i or values[j] is None:
                    continue
                if values[j] <= values[i]:
                    is_minimum = False
                    break
            
            if is_minimum:
                minima.append(i)
        
        return minima
    
    def _find_local_maxima(
        self,
        values: List[Optional[float]],
        window: int = 5
    ) -> List[int]:
        """Find indices of local maxima in a sequence."""
        maxima = []
        
        for i in range(window, len(values) - window):
            if values[i] is None:
                continue
            
            # Check if this is a local maximum
            is_maximum = True
            for j in range(i - window, i + window + 1):
                if j == i or values[j] is None:
                    continue
                if values[j] >= values[i]:
                    is_maximum = False
                    break
            
            if is_maximum:
                maxima.append(i)
        
        return maxima
    
    def _calculate_velocity(
        self,
        values: List[Optional[float]],
        timestamps: List[float]
    ) -> List[Optional[float]]:
        """Calculate velocity (first derivative)."""
        velocities = [None]
        
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
    
    def _find_velocity_peaks(
        self,
        velocities: List[Optional[float]],
        direction: str = "positive",
        threshold: float = 0.0
    ) -> List[int]:
        """Find velocity peaks above threshold."""
        peaks = []
        
        for i, vel in enumerate(velocities):
            if vel is None:
                continue
            
            if direction == "positive" and vel > threshold:
                peaks.append(i)
            elif direction == "negative" and vel < threshold:
                peaks.append(i)
        
        return peaks
