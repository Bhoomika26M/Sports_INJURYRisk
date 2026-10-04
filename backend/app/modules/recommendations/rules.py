"""Recommendation engine — turns an assessment into specific, traceable actions.

Every recommendation is tied to a named finding (a flagged metric with its value, a score
component, an injury-category driver). Nothing generic is emitted just because a score is
high. All five spec categories are produced: exercise, mobility, strengthening, recovery
(planning) and training_modification.

Guidance text is deliberately phrased as screening suggestions for a coach/physiotherapist
to confirm — this is a decision-support tool, not a prescription. Only claims backed by
sources reviewed for this project are stated as evidence (see docs/SCIENCE_CONSTRAINTS.md).
"""

from __future__ import annotations

Z_FLAG = 2.0  # |z| at which a single metric is called out

# priority 1 = act first ... 5 = maintenance
MAX_RECOMMENDATIONS = 8


def _feat(features: list[dict], metric: str, stat: str) -> dict | None:
    for f in features:
        if f["feature"] == f"{metric}.{stat}":
            return f
    return None


def _worst(features: list[dict], metrics: tuple[str, ...], stat: str, direction: int) -> dict | None:
    cands = [f for m in metrics if (f := _feat(features, m, stat)) and f["z"] * direction >= Z_FLAG]
    return max(cands, key=lambda f: f["z"] * direction, default=None)


def _fmt(f: dict) -> str:
    return f"{f['value']:.0f}° vs population median {f['baseline_median']:.0f}° (z={f['z']:+.1f})"


