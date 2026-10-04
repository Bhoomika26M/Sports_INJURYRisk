"""Synthetic human motion with KNOWN ground truth, in MediaPipe world-landmark conventions.

Hip-centred metres, +Y DOWN (head y<0, ankles y>0), side-on camera: x = direction of travel,
z = depth (left side z<0). Joint angles are exact by construction, so tests can assert the
engine recovers them — and then inject the real-world problems it must survive: pose-model
noise, single-frame spikes, occluded legs (low visibility + hallucinated coordinates),
dropped frames and a rolled camera.
"""

import math

import numpy as np

from app.modules.biomechanics.calculations import LANDMARK

THIGH, SHANK, TRUNK, HIP_Z, SHOULDER_Z = 0.45, 0.45, 0.50, 0.09, 0.18


def make_pose(knee_l, knee_r, lean, thigh_l=None, thigh_r=None) -> dict:
    """One pose. knee_*: knee flexion (deg). lean: trunk lean from vertical (deg, forward +x).
    thigh_*: thigh angle from straight-down toward +x (deg); defaults to half the knee flexion."""
    lm = {i: np.zeros(3) for i in range(33)}
    for side, k, th, z in (("left", knee_l, thigh_l, -HIP_Z), ("right", knee_r, thigh_r, HIP_Z)):
        phi = math.radians(k * 0.5 if th is None else th)
        psi = phi - math.radians(k)
        hip = np.array([0.0, 0.0, z])
        knee = hip + THIGH * np.array([math.sin(phi), math.cos(phi), 0.0])
        ankle = knee + SHANK * np.array([math.sin(psi), math.cos(psi), 0.0])
        lm[LANDMARK[f"{side}_hip"]] = hip
        lm[LANDMARK[f"{side}_knee"]] = knee
        lm[LANDMARK[f"{side}_ankle"]] = ankle
        lm[LANDMARK[f"{side}_heel"]] = ankle + np.array([-0.05, 0.03, 0.0])
        lm[LANDMARK[f"{side}_foot_index"]] = ankle + np.array([0.12, 0.04, 0.0])
    lam = math.radians(lean)
    up = TRUNK * np.array([math.sin(lam), -math.cos(lam), 0.0])
    for side, z in (("left", -SHOULDER_Z), ("right", SHOULDER_Z)):
        sh = up + np.array([0.0, 0.0, z])
        lm[LANDMARK[f"{side}_shoulder"]] = sh
        lm[LANDMARK[f"{side}_elbow"]] = sh + np.array([0.02, 0.28, 0.0])
        lm[LANDMARK[f"{side}_wrist"]] = sh + np.array([0.05, 0.55, 0.0])
    head = up + np.array([0.04, -0.25, 0.0])
    for name in ("nose", "left_eye", "right_eye", "left_ear", "right_ear", "mouth_left", "mouth_right"):
        lm[LANDMARK[name]] = head
    return {str(i): v.tolist() for i, v in lm.items()}


def _frame(i, fps, lm, vis=True):
    return {
        "frame_number": i,
        "timestamp_ms": int(round(i * 1000 / fps)),
        "world_landmarks": lm,
        "visibility": [0.99] * 33 if vis else None,
    }


def squat_frames(n_reps=5, fps=30, rep_s=2.0, depth=100.0, depth_r=None, lean_top=5.0, lean_bottom=35.0,
                 lead_s=0.6, tail_s=0.6, noise_m=0.0, seed=0, vis=True, depth_drift=0.0):
    """Squats: standing -> n_reps cosine reps to `depth` deg knee flexion -> standing.
    depth_r: right-knee depth (asymmetry). depth_drift: fractional depth change over the set
    (e.g. -0.3 = last rep 30% shallower than the first)."""
    rng = np.random.default_rng(seed)
    depth_r = depth if depth_r is None else depth_r
    n_lead, n_tail = int(lead_s * fps), int(tail_s * fps)
    n_rep = int(rep_s * fps)
    frames = []
    total = n_lead + n_reps * n_rep + n_tail
    for i in range(total):
        j = i - n_lead
        if 0 <= j < n_reps * n_rep:
            rep_idx, t = divmod(j, n_rep)
            s = (1 - math.cos(2 * math.pi * t / n_rep)) / 2
            scale = 1 + depth_drift * (rep_idx / max(n_reps - 1, 1))
        else:
            s, scale = 0.0, 1.0
        kl, kr = depth * s * scale, depth_r * s * scale
        lean = lean_top + (lean_bottom - lean_top) * s
        lm = make_pose(kl, kr, lean)
        if noise_m:
            lm = {k: (np.array(v) + rng.normal(0, noise_m, 3)).tolist() for k, v in lm.items()}
        frames.append(_frame(i, fps, lm, vis))
    return frames


