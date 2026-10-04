"""Per-injury-type risk assessment — the six categories named in the spec.

ACL, hamstring strain, ankle sprain, shoulder, lower back, overuse. Each is a weighted mean of
named DRIVERS, every driver carrying its evidence level. The design follows what the research
actually supports, which is lopsided:

* Prior injury of the same region is the best-evidenced risk factor for ankle sprain (26-study
  meta-analysis), hamstring strain, low back pain (pooled OR 3.5) and shoulder injury; training
  load and load spikes matter for back and shoulder. These drivers are available for EVERY
  movement, without a baseline.
* Video kinematics have real support mainly for ACL loading (decreased knee flexion, limited
  trunk flexion, knee valgus — the last only as a qualitative flag here). For hamstring,
  ankle and shoulder, single kinematic variables are reported as inconsistent or unvalidated
  from a single camera, so NO video driver is used for them and the result says so.

Output is a risk LEVEL built from named factors, never an injury probability.
"""

from __future__ import annotations

from app.modules.risk_scoring.scoring import (
    HISTORY_LEVELS,
    Component,
    _ramp,
    categorize,
)

# z at which a deviation in the risky direction starts to count / counts fully.
KIN_Z_START, KIN_Z_FULL = 1.0, 3.0
VALGUS_FLAG_PCT = 10.0  # same qualitative threshold as biomechanics.calculations.knee_valgus_flag

CATEGORIES = {
    "acl": {
        "label": "ACL injury",
        "video_movements": {"squatting", "landing", "jumping", "cutting"},
        "evidence": [
            "Decreased knee flexion increases ACL loading; limited trunk flexion and increased "
            "medial knee alignment are associated with higher risk (systematic review, PMC11826863).",
            "Knee valgus is a trainable factor but causal strength is limited by study heterogeneity "
            "(Arch Rehabil 2026); shown here as a qualitative flag only.",
        ],
    },
    "hamstring": {
        "label": "Hamstring strain",
        "video_movements": set(),
        "evidence": [
            "Previous hamstring injury, age and thigh-muscle imbalance are the recurring risk factors; "
            "single kinematic variables are inconsistently associated (BJSM meta-analysis).",
        ],
    },
    "ankle_sprain": {
        "label": "Ankle sprain",
        "video_movements": set(),
        "evidence": [
            "A history of ankle sprain is the most significant risk factor for future sprains "
            "(meta-analysis of 26 studies, PMC12031617). Ankle kinematics are not validated from one camera.",
        ],
    },
    "shoulder": {
        "label": "Shoulder injury",
        "video_movements": {"throwing"},
        "evidence": [
            "Range of motion, strength, previous injury and training load are the primary risk factors "
            "in athletes (prospective-studies systematic review).",
        ],
    },
    "lower_back": {
        "label": "Lower back",
        "video_movements": {"squatting", "running", "sprinting", "landing", "jumping", "cutting"},
        "evidence": [
            "A previous episode (pooled OR 3.5), high training volume and periods of load increase are "
            "the common risk factors (BJSM systematic review with meta-analysis).",
        ],
    },
    "overuse": {
        "label": "Overuse / load-related",
        "video_movements": set(),
        "evidence": [
            "Acute:chronic load spikes and accumulating perceived exertion are the load-management "
            "signals; ACWR is contested (Impellizzeri 2020) and used as one input.",
        ],
    },
}


def _history_driver(injuries: list[dict], region: str | None) -> tuple[float, dict]:
    """0 when no injury recorded for the region; otherwise the highest recency/status level."""
    mine = [i for i in injuries if i["region"] == region]
    if not mine:
        return 0.0, {"note": "no prior injury recorded for this region"}
    score = max(HISTORY_LEVELS[("relevant", i["status"])] for i in mine)
    return score, {"injuries": [{"body_part": i["body_part"], "status": i["status"]} for i in mine]}


def _kinematic_driver(features: list[dict], metrics: tuple[str, ...], stat: str, direction: int) -> tuple[float | None, dict]:
    """Worst deviation in the risky `direction` (+1 above baseline, -1 below) among `metrics`."""
    zs = [
        (f["z"] * direction, f)
        for f in features
        for m in metrics
        if f["feature"] == f"{m}.{stat}"
    ]
    if not zs:
        return None, {}
    z, f = max(zs, key=lambda t: t[0])
    return _ramp(z, KIN_Z_START, KIN_Z_FULL), {
        "feature": f["feature"], "value": f["value"], "baseline_median": f["baseline_median"], "z": f["z"],
    }


