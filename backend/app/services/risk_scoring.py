"""Weighted injury risk scoring (weights from the project specification)."""

import math
from datetime import date, timedelta

import numpy as np

from app.core.config import settings

# Injury Risk Score = weighted sum of five component scores (each 0-100)
WEIGHTS = {
    "biomechanical_deviations": 0.35,
    "historical_injury": 0.20,
    "movement_asymmetry": 0.20,
    "training_load": 0.15,
    "fatigue": 0.10,
}

SEVERITY_WEIGHT = {"minor": 0.3, "moderate": 0.6, "severe": 1.0}


def categorize(score: float) -> str:
    if score >= settings.RISK_CRITICAL_THRESHOLD:
        return "critical"
    if score >= settings.RISK_HIGH_THRESHOLD:
        return "high"
    if score >= settings.RISK_MODERATE_THRESHOLD:
        return "moderate"
    return "low"


# --- Component scores --------------------------------------------------------


def biomech_deviation_score(items: list[dict]) -> float | None:
    """0-100. One serious deviation must not be averaged away, so blend max and top-3 mean."""
    fractions = sorted((i["severity_fraction"] for i in items), reverse=True)
    if not fractions:
        return None
    return 100.0 * (0.6 * fractions[0] + 0.4 * float(np.mean(fractions[:3])))


def injury_recency_factor(injury: dict, today: date) -> float:
    """0-1 weight for one past injury: severity x recency (18-month decay); active injuries count fully."""
    sev = SEVERITY_WEIGHT.get(injury.get("severity", "moderate"), 0.6)
    if injury.get("status") in ("active", "recovering"):
        return sev
    months = max(0.0, (today - injury["injury_date"]).days / 30.4)
    return sev * math.exp(-months / 18.0)


def historical_injury_score(injuries: list[dict], today: date | None = None) -> float:
    today = today or date.today()
    survive = 1.0
    for inj in injuries:
        survive *= 1.0 - 0.7 * injury_recency_factor(inj, today)
    return 100.0 * (1.0 - survive)


def asymmetry_score(symmetry: dict) -> float | None:
    mean_si, max_si = symmetry.get("mean_si"), symmetry.get("max_si")
    if mean_si is None or max_si is None:
        return None
    effective = max(mean_si, 0.7 * max_si)
    return float(np.interp(effective, [5, 10, 15, 25], [0, 35, 65, 100]))


def compute_load_stats(entries: list[dict], today: date | None = None) -> dict | None:
    """Acute:chronic workload ratio from session loads (duration x RPE).

    Needs at least 14 days of history, otherwise the ratio is unreliable and None is returned.
    """
    today = today or date.today()
    if not entries:
        return None
    earliest = min(e["entry_date"] for e in entries)
    if (today - earliest).days < 14:
        return None
    acute = sum(e["load_au"] for e in entries if today - timedelta(days=6) <= e["entry_date"] <= today)
    chronic_total = sum(e["load_au"] for e in entries if today - timedelta(days=27) <= e["entry_date"] <= today)
    chronic_weekly = chronic_total / 4.0
    if chronic_weekly <= 0:
        return None
    return {
        "acute_load": round(acute, 1),
        "chronic_weekly_load": round(chronic_weekly, 1),
        "acwr": round(acute / chronic_weekly, 2),
    }


def training_load_score(load_stats: dict | None) -> float | None:
    if not load_stats:
        return None
    # sweet spot 0.8-1.3, rising risk above 1.3, sharp above 1.5; mild risk when detraining
    return float(np.interp(load_stats["acwr"], [0.5, 0.8, 1.0, 1.3, 1.5, 2.0], [40, 25, 10, 25, 60, 100]))


def fatigue_score(fatigue: dict | None) -> float | None:
    return None if not fatigue else 100.0 * fatigue["fatigue_index"]


# --- Final scores -------------------------------------------------------------


def compute_risk_score(components: dict[str, float | None]) -> dict:
    """Weighted sum; weights are renormalised over components that could be measured."""
    available = {k: v for k, v in components.items() if v is not None}
    missing = [k for k, v in components.items() if v is None]
    if not available:
        return {"score": 0.0, "category": "low", "components": {}, "weights_used": {}, "missing_components": missing}
    total_w = sum(WEIGHTS[k] for k in available)
    weights_used = {k: WEIGHTS[k] / total_w for k in available}
    score = sum(weights_used[k] * available[k] for k in available)
    return {
        "score": round(score, 1),
        "category": categorize(score),
        "components": {k: round(v, 1) for k, v in available.items()},
        "weights_used": {k: round(w, 3) for k, w in weights_used.items()},
        "missing_components": missing,
    }


def compute_aux_scores(
    deviation_score: float | None,
    inconsistency: dict | None,
    biomech: dict,
    fatigue: dict | None,
    risk_score: float,
) -> dict:
    dev = deviation_score or 0.0
    incons = inconsistency["inconsistency_score"] if inconsistency else 0.0
    movement_quality = float(np.clip(100.0 - (0.7 * dev + 0.3 * incons), 0, 100))

    alignment = biomech["metrics"].get("joint_alignment_score")
    alignment = 70.0 if alignment is None else alignment
    mean_si = biomech["symmetry"].get("mean_si") or 0.0
    symmetry_score = 100.0 - float(np.interp(mean_si, [0, 25], [0, 100]))
    efficiency = float(np.clip(0.5 * alignment + 0.3 * symmetry_score + 0.2 * (100 - incons), 0, 100))

    fatigue_risk = fatigue_score(fatigue)
    overall_health = float(
        np.clip(0.5 * (100 - risk_score) + 0.3 * movement_quality + 0.2 * (100 - (fatigue_risk or 0.0)), 0, 100)
    )
    return {
        "movement_quality": round(movement_quality, 1),
        "biomechanical_efficiency": round(efficiency, 1),
        "fatigue_risk": None if fatigue_risk is None else round(fatigue_risk, 1),
        "overall_health": round(overall_health, 1),
    }
