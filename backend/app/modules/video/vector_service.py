"""Skeletal Vector Posture Twin Service.

Transforms 3D MediaPipe pose landmarks at the critical movement inflection frame
into normalized 2D SVG canvas coordinates with joint angle annotations,
plumb-line balance indicators, and color-coded biomechanical fault zones.

Inflection Selection:
- Squatting / Landing / Jumping: Peak eccentric depth (sitting turnaround / ground absorption)
- Running / Sprinting: Peak stride extension (maximum inter-ankle stride separation)
- Throwing: Peak release extension (maximum reach)
- Cutting: Deceleration plant step (widest lateral foot placement relative to pelvis)
"""

from __future__ import annotations

import math
from typing import Any, Optional
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.video.comparison_schemas import PostureSnapshot
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
    if norm1 < 1e-5 or norm2 < 1e-5:
        return 180.0
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
    padding: float = 40.0,
) -> dict[str, Any]:
    """Normalizes 3D MediaPipe coordinates into a scaled 2D SVG bounding box.
    Centers the subject horizontally and anchors feet to the ground line.
    """
    keypoint_coords: dict[str, tuple[float, float]] = {}

    for name, idx in LM.items():
        val = raw_landmarks.get(str(idx)) or raw_landmarks.get(idx)
        if val and len(val) >= 2:
            keypoint_coords[name] = (float(val[0]), float(val[1]))

    if len(keypoint_coords) < 6:
        return {}

    nose_pt = keypoint_coords.get("nose")
    la_pt = keypoint_coords.get("left_ankle") or keypoint_coords.get("right_ankle")
    lh_pt = keypoint_coords.get("left_hip") or keypoint_coords.get("right_hip")

    invert_y = False
    if nose_pt and la_pt and nose_pt[1] >= la_pt[1]:
        invert_y = True
    elif nose_pt and lh_pt and nose_pt[1] >= lh_pt[1]:
        invert_y = True

    if invert_y:
        keypoint_coords = {k: (x, -y) for k, (x, y) in keypoint_coords.items()}

    all_x = [pt[0] for pt in keypoint_coords.values()]
    all_y = [pt[1] for pt in keypoint_coords.values()]

    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)

    width_span = max(max_x - min_x, 0.001)
    height_span = max(max_y - min_y, 0.001)

    scale_x = (target_width - 2 * padding) / width_span
    scale_y = (target_height - 2 * padding) / height_span
    scale = min(scale_x, scale_y)

    ground_y = round(target_height - padding, 1)

    center_x = (min_x + max_x) / 2
    offset_x = (target_width / 2) - (center_x * scale)
    offset_y = ground_y - (max_y * scale)

    normalized: dict[str, list[float]] = {}
    for name, (orig_x, orig_y) in keypoint_coords.items():
        norm_x = round(orig_x * scale + offset_x, 1)
        norm_y = round(orig_y * scale + offset_y, 1)
        normalized[name] = [norm_x, norm_y]

    if normalized.get("nose") and normalized.get("left_ankle"):
        if normalized["nose"][1] > normalized["left_ankle"][1]:
            for name in normalized:
                normalized[name][1] = round(ground_y - (normalized[name][1] - padding), 1)

    ls = normalized.get("left_shoulder")
    rs = normalized.get("right_shoulder")
    lh = normalized.get("left_hip")
    rh = normalized.get("right_hip")

    if ls and rs:
        normalized["mid_shoulder"] = [round((ls[0] + rs[0]) / 2, 1), round((ls[1] + rs[1]) / 2, 1)]
    if lh and rh:
        normalized["mid_hip"] = [round((lh[0] + rh[0]) / 2, 1), round((lh[1] + rh[1]) / 2, 1)]

    angles: dict[str, Any] = {}
    faults: list[str] = []

    if lh and normalized.get("left_knee") and normalized.get("left_ankle"):
        k_angle = _calculate_angle_2d(
            (lh[0], lh[1]),
            (normalized["left_knee"][0], normalized["left_knee"][1]),
            (normalized["left_ankle"][0], normalized["left_ankle"][1]),
        )
        angles["knee_flexion_left"] = k_angle
        if k_angle > 140:
            faults.append("insufficient_depth")

    if rh and normalized.get("right_knee") and normalized.get("right_ankle"):
        k_angle_r = _calculate_angle_2d(
            (rh[0], rh[1]),
            (normalized["right_knee"][0], normalized["right_knee"][1]),
            (normalized["right_ankle"][0], normalized["right_ankle"][1]),
        )
        angles["knee_flexion_right"] = k_angle_r

    if normalized.get("mid_hip") and normalized.get("mid_shoulder"):
        trunk_lean = _calculate_trunk_lean(
            (normalized["mid_hip"][0], normalized["mid_hip"][1]),
            (normalized["mid_shoulder"][0], normalized["mid_shoulder"][1]),
        )
        angles["trunk_lean"] = trunk_lean
        if trunk_lean > 35.0:
            faults.append("excessive_trunk_lean")

    if normalized.get("left_knee") and lh and normalized.get("left_ankle"):
        lk_x = normalized["left_knee"][0]
        lh_x = lh[0]
        la_x = normalized["left_ankle"][0]
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
        "ground_y": ground_y,
    }


