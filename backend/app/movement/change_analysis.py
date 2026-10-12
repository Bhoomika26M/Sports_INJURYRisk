import numpy as np
from typing import List, Dict, Optional, Tuple
from app.pose.estimator import Keypoint
from app.biomechanics.calculator import BiomechanicsCalculator


class MovementChangeAnalyzer:
    """
    Movement-change analysis (non-clinical late-session movement variation).
    
    Splits valid repetitions into EARLY, MIDDLE, LATE and compares:
    - ROM
    - Knee angle behavior
    - Symmetry
    - Movement duration
    - Velocity
    - Smoothness
    - Stability
    - Trunk lean
    
    Output includes:
    - early_mean
    - late_mean
    - absolute_change
    - percentage_change
    - direction
    
    Note: This is NOT a medical fatigue diagnosis. It provides movement-change
    indicators that can later become inputs to Milestone 3.
    """
    
    def __init__(self):
        self.biomechanics = BiomechanicsCalculator()
    
    def analyze_movement_change(
        self,
        movement_windows: List[Dict],
        keypoints_sequence: List[List[Keypoint]],
        timestamps: List[float]
    ) -> Dict:
        """
        Analyze movement changes across early vs late repetitions.
        
        Args:
            movement_windows: List of movement window dictionaries
            keypoints_sequence: Full keypoints sequence
            timestamps: Frame timestamps
        
        Returns:
            Dictionary with movement-change analysis results
        """
        if len(movement_windows) < 3:
            # Not enough repetitions for meaningful analysis
            return {
                "status": "insufficient_data",
                "message": f"Need at least 3 repetitions, got {len(movement_windows)}",
                "total_repetitions": len(movement_windows)
            }
        
        # Split into EARLY, MIDDLE, LATE
        n = len(movement_windows)
        early_reps = movement_windows[:n//3]
        middle_reps = movement_windows[n//3:2*n//3]
        late_reps = movement_windows[2*n//3:]
        
        # Calculate metrics for each phase
        early_metrics = self._calculate_phase_metrics(early_reps, keypoints_sequence, timestamps)
        middle_metrics = self._calculate_phase_metrics(middle_reps, keypoints_sequence, timestamps)
        late_metrics = self._calculate_phase_metrics(late_reps, keypoints_sequence, timestamps)
        
        # Compare early vs late
        comparison = self._compare_phases(early_metrics, late_metrics)
        
        return {
            "status": "success",
            "total_repetitions": n,
            "early_count": len(early_reps),
            "middle_count": len(middle_reps),
            "late_count": len(late_reps),
            "early_metrics": early_metrics,
            "middle_metrics": middle_metrics,
            "late_metrics": late_metrics,
            "early_vs_late_comparison": comparison
        }
    
    def _calculate_phase_metrics(
        self,
        phase_reps: List[Dict],
        keypoints_sequence: List[List[Keypoint]],
        timestamps: List[float]
    ) -> Dict:
        """Calculate metrics for a phase (early/middle/late)."""
        if not phase_reps:
            return {}
        
        # Collect metrics across all repetitions in this phase
        rom_values = []
        knee_angle_values = []
        symmetry_values = []
        duration_values = []
        velocity_values = []
        smoothness_values = []
        trunk_lean_values = []
        stability_values = []
        
        for rep in phase_reps:
            start_frame = rep.get("start_frame")
            end_frame = rep.get("end_frame")
            
            if start_frame is None or end_frame is None:
                continue
            
            # Extract frames for this repetition
            rep_keypoints = keypoints_sequence[start_frame:end_frame+1]
            rep_timestamps = timestamps[start_frame:end_frame+1]
            
            if not rep_keypoints:
                continue
            
            # Calculate knee angles
            left_knee_angles = []
            right_knee_angles = []
            trunk_lean_angles = []
            
            for frame_kp in rep_keypoints:
                left_angle = self.biomechanics.calculate_knee_angle(frame_kp, "left")
                right_angle = self.biomechanics.calculate_knee_angle(frame_kp, "right")
                trunk_lean = self.biomechanics.calculate_trunk_lean(frame_kp)
                
                if left_angle is not None:
                    left_knee_angles.append(left_angle)
                if right_angle is not None:
                    right_knee_angles.append(right_angle)
                if trunk_lean is not None:
                    trunk_lean_angles.append(trunk_lean)
            
            # ROM
            if left_knee_angles:
                rom = max(left_knee_angles) - min(left_knee_angles)
                rom_values.append(rom)
                knee_angle_values.extend(left_knee_angles)
            
            # Symmetry
            if left_knee_angles and right_knee_angles:
                min_len = min(len(left_knee_angles), len(right_knee_angles))
                if min_len > 0:
                    differences = [abs(left_knee_angles[i] - right_knee_angles[i]) for i in range(min_len)]
                    if differences:
                        symmetry_values.append(np.mean(differences))
            
            # Duration
            duration = rep_timestamps[-1] - rep_timestamps[0] if len(rep_timestamps) > 1 else 0
            duration_values.append(duration)
            
            # Velocity
            if len(left_knee_angles) > 1:
                velocities = self.biomechanics.calculate_velocity(left_knee_angles, rep_timestamps)
                valid_velocities = [v for v in velocities if v is not None]
                if valid_velocities:
                    velocity_values.append(np.mean(valid_velocities))
            
            # Smoothness (variance of successive differences)
            if len(left_knee_angles) > 1:
                diffs = [abs(left_knee_angles[i+1] - left_knee_angles[i]) for i in range(len(left_knee_angles)-1)]
                if diffs:
                    smoothness_values.append(np.std(diffs))
            
            # Trunk lean
            if trunk_lean_angles:
                trunk_lean_values.extend([abs(t) for t in trunk_lean_angles])
            
            # Stability (variance of knee angles)
            if left_knee_angles:
                stability_values.append(np.std(left_knee_angles))
        
        # Calculate phase means
        metrics = {}
        
        if rom_values:
            metrics["rom_mean"] = float(np.mean(rom_values))
            metrics["rom_std"] = float(np.std(rom_values))
        
        if knee_angle_values:
            metrics["knee_angle_mean"] = float(np.mean(knee_angle_values))
            metrics["knee_angle_std"] = float(np.std(knee_angle_values))
        
        if symmetry_values:
            metrics["symmetry_mean"] = float(np.mean(symmetry_values))
            metrics["symmetry_std"] = float(np.std(symmetry_values))
        
        if duration_values:
            metrics["duration_mean"] = float(np.mean(duration_values))
            metrics["duration_std"] = float(np.std(duration_values))
        
        if velocity_values:
            metrics["velocity_mean"] = float(np.mean(velocity_values))
            metrics["velocity_std"] = float(np.std(velocity_values))
        
        if smoothness_values:
            metrics["smoothness_mean"] = float(np.mean(smoothness_values))
            metrics["smoothness_std"] = float(np.std(smoothness_values))
        
        if trunk_lean_values:
            metrics["trunk_lean_mean"] = float(np.mean(trunk_lean_values))
            metrics["trunk_lean_std"] = float(np.std(trunk_lean_values))
        
        if stability_values:
            metrics["stability_mean"] = float(np.mean(stability_values))
            metrics["stability_std"] = float(np.std(stability_values))
        
        return metrics
    
    def _compare_phases(
        self,
        early_metrics: Dict,
        late_metrics: Dict
    ) -> Dict:
        """Compare early vs late phase metrics."""
        comparison = {}
        
        # Metrics to compare
        metric_names = [
            "rom_mean",
            "knee_angle_mean",
            "symmetry_mean",
            "duration_mean",
            "velocity_mean",
            "smoothness_mean",
            "trunk_lean_mean",
            "stability_mean"
        ]
        
        for metric in metric_names:
            early_value = early_metrics.get(metric)
            late_value = late_metrics.get(metric)
            
            if early_value is not None and late_value is not None:
                absolute_change = late_value - early_value
                
                # Calculate percentage change (avoid division by zero)
                if early_value != 0:
                    percentage_change = (absolute_change / early_value) * 100
                else:
                    percentage_change = 0.0
                
                # Determine direction
                if absolute_change > 0:
                    direction = "increase"
                elif absolute_change < 0:
                    direction = "decrease"
                else:
                    direction = "no_change"
                
                comparison[metric] = {
                    "early_mean": early_value,
                    "late_mean": late_value,
                    "absolute_change": absolute_change,
                    "percentage_change": percentage_change,
                    "direction": direction
                }
        
        return comparison
    
    def calculate_movement_quality_change(
        self,
        early_quality: float,
        late_quality: float
    ) -> Dict:
        """
        Calculate movement quality change between early and late phases.
        
        Args:
            early_quality: Movement quality score in early phase
            late_quality: Movement quality score in late phase
        
        Returns:
            Dictionary with quality change metrics
        """
        absolute_change = late_quality - early_quality
        
        if early_quality != 0:
            percentage_change = (absolute_change / early_quality) * 100
        else:
            percentage_change = 0.0
        
        if absolute_change > 0:
            direction = "improvement"
        elif absolute_change < 0:
            direction = "decline"
        else:
            direction = "no_change"
        
        return {
            "early_quality": early_quality,
            "late_quality": late_quality,
            "absolute_change": absolute_change,
            "percentage_change": percentage_change,
            "direction": direction
        }
