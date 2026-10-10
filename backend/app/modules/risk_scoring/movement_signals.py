"""Four additive signals on top of the engine. Pure (no DB, no model); NONE of them feeds the composite score.

* rep_outliers    one bad repetition vs other athletes' sets (a video-level p95 hides it)
* heuristic_flags absolute, literature-cited cut-offs: stiff landing, partial-depth squat, low step rate
                  (overstride is refused: see OVERSTRIDE)
* athlete_trend   this video vs the same athlete's earlier videos: descriptive change, not risk
* fatigue_index   direction-agnostic drift of rep peaks across a set (robust slope)

Review aids for a coach / physiotherapist. Nothing here predicts injury (docs/SCIENCE_CONSTRAINTS.md).
"""

from __future__ import annotations

import numpy as np

from app.modules.biomechanics.movement_analysis import MEASUREMENT_NOISE_DEG
from app.modules.risk_scoring.anomaly import robust_z, z_tail_score
from app.modules.risk_scoring.scoring import PROVISIONAL_BELOW_VIDEOS, _ramp

MIN_REPS = 3                # fewer reps than this and "one bad rep" means nothing
REP_OUTLIER_FLAG = 50.0     # score at/above which a set is called out (~4 robust SD, widened for small populations)
FATIGUE_MIN_REPS = 5        # Theil-Sen over 5 reps = 10 pairwise slopes; one bad rep touches only 4 of them
MIN_PRIORS, MAX_PRIORS = 3, 10
TREND_Z_NOTABLE, TREND_Z_CLIP = 2.0, 10.0


def _na(reason: str) -> dict:
    return {"available": False, "reason": reason}


# --------------------------------------------------------------------------- #
# 1. Rep outliers vs population
# --------------------------------------------------------------------------- #

def _worst_dev(peaks) -> tuple[int, float]:
    """(index, signed deviation) of the rep furthest from the set's median peak."""
    d = np.asarray(peaks, dtype=float) - np.median(peaks)
    i = int(np.argmax(np.abs(d)))
    return i, float(d[i])


def rep_outliers(rep_peaks: list[float], population: list[tuple[str, list[float]]],
                 min_videos: int, min_athletes: int) -> dict:
    """The worst rep's distance from its own set median, vs the same number in other athletes' sets.

    `population`: (athlete_id, rep_peaks) of OTHER videos of this movement, counted on the same signal.
    Same tail logic and floors as the video-level engine, so a normal set rarely scores and a gross
    outlier does. Simulated (reps ~ N, athlete spread log-normal, 3-10 reps/set, 30 population videos):
    1% of normal sets score > 50 (3% with heavy-tailed reps); a single rep 45 deg off scores > 50 in 98%
    (30 deg: 60%, 20 deg: 14%). With 10 population videos: 0.2% / 85% / 39% / 7%.
    Spread (SD) of the peaks was tried first and missed 45-deg reps ~60-80% of the time: one rep adds only d/sqrt(n).
    """
    n = len(rep_peaks)
    if n < MIN_REPS:
        return _na(f"needs >= {MIN_REPS} repetitions, found {n}")
    pop = [(a, abs(_worst_dev(p)[1])) for a, p in population if len(p) >= MIN_REPS]
    athletes = len({a for a, _ in pop})
    if len(pop) < min_videos or athletes < min_athletes:
        return _na(f"needs {min_videos} other videos with >= {MIN_REPS} reps from {min_athletes} athletes, "
                   f"found {len(pop)} from {athletes}")
    i, dev = _worst_dev(rep_peaks)
    base = np.array([v for _, v in pop])
    z = float(robust_z(abs(dev), base))
    score = z_tail_score(max(z, 0.0), len(pop))
    # ponytail: peaks only, one feature, set length not stratified; add rep-count strata if false alarms track set length
    return {
        "available": True, "score": round(score, 1), "flagged": bool(score >= REP_OUTLIER_FLAG), "n_reps": n,
        "worst_rep": {"rep": i + 1, "peak_deg": round(float(rep_peaks[i]), 1), "from_set_median_deg": round(dev, 1)},
        "population_median_worst_dev_deg": round(float(np.median(base)), 1), "z": round(z, 2),
        "population": {"videos": len(pop), "athletes": athletes, "provisional": len(pop) < PROVISIONAL_BELOW_VIDEOS},
        "label": "Unsupervised: the worst repetition's distance from its own set median, compared with other "
                 "athletes' sets. A prompt to review the clip, not an injury prediction.",
    }


# --------------------------------------------------------------------------- #
# 2. Fatigue index
# --------------------------------------------------------------------------- #

