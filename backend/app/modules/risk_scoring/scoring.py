"""Injury-risk scoring — the weighted composite from the project spec.

    Injury Risk Score = 35% biomechanical deviations
                      + 20% historical injury factors
                      + 20% movement asymmetry
                      + 15% training-load indicators
                      + 10% fatigue indicators

The weights come from the spec PDF (docs/AI_Sports Injury Risk Detection from Video.pdf).
They are a SPECIFICATION, not something fitted to injury outcomes — no injury-labelled
dataset exists behind this system (docs/SCIENCE_CONSTRAINTS.md; the prior-art section
explains why that takes thousands of labelled athletes). What makes the composite honest:

* every component is a transparent 0-100 score with its inputs shown;
* a component with no data is reported UNAVAILABLE and excluded — it is never scored as 0
  ("no data" is not "no risk") — and the remaining weights are renormalised, with the
  resulting `data_completeness` reported alongside the score;
* every mapping parameter below is a named constant whose evidence level is stated.
  Where a parameter is an engineering heuristic rather than a literature value, it says so.

Nothing here predicts an injury or outputs an injury probability.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

import numpy as np

from app.modules.biomechanics.movement_analysis import MEASUREMENT_NOISE_DEG, MIN_MEANINGFUL_RANGE_DEG

ENGINE_VERSION = "2.2"   # 2.1: poorly visible legs excluded from the comparison; 2.2: canonical baseline order + provisional flag

# Below this many baseline videos the anomaly comparison is noisy: simulated at production scale, ~10% of PERFECTLY
# NORMAL videos score as strongly anomalous with 10 baseline videos, ~2% with 30 (tests/test_anomaly_calibration.py).
# The floor to score at all stays configurable; scores built on fewer than this are labelled provisional.
PROVISIONAL_BELOW_VIDEOS = 30

METHODOLOGY_NOTE = (
    "Weighted composite per the project spec: biomechanical deviation from a population baseline "
    "(35%), prior-injury history (20%), left/right asymmetry (20%), training load (15%) and fatigue "
    "indicators (10%). Components without data are excluded and the remaining weights renormalised "
    "(see data_completeness). Screening aid only — not a trained injury-prediction model and not a "
    "diagnosis; there is no injury-outcome dataset behind it. See docs/SCIENCE_CONSTRAINTS.md."
)

WEIGHTS = {
    "biomechanical_deviations": 0.35,
    "historical_injury_factors": 0.20,
    "movement_asymmetry": 0.20,
    "training_load_indicators": 0.15,
    "fatigue_indicators": 0.10,
}

# Category cut-offs on the 0-100 score. Even quartiles: a labelling convention, not clinical.
CATEGORY_THRESHOLDS = (25.0, 50.0, 75.0)


def categorize(score: float) -> str:
    lo, mid, hi = CATEGORY_THRESHOLDS
    return "low" if score < lo else "moderate" if score < mid else "high" if score < hi else "critical"


def _ramp(x: float, start: float, full: float) -> float:
    """0 at/below `start`, 100 at/above `full`, linear between."""
    if full == start:
        return 100.0 if x >= full else 0.0
    return float(np.clip((x - start) / (full - start), 0.0, 1.0) * 100.0)


@dataclass
class Component:
    key: str
    score: float | None  # 0-100; None = unavailable
    detail: dict = field(default_factory=dict)

    @property
    def available(self) -> bool:
        return self.score is not None


# --------------------------------------------------------------------------- #
# 1. Biomechanical deviations (35%)
# --------------------------------------------------------------------------- #

def score_biomechanical(anomaly: dict | None) -> Component:
    if anomaly is None:
        return Component("biomechanical_deviations", None, {"reason": "no baseline comparison available"})
    flagged = [f for f in anomaly["features"] if f["flagged"]]
    return Component("biomechanical_deviations", anomaly["deviation_score"], {
        "method": "Isolation Forest on video-level extremes + robust-z extremity, vs other videos of this movement",
        "baseline_videos": anomaly["n_baseline"],
        "percentile_vs_baseline": anomaly["percentile"],
        "pattern_score": anomaly["isolation_forest_score"],
        "extremity_score": anomaly["extremity_score"],
        "deviating_features": [
            {k: f[k] for k in ("feature", "value", "baseline_median", "z", "direction")} for f in flagged[:6]
        ],
    })


# --------------------------------------------------------------------------- #
# 2. Historical injury factors (20%)
# --------------------------------------------------------------------------- #
# Prior injury is the best-evidenced risk factor across the injuries in scope (ankle sprain:
# meta-analysis of 26 studies; hamstring; low back pain pooled OR 3.5; shoulder). The literature
# does NOT support a precise multiplier, so this is a coarse, ordinal 4-level score, not a
# fabricated percentage.

REGION_KEYWORDS = {
    "knee": ("knee", "acl", "mcl", "pcl", "meniscus", "patell"),
    "hamstring": ("hamstring", "thigh", "quad"),
    "ankle": ("ankle", "foot", "achilles", "heel", "plantar", "calf", "shin"),
    "hip_groin": ("hip", "groin", "adductor", "glute"),
    "lower_back": ("back", "lumbar", "spine", "spinal", "sacr"),
    "shoulder": ("shoulder", "rotator", "elbow", "arm", "wrist", "clavicle", "bicep", "tricep"),
}

MOVEMENT_REGIONS = {
    "squatting": {"knee", "hip_groin", "lower_back", "ankle"},
    "landing": {"knee", "ankle", "hip_groin", "hamstring"},
    "jumping": {"knee", "ankle", "hip_groin"},
    "running": {"hamstring", "knee", "ankle", "hip_groin", "lower_back"},
    "sprinting": {"hamstring", "knee", "ankle", "hip_groin", "lower_back"},
    "cutting": {"knee", "ankle", "hamstring", "hip_groin"},
    "throwing": {"shoulder", "lower_back"},
}

HISTORY_RECENT_MONTHS = 24
HISTORY_LEVELS = {  # (relevant to this movement, status) -> score
    ("relevant", "unresolved"): 100.0,
    ("relevant", "recent"): 70.0,
    ("relevant", "remote"): 40.0,
    ("other", "unresolved"): 40.0,
    ("other", "recent"): 25.0,
    ("other", "remote"): 10.0,
}


def body_part_region(body_part: str) -> str | None:
    text = body_part.lower()
    for region, words in REGION_KEYWORDS.items():
        if any(re.search(r"\b" + re.escape(w), text) for w in words):
            return region
    return None


def _months_between(earlier: date, later: date) -> float:
    return (later - earlier).days / 30.44


def score_history(injuries: list[dict], movement_type: str, today: date | None = None) -> Component:
    """`injuries`: dicts with body_part, severity, injury_date, recovery_date (date | None)."""
    today = today or date.today()
    if not injuries:
        return Component("historical_injury_factors", 0.0, {"prior_injuries": 0, "note": "no prior injuries recorded"})

    relevant_regions = MOVEMENT_REGIONS.get(movement_type)  # None = every region counts
    rows = []
    for inj in injuries:
        region = body_part_region(inj["body_part"])
        # an unrecognised body part is treated as relevant — never under-report on a guess
        relevant = relevant_regions is None or region is None or region in relevant_regions
        if inj.get("recovery_date") is None:
            status = "unresolved"
        else:
            status = "recent" if _months_between(inj["recovery_date"], today) < HISTORY_RECENT_MONTHS else "remote"
        score = HISTORY_LEVELS[("relevant" if relevant else "other", status)]
        rows.append({
            "body_part": inj["body_part"], "region": region, "severity": inj.get("severity"),
            "status": status, "relevant_to_movement": relevant, "level_score": score,
        })
    top = max(r["level_score"] for r in rows)
    return Component("historical_injury_factors", top, {
        "prior_injuries": len(rows),
        "basis": "highest level among recorded injuries (relevance to this movement x recovery status)",
        "injuries": rows,
    })


# --------------------------------------------------------------------------- #
# 3. Movement asymmetry (20%)
# --------------------------------------------------------------------------- #
# The 90% LSI convention has documented predictive-validity problems (SCIENCE_CONSTRAINTS.md;
# only ~24% of healthy athletes meet it), so a hard pass/fail at 90 would be dishonest. The
# score ramps continuously: 0 at LSI >= 90, 100 at LSI <= 70 (endpoints: the convention, and a
# 30% deficit; both heuristic).

LSI_NO_CONCERN, LSI_FULL_CONCERN = 90.0, 70.0
# One leg must have been reliably visible for a left/right comparison to mean anything.
MIN_LEG_USABLE_PCT = 60.0
LSI_CAVEAT = (
    "The 90% LSI convention has documented predictive-validity problems; shown as a continuous "
    "signal, never a pass/fail."
)


def limb_symmetry_index(left: float, right: float) -> float:
    weaker, stronger = min(left, right), max(left, right)
    return 100.0 if stronger == 0 else 100.0 * weaker / stronger


def score_asymmetry(features: dict[str, float], leg_usable_pct: dict | None = None) -> Component:
    key = "movement_asymmetry"
    left, right = features.get("knee_flexion_angle_left.p95"), features.get("knee_flexion_angle_right.p95")
    if left is None or right is None:
        return Component(key, None, {"reason": "no left/right knee-flexion pair for this movement/camera view"})
    if leg_usable_pct and min(leg_usable_pct.get("left_leg", 100), leg_usable_pct.get("right_leg", 100)) < MIN_LEG_USABLE_PCT:
        return Component(key, None, {
            "reason": "one leg was not reliably visible (occluded or out of frame); a left/right "
                      "comparison would measure the camera angle, not the athlete",
        })
    if max(left, right) < MIN_MEANINGFUL_RANGE_DEG:
        return Component(key, None, {
            "reason": f"peak knee flexion below ~{MIN_MEANINGFUL_RANGE_DEG:.0f} deg (3x pose-model noise): "
                      "too small a movement to compare sides",
        })
    lsi = limb_symmetry_index(left, right)
    return Component(key, _ramp(-lsi, -LSI_NO_CONCERN, -LSI_FULL_CONCERN), {
        "metric": "peak knee flexion, weaker / stronger side",
        "left_peak_deg": round(left, 1), "right_peak_deg": round(right, 1),
        "lsi_pct": round(lsi, 1), "caveat": LSI_CAVEAT,
    })


# --------------------------------------------------------------------------- #
# 4. Training-load indicators (15%)
# --------------------------------------------------------------------------- #
# ACWR zones from the workload literature (Gabbett 2016): 0.8-1.3 "sweet spot", >=1.5 elevated.
# ACWR itself is contested (Impellizzeri et al. 2020, Sports Med 51:581), hence a bounded 15%
# input and an explicit refusal to compute it without a full 28-day chronic window.

ACWR_OK_UPPER, ACWR_ELEVATED, ACWR_FULL = 1.3, 1.5, 2.0


def score_training_load(acwr: dict | None) -> Component:
    key = "training_load_indicators"
    if not acwr or acwr.get("acwr") is None:
        return Component(key, None, {"reason": (acwr or {}).get("message", "no training-load data")})
    v = acwr["acwr"]
    # 0 through the sweet spot, 50 at 1.5, 100 at >= 2.0
    if v <= ACWR_OK_UPPER:
        s = 0.0
    elif v <= ACWR_ELEVATED:
        s = _ramp(v, ACWR_OK_UPPER, ACWR_ELEVATED) * 0.5
    else:
        s = 50.0 + _ramp(v, ACWR_ELEVATED, ACWR_FULL) * 0.5
    return Component(key, s, {
        "acwr": v, "acute_load": acwr.get("acute_load"), "chronic_load": acwr.get("chronic_load"),
        "zones": "0.8-1.3 typical, >=1.5 elevated (Gabbett 2016)",
        "caveat": "ACWR is contested in the literature (Impellizzeri 2020); treat as one input.",
    })


# --------------------------------------------------------------------------- #
# 5. Fatigue indicators (10%)
# --------------------------------------------------------------------------- #
# Two indicators, averaged when both exist:
#  * RPE trend: recent-week mean RPE minus the preceding three weeks' (heuristic ramp 0.5 -> 2.5 RPE points).
#  * Within-session movement drift across repetitions: SIZE of change between the first and last
#    third of reps. Direction-agnostic on purpose — a 2025 meta-analysis (44 studies) found no
#    consistent directional fatigue effect on landing hip/knee flexion. Floor 5% ~ pose-model
#    noise relative to a typical ~100 deg squat range; full scale 30% is a heuristic.

RPE_TREND_START, RPE_TREND_FULL = 0.5, 2.5
DRIFT_START_PCT, DRIFT_FULL_PCT = 5.0, 30.0
CV_START_PCT, CV_FULL_PCT = 5.0, 25.0


def score_fatigue(rpe: dict | None, dynamics: dict | None) -> Component:
    key = "fatigue_indicators"
    parts, detail = [], {}
    if rpe and rpe.get("rpe_trend") is not None:
        s = _ramp(rpe["rpe_trend"], RPE_TREND_START, RPE_TREND_FULL)
        parts.append(s)
        detail["rpe_trend"] = {**rpe, "score": round(s, 1)}
    if dynamics and dynamics.get("drift_pct") is not None:
        s = _ramp(abs(dynamics["drift_pct"]), DRIFT_START_PCT, DRIFT_FULL_PCT)
        parts.append(s)
        detail["movement_drift"] = {
            "n_reps": dynamics["n_reps"], "drift_pct": dynamics["drift_pct"],
            "direction": dynamics.get("drift_direction"), "score": round(s, 1),
            "note": "size of change across the clip's repetitions; direction reported, not assumed harmful",
        }
    if not parts:
        return Component(key, None, {
            "reason": "needs >=3 rated sessions in each of the last week and prior 3 weeks, "
                      "or >=4 repetitions in this clip",
        })
    return Component(key, float(np.mean(parts)), detail)


def consistency_score(dynamics: dict | None) -> tuple[float | None, dict]:
    """Rep-to-rep inconsistency (coefficient of variation of rep peaks), 0-100. Needs >=3 reps."""
    if not dynamics or dynamics.get("cv_pct") is None or dynamics["n_reps"] < 3:
        return None, {}
    return _ramp(dynamics["cv_pct"], CV_START_PCT, CV_FULL_PCT), {"cv_pct": dynamics["cv_pct"], "n_reps": dynamics["n_reps"]}


# --------------------------------------------------------------------------- #
# Combination
# --------------------------------------------------------------------------- #

def combine(components: list[Component]) -> dict:
    """Weighted composite over the AVAILABLE components (weights renormalised)."""
    by_key = {c.key: c for c in components}
    avail_weight = sum(WEIGHTS[k] for k, c in by_key.items() if c.available)
    if avail_weight <= 0:
        raise ValueError("no scoreable component")

    breakdown, overall = {}, 0.0
    for key, nominal in WEIGHTS.items():
        c = by_key.get(key) or Component(key, None, {"reason": "not assessed"})
        if c.available:
            eff = nominal / avail_weight
            points = eff * c.score
            overall += points
            breakdown[key] = {
                "points": round(points, 1), "max": round(eff * 100, 1), "score": round(c.score, 1),
                "weight": nominal, "effective_weight": round(eff, 3), "available": True, "detail": c.detail,
            }
        else:
            breakdown[key] = {
                "points": 0.0, "max": 0.0, "score": None, "weight": nominal,
                "effective_weight": 0.0, "available": False, "detail": c.detail,
            }
    overall = round(float(np.clip(overall, 0, 100)), 1)
    return {
        "overall_score": overall,
        "risk_category": categorize(overall),
        "score_breakdown": breakdown,
        "data_completeness": round(avail_weight, 2),
        "missing_components": [k for k, b in breakdown.items() if not b["available"]],
    }


def compute_sub_scores(components: list[Component], overall: float, dynamics: dict | None) -> dict:
    """The five scores the spec lists (module 8), each 0-100 with a stated definition.

    Higher is worse for the two risk scores; higher is better for the three quality/health ones.
    """
    by = {c.key: c for c in components}
    bio = by.get("biomechanical_deviations")
    fat = by.get("fatigue_indicators")
    asym = by.get("movement_asymmetry")

    movement_quality = round(100 - bio.score, 1) if bio and bio.available else None
    fatigue_risk = round(fat.score, 1) if fat and fat.available else None

    cons, _ = consistency_score(dynamics)
    parts = [p for p in (asym.score if asym and asym.available else None, cons) if p is not None]
    efficiency = round(100 - float(np.mean(parts)), 1) if parts else None

    health_parts = [p for p in (
        movement_quality, 100 - overall, (100 - fatigue_risk) if fatigue_risk is not None else None
    ) if p is not None]
    health = round(float(np.mean(health_parts)), 1) if health_parts else None

    return {
        "injury_risk": {"score": overall, "higher_is": "worse",
                        "definition": "the weighted composite above"},
        "movement_quality": {"score": movement_quality, "higher_is": "better",
                             "definition": "100 minus the biomechanical-deviation score: how typical the movement "
                                           "pattern is relative to the population baseline"},
        "biomechanical_efficiency": {"score": efficiency, "higher_is": "better",
                                     "definition": "PROXY: 100 minus the mean of left/right asymmetry and rep-to-rep "
                                                   "inconsistency. True mechanical efficiency needs force/energy data "
                                                   "that single-camera video cannot provide."},
        "fatigue_risk": {"score": fatigue_risk, "higher_is": "worse",
                         "definition": "the fatigue-indicators component (RPE trend and within-session drift)"},
        "overall_health": {"score": health, "higher_is": "better",
                           "definition": "mean of movement quality, (100 - injury risk) and (100 - fatigue risk), "
                                         "over those available"},
    }
