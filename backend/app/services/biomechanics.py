import math
import numpy as np
from typing import List, Dict, Any, Optional, Tuple


def calculate_angle_2d(p1: Dict[str, float], p2: Dict[str, float], p3: Dict[str, float]) -> float:
    """
    Calculate the 2D angle (in degrees) at vertex p2 formed by points p1-p2-p3.
    """
    v1 = np.array([p1["x"] - p2["x"], p1["y"] - p2["y"]])
    v2 = np.array([p3["x"] - p2["x"], p3["y"] - p2["y"]])

    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)

    if norm_v1 == 0 or norm_v2 == 0:
        return 180.0

    cosine = np.dot(v1, v2) / (norm_v1 * norm_v2)
    cosine = np.clip(cosine, -1.0, 1.0)
    angle_rad = np.arccos(cosine)
    return round(float(np.degrees(angle_rad)), 2)


def calculate_knee_valgus(hip: Dict[str, float], knee: Dict[str, float], ankle: Dict[str, float], is_left: bool) -> float:
    """
    Calculate Dynamic Knee Valgus Angle (inward collapse) in degrees.
    In standard frontal view:
    Normal anatomical angle is straight (~0 deg valgus).
    Inward medial collapse creates a valgus deviation.
    """
    internal_angle = calculate_angle_2d(hip, knee, ankle)
    # Deviation from straight line
    deviation = abs(180.0 - internal_angle)

    # Check if knee moves medially (inward towards center line between hip and ankle)
    mid_x = (hip["x"] + ankle["x"]) / 2.0
    
    # In camera view:
    # If athlete is facing camera, Left knee (screen right) moves medial when x decreases towards mid_x
    # Right knee (screen left) moves medial when x increases towards mid_x
    if is_left:
        is_medial = knee["x"] < mid_x if hip["x"] > ankle["x"] else knee["x"] < hip["x"]
    else:
        is_medial = knee["x"] > mid_x if hip["x"] < ankle["x"] else knee["x"] > hip["x"]

    # Even if subtle, return the frontal deviation angle
    valgus_angle = deviation if deviation < 45.0 else 0.0
    return round(float(valgus_angle), 2)


def calculate_trunk_lean(
    left_shoulder: Dict[str, float],
    right_shoulder: Dict[str, float],
    left_hip: Dict[str, float],
    right_hip: Dict[str, float]
) -> Dict[str, float]:
    """
    Calculate forward and lateral trunk lean relative to vertical axis.
    """
    mid_shoulder = {
        "x": (left_shoulder["x"] + right_shoulder["x"]) / 2.0,
        "y": (left_shoulder["y"] + right_shoulder["y"]) / 2.0
    }
    mid_hip = {
        "x": (left_hip["x"] + right_hip["x"]) / 2.0,
        "y": (left_hip["y"] + right_hip["y"]) / 2.0
    }

    # Trunk vector pointing from hip to shoulder
    dx = mid_shoulder["x"] - mid_hip["x"]
    dy = mid_shoulder["y"] - mid_hip["y"]  # In image coords, shoulder is above hip so dy < 0

    # Angle with upward vertical vector [0, -1]
    trunk_vec = np.array([dx, dy])
    up_vec = np.array([0.0, -1.0])

    norm_t = np.linalg.norm(trunk_vec)
    if norm_t == 0:
        return {"trunk_lean": 0.0, "lateral_lean": 0.0}

    cos_theta = np.dot(trunk_vec, up_vec) / norm_t
    cos_theta = np.clip(cos_theta, -1.0, 1.0)
    lean_deg = float(np.degrees(np.arccos(cos_theta)))

    # Lateral lean is tilt in X axis
    lateral_lean = float(abs(np.degrees(np.arctan2(dx, -dy)))) if dy != 0 else 0.0

    return {
        "trunk_lean": round(lean_deg, 2),
        "lateral_lean": round(lateral_lean, 2)
    }


def calculate_asymmetry_index(left_val: float, right_val: float) -> float:
    """
    Bilateral Asymmetry Index (ASI %):
    ASI = (|Left - Right| / (0.5 * (Left + Right))) * 100
    """
    mean_val = 0.5 * (abs(left_val) + abs(right_val))
    if mean_val < 1.0:
        return 0.0
    diff = abs(left_val - right_val)
    asi = (diff / mean_val) * 100.0
    return round(float(asi), 2)