def fatigue_index(rep_peaks: list[float]) -> dict:
    """0-100 drift of rep peaks across the set: |Theil-Sen total change| from 1x to 4x the pose-model noise.

    Direction-agnostic on purpose (SCIENCE_CONSTRAINTS.md: a 44-study meta-analysis found no consistent
    direction of fatigue effects on landing kinematics); the direction is reported, not assumed harmful.
    Theil-Sen (median of pairwise slopes) so ONE bad rep cannot fake or hide a drift, unlike first-vs-last thirds.
    """
    n = len(rep_peaks)
    if n < FATIGUE_MIN_REPS:
        return _na(f"needs >= {FATIGUE_MIN_REPS} repetitions, found {n}")
    y = np.asarray(rep_peaks, dtype=float)
    change = float(np.median([(y[j] - y[i]) / (j - i) for i in range(n) for j in range(i + 1, n)])) * (n - 1)
    # ponytail: rep peaks only; rep-duration drift (velocity loss) needs per-rep timing the stored analysis does not keep
    return {
        "available": True, "index": round(_ramp(abs(change), MEASUREMENT_NOISE_DEG, 4 * MEASUREMENT_NOISE_DEG), 1),
        "n_reps": n, "total_change_deg": round(change, 1),
        "direction": "stable" if abs(change) < MEASUREMENT_NOISE_DEG else "increase" if change > 0 else "decrease",
        "label": "Within-set kinematic drift of the repetition peaks (direction not assumed harmful). "
                 "Not a measurement of physiological fatigue.",
    }


# --------------------------------------------------------------------------- #
# 3. Heuristic flags (absolute, literature-cited)
# --------------------------------------------------------------------------- #
# status: "flagged" only when the value is beyond the cut-off by MORE than its measurement margin; "borderline"
# when beyond it but inside the margin; otherwise "ok". Uncertainty is never read as a finding.

FLAGS = {
    "stiff_landing": {
        "movements": ("landing",), "label": "Stiff landing", "unit": "deg", "threshold": 45.0,
        "margin": MEASUREMENT_NOISE_DEG,
        "measure": "knee-flexion range across the clip (95th - 5th percentile, reliably visible legs)",
        "evidence": "The Landing Error Scoring System counts knee flexion < 45 deg between initial contact and peak "
                    "flexion as an error (Padua 2009, Am J Sports Med 37:1996-2002, doi:10.1177/0363546509343200; item "
                    "definitions PMC4527442). Stiff, upright landings carry higher vertical ground reaction force than "
                    "soft ones (SL-LESS, J Sport Med Allied Health Sci 9(2), doi:10.25035/jsmahs.09.02.03).",
        "caveat": "Approximates LESS knee-flexion displacement by the clip's knee-flexion range; it is not measured "
                  "from initial contact. Screening aid, not a diagnosis.",
    },
    "inadequate_depth": {
        "movements": ("squatting",), "label": "Partial-depth squat", "unit": "deg", "threshold": 90.0,
        "margin": MEASUREMENT_NOISE_DEG,
        "measure": "peak knee flexion (95th percentile, reliably visible legs)",
        "evidence": "Squats ending above 90 deg of knee flexion are partial (half / quarter) squats. In a 10-week "
                    "trial of loaded squats (53 men) only the half-squat group reported rising pain, stiffness and "
                    "disability (Pallares 2019, Eur J Sport Sci, doi:10.1080/17461391.2019.1612952).",
        "caveat": "Movement-quality / range-of-motion flag from loaded-squat evidence; it drives no injury category. "
                  "Monocular pose over-reads squat angles by ~17 deg (docs/SCIENCE_CONSTRAINTS.md), so a shallow squat "
                  "can read deeper than it was: a flag is credible, a pass is not proof of depth.",
    },
    "low_cadence": {
        "movements": ("running",), "label": "Low step rate", "unit": "spm", "threshold": 166.0, "margin": 5.0,
        "measure": "steps per minute from foot-crossing timing",
        "evidence": "High-school runners in the lowest step-rate tertile (<= 166 spm, self-selected pace) had higher "
                    "odds of shin injury (OR 5.85, 95% CI 1.1-32.1; Luedke 2016, Med Sci Sports Exerc, PMID 26818150). "
                    "Lower step rate also predicted bone stress injury in collegiate runners (RR 0.95 per +1 step/min; "
                    "Kliethermes 2021, Br J Sports Med 55:851).",
        "caveat": "The cut-off is one cohort's tertile with a wide confidence interval, not a validated threshold, and "
                  "step rate rises with speed: a slow jog reads low. Interpret with the running speed.",
    },
}

