"""Injury risk prediction per injury category.

Each category score (0-100) combines the severity of the biomechanical findings
that research links to that injury with the athlete's prior injuries. If a
trained model exists at MODEL_PATH (see backend/ml/train_injury_model.py) its
probability is blended with the rule-based one.

These are screening indicators, not diagnoses.
"""

import logging
import math
from datetime import date
from pathlib import Path

import numpy as np

from app.core.config import settings
from app.services.risk_scoring import categorize, injury_recency_factor

logger = logging.getLogger(__name__)

# Features fed to the optional ML model (order matters)
FEATURE_NAMES = [
    "knee_valgus_peak_deg",
    "landing_knee_flexion_deg",
    "trunk_lean_max_deg",
    "hip_stability_pelvic_drop_deg",
    "knee_flexion_rom_si",
    "hip_flexion_rom_si",
    "ankle_angle_rom_si",
    "shoulder_elevation_rom_si",
    "balance_sway_ml_norm",
    "stride_variability_pct",
    "fatigue_index",
    "acwr",
    "prior_injury_load",
]
NEUTRAL = {"landing_knee_flexion_deg": 40.0, "acwr": 1.0}


def extract_features(items: list[dict], fatigue: dict | None, load_stats: dict | None, prior_load: float) -> dict:
    values = {i["metric"]: i["value"] for i in items}
    feats = {name: values.get(name, NEUTRAL.get(name, 0.0)) for name in FEATURE_NAMES}
    feats["fatigue_index"] = fatigue["fatigue_index"] if fatigue else 0.0
    feats["acwr"] = load_stats["acwr"] if load_stats else NEUTRAL["acwr"]
    feats["prior_injury_load"] = prior_load
    return feats


def prior_injury_factor(injuries: list[dict], keywords: list[str], today: date | None = None) -> float:
    """0-1: how much past injuries to the relevant body region raise current risk."""
    today = today or date.today()
    survive = 1.0
    for inj in injuries:
        text = f"{inj.get('body_part', '')} {inj.get('injury_type', '')}".lower()
        if keywords and not any(k in text for k in keywords):
            continue
        survive *= 1.0 - injury_recency_factor(inj, today)
    return 1.0 - survive


def _combine(parts: list[tuple[str, float, float | None]], prior: float, prior_weight: float = 0.25) -> tuple[float, list[dict]]:
    """parts = (driver name, weight, severity 0-1 or None). Missing parts drop out."""
    usable = [(n, w, s) for n, w, s in parts if s is not None]
    if not usable:
        return 100.0 * prior_weight * prior, []
    total_w = sum(w for _, w, _ in usable)
    contributions = [(n, w / total_w * s, s) for n, w, s in usable]
    base = sum(c for _, c, _ in contributions)
    score = 100.0 * min(1.0, base + prior_weight * prior)
    drivers = [
        {"driver": n, "contribution": round(100 * c, 1), "severity": round(s, 2)}
        for n, c, s in sorted(contributions, key=lambda x: x[1], reverse=True)
        if s >= 0.4
    ]
    if prior >= 0.3:
        drivers.append({"driver": "prior_injury_history", "contribution": round(100 * prior_weight * prior, 1), "severity": round(prior, 2)})
    return score, drivers


