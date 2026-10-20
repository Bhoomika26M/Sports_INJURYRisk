"""Movement anomaly detection: deviation from reference norms, inconsistency,
fatigue-related drift and performance decline.

The reference norms below are screening heuristics for decision support. They
should be reviewed and tuned by the sports-science team and validated against
your own athlete data before being relied on.
"""

import numpy as np

# direction "high": larger values are worse. direction "low": smaller values are worse.
# path: where the value lives inside the biomechanics result.
METRIC_NORMS: dict[str, dict] = {
    "knee_valgus_peak_deg": dict(
        path=("metrics", "knee_valgus_peak_deg"), normal=5, caution=8, high=12, direction="high",
        label="Knee valgus", issue="knee_valgus",
        message="Knee collapses inward during loading (dynamic valgus).",
    ),
    "landing_knee_flexion_deg": dict(
        path=("metrics", "landing_knee_flexion_deg"), normal=35, caution=25, high=15, direction="low",
        label="Landing knee flexion", issue="stiff_landing",
        message="Landing with straight knees increases impact load.",
    ),
    "trunk_lean_max_deg": dict(
        path=("metrics", "trunk_lean_max_deg"), normal=10, caution=15, high=25, direction="high",
        label="Trunk lean", issue="trunk_control",
        message="Excessive trunk lean from vertical.",
    ),
    "hip_stability_pelvic_drop_deg": dict(
        path=("metrics", "hip_stability_pelvic_drop_deg"), normal=3, caution=5, high=8, direction="high",
        label="Pelvic drop (hip stability)", issue="hip_stability",
        message="Pelvis drops or tilts, suggesting weak hip stabilisers.",
    ),
    "knee_flexion_rom_si": dict(
        path=("symmetry", "knee_flexion_rom_si"), normal=5, caution=10, high=15, direction="high",
        label="Knee ROM asymmetry (%)", issue="asymmetry",
        message="Left and right knee range of motion differ noticeably.",
    ),
    "hip_flexion_rom_si": dict(
        path=("symmetry", "hip_flexion_rom_si"), normal=5, caution=10, high=15, direction="high",
        label="Hip ROM asymmetry (%)", issue="asymmetry",
        message="Left and right hip range of motion differ noticeably.",
    ),
    "ankle_angle_rom_si": dict(
        path=("symmetry", "ankle_angle_rom_si"), normal=5, caution=10, high=15, direction="high",
        label="Ankle ROM asymmetry (%)", issue="ankle_control",
        message="Left and right ankle motion differ noticeably.",
    ),
    "shoulder_elevation_rom_si": dict(
        path=("symmetry", "shoulder_elevation_rom_si"), normal=5, caution=10, high=15, direction="high",
        label="Shoulder ROM asymmetry (%)", issue="shoulder_control",
        message="Left and right shoulder motion differ noticeably.",
    ),
    "balance_sway_ml_norm": dict(
        path=("metrics", "balance_sway_ml_norm"), normal=0.02, caution=0.04, high=0.07, direction="high",
        label="Lateral sway (body-height units)", issue="balance",
        message="Large side-to-side centre-of-mass sway.",
    ),
    "stride_variability_pct": dict(
        path=("metrics", "stride_variability_pct"), normal=5, caution=10, high=18, direction="high",
        label="Stride variability (%)", issue="stride_consistency",
        message="Stride length varies a lot from step to step.",
    ),
    "posture_shoulder_tilt_deg": dict(
        path=("metrics", "posture_shoulder_tilt_deg"), normal=3, caution=6, high=10, direction="high",
        label="Shoulder tilt", issue="posture",
        message="Shoulders are uneven.",
    ),
    "posture_head_offset_norm": dict(
        path=("metrics", "posture_head_offset_norm"), normal=0.03, caution=0.06, high=0.10, direction="high",
        label="Head offset from shoulders", issue="posture",
        message="Head sits off-centre relative to the shoulders.",
    ),
}

# Activity-specific overrides: a dict replaces thresholds, None skips the metric.
ACTIVITY_OVERRIDES: dict[str, dict[str, dict | None]] = {
    "sprinting": {"trunk_lean_max_deg": dict(normal=25, caution=40, high=55)},
    "running": {"trunk_lean_max_deg": dict(normal=15, caution=22, high=30)},
    "squatting": {"trunk_lean_max_deg": dict(normal=30, caution=45, high=60)},
    "throwing": {"trunk_lean_max_deg": None, "stride_variability_pct": None},
    "jumping": {"stride_variability_pct": None},
    "landing": {"stride_variability_pct": None},
}


