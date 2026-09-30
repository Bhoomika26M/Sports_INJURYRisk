"""Biomechanics shared calculations and landmark indices.

Verified against MediaPipe's PoseLandmark enum (google-ai-edge/mediapipe source, 2026).
"""

import numpy as np

LANDMARK = {
    "nose": 0,
    "left_eye_inner": 1, "left_eye": 2, "left_eye_outer": 3,
    "right_eye_inner": 4, "right_eye": 5, "right_eye_outer": 6,
    "left_ear": 7, "right_ear": 8,
    "mouth_left": 9, "mouth_right": 10,
    "left_shoulder": 11, "right_shoulder": 12,
    "left_elbow": 13, "right_elbow": 14,
    "left_wrist": 15, "right_wrist": 16,
    "left_pinky": 17, "right_pinky": 18,
    "left_index": 19, "right_index": 20,
    "left_thumb": 21, "right_thumb": 22,
    "left_hip": 23, "right_hip": 24,
    "left_knee": 25, "right_knee": 26,
    "left_ankle": 27, "right_ankle": 28,
    "left_heel": 29, "right_heel": 30,
    "left_foot_index": 31, "right_foot_index": 32,
}


def joint_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Interior angle in degrees at vertex b, from 3D world-landmark points a, b, c."""
    v1, v2 = a - b, c - b
    cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    cos_angle = np.clip(cos_angle, -1.0, 1.0)
    return float(np.degrees(np.arccos(cos_angle)))


def knee_flexion_angle(world_landmarks: dict, side: str) -> float:
    """0° = leg fully straight, larger = more bent. Flexion-from-extension convention."""
    hip = np.array(world_landmarks[str(LANDMARK[f"{side}_hip"])])
    knee = np.array(world_landmarks[str(LANDMARK[f"{side}_knee"])])
    ankle = np.array(world_landmarks[str(LANDMARK[f"{side}_ankle"])])
    return round(180.0 - joint_angle(hip, knee, ankle), 1)


def hip_flexion_angle(world_landmarks: dict, side: str) -> float:
    """Hip flexion: 0° = leg extended back, larger = more flexed forward."""
    shoulder = np.array(world_landmarks[str(LANDMARK[f"{side}_shoulder"])])
    hip = np.array(world_landmarks[str(LANDMARK[f"{side}_hip"])])
    knee = np.array(world_landmarks[str(LANDMARK[f"{side}_knee"])])
    return round(joint_angle(shoulder, hip, knee), 1)


def trunk_lean_angle(world_landmarks: dict) -> float | None:
    """Trunk lean from upright. 0° = upright, positive = forward lean.

    NOTE: MediaPipe world +Y points DOWN (verified against real data:
    head y≈-0.6, ankle y≈+0.75), so 'up' is [0,-1,0]. Measuring against
    +Y would report ~180°-lean (verified bug, 2026-09-30).
    """
    shoulder_mid = (np.array(world_landmarks[str(LANDMARK["left_shoulder"])]) +
                    np.array(world_landmarks[str(LANDMARK["right_shoulder"])]) ) / 2
    hip_mid = (np.array(world_landmarks[str(LANDMARK["left_hip"])]) +
               np.array(world_landmarks[str(LANDMARK["right_hip"])]) ) / 2
    trunk_vector = shoulder_mid - hip_mid
    norm = np.linalg.norm(trunk_vector)
    if norm < 1e-6:
        return None
    up = np.array([0.0, -1.0, 0.0])
    cos_angle = np.clip(np.dot(trunk_vector, up) / norm, -1.0, 1.0)
    return round(float(np.degrees(np.arccos(cos_angle))), 1)


def knee_valgus_flag(world_landmarks: dict, side: str, threshold_pct: float = 10.0) -> dict:
    """
    QUALITATIVE ONLY. See /docs/SCIENCE_CONSTRAINTS.md — monocular frontal-plane knee angle
    is not valid against motion-capture ground truth. This returns a flag, not a precise angle:
    frontal-plane (x-axis) deviation of the knee from the straight hip-ankle line, as a
    percentage of leg length.
    """
    hip = np.array(world_landmarks[str(LANDMARK[f"{side}_hip"])])
    knee = np.array(world_landmarks[str(LANDMARK[f"{side}_knee"])])
    ankle = np.array(world_landmarks[str(LANDMARK[f"{side}_ankle"])])
    leg_length = np.linalg.norm(ankle - hip)
    if leg_length == 0:
        return {"deviation_pct": None, "flagged": False, "confidence": "qualitative"}
    line_unit = (ankle - hip) / leg_length
    knee_vec = knee - hip
    perpendicular = knee_vec - np.dot(knee_vec, line_unit) * line_unit
    deviation_pct = (abs(perpendicular[0]) / leg_length) * 100
    return {
        "deviation_pct": round(float(deviation_pct), 1),
        "flagged": deviation_pct > threshold_pct,
        "confidence": "qualitative",
    }


def limb_symmetry_index(left_peak: float, right_peak: float) -> float:
    """Standard LSI (used in sports-science return-to-sport testing): weaker / stronger × 100. 100 = perfect symmetry."""
    weaker, stronger = min(left_peak, right_peak), max(left_peak, right_peak)
    if stronger == 0:
        return 100.0
    return round((weaker / stronger) * 100, 1)


# Mapping metric names to their confidence levels
METRIC_CONFIDENCE = {
    "knee_flexion_angle_left": "validated",
    "knee_flexion_angle_right": "validated",
    "hip_flexion_angle_left": "validated",
    "hip_flexion_angle_right": "validated",
    "trunk_lean_angle": "validated",
    "knee_valgus_deviation_left": "qualitative",
    "knee_valgus_deviation_right": "qualitative",
}