def predict_category_risks(
    items: list[dict],
    injuries: list[dict],
    load_sev: float | None,
    fatigue_sev: float | None,
    mean_si_sev: float | None,
    today: date | None = None,
) -> list[dict]:
    sev = {i["metric"]: i["severity_fraction"] for i in items}
    g = sev.get

    definitions = {
        "ACL injury": (
            [("knee_valgus", 0.35, g("knee_valgus_peak_deg")),
             ("stiff_landing", 0.25, g("landing_knee_flexion_deg")),
             ("trunk_lean", 0.15, g("trunk_lean_max_deg")),
             ("knee_asymmetry", 0.15, g("knee_flexion_rom_si")),
             ("pelvic_drop", 0.10, g("hip_stability_pelvic_drop_deg"))],
            ["acl", "cruciate", "knee"],
        ),
        "Hamstring injury": (
            [("hip_asymmetry", 0.30, g("hip_flexion_rom_si")),
             ("knee_asymmetry", 0.15, g("knee_flexion_rom_si")),
             ("stride_variability", 0.15, g("stride_variability_pct")),
             ("trunk_lean", 0.10, g("trunk_lean_max_deg")),
             ("pelvic_drop", 0.10, g("hip_stability_pelvic_drop_deg")),
             ("training_load", 0.20, load_sev)],
            ["hamstring", "thigh", "posterior"],
        ),
        "Ankle sprain": (
            [("ankle_asymmetry", 0.30, g("ankle_angle_rom_si")),
             ("balance_sway", 0.30, g("balance_sway_ml_norm")),
             ("knee_valgus", 0.15, g("knee_valgus_peak_deg")),
             ("stiff_landing", 0.15, g("landing_knee_flexion_deg")),
             ("pelvic_drop", 0.10, g("hip_stability_pelvic_drop_deg"))],
            ["ankle"],
        ),
        "Shoulder injury": (
            [("shoulder_asymmetry", 0.35, g("shoulder_elevation_rom_si")),
             ("shoulder_tilt", 0.20, g("posture_shoulder_tilt_deg")),
             ("head_posture", 0.10, g("posture_head_offset_norm")),
             ("trunk_lean", 0.15, g("trunk_lean_max_deg")),
             ("training_load", 0.20, load_sev)],
            ["shoulder", "rotator", "clavicle"],
        ),
        "Lower back injury": (
            [("trunk_lean", 0.35, g("trunk_lean_max_deg")),
             ("pelvic_drop", 0.20, g("hip_stability_pelvic_drop_deg")),
             ("hip_asymmetry", 0.15, g("hip_flexion_rom_si")),
             ("head_posture", 0.10, g("posture_head_offset_norm")),
             ("fatigue", 0.20, fatigue_sev)],
            ["back", "lumbar", "spine", "spinal"],
        ),
        "Overuse injury": (
            [("training_load", 0.45, load_sev),
             ("fatigue", 0.35, fatigue_sev),
             ("movement_asymmetry", 0.20, mean_si_sev)],
            [],  # any recent injury counts
        ),
    }

    results = []
    for name, (parts, keywords) in definitions.items():
        prior = prior_injury_factor(injuries, keywords, today)
        score, drivers = _combine(parts, prior)
        results.append({"category": name, "score": round(score, 1), "level": categorize(score), "drivers": drivers})
    results.sort(key=lambda r: r["score"], reverse=True)
    return results


# --- Overall probability (heuristic, optionally blended with a trained model) ---

_model_bundle = None
_model_loaded = False


def _load_model():
    global _model_bundle, _model_loaded
    if _model_loaded:
        return _model_bundle
    _model_loaded = True
    path = Path(settings.MODEL_PATH)
    if path.exists():
        try:
            import joblib

            _model_bundle = joblib.load(path)
            logger.info("Loaded injury model from %s", path)
        except Exception:  # noqa: BLE001
            logger.exception("Could not load injury model; using heuristic only")
    return _model_bundle


def overall_probability(category_risks: list[dict], features: dict) -> dict:
    scores = [r["score"] for r in category_risks]
    combined = 0.6 * max(scores) + 0.4 * float(np.mean(scores))
    heuristic = 1.0 / (1.0 + math.exp(-(combined - 50.0) / 12.0))
    bundle = _load_model()
    if bundle is None:
        return {"probability": round(heuristic, 3), "source": "heuristic"}
    x = np.array([[features[n] for n in bundle["features"]]])
    model_p = float(bundle["model"].predict_proba(x)[0, 1])
    return {"probability": round(0.5 * heuristic + 0.5 * model_p, 3), "source": "blended"}
