"""Skeletal Vector Posture Twin Service.

Transforms 3D MediaPipe pose landmarks at the critical movement inflection frame
into normalized 2D SVG canvas coordinates with joint angle annotations,
plumb-line balance indicators, and color-coded biomechanical fault zones.
"""

from __future__ import annotations

import math
from typing import Any, Optional
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.video.models import PoseFrame, Video


# MediaPipe Landmark Index Mapping
LM = {
    "nose": 0,
    "left_shoulder": 11,
    "right_shoulder": 12,
    "left_elbow": 13,
    "right_elbow": 14,
    "left_wrist": 15,
    "right_wrist": 16,
    "left_hip": 23,
    "right_hip": 24,
    "left_knee": 25,
    "right_knee": 26,
    "left_ankle": 27,
    "right_ankle": 28,
    "left_heel": 29,
    "right_heel": 30,
    "left_foot_index": 31,
    "right_foot_index": 32,
}


def _calculate_angle_2d(p1: tuple[float, float], p2: tuple[float, float], p3: tuple[float, float]) -> float:
    """Calculate the interior angle (in degrees) at vertex p2 between p1-p2 and p3-p2."""
    v1 = np.array([p1[0] - p2[0], p1[1] - p2[1]])
    v2 = np.array([p3[0] - p2[0], p3[1] - p2[1]])
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return 0.0
    cosine = np.dot(v1, v2) / (norm1 * norm2)
    angle = np.degrees(np.arccos(np.clip(cosine, -1.0, 1.0)))
    return round(float(angle), 1)


def _calculate_trunk_lean(mid_hip: tuple[float, float], mid_shoulder: tuple[float, float]) -> float:
    """Calculate forward trunk lean angle relative to vertical axis (0 = vertical)."""
    dx = abs(mid_shoulder[0] - mid_hip[0])
    dy = abs(mid_shoulder[1] - mid_hip[1])
    if dy == 0:
        return 90.0
    rad = math.atan2(dx, dy)
    return round(float(math.degrees(rad)), 1)


