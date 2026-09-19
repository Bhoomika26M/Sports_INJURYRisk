import numpy as np

# Verified against MediaPipe's PoseLandmark enum (google-ai-edge/mediapipe source, 2026)
LANDMARK = {
    "left_shoulder": 11, "right_shoulder": 12,
    "left_hip": 23, "right_hip": 24,
    "left_knee": 25, "right_knee": 26,
    "left_ankle": 27, "right_ankle": 28,
}


def joint_angle(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    """Interior angle in degrees at vertex b, from 3D world-landmark points a, b, c."""
    v1, v2 = a - b, c - b
    cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
    cos_angle = np.clip(cos_angle, -1.0, 1.0)  # floating-point drift can push this slightly outside
    return float(np.degrees(np.arccos(cos_angle)))


def knee_flexion_angle(world_landmarks: dict, side: str) -> float:
    """0° = leg fully straight, larger = more bent. This is the flexion-from-extension convention
    used throughout this system's UI and reports — not the raw interior angle."""
    hip = np.array(world_landmarks[str(LANDMARK[f"{side}_hip"])])
    knee = np.array(world_landmarks[str(LANDMARK[f"{side}_knee"])])
    ankle = np.array(world_landmarks[str(LANDMARK[f"{side}_ankle"])])
    return round(180.0 - joint_angle(hip, knee, ankle), 1)


def trunk_lean_angle(world_landmarks: dict) -> float | None:
    shoulder_mid = (np.array(world_landmarks[str(LANDMARK["left_shoulder"])]) + np.array(world_landmarks[str(LANDMARK["right_shoulder"])])) / 2
    hip_mid = (np.array(world_landmarks[str(LANDMARK["left_hip"])]) + np.array(world_landmarks[str(LANDMARK["right_hip"])])) / 2
    trunk_vector = shoulder_mid - hip_mid
    norm = np.linalg.norm(trunk_vector)
    if norm < 1e-6:
        return None  # degenerate frame — caller must skip, not store, this value
    vertical = np.array([0.0, 1.0, 0.0])
    cos_angle = np.clip(np.dot(trunk_vector, vertical) / norm, -1.0, 1.0)
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
    """Standard LSI (used in sports-science return-to-sport testing): weaker / stronger × 100.
    100 = perfect symmetry."""
    weaker, stronger = min(left_peak, right_peak), max(left_peak, right_peak)
    if stronger == 0:
        return 100.0
    return round((weaker / stronger) * 100, 1)

# Mapping metric names to their confidence levels
METRIC_CONFIDENCE = {
    "knee_flexion_angle_left": "validated",
    "knee_flexion_angle_right": "validated",
    "trunk_lean_angle": "validated",
    "knee_valgus_deviation_left": "qualitative",
    "knee_valgus_deviation_right": "qualitative",
}