def run_frames(cadence_spm=170.0, seconds=6.0, fps=30, asym=0.0, kmax=80.0, swing_deg=35.0, noise_m=0.0, seed=0):
    """Running: legs swing in antiphase. Each ankle crossing is one step, so the step rate equals
    `cadence_spm`. asym>0 stretches alternate half-cycles (step-time asymmetry)."""
    rng = np.random.default_rng(seed)
    omega = 2 * math.pi * (cadence_spm / 60.0) / 2  # stride (full leg cycle) angular frequency
    dt = 1.0 / fps
    theta, frames = 0.0, []
    for i in range(int(seconds * fps)):
        s = math.sin(theta)
        thigh_l, thigh_r = swing_deg * s, -swing_deg * s
        kl = kmax * (0.5 + 0.5 * math.cos(theta + math.pi / 2))
        kr = kmax * (0.5 + 0.5 * math.cos(theta - math.pi / 2))
        lm = make_pose(kl, kr, 8.0, thigh_l, thigh_r)
        if noise_m:
            lm = {k: (np.array(v) + rng.normal(0, noise_m, 3)).tolist() for k, v in lm.items()}
        frames.append(_frame(i, fps, lm))
        theta += omega * dt * ((1 + asym) if s > 0 else (1 - asym))
    return frames


# ------------------------------- problem injectors -------------------------------------

LEG_LANDMARKS = {
    "left": ("left_knee", "left_ankle", "left_heel", "left_foot_index"),
    "right": ("right_knee", "right_ankle", "right_heel", "right_foot_index"),
}


def occlude_leg(frames, side, frac=1.0, vis=0.08, seed=1):
    """Hide a leg in the first `frac` of frames: visibility drops AND coordinates become garbage,
    exactly what a pose model does for a limb it cannot see."""
    rng = np.random.default_rng(seed)
    out = []
    cut = int(len(frames) * frac)
    for n, fr in enumerate(frames):
        fr = {**fr, "world_landmarks": dict(fr["world_landmarks"]), "visibility": list(fr["visibility"])}
        if n < cut:
            for name in LEG_LANDMARKS[side]:
                idx = LANDMARK[name]
                fr["world_landmarks"][str(idx)] = rng.uniform(-0.8, 0.8, 3).tolist()
                fr["visibility"][idx] = vis
        out.append(fr)
    return out


def spike(frames, frame_idx, landmark="left_knee", metres=0.6):
    fr = frames[frame_idx]
    lm = dict(fr["world_landmarks"])
    idx = str(LANDMARK[landmark])
    lm[idx] = (np.array(lm[idx]) + np.array([metres, 0, 0])).tolist()
    frames[frame_idx] = {**fr, "world_landmarks": lm}
    return frames


def drop_frames(frames, every=None, ranges=()):
    keep = []
    for n, fr in enumerate(frames):
        if every and n % every == 0 and n:
            continue
        if any(a <= n < b for a, b in ranges):
            continue
        keep.append(fr)
    return keep


def roll_camera(frames, deg):
    """Rotate every pose about the depth axis, as if the phone were rolled by `deg`."""
    r = math.radians(deg)
    R = np.array([[math.cos(r), -math.sin(r), 0], [math.sin(r), math.cos(r), 0], [0, 0, 1]])
    return [{**fr, "world_landmarks": {k: (R @ np.array(v)).tolist() for k, v in fr["world_landmarks"].items()}}
            for fr in frames]


def strip_visibility(frames):
    return [{**fr, "visibility": None} for fr in frames]