class BiomechanicalAnalyzer:
    """
    Analyzes body kinematics, joint angles, bilateral symmetry, 
    and movement quality scores from pose landmark time-series.
    """

    def analyze_frame(self, landmarks: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Analyze a single frame's pose landmarks.
        """
        if not landmarks or len(landmarks) < 33:
            return None

        lm_by_id = {lm["id"]: lm for lm in landmarks}

        try:
            # Key joints
            l_sh = lm_by_id[11]
            r_sh = lm_by_id[12]
            l_hip = lm_by_id[23]
            r_hip = lm_by_id[24]
            l_knee = lm_by_id[25]
            r_knee = lm_by_id[26]
            l_ankle = lm_by_id[27]
            r_ankle = lm_by_id[28]

            # Internal Joint Angles
            l_knee_angle = calculate_angle_2d(l_hip, l_knee, l_ankle)
            r_knee_angle = calculate_angle_2d(r_hip, r_knee, r_ankle)

            # Knee Flexion (0 deg = straight, 90 deg = bent)
            l_knee_flexion = round(max(0.0, 180.0 - l_knee_angle), 2)
            r_knee_flexion = round(max(0.0, 180.0 - r_knee_angle), 2)

            # Hip Angles
            l_hip_angle = calculate_angle_2d(l_sh, l_hip, l_knee)
            r_hip_angle = calculate_angle_2d(r_sh, r_hip, r_knee)

            # Dynamic Knee Valgus
            l_valgus = calculate_knee_valgus(l_hip, l_knee, l_ankle, is_left=True)
            r_valgus = calculate_knee_valgus(r_hip, r_knee, r_ankle, is_left=False)

            # Trunk Posture
            trunk = calculate_trunk_lean(l_sh, r_sh, l_hip, r_hip)

            # Bilateral Symmetry
            knee_symmetry = calculate_asymmetry_index(l_knee_flexion, r_knee_flexion)
            valgus_symmetry = calculate_asymmetry_index(l_valgus, r_valgus)

            return {
                "left_knee_angle": l_knee_angle,
                "right_knee_angle": r_knee_angle,
                "left_knee_flexion": l_knee_flexion,
                "right_knee_flexion": r_knee_flexion,
                "left_hip_angle": l_hip_angle,
                "right_hip_angle": r_hip_angle,
                "left_valgus_angle": l_valgus,
                "right_valgus_angle": r_valgus,
                "trunk_lean": trunk["trunk_lean"],
                "lateral_lean": trunk["lateral_lean"],
                "knee_symmetry_index": knee_symmetry,
                "valgus_symmetry_index": valgus_symmetry
            }
        except KeyError:
            return None

    def assess_movement_quality(self, frames_kinematics: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Aggregate video time-series kinematics into comprehensive Movement Quality Assessment.
        """
        valid_frames = [f for f in frames_kinematics if f is not None]
        if not valid_frames:
            return {
                "overall_score": 0.0,
                "grade": "INSUFFICIENT_DATA",
                "symmetry_score": 0.0,
                "valgus_stability_score": 0.0,
                "rom_score": 0.0,
                "posture_score": 0.0,
                "metrics_summary": {},
                "anomalies": ["Insufficient body landmarks detected to evaluate movement quality."]
            }

        # Extract metric arrays
        l_valgus_arr = [f["left_valgus_angle"] for f in valid_frames]
        r_valgus_arr = [f["right_valgus_angle"] for f in valid_frames]
        l_flex_arr = [f["left_knee_flexion"] for f in valid_frames]
        r_flex_arr = [f["right_knee_flexion"] for f in valid_frames]
        symm_arr = [f["knee_symmetry_index"] for f in valid_frames]
        trunk_arr = [f["trunk_lean"] for f in valid_frames]

        max_l_valgus = float(np.max(l_valgus_arr))
        max_r_valgus = float(np.max(r_valgus_arr))
        peak_valgus = max(max_l_valgus, max_r_valgus)
        avg_valgus = float(np.mean(l_valgus_arr + r_valgus_arr))

        max_l_flex = float(np.max(l_flex_arr))
        max_r_flex = float(np.max(r_flex_arr))
        peak_flexion = max(max_l_flex, max_r_flex)

        mean_asymmetry = float(np.mean(symm_arr))
        peak_asymmetry = float(np.max(symm_arr))

        mean_trunk_lean = float(np.mean(trunk_arr))
        peak_trunk_lean = float(np.max(trunk_arr))

        # Scoring Modules (0 to 100 each)
        # 1. Valgus Stability: Deduct heavily for valgus collapse > 10 deg
        valgus_stability_score = max(0.0, min(100.0, 100.0 - (peak_valgus * 4.5)))

        # 2. Symmetry Score: Deduct for asymmetry > 10%
        symmetry_score = max(0.0, min(100.0, 100.0 - (mean_asymmetry * 3.5)))

        # 3. Range of Motion (ROM) Score:
        # For squat/jump/landing, knee flexion between 70 and 110 deg is standard
        if peak_flexion >= 75.0:
            rom_score = 95.0
        elif peak_flexion >= 50.0:
            rom_score = 75.0 + (peak_flexion - 50.0) * 0.8
        else:
            rom_score = max(30.0, peak_flexion * 1.4)

        # 4. Posture / Trunk Stability Score:
        posture_score = max(0.0, min(100.0, 100.0 - (peak_trunk_lean * 1.4)))

        # Composite Overall Score
        overall_score = round(
            (0.35 * valgus_stability_score) +
            (0.25 * symmetry_score) +
            (0.25 * rom_score) +
            (0.15 * posture_score),
            1
        )

        # Grade Determination
        if overall_score >= 85.0:
            grade = "EXCELLENT"
        elif overall_score >= 70.0:
            grade = "GOOD"
        elif overall_score >= 50.0:
            grade = "MODERATE_RISK"
        else:
            grade = "HIGH_RISK"

        # Anomaly Detection Flags
        anomalies = []
        if peak_valgus >= 14.0:
            side = "Left" if max_l_valgus > max_r_valgus else "Right"
            anomalies.append(f"Severe Dynamic Knee Valgus Collapse ({side} knee reached {peak_valgus}° deviation).")
        elif peak_valgus >= 9.0:
            anomalies.append(f"Mild-to-Moderate Knee Valgus medial shift observed ({peak_valgus}°).")

        if mean_asymmetry >= 18.0:
            anomalies.append(f"High bilateral load asymmetry ({mean_asymmetry:.1f}% mean asymmetry).")
        elif mean_asymmetry >= 12.0:
            anomalies.append(f"Moderate bilateral limb asymmetry detected ({mean_asymmetry:.1f}%).")

        if peak_trunk_lean >= 35.0:
            anomalies.append(f"Excessive forward trunk lean ({peak_trunk_lean}°), indicating core instability.")

        if peak_flexion < 55.0:
            anomalies.append("Limited knee flexion depth (stiff landing / shallow range of motion).")

        if not anomalies:
            anomalies.append("Biomechanical movement patterns within optimal functional ranges.")

        return {
            "overall_score": overall_score,
            "grade": grade,
            "valgus_stability_score": round(valgus_stability_score, 1),
            "symmetry_score": round(symmetry_score, 1),
            "rom_score": round(rom_score, 1),
            "posture_score": round(posture_score, 1),
            "metrics_summary": {
                "peak_knee_valgus_left": round(max_l_valgus, 1),
                "peak_knee_valgus_right": round(max_r_valgus, 1),
                "peak_valgus_overall": round(peak_valgus, 1),
                "avg_valgus_overall": round(avg_valgus, 1),
                "peak_knee_flexion_left": round(max_l_flex, 1),
                "peak_knee_flexion_right": round(max_r_flex, 1),
                "peak_flexion_overall": round(peak_flexion, 1),
                "mean_asymmetry_index": round(mean_asymmetry, 1),
                "peak_asymmetry_index": round(peak_asymmetry, 1),
                "mean_trunk_lean": round(mean_trunk_lean, 1),
                "peak_trunk_lean": round(peak_trunk_lean, 1)
            },
            "anomalies": anomalies
        }

    def generate_synthetic_biomechanics_demo(self, movement_type: str = "SQUAT") -> Dict[str, Any]:
        """
        Generate realistic kinematic data for instant demonstration without requiring video upload.
        """
        frames_kinematics = []
        num_frames = 60

        for i in range(num_frames):
            # Phase of movement: 0 to pi (eccentric) to 2pi (concentric)
            phase = (i / num_frames) * 2 * math.pi
            depth_factor = (1.0 - math.cos(phase)) / 2.0  # 0.0 at standing, 1.0 at peak depth

            # Knee flexion cycles from 5 deg to 92 deg
            l_flex = 8.0 + (84.0 * depth_factor) + (np.sin(i * 0.4) * 1.5)
            # Slight natural asymmetry (right leg slightly lags)
            r_flex = 7.0 + (78.0 * depth_factor) + (np.cos(i * 0.4) * 1.2)

            # Knee valgus (medial collapse) occurs near max depth
            l_valgus = 2.0 + (9.5 * (depth_factor ** 1.5))
            r_valgus = 1.8 + (6.2 * (depth_factor ** 1.5))

            # Trunk lean increases during descent
            trunk_lean = 6.0 + (22.0 * depth_factor)

            # Asymmetry
            knee_symm = calculate_asymmetry_index(l_flex, r_flex)
            valgus_symm = calculate_asymmetry_index(l_valgus, r_valgus)

            frames_kinematics.append({
                "frame_index": i,
                "timestamp": round(i / 30.0, 2),
                "left_knee_angle": round(180.0 - l_flex, 1),
                "right_knee_angle": round(180.0 - r_flex, 1),
                "left_knee_flexion": round(l_flex, 1),
                "right_knee_flexion": round(r_flex, 1),
                "left_hip_angle": round(170.0 - (70.0 * depth_factor), 1),
                "right_hip_angle": round(168.0 - (67.0 * depth_factor), 1),
                "left_valgus_angle": round(l_valgus, 1),
                "right_valgus_angle": round(r_valgus, 1),
                "trunk_lean": round(trunk_lean, 1),
                "lateral_lean": round(abs(np.sin(i * 0.2) * 3.5), 1),
                "knee_symmetry_index": round(knee_symm, 1),
                "valgus_symmetry_index": round(valgus_symm, 1)
            })

        quality_report = self.assess_movement_quality(frames_kinematics)

        return {
            "movement_type": movement_type,
            "total_frames": num_frames,
            "fps": 30.0,
            "duration": 2.0,
            "quality_report": quality_report,
            "sampled_frames": frames_kinematics[::2]  # Every second frame for clean payload
        }
