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
    """Hip flexion, flexion-from-extension convention (same as knee_flexion_angle).

    0° = trunk and thigh in line (standing upright), larger = more flexed.

    Two corrections (2026-10-02):
    * Convention: the raw shoulder-hip-knee interior angle is ~180° when standing, so flexion =
      180° - interior. It used to return the interior angle, so a standing athlete read ~170°.
    * Lateral offset: the trunk axis is the shoulder-MIDPOINT minus hip-MIDPOINT (as in
      trunk_lean_angle), not the same-side shoulder. Shoulders sit ~9 cm further out laterally
      than hips, so using one shoulder leaked ~10° of frontal-plane offset into a sagittal angle
      (a perfectly upright standing pose read ~10° of hip flexion).
    """
    def pt(name):
        return np.array(world_landmarks[str(LANDMARK[name])])

    trunk_axis = (pt("left_shoulder") + pt("right_shoulder")) / 2 - (pt("left_hip") + pt("right_hip")) / 2
    hip = pt(f"{side}_hip")
    knee = pt(f"{side}_knee")
    return round(180.0 - joint_angle(hip + trunk_axis, hip, knee), 1)


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


def ankle_dorsiflexion_angle(world_landmarks: dict, side: str) -> float | None:
    """Sagittal ankle angle, 0 deg = shank (ankle->knee) perpendicular to the foot (heel->toe), + = dorsiflexion.

    None when a foot landmark is absent or the geometry is degenerate; NaN-free by construction.
    The foot landmarks are the least reliable ones the pose model gives: MediaPipe vs IMU on 27 adults had
    MAE ~7.5-7.8 deg and ICC < 0.5 for dorsiflexion (Russo 2026, Sensors 26:2148) against ~2-4.6 deg for the knee
    (docs/DECISIONS.md 2026-10-08). Read it as a within-athlete trend, never as an absolute clinical angle.
    """
    try:
        knee, ankle, heel, toe = (np.array(world_landmarks[str(LANDMARK[f"{side}_{n}"])]) for n in ("knee", "ankle", "heel", "foot_index"))
    except KeyError:
        return None
    if not (np.linalg.norm(knee - ankle) > 1e-6 and np.linalg.norm(toe - heel) > 1e-6):  # also False for NaN (occluded)
        return None
    return round(90.0 - joint_angle(knee, ankle, ankle + toe - heel), 1)


def hip_adduction_deviation(world_landmarks: dict, side: str) -> float | None:
    """QUALITATIVE ONLY (frontal plane, same rule as knee_valgus_flag): knee offset medial to the hip as % of thigh length.

    + = knee toward the midline (adducted), - = abducted. Frontal x is the lateral axis, like knee_valgus_flag.
    No flag threshold: no validated cut-off exists for it, so it is stored as a deviation, never as a precise angle.
    """
    other = "right" if side == "left" else "left"
    try:
        hip, knee, hip_o = (np.array(world_landmarks[str(LANDMARK[n])]) for n in (f"{side}_hip", f"{side}_knee", f"{other}_hip"))
    except KeyError:
        return None
    thigh, medial = np.linalg.norm(knee - hip), np.sign(hip_o[0] - hip[0])
    if not (thigh > 1e-6) or medial == 0:
        return None
    return round(float(100 * medial * (knee[0] - hip[0]) / thigh), 1)


def lower_body_extras(landmarks: dict, camera_view: str) -> list[dict]:
    """Engine 2.3 per-frame metrics shared by every lower-body calculator (one call each, registry untouched)."""
    out = []
    for side in ("left", "right"):
        if camera_view in ("sagittal", "other"):
            v = ankle_dorsiflexion_angle(landmarks, side)
            name = f"ankle_dorsiflexion_angle_{side}"
            if v is not None:
                out.append({"name": name, "value": v, "plane": "sagittal", "confidence": METRIC_CONFIDENCE[name]})
        if camera_view in ("frontal", "other"):
            v = hip_adduction_deviation(landmarks, side)
            name = f"hip_adduction_deviation_{side}"
            if v is not None:
                out.append({"name": name, "value": v, "plane": "frontal", "confidence": METRIC_CONFIDENCE[name]})
    return out


# Mapping metric names to their confidence levels
METRIC_CONFIDENCE = {
    "knee_flexion_angle_left": "validated",
    "knee_flexion_angle_right": "validated",
    "hip_flexion_angle_left": "validated",
    "hip_flexion_angle_right": "validated",
    "trunk_lean_angle": "validated",
    "knee_valgus_deviation_left": "qualitative",
    "knee_valgus_deviation_right": "qualitative",
    # Qualitative, not validated: SCIENCE_CONSTRAINTS sources knee/hip flexion and trunk lean only, and the one ankle study
    # found (Russo 2026: MAE ~7.5 deg, ICC < 0.5) is below that bar. A qualitative metric never becomes an anomaly feature.
    "ankle_dorsiflexion_angle_left": "qualitative",
    "ankle_dorsiflexion_angle_right": "qualitative",
    "hip_adduction_deviation_left": "qualitative",
    "hip_adduction_deviation_right": "qualitative",
}