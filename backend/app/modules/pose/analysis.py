"""Landmark cleaning and video quality assessment (pure numpy/pandas — no model, no DB).

The pose model returns a coordinate for EVERY landmark in EVERY frame, including limbs it
cannot see (out of frame, hidden behind the other leg, in shadow). Those coordinates are
plausible-looking guesses. Before this module existed they flowed straight into
"validated" angle metrics. The rules here:

1. Raw landmarks are stored untouched (reproducible); cleaning happens at analysis time.
2. A landmark whose visibility is below VIS_THRESHOLD in a frame is treated as MISSING in
   that frame — never as a measurement.
3. Short gaps (<= MAX_GAP_S) are linearly interpolated so one dropped frame doesn't break
   a repetition; long gaps stay missing. Metrics are only emitted for frames the model
   actually observed, never for interpolated ones.
4. Single-frame landmark glitches are removed with a Hampel filter, then a frequency-aware
   Gaussian smooths residual jitter. The cutoff is set per movement type: a slow squat
   tolerates heavy smoothing, a sprint does not.
5. A quality report states what was usable and why the result may be unreliable (lighting,
   occlusion, noise, camera tilt, wrong camera view). Grade thresholds below are
   engineering heuristics, NOT validated cut-offs — they exist so a poor recording
   degrades visibly rather than silently.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.modules.biomechanics.calculations import LANDMARK
from app.modules.biomechanics.movement_analysis import MEASUREMENT_NOISE_DEG

N_LANDMARKS = 33
VIS_THRESHOLD = 0.5
MAX_GAP_S = 0.3
HAMPEL_HALF_WINDOW_S = 0.1
HAMPEL_NSIGMA = 3.0
HAMPEL_FLOOR_M = 0.01  # 1 cm: below this a "spike" is indistinguishable from landmark noise

# Low-pass cutoff (Hz) per movement. sigma_frames = 0.1325 * fps / cutoff (Gaussian -3 dB point).
SMOOTHING_CUTOFF_HZ = {
    "squatting": 4.0, "landing": 8.0, "jumping": 8.0, "throwing": 10.0,
    "running": 10.0, "sprinting": 12.0, "cutting": 10.0,
}
DEFAULT_CUTOFF_HZ = 6.0
MIN_SIGMA_FRAMES = 0.35  # below this the kernel collapses to a no-op

GROUPS = {
    "left_leg": ("left_hip", "left_knee", "left_ankle"),
    "right_leg": ("right_hip", "right_knee", "right_ankle"),
    "trunk": ("left_shoulder", "right_shoulder", "left_hip", "right_hip"),
}

# Grade heuristics (documented as heuristics — see module docstring).
USABLE_POOR, USABLE_FAIR = 50.0, 80.0
JITTER_FAIR_DEG = 3.5
JITTER_POOR_DEG = MEASUREMENT_NOISE_DEG
INTERPOLATED_FAIR_PCT = 15.0
MIN_CLIP_SECONDS = 1.5
LOW_FPS = 15.0
CAMERA_TILT_WARN_DEG = 10.0
STANDING_KNEE_DEG = 15.0


@dataclass
class Track:
    grid: np.ndarray          # frame numbers on a uniform grid [G]
    step: int                 # frame step between grid points
    fps_eff: float            # effective sampling rate (Hz)
    observed: np.ndarray      # [G] bool: pose model returned landmarks for this frame
    t_ms: np.ndarray          # [G] timestamp (ms), NaN where unobserved
    xyz: np.ndarray           # [G,33,3] raw world landmarks, NaN where unobserved
    vis: np.ndarray           # [G,33] visibility, NaN where unobserved/unknown
    has_visibility: bool


# --------------------------------------------------------------------------- #
# Building the track
# --------------------------------------------------------------------------- #

def build_track(frame_results: list[dict], fps: float | None) -> Track | None:
    """Dense uniform-grid representation of the detected frames."""
    by_frame: dict[int, dict] = {}
    for fr in frame_results:
        lm = fr.get("world_landmarks")
        if lm:
            by_frame[int(fr["frame_number"])] = fr
    if not by_frame:
        return None
    frames = np.array(sorted(by_frame))
    diffs = np.diff(frames)
    step = int(np.gcd.reduce(diffs)) if len(diffs) else 1
    step = max(step, 1)
    grid = np.arange(frames[0], frames[-1] + 1, step)
    G = len(grid)
    idx = {f: i for i, f in enumerate(grid)}

    xyz = np.full((G, N_LANDMARKS, 3), np.nan)
    vis = np.full((G, N_LANDMARKS), np.nan)
    t_ms = np.full(G, np.nan)
    observed = np.zeros(G, dtype=bool)
    has_vis = False
    for f, fr in by_frame.items():
        i = idx[f]
        observed[i] = True
        t_ms[i] = fr.get("timestamp_ms", np.nan)
        for k, v in fr["world_landmarks"].items():
            j = int(k)
            if 0 <= j < N_LANDMARKS:
                xyz[i, j] = v[:3]
        v = fr.get("visibility")
        if v is not None and len(v) >= N_LANDMARKS:
            vis[i] = v[:N_LANDMARKS]
            has_vis = True

    xyz[~np.isfinite(xyz)] = np.nan  # NaN/inf coordinates are missing measurements, never values
    fps_eff = _effective_fps(t_ms, grid, step, fps)
    return Track(grid, step, fps_eff, observed, t_ms, xyz, vis, has_vis)


def _effective_fps(t_ms: np.ndarray, grid: np.ndarray, step: int, fps: float | None) -> float:
    if fps and fps > 0:
        return float(fps) / step
    ok = np.flatnonzero(~np.isnan(t_ms))
    if len(ok) > 1:
        dt = np.diff(t_ms[ok]) / np.diff(ok)  # ms per grid step
        dt = dt[dt > 0]
        if len(dt):
            return float(1000.0 / np.median(dt))
    return 30.0 / step


# --------------------------------------------------------------------------- #
# Cleaning
# --------------------------------------------------------------------------- #

def _fill_short_gaps(a: np.ndarray, max_gap: int) -> np.ndarray:
    """Linearly interpolate NaN runs of length <= max_gap that have valid neighbours."""
    out = a.copy()
    nan = np.isnan(out)
    if not nan.any() or nan.all():
        return out
    idx = np.flatnonzero(~nan)
    i = 0
    n = len(out)
    while i < n:
        if nan[i]:
            j = i
            while j < n and nan[j]:
                j += 1
            if i > 0 and j < n and (j - i) <= max_gap:
                out[i:j] = np.interp(np.arange(i, j), [i - 1, j], [out[i - 1], out[j]])
            i = j
        else:
            i += 1
    return out


def _hampel(df: pd.DataFrame, half_window: int) -> pd.DataFrame:
    win = 2 * half_window + 1
    med = df.rolling(win, center=True, min_periods=1).median()
    mad = (df - med).abs().rolling(win, center=True, min_periods=1).median() * 1.4826
    thresh = HAMPEL_NSIGMA * mad.clip(lower=HAMPEL_FLOOR_M)
    spike = (df - med).abs() > thresh
    return df.where(~spike, med)


def _gaussian_nan(x: np.ndarray, sigma: float) -> np.ndarray:
    """Gaussian smoothing along axis 0 that ignores NaN (normalised convolution)."""
    radius = int(np.ceil(3 * sigma))
    k = np.exp(-0.5 * (np.arange(-radius, radius + 1) / sigma) ** 2)
    valid = (~np.isnan(x)).astype(float)
    filled = np.nan_to_num(x)
    out = np.empty_like(x)
    for c in range(x.shape[1]):
        # mode="full" + slice: mode="same" returns max(len(x), len(k)) samples, which breaks for a clip
        # shorter than the kernel (found by property-based fuzzing: a 1-frame clip crashed analysis)
        num = np.convolve(filled[:, c], k, mode="full")[radius:radius + len(x)]
        den = np.convolve(valid[:, c], k, mode="full")[radius:radius + len(x)]
        with np.errstate(invalid="ignore", divide="ignore"):
            out[:, c] = np.where(den > 1e-9, num / den, np.nan)
    out[np.isnan(x)] = np.nan
    return out


def clean_track(track: Track, movement_type: str | None = None, despike: bool = True) -> np.ndarray:
    """Cleaned [G,33,3] landmarks (NaN = unusable). See module docstring for the rules.

    `despike=False` skips the Hampel pass. That pass clips the extremes of fast cyclic motion (a 0.5 m ankle swing
    at 170 steps/min loses ~6 cm), so a metric read off a PEAK (stride length) takes its amplitude from a track
    cleaned without it; the NaN pattern is identical either way. See docs/DECISIONS.md 2026-10-09.
    """
    G = len(track.grid)
    xyz = track.xyz.copy()
    if track.has_visibility:
        low = np.nan_to_num(track.vis, nan=1.0) < VIS_THRESHOLD  # unknown visibility -> trusted
        xyz[low] = np.nan

    flat = xyz.reshape(G, -1)
    max_gap = max(1, int(round(MAX_GAP_S * track.fps_eff)))
    for c in range(flat.shape[1]):
        flat[:, c] = _fill_short_gaps(flat[:, c], max_gap)

    half = max(1, int(round(HAMPEL_HALF_WINDOW_S * track.fps_eff)))
    if despike and G >= 2 * half + 1:
        flat = _hampel(pd.DataFrame(flat), half).to_numpy()

    cutoff = SMOOTHING_CUTOFF_HZ.get(movement_type or "", DEFAULT_CUTOFF_HZ)
    sigma = 0.1325 * track.fps_eff / cutoff
    if sigma >= MIN_SIGMA_FRAMES:
        flat = _gaussian_nan(flat, sigma)
    return flat.reshape(G, N_LANDMARKS, 3)


def frames_for_metrics(track: Track, cleaned: np.ndarray) -> list[dict]:
    """Per-frame landmark dicts for OBSERVED frames only (NaN where a landmark is unusable).

    Interpolated frames are deliberately excluded: metrics must come from frames the model
    actually saw.
    """
    out = []
    for i in np.flatnonzero(track.observed):
        out.append({
            "frame_number": int(track.grid[i]),
            "timestamp_ms": int(track.t_ms[i]) if not np.isnan(track.t_ms[i]) else 0,
            "world_landmarks": {str(j): cleaned[i, j].tolist() for j in range(N_LANDMARKS)},
        })
    return out


# --------------------------------------------------------------------------- #
# Quality assessment
# --------------------------------------------------------------------------- #

def _angle_series(xyz: np.ndarray, a: int, b: int, c: int) -> np.ndarray:
    v1, v2 = xyz[:, a] - xyz[:, b], xyz[:, c] - xyz[:, b]
    denom = np.linalg.norm(v1, axis=1) * np.linalg.norm(v2, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        cos = np.clip(np.einsum("ij,ij->i", v1, v2) / denom, -1, 1)
    return np.degrees(np.arccos(cos))


def jitter_deg(angle: np.ndarray) -> float | None:
    """Frame-to-frame tracking noise of an angle series (deg), robust to real motion.

    Robust sigma of the second difference: 1.4826 * MAD(d2) / sqrt(6). The MAD ignores the
    few large second differences that genuine fast movement produces. NaN marks frames where
    the limb was not visible: only runs of three CONSECUTIVE valid frames contribute, so a
    hidden limb's hallucinated coordinates are never mistaken for tracking noise.
    """
    d2 = np.diff(np.asarray(angle, dtype=float), n=2)
    d2 = d2[np.isfinite(d2)]
    if len(d2) < 10:
        return None
    mad = np.median(np.abs(d2 - np.median(d2)))
    return float(1.4826 * mad / np.sqrt(6))


def camera_tilt_deg(xyz: np.ndarray) -> float | None:
    """Deviation of 'standing upright' from the camera-frame vertical, in degrees.

    World landmarks use the camera's axes (+Y down), so a pitched or rolled camera tilts
    every trunk-lean measurement by the same offset. In frames where both knees are nearly
    straight the shoulders should sit directly above the ankles, so their mean direction
    estimates that offset. Needs >= 10 such frames; returns None otherwise (running,
    sprinting and cutting rarely have them).
    """
    lk = 180 - _angle_series(xyz, LANDMARK["left_hip"], LANDMARK["left_knee"], LANDMARK["left_ankle"])
    rk = 180 - _angle_series(xyz, LANDMARK["right_hip"], LANDMARK["right_knee"], LANDMARK["right_ankle"])
    standing = (lk < STANDING_KNEE_DEG) & (rk < STANDING_KNEE_DEG)
    if standing.sum() < 10:
        return None
    sh = (xyz[:, LANDMARK["left_shoulder"]] + xyz[:, LANDMARK["right_shoulder"]]) / 2
    an = (xyz[:, LANDMARK["left_ankle"]] + xyz[:, LANDMARK["right_ankle"]]) / 2
    v = (sh - an)[standing]
    v = v[np.isfinite(v).all(axis=1)]
    if len(v) < 10:
        return None
    m = v.mean(axis=0)
    n = np.linalg.norm(m)
    if n < 1e-6:
        return None
    cos = np.clip(np.dot(m / n, np.array([0.0, -1.0, 0.0])), -1, 1)
    return float(np.degrees(np.arccos(cos)))


def assess_lighting(luma_samples: list[tuple[float, float]]) -> dict:
    """From (mean, p95-p5 range) luma samples of sampled frames (0-255 scale)."""
    if not luma_samples:
        return {"mean_luma": None, "luma_range": None, "low_light": False}
    mean = float(np.mean([m for m, _ in luma_samples]))
    rng = float(np.mean([r for _, r in luma_samples]))
    return {
        "mean_luma": round(mean, 1),
        "luma_range": round(rng, 1),
        "low_light": bool(mean < LOW_LIGHT_MEAN or rng < LOW_CONTRAST_RANGE),
    }


LOW_LIGHT_MEAN = 70.0
LOW_CONTRAST_RANGE = 70.0


def _warn(code: str, message: str) -> dict:
    return {"code": code, "message": message}


def quality_report(
    track: Track,
    cleaned: np.ndarray,
    *,
    movement_type: str,
    camera_view: str,
    n_total_frames: int | None,
    lighting: dict | None = None,
    clahe_applied: bool = False,
    has_validated_metrics: bool = True,
) -> dict:
    """Plain-language account of how trustworthy this video's numbers are."""
    warnings: list[dict] = []
    obs = track.observed
    n_obs = int(obs.sum())

    frames = {
        "detected": n_obs,
        "total": int(n_total_frames) if n_total_frames else None,
        "interpolated_pct": round(100 * float((~obs).sum()) / max(len(obs), 1), 1),
        "effective_fps": round(track.fps_eff, 1),
        "duration_s": round(n_obs / track.fps_eff, 1) if track.fps_eff else None,
    }
    if n_obs:
        gaps = _longest_gap(obs)
        frames["longest_gap_s"] = round(gaps / track.fps_eff, 2)

    # Per-group usability: share of detected frames where EVERY landmark of the group survived.
    usable, visibility = {}, {}
    for g, names in GROUPS.items():
        cols = [LANDMARK[n] for n in names]
        ok = np.isfinite(cleaned[obs][:, cols, :]).all(axis=(1, 2)) if n_obs else np.array([])
        usable[g] = round(100 * float(ok.mean()), 1) if len(ok) else 0.0
        if track.has_visibility and n_obs:
            visibility[g] = round(float(np.nanmean(track.vis[obs][:, cols])), 2)

    # jitter of the RAW signal, but only where that limb survived cleaning (i.e. was visible)
    raw_obs = track.xyz[obs].copy()
    raw_obs[~np.isfinite(cleaned[obs])] = np.nan
    jit = [j for j in (
        jitter_deg(_angle_series(raw_obs, LANDMARK[f"{s}_hip"], LANDMARK[f"{s}_knee"], LANDMARK[f"{s}_ankle"]))
        for s in ("left", "right")
    ) if j is not None]
    jitter = round(float(np.mean(jit)), 1) if jit else None
    tilt = camera_tilt_deg(cleaned)

    # --- warnings -----------------------------------------------------------
    for side in ("left", "right"):
        if usable[f"{side}_leg"] < USABLE_FAIR:
            warnings.append(_warn(
                f"{side}_leg_poorly_visible",
                f"The {side} leg was fully visible in only {usable[f'{side}_leg']:.0f}% of frames "
                "(hidden behind the other leg, out of frame, or in shadow). Metrics from that leg "
                "are dropped where it was not visible, and left/right symmetry is unreliable.",
            ))
    if usable["trunk"] < USABLE_FAIR:
        warnings.append(_warn("trunk_poorly_visible",
                              f"Shoulders and hips were all visible in only {usable['trunk']:.0f}% of frames."))
    if not track.has_visibility:
        warnings.append(_warn(
            "visibility_unavailable",
            "This video was processed before visibility was recorded, so occluded landmarks could "
            "not be excluded. Re-run pose extraction for full occlusion handling.",
        ))
    if lighting and lighting.get("low_light"):
        msg = "Low light / low contrast detected"
        msg += "; contrast enhancement was applied but pose accuracy is still reduced." if clahe_applied else "."
        warnings.append(_warn("low_light", msg))
    if jitter is not None and jitter >= JITTER_FAIR_DEG:
        warnings.append(_warn(
            "noisy_tracking",
            f"Frame-to-frame joint-angle jitter is about {jitter:.1f} deg (typical pose-model noise "
            f"is ~{MEASUREMENT_NOISE_DEG} deg RMSE). Motion blur, loose clothing or poor lighting are common causes.",
        ))
    if tilt is not None and tilt > CAMERA_TILT_WARN_DEG:
        warnings.append(_warn(
            "camera_tilt_suspected",
            f"The athlete's upright posture reads {tilt:.0f} deg off vertical, which suggests the "
            "camera was tilted. Trunk-lean values carry this offset. Film with the phone level.",
        ))
    if frames["interpolated_pct"] > INTERPOLATED_FAIR_PCT:
        warnings.append(_warn("many_dropped_frames",
                              f"{frames['interpolated_pct']:.0f}% of frames had no pose detection."))
    if frames["duration_s"] is not None and frames["duration_s"] < MIN_CLIP_SECONDS:
        warnings.append(_warn("short_clip", f"Only {frames['duration_s']}s of pose data — too short for reliable rep analysis."))
    if track.fps_eff < LOW_FPS:
        warnings.append(_warn("low_frame_rate",
                              f"Effective frame rate is {track.fps_eff:.0f} fps; fast movements are under-sampled."))
    if not has_validated_metrics:
        warnings.append(_warn(
            "no_validated_metrics",
            f"The '{camera_view}' camera view produced no validated joint-angle metrics for "
            f"'{movement_type}'. Validated sagittal angles need a side-on (sagittal) camera; "
            "a frontal view gives only qualitative knee-valgus flags.",
        ))

    # --- grade --------------------------------------------------------------
    poor = (
        usable["trunk"] < USABLE_POOR
        or min(usable["left_leg"], usable["right_leg"]) < USABLE_POOR and max(usable["left_leg"], usable["right_leg"]) < USABLE_FAIR
        or (jitter is not None and jitter >= JITTER_POOR_DEG)
        or not has_validated_metrics
    )
    fair = bool(warnings)
    grade = "poor" if poor else "fair" if fair else "good"

    return {
        "grade": grade,
        "frames": frames,
        "usable_pct": usable,
        "mean_visibility": visibility or None,
        "jitter_deg": jitter,
        "camera_tilt_deg": round(tilt, 1) if tilt is not None else None,
        "lighting": lighting,
        "contrast_enhanced": clahe_applied,
        "warnings": warnings,
    }


def _longest_gap(observed: np.ndarray) -> int:
    longest = cur = 0
    for o in observed:
        cur = 0 if o else cur + 1
        longest = max(longest, cur)
    return longest