def normalize_landmarks_to_svg(
    raw_landmarks: dict[str, list[float]],
    target_width: float = 300.0,
    target_height: float = 400.0,
    padding: float = 40.0
) -> dict[str, Any]:
    """
    Normalizes 3D MediaPipe coordinates into a scaled 2D SVG bounding box.
    Centers the subject horizontally and anchors feet to the ground line.
    """
    keypoint_coords: dict[str, tuple[float, float]] = {}

    all_x = []
    all_y = []

    for name, idx in LM.items():
        val = raw_landmarks.get(str(idx)) or raw_landmarks.get(idx)
        if val and len(val) >= 2:
            x, y = float(val[0]), float(val[1])
            keypoint_coords[name] = (x, y)
            all_x.append(x)
            all_y.append(y)

    if not keypoint_coords or len(all_x) < 6:
        return {}

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)

    width_span = max(max_x - min_x, 0.001)
    height_span = max(max_y - min_y, 0.001)

    scale_x = (target_width - 2 * padding) / width_span
    scale_y = (target_height - 2 * padding) / height_span
    scale = min(scale_x, scale_y)

    # Centering offsets
    center_x = (min_x + max_x) / 2
    offset_x = (target_width / 2) - (center_x * scale)
    offset_y = (target_height - padding) - (max_y * scale)

    normalized: dict[str, list[float]] = {}
    for name, (orig_x, orig_y) in keypoint_coords.items():
        norm_x = round(orig_x * scale + offset_x, 1)
        norm_y = round(orig_y * scale + offset_y, 1)
        normalized[name] = [norm_x, norm_y]

    # Compute mid-points
    ls = normalized.get("left_shoulder")
    rs = normalized.get("right_shoulder")
    lh = normalized.get("left_hip")
    rh = normalized.get("right_hip")

    if ls and rs:
        normalized["mid_shoulder"] = [round((ls[0] + rs[0]) / 2, 1), round((ls[1] + rs[1]) / 2, 1)]
    if lh and rh:
        normalized["mid_hip"] = [round((lh[0] + rh[0]) / 2, 1), round((lh[1] + rh[1]) / 2, 1)]

    # Compute Kinematic Angles
    angles: dict[str, Any] = {}
    faults: list[str] = []

    # Left Knee Flexion
    if lh and normalized.get("left_knee") and normalized.get("left_ankle"):
        k_angle = _calculate_angle_2d(
            (lh[0], lh[1]),
            (normalized["left_knee"][0], normalized["left_knee"][1]),
            (normalized["left_ankle"][0], normalized["left_ankle"][1]),
        )
        angles["knee_flexion_left"] = k_angle
        if k_angle > 140:
            faults.append("insufficient_depth")

    # Right Knee Flexion
    if rh and normalized.get("right_knee") and normalized.get("right_ankle"):
        k_angle_r = _calculate_angle_2d(
            (rh[0], rh[1]),
            (normalized["right_knee"][0], normalized["right_knee"][1]),
            (normalized["right_ankle"][0], normalized["right_ankle"][1]),
        )
        angles["knee_flexion_right"] = k_angle_r

    # Trunk Lean
    if normalized.get("mid_hip") and normalized.get("mid_shoulder"):
        trunk_lean = _calculate_trunk_lean(
            (normalized["mid_hip"][0], normalized["mid_hip"][1]),
            (normalized["mid_shoulder"][0], normalized["mid_shoulder"][1]),
        )
        angles["trunk_lean"] = trunk_lean
        if trunk_lean > 35.0:
            faults.append("excessive_trunk_lean")

    # Frontal Knee Valgus Check
    # In frontal view, if knee x-coord drifts medially inward past the hip-ankle corridor
    if normalized.get("left_knee") and lh and normalized.get("left_ankle"):
        lk_x = normalized["left_knee"][0]
        lh_x = lh[0]
        la_x = normalized["left_ankle"][0]
        # In left leg (viewer's left or subject's left), medial is toward the right (center)
        if lk_x > min(lh_x, la_x) + abs(lh_x - la_x) * 0.4 and abs(lh_x - la_x) > 5:
            angles["knee_valgus_left"] = "mild"
            faults.append("knee_valgus")
        else:
            angles["knee_valgus_left"] = "none"

    if normalized.get("right_knee") and rh and normalized.get("right_ankle"):
        rk_x = normalized["right_knee"][0]
        rh_x = rh[0]
        ra_x = normalized["right_ankle"][0]
        if rk_x < max(rh_x, ra_x) - abs(rh_x - ra_x) * 0.4 and abs(rh_x - ra_x) > 5:
            angles["knee_valgus_right"] = "mild"
            if "knee_valgus" not in faults:
                faults.append("knee_valgus")
        else:
            angles["knee_valgus_right"] = "none"

    return {
        "landmarks": normalized,
        "angles": angles,
        "faults": list(set(faults)),
        "ground_y": round(target_height - padding, 1),
    }