def assess_injury_categories(
    *,
    movement_type: str,
    anomaly: dict | None,
    injuries: list[dict],
    components: dict[str, Component],
    qualitative: dict[str, float] | None,
) -> dict:
    """`injuries`: score_history detail rows (body_part, region, status, ...)."""
    feats = anomaly["features"] if anomaly else []
    load = components.get("training_load_indicators")
    fatigue = components.get("fatigue_indicators")
    asym = components.get("movement_asymmetry")
    qualitative = qualitative or {}

    def comp_driver(c: Component | None) -> float | None:
        return c.score if c is not None and c.available else None

    out = {}
    for key, meta in CATEGORIES.items():
        video_on = movement_type in meta["video_movements"]
        drivers: list[dict] = []

        def add(name: str, score: float | None, weight: float, source: str, detail: dict | None = None):
            if score is None:
                return
            drivers.append({"factor": name, "score": round(score, 1), "weight": weight,
                            "source": source, **({"detail": detail} if detail else {})})

        if key == "acl":
            s, d = _history_driver(injuries, "knee"); add("prior knee injury", s, 3.0, "history", d)
            if video_on:
                s, d = _kinematic_driver(feats, ("knee_flexion_angle_left", "knee_flexion_angle_right"), "p95", -1)
                add("reduced peak knee flexion", s, 2.0, "video", d)
                s, d = _kinematic_driver(feats, ("trunk_lean_angle",), "p95", -1)
                add("limited trunk flexion", s, 1.0, "video", d)
                valgus = [v for k, v in qualitative.items() if k.startswith("knee_valgus")]
                if valgus:
                    add("knee valgus flag (qualitative)", 100.0 if max(valgus) >= VALGUS_FLAG_PCT else 0.0, 1.0, "video",
                        {"max_deviation_pct": round(max(valgus), 1), "note": "visual flag, not an angle"})
                add("left/right asymmetry", comp_driver(asym), 1.0, "video")
        elif key == "hamstring":
            s, d = _history_driver(injuries, "hamstring"); add("prior hamstring/thigh injury", s, 3.0, "history", d)
            add("training-load spike (ACWR)", comp_driver(load), 1.5, "training_load")
            add("left/right asymmetry (kinematic proxy)", comp_driver(asym), 1.0, "video")
            add("fatigue indicators", comp_driver(fatigue), 1.0, "fatigue")
        elif key == "ankle_sprain":
            s, d = _history_driver(injuries, "ankle"); add("prior ankle injury", s, 4.0, "history", d)
            add("training-load spike (ACWR)", comp_driver(load), 1.0, "training_load")
            add("fatigue indicators", comp_driver(fatigue), 0.5, "fatigue")
        elif key == "shoulder":
            s, d = _history_driver(injuries, "shoulder"); add("prior shoulder/elbow injury", s, 3.0, "history", d)
            add("throwing-load spike (ACWR)", comp_driver(load), 2.0, "training_load")
            if video_on:
                s, d = _kinematic_driver(feats, ("trunk_rotation",), "p95", +1)
                add("trunk rotation above baseline", s, 1.0, "video", d)
            add("fatigue indicators", comp_driver(fatigue), 0.5, "fatigue")
        elif key == "lower_back":
            s, d = _history_driver(injuries, "lower_back"); add("prior back injury", s, 3.0, "history", d)
            add("training-load increase (ACWR)", comp_driver(load), 2.0, "training_load")
            if video_on:
                up, du = _kinematic_driver(feats, ("trunk_lean_angle",), "p95", +1)
                dn, dd = _kinematic_driver(feats, ("trunk_lean_angle",), "p95", -1)
                if up is not None and dn is not None:
                    add("trunk lean outside baseline range", max(up, dn), 1.0, "video", du if up >= dn else dd)
            add("fatigue indicators", comp_driver(fatigue), 0.5, "fatigue")
        elif key == "overuse":
            add("training-load spike (ACWR)", comp_driver(load), 3.0, "training_load")
            add("fatigue indicators", comp_driver(fatigue), 2.0, "fatigue")
            unresolved = [i for i in injuries if i["status"] == "unresolved"]
            add("unresolved prior injury", (100.0 if unresolved else 0.0), 1.0, "history")

        if drivers:
            total_w = sum(d["weight"] for d in drivers)
            risk = sum(d["score"] * d["weight"] for d in drivers) / total_w
            sources = sorted({d["source"] for d in drivers})
            out[key] = {
                "label": meta["label"],
                "risk_score": round(risk, 1),
                "level": categorize(risk),
                "drivers": sorted(drivers, key=lambda d: d["score"] * d["weight"], reverse=True),
                "based_on": sources,
                "video_kinematics_used": video_on and any(d["source"] == "video" for d in drivers),
                "evidence": meta["evidence"],
            }
        else:
            out[key] = {
                "label": meta["label"], "risk_score": None, "level": "insufficient_data",
                "drivers": [], "based_on": [], "video_kinematics_used": False, "evidence": meta["evidence"],
            }
    return out