def severity_fraction(value: float, normal: float, caution: float, high: float, direction: str = "high") -> float:
    """Map a metric value to 0-1: 0 at/below normal, 0.4 at caution, 0.8 at high, 1 far beyond."""
    if direction == "low":
        value, normal, caution, high = -value, -normal, -caution, -high
    xp = [normal, caution, high, high + (high - normal)]
    return float(np.interp(value, xp, [0.0, 0.4, 0.8, 1.0]))


def _get(biomech: dict, path: tuple[str, str]):
    section = biomech.get(path[0]) or {}
    return section.get(path[1])


def evaluate_metrics(biomech: dict, activity: str) -> list[dict]:
    """Evaluate every available metric against its norms (sorted, worst first)."""
    overrides = ACTIVITY_OVERRIDES.get(activity, {})
    items = []
    for key, spec in METRIC_NORMS.items():
        spec = dict(spec)
        if key in overrides:
            if overrides[key] is None:
                continue
            spec.update(overrides[key])
        value = _get(biomech, spec["path"])
        if value is None:
            continue
        frac = severity_fraction(value, spec["normal"], spec["caution"], spec["high"], spec["direction"])
        beyond_high = value >= spec["high"] if spec["direction"] == "high" else value <= spec["high"]
        beyond_caution = value >= spec["caution"] if spec["direction"] == "high" else value <= spec["caution"]
        level = "high" if beyond_high else "moderate" if beyond_caution else "normal"
        items.append(
            {
                "metric": key,
                "label": spec["label"],
                "issue": spec["issue"],
                "value": value,
                "normal": spec["normal"],
                "caution": spec["caution"],
                "high": spec["high"],
                "direction": spec["direction"],
                "severity_fraction": round(frac, 3),
                "level": level,
                "message": spec["message"] if level != "normal" else None,
            }
        )
    items.sort(key=lambda d: d["severity_fraction"], reverse=True)
    return items


def _clean(values: list) -> np.ndarray:
    return np.array([np.nan if v is None else v for v in values], dtype=float)


def movement_inconsistency(repetitions: dict) -> dict | None:
    """Rep-to-rep variability in depth and valgus (needs at least 3 repetitions)."""
    flex = _clean(repetitions.get("peak_knee_flexion", []))
    valgus = _clean(repetitions.get("peak_valgus", []))
    flex, valgus = flex[~np.isnan(flex)], valgus[~np.isnan(valgus)]
    if len(flex) < 3:
        return None
    depth_cv = float(np.std(flex) / (abs(np.mean(flex)) + 1e-9) * 100)
    valgus_sd = float(np.std(valgus)) if len(valgus) >= 3 else 0.0
    score = float(np.clip(2.5 * depth_cv + 3.0 * valgus_sd, 0, 100))
    return {
        "repetitions": int(len(flex)),
        "depth_cv_pct": round(depth_cv, 2),
        "valgus_sd_deg": round(valgus_sd, 2),
        "inconsistency_score": round(score, 1),
    }


def fatigue_trend(repetitions: dict) -> dict | None:
    """Look for drift across repetitions: shallower depth, more valgus, more trunk lean."""
    flex = _clean(repetitions.get("peak_knee_flexion", []))
    valgus = _clean(repetitions.get("peak_valgus", []))
    trunk = _clean(repetitions.get("trunk_lean", []))
    n = len(flex)
    if n < 4:
        return None

    def total_change(arr: np.ndarray) -> float:
        mask = ~np.isnan(arr)
        if mask.sum() < 4:
            return 0.0
        x = np.arange(n)[mask]
        slope = np.polyfit(x, arr[mask], 1)[0]
        return float(slope * (n - 1))

    mean_flex = float(np.nanmean(flex)) if not np.isnan(flex).all() else 1.0
    depth_drop_pct = max(0.0, -total_change(flex) / (abs(mean_flex) + 1e-9) * 100)
    valgus_increase = max(0.0, total_change(valgus))
    trunk_increase = max(0.0, total_change(trunk))
    index = float(np.clip(0.4 * depth_drop_pct / 20 + 0.4 * valgus_increase / 6 + 0.2 * trunk_increase / 10, 0, 1))
    return {
        "repetitions": n,
        "depth_drop_pct": round(depth_drop_pct, 2),
        "valgus_increase_deg": round(valgus_increase, 2),
        "trunk_lean_increase_deg": round(trunk_increase, 2),
        "fatigue_index": round(index, 3),
    }


def performance_decline(history: list[float], current: float, min_history: int = 3) -> dict | None:
    """Compare the current movement-quality score with the athlete's recent baseline."""
    if len(history) < min_history:
        return None
    baseline = float(np.mean(history[-5:]))
    if baseline <= 0:
        return None
    drop_pct = (baseline - current) / baseline * 100
    return {
        "baseline_quality": round(baseline, 1),
        "current_quality": round(current, 1),
        "decline_pct": round(drop_pct, 1),
        "flagged": bool(drop_pct > 10),
    }
