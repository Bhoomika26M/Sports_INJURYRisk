"""Synthetic keypoint sequences for tests (front-view person, normalised image coords)."""

import numpy as np

from app.services.pose_estimation import JOINT_INDEX, JOINT_NAMES


def make_sequence(
    frames: int = 120,
    fps: float = 30.0,
    squat_reps: int = 4,
    valgus_offset: float = 0.0,
    pelvic_drop: float = 0.0,
    left_rom_scale: float = 1.0,
    fatigue_drift: float = 0.0,
) -> np.ndarray:
    """Side/front hybrid skeleton doing squats.

    Knee flexion is created by moving the knees forward in x relative to hip/ankle
    (so the 2D hip-knee-ankle angle changes). `valgus_offset` shifts the knees
    toward the midline, `pelvic_drop` tilts the pelvis, `left_rom_scale` shrinks the
    left squat depth (asymmetry), and `fatigue_drift` reduces depth over reps.
    """
    t = np.arange(frames) / fps
    phase = np.sin(np.pi * squat_reps * t / t[-1]) ** 2  # 0..1, one cycle per rep
    rep_idx = np.minimum((np.arange(frames) / frames * squat_reps).astype(int), squat_reps - 1)
    depth = 0.10 * (1.0 - fatigue_drift * rep_idx / max(squat_reps - 1, 1))

    P = np.zeros((frames, len(JOINT_NAMES), 2))

    def put(name, x, y):
        P[:, JOINT_INDEX[name], 0] = x
        P[:, JOINT_INDEX[name], 1] = y

    for side, sx, scale in (("left", 0.55, left_rom_scale), ("right", 0.45, 1.0)):
        inward = -1 if side == "left" else 1  # toward the body midline (x = 0.5)
        d = depth * phase * scale
        hip_y = 0.50 + d
        put(f"{side}_shoulder", sx, 0.30 + d)
        put(f"{side}_hip", sx, hip_y + (pelvic_drop * phase if side == "left" else 0.0))
        put(f"{side}_knee", sx + inward * valgus_offset * phase + 0.6 * d, 0.70 + 0.3 * d)
        put(f"{side}_ankle", sx, 0.90)
        put(f"{side}_foot", sx + 0.05, 0.92)
        put(f"{side}_elbow", sx + (0.04 if side == "left" else -0.04), 0.42 + d)
        put(f"{side}_wrist", sx + (0.05 if side == "left" else -0.05), 0.55 + d)
    put("nose", 0.5, 0.15 + 0.5 * depth * phase)
    return P
