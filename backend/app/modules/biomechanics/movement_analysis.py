"""Movement-specific analysis on top of the per-frame joint angles.

Per-frame angles alone treat a squat, a sprint and a throw identically. This module
adds what differs between movements, using only signals that monocular video estimates
reasonably well:

* Repetition segmentation (squat / landing / jump / throw): how many reps, each rep's
  peak, and tempo (descent vs ascent time). TIMING is far more robust to pose-model
  error than absolute angles — a consistent joint-angle bias (SCIENCE_CONSTRAINTS.md)
  shifts every peak equally but does not move when the peak happens.
* Gait timing (running / sprint / cutting): step cadence and left/right step-time
  asymmetry from the moments the feet pass each other.
* Label sanity: a clip labelled "squatting" that contains a periodic stride pattern (or
  the reverse) is flagged, because a mislabelled clip silently poisons the population
  baseline for that movement type.

Everything is pure numpy: no DB, no model, unit-testable against synthetic motion with
known ground truth.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.modules.biomechanics.calculations import LANDMARK

# Sagittal joint-angle RMSE vs. marker-based capture is 5.9-6.8 deg (SCIENCE_CONSTRAINTS.md).
# Anything smaller than ~3x that is not distinguishable from tracking noise.
MEASUREMENT_NOISE_DEG = 6.5
MIN_MEANINGFUL_RANGE_DEG = 3 * MEASUREMENT_NOISE_DEG  # ~20 deg
MIN_FRAMES = 15
MIN_REPS_FOR_DRIFT = 4

REP_MOVEMENTS = {"squatting", "landing", "jumping", "throwing"}
GAIT_MOVEMENTS = {"running", "sprinting", "cutting"}

# Gait: feet-passing signal must swing at least this far (metres) to count as strides,
# and a stride train needs at least this many step events to be called "gait".
MIN_ANKLE_SEPARATION_RANGE_M = 0.15
MIN_STEPS_FOR_GAIT = 4
# A crossing only counts once the signal has moved this fraction of its range past the midline.
GAIT_CONFIRM_BAND = 0.15
# Plausible step rates (steps/min) — outside this the detector is counting noise.
CADENCE_PLAUSIBLE_SPM = (60.0, 330.0)


@dataclass
class Rep:
    start: int
    peak_idx: int
    end: int
    peak: float


# --------------------------------------------------------------------------- #
# Repetition segmentation
# --------------------------------------------------------------------------- #

def _smooth(v: np.ndarray, k: int = 5) -> np.ndarray:
    padded = np.pad(v, (k // 2, k // 2), mode="edge")
    return np.convolve(padded, np.ones(k) / k, mode="valid")


def detect_reps_detailed(values: np.ndarray, min_range: float = MIN_MEANINGFUL_RANGE_DEG) -> list[Rep]:
    """Completed repetitions via hysteresis thresholding.

    A rep starts when the smoothed signal rises above 60% of its 5th-95th percentile
    range and ends when it falls back below 40%. The dead band makes this immune to
    frame-to-frame jitter. Returns [] when the signal's range is below what tracking
    noise alone could produce (no real repeated movement to count).
    """
    v = np.asarray(values, dtype=float)
    if len(v) < MIN_FRAMES or not np.isfinite(v).all():
        return []
    smooth = _smooth(v)
    lo, hi = np.percentile(smooth, [5, 95])
    rng = hi - lo
    if rng < min_range:
        return []
    up, down = lo + 0.6 * rng, lo + 0.4 * rng

    # 1) find each rep's peak with hysteresis (robust to jitter)
    peaks: list[tuple[int, float]] = []
    in_rep, peak, peak_idx = False, -np.inf, 0
    for i, x in enumerate(smooth):
        if not in_rep:
            if x >= up:
                in_rep, peak, peak_idx = True, x, i
        else:
            if x > peak:
                peak, peak_idx = x, i
            if x <= down:
                peaks.append((peak_idx, float(peak)))
                in_rep, peak = False, -np.inf

    # 2) time each rep peak-to-valley: start/end are where the signal returns to the valley
    #    next to the peak. (Timing the span above 40% of range would measure only ~56% of the cycle.)
    near = 0.05 * rng
    reps: list[Rep] = []
    for k, (pi, pv) in enumerate(peaks):
        prev_pi = peaks[k - 1][0] if k else 0
        next_pi = peaks[k + 1][0] if k + 1 < len(peaks) else len(smooth) - 1
        left = smooth[prev_pi:pi + 1]
        right = smooth[pi:next_pi + 1]
        start = prev_pi + int(np.flatnonzero(left <= left.min() + near)[-1])
        end = pi + int(np.flatnonzero(right <= right.min() + near)[0])
        reps.append(Rep(start, pi, end, pv))
    return reps


def detect_reps(values: np.ndarray) -> list[float]:
    """Peak value of each completed repetition (see detect_reps_detailed)."""
    return [r.peak for r in detect_reps_detailed(values)]


def movement_dynamics(rep_peaks: list[float]) -> dict:
    """Consistency and within-session drift from per-rep peaks.

    `drift_pct` is direction-agnostic on purpose: a 2025 meta-analysis (44 studies) found
    no consistent directional effect of fatigue on landing hip/knee flexion — individual
    studies disagree. So we report the size of change, plus its direction for the human.
    """
    n = len(rep_peaks)
    out: dict = {"n_reps": n, "rep_peaks": [round(p, 1) for p in rep_peaks]}
    if n < 2:
        return out
    arr = np.asarray(rep_peaks, dtype=float)
    mean = float(arr.mean())
    if abs(mean) > 1e-6:
        out["cv_pct"] = round(float(100 * arr.std(ddof=1) / abs(mean)), 1)
    if n >= MIN_REPS_FOR_DRIFT:
        k = max(1, n // 3)
        early, late = float(arr[:k].mean()), float(arr[-k:].mean())
        if abs(early) > 1e-6:
            drift = 100 * (late - early) / abs(early)
            out["drift_pct"] = round(drift, 1)
            out["drift_direction"] = "decrease" if drift < -1 else "increase" if drift > 1 else "stable"
    return out


def primary_signal(series: dict[str, np.ndarray], movement_type: str | None = None) -> tuple[str, np.ndarray] | None:
    """The signal repetitions are counted on.

    Mean knee flexion for lower-body movements; trunk rotation for throwing (distance from
    its resting value, since the sign of rotation depends on handedness); otherwise trunk
    lean.
    """
    if movement_type == "throwing" and "trunk_rotation" in series:
        r = series["trunk_rotation"]
        return "trunk_rotation", np.abs(r - np.median(r))
    knees = [series[k] for k in ("knee_flexion_angle_left", "knee_flexion_angle_right") if k in series]
    if knees:
        n = min(len(k) for k in knees)
        return "knee_flexion", np.mean([k[:n] for k in knees], axis=0)
    for name in ("trunk_lean_angle", "trunk_rotation"):
        if name in series:
            return name, series[name]
    return None


def analyze_reps(series: dict[str, np.ndarray], movement_type: str, fps: float) -> dict | None:
    sig = primary_signal(series, movement_type)
    if sig is None:
        return None
    name, values = sig
    reps = detect_reps_detailed(values)
    out = {"signal": name, **movement_dynamics([r.peak for r in reps])}
    if reps and fps > 0:
        dur = [(r.end - r.start) / fps for r in reps]
        down = [(r.peak_idx - r.start) / fps for r in reps]
        up = [(r.end - r.peak_idx) / fps for r in reps]
        # ACTIVE time: valley edge to valley edge (within 5% of the range). A rep's flat bottom/top is
        # excluded, so for continuous reps this runs ~10-14% shorter than the true cycle...
        out["mean_rep_s"] = round(float(np.mean(dur)), 2)
        if len(reps) >= 2:  # ...so the exact CYCLE time (peak-to-peak spacing) is reported alongside it
            out["mean_cycle_s"] = round(float(np.mean(np.diff([r.peak_idx for r in reps])) / fps), 2)
        out["mean_descent_s"] = round(float(np.mean(down)), 2)
        out["mean_ascent_s"] = round(float(np.mean(up)), 2)
    return out


# --------------------------------------------------------------------------- #
# Gait timing
# --------------------------------------------------------------------------- #

def analyze_gait(xyz: np.ndarray, fps: float) -> dict | None:
    """Step cadence and left/right step-time asymmetry from feet-passing events.

    `xyz` is [T, 33, 3] world landmarks (hip-centred, NaN allowed). The signed separation
    of the two ankles along the direction of travel oscillates once per step; each zero
    crossing is one step event. The travel axis is found by PCA of the ankle-separation
    vector in the ground plane (x, z), so it works for a side-on camera AND oblique
    angles without being told which way the athlete runs.

    Returns None when no stride pattern is present. Timing only — no absolute angles.
    """
    if xyz.ndim != 3 or len(xyz) < MIN_FRAMES or fps <= 0:
        return None
    la = xyz[:, LANDMARK["left_ankle"], :]
    ra = xyz[:, LANDMARK["right_ankle"], :]
    sep = (la - ra)[:, [0, 2]]  # ground-plane separation (x, z); y is vertical
    ok = np.isfinite(sep).all(axis=1)
    if ok.sum() < MIN_FRAMES:
        return None
    sep = sep[ok]
    centred = sep - sep.mean(axis=0)
    # principal direction of ankle separation = direction of travel
    _, _, vt = np.linalg.svd(centred, full_matrices=False)
    signal = _smooth(centred @ vt[0])

    lo, hi = np.percentile(signal, [5, 95])
    rng = hi - lo
    if rng < MIN_ANKLE_SEPARATION_RANGE_M:
        return None
    mid = (hi + lo) / 2
    band = GAIT_CONFIRM_BAND * rng
    # A step event is the signal's true MID crossing, located by linear interpolation. The
    # +/- band only CONFIRMS a crossing (rejects jitter). Timestamping the band crossing instead
    # delays rising and falling edges by different amounts for a skewed waveform, which reads as
    # step-time asymmetry in perfectly symmetric gait.
    events: list[float] = []
    state = 1 if signal[0] > mid else -1
    pending: float | None = None
    for i in range(1, len(signal)):
        prev, x = signal[i - 1], signal[i]
        if (prev - mid) * (x - mid) < 0:  # sign change = candidate mid crossing
            pending = (i - 1) + (mid - prev) / (x - prev)
        if state < 0 and x > mid + band:
            state = 1
            if pending is not None:
                events.append(pending)
        elif state > 0 and x < mid - band:
            state = -1
            if pending is not None:
                events.append(pending)
        if (state > 0 and x > mid + band) or (state < 0 and x < mid - band):
            pending = None
    if len(events) < MIN_STEPS_FOR_GAIT:
        return None

    intervals = np.diff(events) / fps  # seconds between consecutive step events
    mean_step = float(intervals.mean())
    if mean_step <= 0:
        return None
    cadence = 60.0 / mean_step
    if not (CADENCE_PLAUSIBLE_SPM[0] <= cadence <= CADENCE_PLAUSIBLE_SPM[1]):
        return None

    out = {
        "n_steps": len(events),
        "cadence_spm": round(cadence, 1),
        "step_time_cv_pct": round(float(100 * intervals.std(ddof=1) / mean_step), 1) if len(intervals) > 1 else None,
    }
    if len(intervals) >= 4:
        a, b = intervals[0::2].mean(), intervals[1::2].mean()
        out["step_time_asymmetry_pct"] = round(float(100 * abs(a - b) / ((a + b) / 2)), 1)
    return out


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def analyze_movement(
    movement_type: str,
    camera_view: str,
    series: dict[str, np.ndarray],
    xyz: np.ndarray | None,
    fps: float,
) -> dict:
    """Movement-appropriate analysis + label-sanity warnings.

    `series`: {metric_name: dense per-frame values} of VALIDATED metrics.
    `xyz`   : cleaned [T,33,3] world landmarks (for gait timing) or None.
    """
    out: dict = {"movement_type": movement_type}
    warnings: list[dict] = []

    reps = analyze_reps(series, movement_type, fps) if series else None
    # Gait timing needs the direction of travel to lie in the image plane. Head-on/tail-on
    # (frontal) running puts travel along depth, which monocular video estimates worst.
    gait = analyze_gait(xyz, fps) if (xyz is not None and camera_view != "frontal") else None

    if movement_type in REP_MOVEMENTS:
        out["reps"] = reps
        if reps is not None and reps["n_reps"] == 0:
            warnings.append({
                "code": "no_repetitions_detected",
                "message": "No completed repetitions were found — the movement range was too small "
                           "or the clip ends mid-repetition. Anomaly scoring uses the whole clip's "
                           "extremes, so check the clip really shows this movement.",
            })
        if gait is not None and gait["n_steps"] >= 6:
            warnings.append({
                "code": "movement_type_mismatch_suspected",
                "message": f"A running-like stride pattern ({gait['n_steps']} steps, "
                           f"{gait['cadence_spm']} steps/min) was detected in a clip labelled "
                           f"'{movement_type}'. A mislabelled clip corrupts that movement's baseline.",
            })
    elif movement_type in GAIT_MOVEMENTS:
        out["gait"] = gait
        out["reps"] = reps
        if camera_view == "frontal":
            warnings.append({
                "code": "gait_timing_needs_side_view",
                "message": "Step timing is not computed from a head-on/tail-on camera; film from the side.",
            })
        elif gait is None:
            warnings.append({
                "code": "no_stride_pattern_detected",
                "message": "No stride pattern was detected — at least ~4 steps with both legs "
                           "visible are needed for cadence and step-symmetry analysis.",
            })
    else:  # sport_specific / unknown: report whatever structure exists, no label to contradict
        out["reps"] = reps
        out["gait"] = gait

    out["warnings"] = warnings
    return out
