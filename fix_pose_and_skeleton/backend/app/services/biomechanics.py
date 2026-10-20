"""Biomechanical analysis from 2D pose keypoints.

Input is an array P of shape (T, J, 2): normalised image coordinates with the
y axis pointing DOWN, joints ordered as in pose_estimation.JOINT_NAMES.

IMPORTANT: angles are 2D projections. Frontal-plane measures (knee valgus,
pelvic drop) need a front/back camera view; sagittal-plane measures (knee
flexion, trunk lean) need a side view. They are screening indicators for
decision support, not clinical measurements.
"""

import math

import numpy as np

from app.services.pose_estimation import JOINT_INDEX

# ---------------------------------------------------------------------------
# Small numeric helpers
# ---------------------------------------------------------------------------


def _f(x) -> float | None:
    """float() that maps NaN/inf to None so results stay JSON-safe."""
    if x is None:
        return None
    x = float(x)
    return None if (math.isnan(x) or math.isinf(x)) else round(x, 3)


def joint(P: np.ndarray, name: str) -> np.ndarray:
    return P[:, JOINT_INDEX[name], :]


def angle_between(a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Angle ABC (degrees) at vertex b. Inputs have shape (..., 2)."""
    ba, bc = a - b, c - b
    denom = np.linalg.norm(ba, axis=-1) * np.linalg.norm(bc, axis=-1) + 1e-9
    cos = np.sum(ba * bc, axis=-1) / denom
    return np.degrees(np.arccos(np.clip(cos, -1.0, 1.0)))


def interpolate_nans(P: np.ndarray) -> np.ndarray:
    """Linearly fill missing keypoints over time."""
    P = P.copy()
    t = np.arange(P.shape[0])
    for j in range(P.shape[1]):
        for k in range(P.shape[2]):
            col = P[:, j, k]
            mask = np.isnan(col)
            if mask.all() or not mask.any():
                continue
            col[mask] = np.interp(t[mask], t[~mask], col[~mask])
            P[:, j, k] = col
    return P


def smooth(P: np.ndarray, window: int = 5) -> np.ndarray:
    """Moving-average smoothing along time (window forced odd)."""
    window |= 1
    if window <= 1 or P.shape[0] < window:
        return P
    pad = window // 2
    kernel = np.ones(window) / window
    padded = np.pad(P, ((pad, pad), (0, 0), (0, 0)), mode="edge")
    out = np.empty_like(P)
    for j in range(P.shape[1]):
        for k in range(P.shape[2]):
            out[:, j, k] = np.convolve(padded[:, j, k], kernel, mode="valid")
    return out


def symmetry_index(left: float, right: float) -> float:
    """Robinson symmetry index in percent (0 = perfectly symmetric)."""
    denom = 0.5 * (abs(left) + abs(right))
    if denom < 1e-6:
        return 0.0
    return abs(left - right) / denom * 100.0


def find_peaks(x: np.ndarray, min_distance: int = 3, min_prominence: float = 0.0) -> list[int]:
    """Minimal local-maximum finder (avoids a SciPy dependency)."""
    floor = float(np.min(x))
    peaks: list[int] = []
    for i in range(1, len(x) - 1):
        if x[i] > x[i - 1] and x[i] >= x[i + 1] and (x[i] - floor) >= min_prominence:
            if peaks and i - peaks[-1] < min_distance:
                if x[i] > x[peaks[-1]]:
                    peaks[-1] = i
                continue
            peaks.append(i)
    return peaks


def detect_repetitions(series: np.ndarray, fps: float) -> list[int]:
    """Indices of repetition peaks (e.g. deepest knee flexion per squat or stride)."""
    rng = float(np.max(series) - np.min(series))
    if rng < 10:  # almost no movement
        return []
    return find_peaks(series, min_distance=max(3, int(0.3 * fps)), min_prominence=0.4 * rng)


# ---------------------------------------------------------------------------
# Per-frame joint measures
# ---------------------------------------------------------------------------


def knee_flexion(P: np.ndarray, side: str) -> np.ndarray:
    return 180.0 - angle_between(joint(P, f"{side}_hip"), joint(P, f"{side}_knee"), joint(P, f"{side}_ankle"))


def hip_flexion(P: np.ndarray, side: str) -> np.ndarray:
    return 180.0 - angle_between(joint(P, f"{side}_shoulder"), joint(P, f"{side}_hip"), joint(P, f"{side}_knee"))


def elbow_flexion(P: np.ndarray, side: str) -> np.ndarray:
    return 180.0 - angle_between(joint(P, f"{side}_shoulder"), joint(P, f"{side}_elbow"), joint(P, f"{side}_wrist"))


def ankle_angle(P: np.ndarray, side: str) -> np.ndarray:
    return angle_between(joint(P, f"{side}_knee"), joint(P, f"{side}_ankle"), joint(P, f"{side}_foot"))


def shoulder_elevation(P: np.ndarray, side: str) -> np.ndarray:
    return angle_between(joint(P, f"{side}_hip"), joint(P, f"{side}_shoulder"), joint(P, f"{side}_elbow"))


def knee_valgus_angle(P: np.ndarray, side: str) -> np.ndarray:
    """Frontal-plane projection angle of the knee, signed.

    Positive = knee collapsing toward the body midline (valgus),
    negative = knee bowing outward (varus).
    """
    hip, knee, ankle = (joint(P, f"{side}_{n}") for n in ("hip", "knee", "ankle"))
    fppa = 180.0 - angle_between(hip, knee, ankle)  # deviation from a straight leg
    midline_x = 0.5 * (joint(P, "left_hip")[:, 0] + joint(P, "right_hip")[:, 0])
    # x position of the hip->ankle line at the knee's height
    t = (knee[:, 1] - hip[:, 1]) / np.where(np.abs(ankle[:, 1] - hip[:, 1]) < 1e-9, 1e-9, ankle[:, 1] - hip[:, 1])
    line_x = hip[:, 0] + t * (ankle[:, 0] - hip[:, 0])
    toward_midline = np.sign(midline_x - hip[:, 0])
    medial_offset = (knee[:, 0] - line_x) * toward_midline
    return np.where(medial_offset >= 0, fppa, -fppa)


def trunk_lean(P: np.ndarray) -> np.ndarray:
    """Signed trunk angle from vertical (degrees)."""
    hip_mid = 0.5 * (joint(P, "left_hip") + joint(P, "right_hip"))
    sh_mid = 0.5 * (joint(P, "left_shoulder") + joint(P, "right_shoulder"))
    d = sh_mid - hip_mid
    return np.degrees(np.arctan2(d[:, 0], -d[:, 1]))


def pelvic_tilt(P: np.ndarray) -> np.ndarray:
    """Pelvic line angle from horizontal, wrapped to [-90, 90)."""
    lh, rh = joint(P, "left_hip"), joint(P, "right_hip")
    a = np.degrees(np.arctan2(rh[:, 1] - lh[:, 1], rh[:, 0] - lh[:, 0]))
    return ((a + 90.0) % 180.0) - 90.0


def body_height(P: np.ndarray) -> float:
    """Median nose-to-ankle vertical extent in normalised units."""
    ankle_y = 0.5 * (joint(P, "left_ankle")[:, 1] + joint(P, "right_ankle")[:, 1])
    h = np.abs(ankle_y - joint(P, "nose")[:, 1])
    return float(np.median(h)) if len(h) else 1.0


def centre_of_mass(P: np.ndarray) -> np.ndarray:
    """Approximate CoM: mean of the hip and shoulder midpoints (trunk-weighted)."""
    hip_mid = 0.5 * (joint(P, "left_hip") + joint(P, "right_hip"))
    sh_mid = 0.5 * (joint(P, "left_shoulder") + joint(P, "right_shoulder"))
    return 0.6 * hip_mid + 0.4 * sh_mid


# ---------------------------------------------------------------------------
# Higher-level analyses
# ---------------------------------------------------------------------------


def landing_analysis(P: np.ndarray, fps: float, knee_flex: np.ndarray, valgus: np.ndarray, lean: np.ndarray, bh: float) -> dict | None:
    """Detect the dominant landing and describe its mechanics."""
    ankle_y = 0.5 * (joint(P, "left_ankle")[:, 1] + joint(P, "right_ankle")[:, 1])
    if (np.max(ankle_y) - np.min(ankle_y)) / max(bh, 1e-6) < 0.08:
        return None  # no vertical foot excursion -> no jump/landing
    vy = np.gradient(ankle_y) * fps  # positive = foot moving down
    fastest = int(np.argmax(vy))
    if vy[fastest] <= 0:
        return None
    after = np.where(vy[fastest:] < 0.2 * vy[fastest])[0]
    contact = fastest + (int(after[0]) if len(after) else 0)
    contact = min(contact, len(vy) - 1)
    end = min(len(vy), contact + max(3, int(0.3 * fps)))
    win = slice(contact, end)

    kf = 0.5 * (knee_flex[:, 0] + knee_flex[:, 1])
    return {
        "contact_frame": contact,
        "knee_flexion_at_contact_deg": _f(kf[contact]),
        "peak_knee_flexion_deg": _f(np.max(kf[win])),
        "peak_valgus_deg": _f(np.max(valgus[win])),
        "trunk_lean_at_contact_deg": _f(abs(lean[contact])),
        "stiff_landing": bool(kf[contact] < 25),
    }


def estimate_vertical_grf(com_y: np.ndarray, fps: float, bh: float, height_cm: float, weight_kg: float) -> dict | None:
    """Approximate vertical ground reaction force from CoM acceleration.

    GRF = m (g + a). Scale: nose-to-ankle span is ~87% of standing height. This is
    sensitive to camera angle and noise; treat it as a relative indicator only.
    """
    if len(com_y) < 7 or bh <= 1e-6:
        return None
    metres_per_unit = (height_cm / 100.0 * 0.87) / bh
    z = -com_y * metres_per_unit  # up is positive
    kernel = np.ones(5) / 5
    z = np.convolve(np.pad(z, 2, mode="edge"), kernel, mode="valid")
    acc = np.gradient(np.gradient(z)) * fps**2
    g = 9.81
    grf_bw = np.clip(1.0 + acc / g, 0.0, 6.0)
    return {
        "peak_grf_bw": _f(np.max(grf_bw)),
        "mean_grf_bw": _f(np.mean(grf_bw)),
        "peak_grf_n": _f(np.max(grf_bw) * weight_kg * g),
        "note": "Approximate; derived from 2D centre-of-mass motion.",
    }


def _stats(series: np.ndarray) -> dict:
    return {
        "mean": _f(np.nanmean(series)),
        "min": _f(np.nanmin(series)),
        "max": _f(np.nanmax(series)),
        "rom": _f(np.nanmax(series) - np.nanmin(series)),
    }


def downsample(series: np.ndarray, n: int = 100) -> list[float | None]:
    if len(series) <= n:
        return [_f(v) for v in series]
    idx = np.linspace(0, len(series) - 1, n).astype(int)
    return [_f(series[i]) for i in idx]


def analyze_biomechanics(
    P_raw: np.ndarray,
    fps: float,
    activity: str = "squatting",
    height_cm: float | None = None,
    weight_kg: float | None = None,
) -> dict:
    """Full biomechanical assessment for one video. Returns a JSON-safe dict."""
    if P_raw.shape[0] < 5:
        raise ValueError("Too few frames for biomechanical analysis.")
    P = smooth(interpolate_nans(P_raw))
    if np.isnan(P).any():
        from app.services.pose_estimation import JOINT_NAMES  # local import avoids a cycle

        missing = [JOINT_NAMES[j].replace("_", " ") for j in range(P.shape[1]) if np.isnan(P[:, j]).any()]
        raise ValueError(
            "These body points were never clearly visible: " + ", ".join(missing)
            + ". Record the whole body from head to feet in frame, in good light."
        )

    bh = body_height(P)
    sides = ("left", "right")
    angles = {
        "knee_flexion": np.stack([knee_flexion(P, s) for s in sides], axis=1),
        "hip_flexion": np.stack([hip_flexion(P, s) for s in sides], axis=1),
        "elbow_flexion": np.stack([elbow_flexion(P, s) for s in sides], axis=1),
        "ankle_angle": np.stack([ankle_angle(P, s) for s in sides], axis=1),
        "shoulder_elevation": np.stack([shoulder_elevation(P, s) for s in sides], axis=1),
    }
    valgus = np.stack([knee_valgus_angle(P, s) for s in sides], axis=1)
    lean = trunk_lean(P)
    tilt = pelvic_tilt(P)

    joint_angles: dict[str, dict] = {}
    for name, arr in angles.items():
        joint_angles[name] = {"left": _stats(arr[:, 0]), "right": _stats(arr[:, 1])}

    # Range of motion and symmetry (left vs right ROM)
    symmetry: dict[str, float | None] = {}
    for name in ("knee_flexion", "hip_flexion", "ankle_angle", "shoulder_elevation"):
        rom_l = joint_angles[name]["left"]["rom"] or 0.0
        rom_r = joint_angles[name]["right"]["rom"] or 0.0
        symmetry[f"{name}_rom_si"] = _f(symmetry_index(rom_l, rom_r))
    si_values = [v for v in symmetry.values() if v is not None]
    symmetry["mean_si"] = _f(np.mean(si_values)) if si_values else None
    symmetry["max_si"] = _f(np.max(si_values)) if si_values else None

    # Frontal-plane / posture / stability metrics
    com = centre_of_mass(P)
    sway_path = float(np.sum(np.linalg.norm(np.diff(com, axis=0), axis=1))) / max(bh, 1e-6)
    sway_ml = float(np.std(com[:, 0])) / max(bh, 1e-6)
    shoulder_tilt = np.degrees(np.arctan2(
        joint(P, "right_shoulder")[:, 1] - joint(P, "left_shoulder")[:, 1],
        joint(P, "right_shoulder")[:, 0] - joint(P, "left_shoulder")[:, 0],
    ))
    shoulder_tilt = ((shoulder_tilt + 90.0) % 180.0) - 90.0
    sh_mid_x = 0.5 * (joint(P, "left_shoulder")[:, 0] + joint(P, "right_shoulder")[:, 0])
    head_offset = np.abs(joint(P, "nose")[:, 0] - sh_mid_x) / max(bh, 1e-6)

    knee_valgus_peak = float(np.max(valgus))
    pelvic_drop = float(np.max(np.abs(tilt - np.median(tilt))))
    trunk_lean_max = float(np.max(np.abs(lean)))

    # Stride length: peak horizontal ankle separation, normalised by body height
    ankle_sep = np.abs(joint(P, "left_ankle")[:, 0] - joint(P, "right_ankle")[:, 0])
    stride_peaks = find_peaks(ankle_sep, min_distance=max(3, int(0.2 * fps)), min_prominence=0.1 * float(np.ptp(ankle_sep) + 1e-9))
    stride_norm = float(np.mean(ankle_sep[stride_peaks]) / max(bh, 1e-6)) if stride_peaks else None
    stride_cv = (
        float(np.std(ankle_sep[stride_peaks]) / (np.mean(ankle_sep[stride_peaks]) + 1e-9) * 100)
        if len(stride_peaks) >= 3 else None
    )

    # Joint alignment: composite of valgus, trunk lean and pelvic drop (100 = ideal)
    alignment = 100.0 - min(40.0, max(knee_valgus_peak, 0) * 2.5) - min(30.0, trunk_lean_max) - min(30.0, pelvic_drop * 3)
    alignment = max(0.0, alignment)

    # Repetitions (peak knee flexion) for fatigue and consistency analysis
    knee_mean = angles["knee_flexion"].mean(axis=1)
    reps = detect_repetitions(knee_mean, fps)
    rep_metrics = {
        "peak_knee_flexion": [_f(knee_mean[i]) for i in reps],
        "peak_valgus": [_f(valgus[max(i - 2, 0): i + 3].max()) for i in reps],
        "trunk_lean": [_f(abs(lean[i])) for i in reps],
    }

    landing = landing_analysis(P, fps, angles["knee_flexion"], valgus, lean, bh)
    force = None
    if height_cm and weight_kg:
        force = estimate_vertical_grf(com[:, 1], fps, bh, height_cm, weight_kg)

    metrics = {
        "knee_valgus_peak_deg": _f(knee_valgus_peak),
        "knee_valgus_left_peak_deg": _f(np.max(valgus[:, 0])),
        "knee_valgus_right_peak_deg": _f(np.max(valgus[:, 1])),
        "hip_stability_pelvic_drop_deg": _f(pelvic_drop),
        "trunk_lean_mean_deg": _f(np.mean(np.abs(lean))),
        "trunk_lean_max_deg": _f(trunk_lean_max),
        "landing_knee_flexion_deg": landing["knee_flexion_at_contact_deg"] if landing else None,
        "stride_length_norm": _f(stride_norm),
        "stride_variability_pct": _f(stride_cv),
        "joint_alignment_score": _f(alignment),
        "balance_sway_path_norm": _f(sway_path),
        "balance_sway_ml_norm": _f(sway_ml),
        "posture_shoulder_tilt_deg": _f(np.mean(np.abs(shoulder_tilt))),
        "posture_head_offset_norm": _f(np.mean(head_offset)),
    }

    return {
        "activity": activity,
        "fps": _f(fps),
        "frames": int(P.shape[0]),
        "joint_angles": joint_angles,
        "symmetry": symmetry,
        "metrics": metrics,
        "landing": landing,
        "repetitions": {"count": len(reps), **rep_metrics},
        "force_estimate": force,
        "series": {
            "knee_flexion_left": downsample(angles["knee_flexion"][:, 0]),
            "knee_flexion_right": downsample(angles["knee_flexion"][:, 1]),
            "trunk_lean": downsample(lean),
            "knee_valgus_left": downsample(valgus[:, 0]),
            "knee_valgus_right": downsample(valgus[:, 1]),
        },
    }