def generate_recommendations(assessment: dict, movement_type: str) -> list[dict]:
    recs: list[dict] = []

    def add(category: str, priority: int, title: str, description: str):
        recs.append({"category": category, "priority": priority, "title": title[:255], "description": description})

    breakdown = assessment["score_breakdown"]
    features = assessment.get("anomaly_features", [])
    cats = assessment.get("injury_categories", {})
    sub = assessment.get("sub_scores", {})
    overall = assessment["overall_score"]

    def score(key: str) -> float | None:
        return breakdown.get(key, {}).get("score")

    knees = ("knee_flexion_angle_left", "knee_flexion_angle_right")
    hips = ("hip_flexion_angle_left", "hip_flexion_angle_right")

    # --- specific flagged movement findings --------------------------------------------
    f = _worst(features, knees, "p95", -1)
    if f:
        side = f["metric"].rsplit("_", 1)[-1]
        if movement_type in ("landing", "jumping", "cutting"):
            add("exercise", 2, "Soft-landing and depth-control drills",
                f"Peak {side} knee flexion was reduced ({_fmt(f)}). Reduced knee flexion at landing is associated with "
                "higher ACL loading (systematic review, PMC11826863). Progress landing drills from box step-downs to "
                "bilateral then single-leg landings, cueing 'land quietly, knees tracking over toes'; re-record to track change.")
        else:
            add("exercise", 3, "Depth progression (tempo / box squat)",
                f"Peak {side} knee flexion was reduced ({_fmt(f)}). Use tempo or box squats to a progressively deeper, "
                "pain-free target depth and re-record to confirm the change.")
        add("mobility", 3, "Screen ankle dorsiflexion and hip mobility",
            f"Limited peak knee flexion ({_fmt(f)}) can reflect a mobility restriction rather than a strength or "
            "technique problem. Have a physiotherapist screen ankle dorsiflexion and hip flexion range before loading deeper.")

    f = _worst(features, ("trunk_lean_angle",), "p95", +1)
    if f:
        add("strengthening", 3, "Trunk and posterior-chain control",
            f"Peak trunk lean was higher than the population ({_fmt(f)}). Add trunk-bracing and posterior-chain work "
            "(e.g. Romanian deadlifts, back extensions, front-loaded squats) and cue an upright chest. Note camera tilt "
            "adds a constant offset to trunk lean — check the video quality notes first.")
    f = _worst(features, ("trunk_lean_angle",), "p95", -1)
    if f and movement_type in ("landing", "jumping", "cutting"):
        add("exercise", 3, "Landing posture: allow trunk flexion",
            f"Peak trunk lean was lower than the population ({_fmt(f)}). Limited trunk flexion during landing/cutting is "
            "associated with higher ACL risk and lower hamstring force (reviews: PMC11826863; Hughes). Coach 'chest over knees' landings.")

    f = _worst(features, hips, "p95", -1)
    if f:
        add("mobility", 4, "Hip flexion range",
            f"Peak hip flexion was reduced ({_fmt(f)}). Include hip-flexor/hamstring/adductor mobility work and re-test range.")

    dev = score("biomechanical_deviations")
    if dev is not None and dev >= 50 and not recs:
        add("exercise", 2, "Technique review against the population pattern",
            f"The movement pattern is unusual versus other {movement_type} videos (deviation score {dev:.0f}/100) but no "
            "single joint stands out. Have a coach or physiotherapist review the clip before assuming a strength or mobility cause.")

    # --- asymmetry ---------------------------------------------------------------------
    asym = breakdown.get("movement_asymmetry", {})
    if asym.get("available") and asym["score"] >= 30:
        d = asym["detail"]
        add("strengthening", 2 if asym["score"] >= 60 else 3, "Address left/right asymmetry",
            f"Peak knee flexion differs between sides (left {d['left_peak_deg']:.0f}°, right {d['right_peak_deg']:.0f}°; "
            f"LSI {d['lsi_pct']:.0f}%). Add unilateral work (split squats, single-leg RDLs, step-ups) biased to the weaker side. "
            "The 90% LSI convention has documented limits, so use this as a re-test target, not a pass/fail.")

    # --- fatigue / drift ---------------------------------------------------------------
    fat = breakdown.get("fatigue_indicators", {})
    if fat.get("available") and fat["score"] >= 40:
        det = fat["detail"]
        if "movement_drift" in det:
            m = det["movement_drift"]
            add("training_modification", 2, "Reduce set length or add rest between sets",
                f"Movement changed by {m['drift_pct']:+.0f}% from the first to the last repetitions ({m['n_reps']} reps, "
                f"{m.get('direction') or 'changing'}), a sign of within-session technique drift. Shorten sets or lengthen "
                "rest so every repetition is performed at the quality of the first.")
        if "rpe_trend" in det:
            r = det["rpe_trend"]
            add("recovery", 2, "Plan recovery: perceived exertion is climbing",
                f"Recent sessions are rated {r['recent_mean_rpe']:.1f} RPE versus {r['baseline_mean_rpe']:.1f} over the "
                f"preceding weeks (trend {r['rpe_trend']:+.1f}). Schedule a lighter day or deload, prioritise sleep and "
                "nutrition, and re-check next week.")

    # --- training load -----------------------------------------------------------------
    load = breakdown.get("training_load_indicators", {})
    if load.get("available") and load["score"] >= 25:
        acwr = load["detail"]["acwr"]
        add("training_modification", 1 if load["score"] >= 50 else 2, "Manage training-load spike",
            f"Acute:chronic workload ratio is {acwr:.2f} (typical 0.8–1.3, elevated from 1.5; Gabbett 2016). Hold or reduce "
            "this week's volume/intensity and build back toward the chronic baseline in steps. ACWR is contested in the "
            "literature (Impellizzeri 2020) — treat it as one signal.")
        add("recovery", 3, "Recovery plan for a high-load week",
            "Add an extra rest or low-intensity day, and monitor soreness and sleep until the ratio returns to the typical range.")

    # --- injury history ----------------------------------------------------------------
    hist = breakdown.get("historical_injury_factors", {})
    unresolved = [i for i in hist.get("detail", {}).get("injuries", []) if i["status"] == "unresolved"]
    if unresolved:
        parts = ", ".join(sorted({i["body_part"] for i in unresolved}))
        add("training_modification", 1, "Coordinate loading with the treating physiotherapist",
            f"Unresolved prior injury recorded ({parts}). Agree load limits and return-to-sport criteria with the physiotherapist "
            "before progressing intensity on this movement.")
    elif hist.get("available") and hist["score"] >= 70:
        add("recovery", 3, "Keep monitoring a recently-recovered injury",
            "A relevant injury recovered within the last 24 months; prior injury is the best-evidenced risk factor for re-injury. "
            "Keep the rehabilitation strength work in the program.")

    # --- injury-category programs (only when the category is at least moderate) --------
    def cat_level(k: str) -> str:
        return cats.get(k, {}).get("level", "low")

    elevated = {"moderate", "high", "critical"}
    if cat_level("hamstring") in elevated:
        add("strengthening", 2 if cat_level("hamstring") != "moderate" else 3, "Eccentric hamstring program (Nordic hamstring exercise)",
            "Hamstring-strain risk factors are elevated. Nordic hamstring exercise programs have been associated with a "
            "substantial reduction in hamstring injury incidence in athletes who adhere to them (reviews: SAJRSPER 2018; Appl Sci 2025). "
            "Introduce progressively (1–2 sessions per week) with a physiotherapist.")
    if cat_level("acl") in elevated:
        add("exercise", 2 if cat_level("acl") != "moderate" else 3, "Neuromuscular / landing-technique program",
            "ACL-related risk factors are elevated. Combine landing-technique training, hip and hamstring strengthening and trunk "
            "control in a structured warm-up (e.g. FIFA 11+) rather than isolated drills.")
    if cat_level("ankle_sprain") in elevated:
        add("exercise", 3, "Balance and proprioception training",
            "Prior ankle injury is the strongest recorded risk factor for a further sprain (meta-analysis, PMC12031617). Include single-leg "
            "balance progressions and ankle strengthening in every warm-up and confirm bracing/taping advice with a physiotherapist.")
    if cat_level("lower_back") in elevated:
        add("strengthening", 3, "Trunk and hip strength for the lower back",
            "Lower-back risk factors are elevated (previous episode, load increase). Build trunk endurance and hip-extensor strength and "
            "avoid sudden jumps in training volume (BJSM systematic review).")
    if cat_level("shoulder") in elevated:
        add("training_modification", 3, "Manage throwing volume; rotator-cuff and scapular work",
            "Shoulder risk factors are elevated (training load and previous injury are the primary ones). Cap weekly throwing volume, "
            "ramp it gradually, and include rotator-cuff and scapular-control strengthening.")
    if cat_level("overuse") in elevated and not load.get("available"):
        add("recovery", 3, "Log training load to enable overuse monitoring",
            "Overuse risk cannot be assessed well without a training log. Record session duration and RPE for 4 weeks.")

    # --- keep it honest when there is nothing to fix -----------------------------------
    if not recs:
        add("training_modification", 5, "No deviations flagged — maintain and track",
            f"No metric, asymmetry, load or history factor stood out for this {movement_type} clip (score {overall:.0f}/100). "
            "Continue the current program and re-record periodically so the trend, not a single clip, drives decisions.")

    recs.sort(key=lambda r: r["priority"])
    seen, unique = set(), []
    for r in recs:
        if r["title"] not in seen:
            seen.add(r["title"])
            unique.append(r)
    return unique[:MAX_RECOMMENDATIONS]