def select_peak_inflection_frame(frames: list[PoseFrame], movement_type: str) -> PoseFrame | None:
    """Identifies the biomechanically significant inflection frame from pose frames."""
    if not frames:
        return None

    valid: list[PoseFrame] = []
    for fr in frames:
        kp = fr.keypoints or {}
        n = kp.get("0") or kp.get(0)
        lh = kp.get("23") or kp.get(23)
        rh = kp.get("24") or kp.get(24)
        la = kp.get("27") or kp.get(27)
        ra = kp.get("28") or kp.get(28)
        lk = kp.get("25") or kp.get(25)
        rk = kp.get("26") or kp.get(26)

        if not (n and lh and rh and la and ra and lk and rk):
            continue

        mid_hip_y = (float(lh[1]) + float(rh[1])) / 2
        mid_ank_y = (float(la[1]) + float(ra[1])) / 2

        if float(n[1]) < mid_hip_y and mid_hip_y < mid_ank_y:
            valid.append(fr)

    if not valid:
        return frames[len(frames) // 2]

    mv = (movement_type or "").lower()

    if "squat" in mv:
        def knee_depth(f: PoseFrame) -> float:
            kp = f.keypoints or {}
            k_left = _calculate_angle_2d(
                (float(kp["23"][0]), float(kp["23"][1])),
                (float(kp["25"][0]), float(kp["25"][1])),
                (float(kp["27"][0]), float(kp["27"][1])),
            )
            k_right = _calculate_angle_2d(
                (float(kp["24"][0]), float(kp["24"][1])),
                (float(kp["26"][0]), float(kp["26"][1])),
                (float(kp["28"][0]), float(kp["28"][1])),
            )
            return min(k_left, k_right)
        return min(valid, key=knee_depth)

    elif "run" in mv or "sprint" in mv:
        def stride_extension(f: PoseFrame) -> float:
            kp = f.keypoints or {}
            la = np.array([float(kp["27"][0]), float(kp["27"][1])])
            ra = np.array([float(kp["28"][0]), float(kp["28"][1])])
            return float(np.linalg.norm(la - ra))
        return max(valid, key=stride_extension)

    elif "throw" in mv:
        def throwing_reach(f: PoseFrame) -> float:
            kp = f.keypoints or {}
            reach_r, reach_l = 0.0, 0.0
            if "16" in kp and "12" in kp:
                rw = np.array([float(kp["16"][0]), float(kp["16"][1])])
                rs = np.array([float(kp["12"][0]), float(kp["12"][1])])
                reach_r = float(np.linalg.norm(rw - rs))
            if "15" in kp and "11" in kp:
                lw = np.array([float(kp["15"][0]), float(kp["15"][1])])
                ls = np.array([float(kp["11"][0]), float(kp["11"][1])])
                reach_l = float(np.linalg.norm(lw - ls))
            return max(reach_r, reach_l)
        return max(valid, key=throwing_reach)

    elif "cut" in mv:
        def cutting_plant(f: PoseFrame) -> float:
            kp = f.keypoints or {}
            lh_x = float(kp["23"][0])
            rh_x = float(kp["24"][0])
            pelvis_x = (lh_x + rh_x) / 2
            la_x = float(kp["27"][0])
            ra_x = float(kp["28"][0])
            return max(abs(la_x - pelvis_x), abs(ra_x - pelvis_x))
        return max(valid, key=cutting_plant)

    elif "land" in mv or "jump" in mv:
        def landing_impact(f: PoseFrame) -> float:
            kp = f.keypoints or {}
            k_left = _calculate_angle_2d(
                (float(kp["23"][0]), float(kp["23"][1])),
                (float(kp["25"][0]), float(kp["25"][1])),
                (float(kp["27"][0]), float(kp["27"][1])),
            )
            k_right = _calculate_angle_2d(
                (float(kp["24"][0]), float(kp["24"][1])),
                (float(kp["26"][0]), float(kp["26"][1])),
                (float(kp["28"][0]), float(kp["28"][1])),
            )
            return min(k_left, k_right)
        return min(valid, key=landing_impact)

    return valid[len(valid) // 2]


async def extract_inflection_vector_for_video(db: AsyncSession, video_id: str) -> dict[str, Any] | None:
    """Extracts normalized keypoint coordinates and angles at the peak inflection frame of a video.
    Returns None if no pose tracking frames are available. Never fabricates textbook data.
    """
    video = await db.scalar(select(Video).where(Video.id == video_id))
    if not video:
        return None

    movement_type = video.movement_type if video else "squatting"

    frames = list((await db.scalars(
        select(PoseFrame)
        .where(PoseFrame.video_id == video_id)
        .order_by(PoseFrame.frame_number)
    )).all())

    if not frames:
        return None

    best_frame = select_peak_inflection_frame(frames, movement_type)
    if not best_frame or not best_frame.keypoints:
        return None

    vector_data = normalize_landmarks_to_svg(best_frame.keypoints)
    if not vector_data or not vector_data.get("landmarks"):
        return None

    vector_data["frame_number"] = best_frame.frame_number
    vector_data["timestamp_ms"] = best_frame.timestamp_ms
    vector_data["movement_type"] = movement_type
    return vector_data


def build_posture_snapshot(vector_dict: dict[str, Any] | None, valgus_flag: str | None = None) -> PostureSnapshot | None:
    """Converts raw vector dict to typed PostureSnapshot."""
    if not vector_dict or not vector_dict.get("landmarks"):
        return None
    ts_ms = vector_dict.get("timestamp_ms")
    ts_s = round(float(ts_ms) / 1000.0, 2) if ts_ms is not None else None
    angles_clean: dict[str, float] = {}
    for k, v in (vector_dict.get("angles") or {}).items():
        if isinstance(v, (int, float)):
            angles_clean[k] = round(float(v))
    return PostureSnapshot(
        frame_number=vector_dict.get("frame_number"),
        timestamp_s=ts_s,
        landmarks=vector_dict.get("landmarks", {}),
        angles=angles_clean,
        valgus_flag=valgus_flag,
    )