def get_textbook_ideal_landmarks(movement_type: str = "squatting") -> dict[str, Any]:
    """
    Returns pre-calculated textbook biomechanical alignment coordinates
    for clean side-by-side or ghost overlay against trainee footage.
    """
    mv = (movement_type or "").lower()

    if "jump" in mv or "land" in mv:
        # Athletic landing posture: 90 deg knee flexion, upright balanced trunk, knees tracked over feet
        landmarks = {
            "nose": [150.0, 70.0],
            "left_shoulder": [128.0, 115.0],
            "right_shoulder": [172.0, 115.0],
            "left_elbow": [108.0, 160.0],
            "right_elbow": [192.0, 160.0],
            "left_wrist": [112.0, 205.0],
            "right_wrist": [188.0, 205.0],
            "left_hip": [134.0, 220.0],
            "right_hip": [166.0, 220.0],
            "left_knee": [130.0, 290.0],
            "right_knee": [170.0, 290.0],
            "left_ankle": [130.0, 360.0],
            "right_ankle": [170.0, 360.0],
            "left_heel": [125.0, 365.0],
            "right_heel": [175.0, 365.0],
            "left_foot_index": [130.0, 370.0],
            "right_foot_index": [170.0, 370.0],
            "mid_shoulder": [150.0, 115.0],
            "mid_hip": [150.0, 220.0],
        }
        angles = {
            "knee_flexion_left": 95.0,
            "knee_flexion_right": 95.0,
            "trunk_lean": 15.0,
            "knee_valgus_left": "none",
            "knee_valgus_right": "none",
        }
    elif "sprint" in mv or "run" in mv:
        # High knee drive running posture
        landmarks = {
            "nose": [150.0, 60.0],
            "left_shoulder": [135.0, 105.0],
            "right_shoulder": [165.0, 105.0],
            "left_elbow": [110.0, 150.0],
            "right_elbow": [190.0, 140.0],
            "left_wrist": [125.0, 185.0],
            "right_wrist": [175.0, 95.0],
            "left_hip": [140.0, 205.0],
            "right_hip": [160.0, 205.0],
            "left_knee": [185.0, 235.0],  # Drive leg
            "right_knee": [155.0, 285.0], # Stance leg
            "left_ankle": [175.0, 310.0],
            "right_ankle": [155.0, 360.0],
            "left_heel": [170.0, 315.0],
            "right_heel": [150.0, 365.0],
            "left_foot_index": [180.0, 320.0],
            "right_foot_index": [160.0, 370.0],
            "mid_shoulder": [150.0, 105.0],
            "mid_hip": [150.0, 205.0],
        }
        angles = {
            "knee_flexion_left": 85.0,
            "knee_flexion_right": 165.0,
            "trunk_lean": 8.0,
            "knee_valgus_left": "none",
            "knee_valgus_right": "none",
        }
    else:
        # Standard Deep Squat: Hips parallel, knees over 2nd toe, upright neutral spine
        landmarks = {
            "nose": [150.0, 80.0],
            "left_shoulder": [125.0, 125.0],
            "right_shoulder": [175.0, 125.0],
            "left_elbow": [105.0, 170.0],
            "right_elbow": [195.0, 170.0],
            "left_wrist": [115.0, 210.0],
            "right_wrist": [185.0, 210.0],
            "left_hip": [132.0, 235.0],
            "right_hip": [168.0, 235.0],
            "left_knee": [118.0, 295.0],
            "right_knee": [182.0, 295.0],
            "left_ankle": [122.0, 360.0],
            "right_ankle": [178.0, 360.0],
            "left_heel": [116.0, 365.0],
            "right_heel": [184.0, 365.0],
            "left_foot_index": [122.0, 370.0],
            "right_foot_index": [178.0, 370.0],
            "mid_shoulder": [150.0, 125.0],
            "mid_hip": [150.0, 235.0],
        }
        angles = {
            "knee_flexion_left": 98.0,
            "knee_flexion_right": 98.0,
            "trunk_lean": 18.0,
            "knee_valgus_left": "none",
            "knee_valgus_right": "none",
        }

    return {
        "landmarks": landmarks,
        "angles": angles,
        "faults": [],
        "ground_y": 360.0,
        "is_textbook_benchmark": True,
    }


async def extract_inflection_vector_for_video(db: AsyncSession, video_id: str) -> dict[str, Any]:
    """
    Extracts the keypoint coordinates and angles at the peak inflection frame of a video.
    Falls back to textbook standard if pose frames are missing.
    """
    video = await db.scalar(select(Video).where(Video.id == video_id))
    movement_type = video.movement_type if video else "squatting"

    # Query all pose frames for this video
    frames = list((await db.scalars(
        select(PoseFrame)
        .where(PoseFrame.video_id == video_id)
        .order_by(PoseFrame.frame_number)
    )).all())

    if not frames:
        return get_textbook_ideal_landmarks(movement_type)

    # Search for peak inflection frame: frame with minimum knee y or maximum knee flexion
    # World landmark landmarks have Y positive downward. Mid-hip Y is lowest (numerically highest) at bottom of squat
    best_frame = frames[len(frames) // 2]  # Default to middle frame
    max_hip_y = -999.0

    for fr in frames:
        kp = fr.keypoints or {}
        # Landmark 23 & 24 are hips
        lh = kp.get("23") or kp.get(23)
        rh = kp.get("24") or kp.get(24)
        if lh and rh and len(lh) >= 2 and len(rh) >= 2:
            avg_y = (float(lh[1]) + float(rh[1])) / 2
            if avg_y > max_hip_y:
                max_hip_y = avg_y
                best_frame = fr

    raw_kp = best_frame.keypoints or {}
    vector_data = normalize_landmarks_to_svg(raw_kp)
    if not vector_data:
        return get_textbook_ideal_landmarks(movement_type)

    vector_data["frame_number"] = best_frame.frame_number
    vector_data["timestamp_ms"] = best_frame.timestamp_ms
    vector_data["movement_type"] = movement_type
    return vector_data