# Overstride (foot landing ahead of the hip, Lieberman 2015, J Exp Biol 218:3406-3414) is NOT flagged: the literature
# gives no cut-off to flag it against, and the pipeline only APPROXIMATES the position (Engine 2.3 records
# `overstride_indicator` in the video's movement metrics: leading ankle ahead of the pelvis where the feet are furthest
# apart, metres, not scaled to leg length). Inventing a cut-off would be a fabricated claim. Low step rate is reported
# separately as the evidence-linked proxy.
OVERSTRIDE = {
    "key": "overstride", "label": "Overstride", "status": "not_assessable", "value": None, "unit": "leg lengths",
    "threshold": None, "margin": None, "measure": "foot landing position relative to the hip at touchdown",
    "evidence": "Foot landing position relative to the hip is the studied overstride measure (Lieberman 2015, "
                "J Exp Biol 218:3406-3414); that study gives no cut-off to flag it against.",
    "caveat": "Only approximated: the overstride_indicator in this video's movement metrics (leading ankle ahead of the "
              "pelvis, metres) is recorded, never scored.",
    "reason": "No validated cut-off exists to flag it against, and the pipeline's overstride indicator only "
              "approximates the foot's landing position relative to the hip. See low step rate.",
}


def _knees(features: dict[str, float], stat: str) -> list[float]:
    return [features[k] for s in ("left", "right") if (k := f"knee_flexion_angle_{s}.{stat}") in features]


def _knee_range(features, gait):
    hi, lo = _knees(features, "p95"), _knees(features, "p05")
    return float(np.mean(hi) - np.mean(lo)) if hi and lo else None


def _peak_knee(features, gait):
    hi = _knees(features, "p95")
    return float(np.mean(hi)) if hi else None


def _cadence(features, gait):
    c = (gait or {}).get("cadence_spm")
    return float(c) if c else None


_MEASURES = {"stiff_landing": _knee_range, "inadequate_depth": _peak_knee, "low_cadence": _cadence}


def heuristic_flags(movement_type: str, features: dict[str, float], gait: dict | None = None) -> list[dict]:
    """The flags that apply to this movement. `features`: the video's reliable-leg feature dict; `gait`: stored gait report."""
    out = []
    for key, f in FLAGS.items():
        if movement_type not in f["movements"]:
            continue
        value = _MEASURES[key](features, gait)
        entry = {"key": key, "label": f["label"], "unit": f["unit"], "threshold": f["threshold"],
                 "margin": f["margin"], "measure": f["measure"], "evidence": f["evidence"], "caveat": f["caveat"]}
        if value is None:
            entry |= {"status": "not_assessable", "value": None,
                      "reason": f"{f['measure']} was not measurable from this video"}
        else:
            gap = f["threshold"] - value   # all three: lower is worse
            entry |= {"value": round(value, 1),
                      "status": "flagged" if gap > f["margin"] else "borderline" if gap > 0 else "ok"}
        out.append(entry)
    if movement_type in ("running", "sprinting"):
        out.append(dict(OVERSTRIDE))
    return out


# --------------------------------------------------------------------------- #
# 4. Longitudinal athlete trend
# --------------------------------------------------------------------------- #

def athlete_trend(features: dict[str, float], priors: list[dict[str, float]]) -> dict:
    """This video's features vs the athlete's own earlier ones. `priors`: same athlete, movement and camera view, oldest first.

    Bounded: newest MAX_PRIORS videos, |z| clipped at TREND_Z_CLIP, five largest changes reported. The z scale never
    drops below the pose-model noise (set-ups differ between sessions). Descriptive only; it feeds nothing.
    """
    priors = priors[-MAX_PRIORS:]
    rows = []
    for k, v in features.items():
        vals = np.array([p[k] for p in priors if k in p], dtype=float)
        if len(vals) < MIN_PRIORS:
            continue
        med = float(np.median(vals))
        scale = max(1.4826 * float(np.median(np.abs(vals - med))), MEASUREMENT_NOISE_DEG)
        z = float(np.clip((v - med) / scale, -TREND_Z_CLIP, TREND_Z_CLIP))
        rows.append({"feature": k, "value": round(float(v), 1), "prior_median": round(med, 1),
                     "change_deg": round(float(v) - med, 1), "z": round(z, 2), "n_priors": int(len(vals))})
    if not rows:
        return _na(f"needs >= {MIN_PRIORS} earlier videos of this athlete (same movement and camera view) "
                   f"sharing a measured feature; found {len(priors)}")
    rows.sort(key=lambda r: -abs(r["z"]))
    # ponytail: priors may include a poorly visible leg (only the scored video is filtered); filter per prior if it matters
    return {
        "available": True, "n_priors": len(priors), "notable": any(abs(r["z"]) >= TREND_Z_NOTABLE for r in rows),
        "changes": rows[:5],
        "label": f"Descriptive: this video's peaks versus the athlete's own previous {len(priors)} video(s) of the same "
                 "movement and camera view. Not a risk score and not an injury prediction; a change in camera set-up "
                 "looks like a change in the athlete.",
    }
