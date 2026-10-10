"""What does this clip show, and from which side was it filmed? (pure numpy: no DB, no model)

`classify_movement` infers movement type and camera view from kinematics alone - never from the label
the uploader chose - so the two can be compared (`compare_labels`). It SUGGESTS and WARNS; it never
changes a label or a metric.

Every threshold below is an engineering heuristic, NOT a validated cut-off: no labelled real footage
was available, only synthetic motion (tests/synth.py). `confidence` is a rule-agreement score in
[0, 1] - not a probability - and says nothing about injury.

Known ceiling: MediaPipe world landmarks are hip-CENTRED, so global hip height, take-off and flight
time are discarded before this module sees them. Jump vs landing therefore rests on knee tempo alone
and is capped at WEAK_CAP, as is cutting (inferred from pelvis heading change alone).
"""

from __future__ import annotations

import numpy as np

from app.modules.biomechanics.calculations import LANDMARK
from app.modules.biomechanics.movement_analysis import MIN_FRAMES, _smooth, analyze_gait, detect_reps_detailed

CLASSIFICATION_VERSION = 1

# A movement-label mismatch only WARNS across groups; inside a group the evidence is too weak.
GROUP = {"running": "gait", "sprinting": "gait", "cutting": "gait", "squatting": "squat",
         "jumping": "explosive", "landing": "explosive", "throwing": "throw"}

SUGGEST_MIN_CONF, WARN_MIN_CONF, WEAK_CAP = 0.5, 0.7, 0.6
AUTO = "auto"   # an upload that declared neither label: the footage decides (processing.identify_labels), or the upload fails
SAGITTAL_MAX_DEG, FRONTAL_MIN_DEG = 30.0, 60.0   # hip line vs camera depth axis (0 = side-on)
LEG_RANGE_DEG = 15.0        # a knee must flex this much for the left/right phase test to mean anything
FAST_DEG_S = (250.0, 400.0)  # peak knee speed: slow squat ... explosive jump/landing (ramp)
LANDING_ASYM = 0.3           # (flexion - extension speed) / (sum): a landing absorbs fast and recovers slowly
CUT_TURN_DEG = (45.0, 75.0)  # pelvis heading change over the clip (ramp)
THROW_ROT_DEG = (40.0, 70.0)  # smoothed shoulder-vs-pelvis yaw swing (ramp)


def _ramp(x: float, lo: float, hi: float) -> float:
    return float(np.clip((x - lo) / (hi - lo), 0.0, 1.0))


def _range(v: np.ndarray) -> float:
    return float(np.subtract(*np.percentile(v, [95, 5])))


def _fill(v: np.ndarray) -> np.ndarray | None:
    """Linearly interpolate NaNs; None when under 60% of the frames are usable."""
    ok = np.isfinite(v)
    if ok.sum() < max(MIN_FRAMES, 0.6 * len(v)):
        return None
    return np.interp(np.arange(len(v)), np.flatnonzero(ok), v[ok])


def _knee(xyz: np.ndarray, side: str) -> np.ndarray:
    """Knee flexion (deg, 0 = straight) per frame; same convention as calculations.knee_flexion_angle."""
    hip, knee, ankle = (xyz[:, LANDMARK[f"{side}_{j}"]] for j in ("hip", "knee", "ankle"))
    a, b = hip - knee, ankle - knee
    den = np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        cos = np.einsum("ij,ij->i", a, b) / np.where(den > 0, den, np.nan)
    return 180.0 - np.degrees(np.arccos(np.clip(cos, -1, 1)))


def _ground(xyz: np.ndarray, frm: str, to: str) -> np.ndarray:
    """Vector frm -> to projected on the ground plane (x, z); +Y is down in world landmarks."""
    return (xyz[:, LANDMARK[to]] - xyz[:, LANDMARK[frm]])[:, [0, 2]]


def _phase(kl: np.ndarray | None, kr: np.ndarray | None) -> float | None:
    """Left/right knee correlation: +1 in phase (squat, jump), -1 anti-phase (gait). None if a leg barely flexes."""
    if kl is None or kr is None or min(_range(kl), _range(kr)) < LEG_RANGE_DEG:
        return None
    n = min(len(kl), len(kr))
    return float(np.corrcoef(kl[:n], kr[:n])[0, 1])


def _rotation(xyz: np.ndarray, fps: float) -> float:
    """Swing (deg) of the signed shoulder-line vs hip-line yaw after a ~0.2 s moving average: a real trunk
    rotation is a smooth swing, depth-axis noise is white and averages away."""
    hv, sv = _ground(xyz, "left_hip", "right_hip"), _ground(xyz, "left_shoulder", "right_shoulder")
    rel = _fill(np.degrees(np.arctan2(hv[:, 0] * sv[:, 1] - hv[:, 1] * sv[:, 0], (hv * sv).sum(1))))
    return 0.0 if rel is None else _range(_smooth(rel, 2 * round(0.1 * fps) + 1))


def _turn(xyz: np.ndarray) -> float:
    """Pelvis heading change (deg, 0-180) between the first and last quarter of the clip."""
    h = _ground(xyz, "left_hip", "right_hip")
    h = h[np.isfinite(h).all(axis=1)]
    if len(h) < MIN_FRAMES:
        return 0.0
    q = max(3, len(h) // 4)

    def heading(s):
        return np.degrees(np.arctan2(s[:, 1].mean(), s[:, 0].mean()))

    return float(abs((heading(h[-q:]) - heading(h[:q]) + 180) % 360 - 180))


def _travel_deg(xyz: np.ndarray) -> float | None:
    """Direction of the ankle-separation oscillation (= direction of travel), as an angle from the camera
    x axis (0 = across the image = side-on). Same PCA as movement_analysis.analyze_gait."""
    sep = _ground(xyz, "right_ankle", "left_ankle")
    sep = sep[np.isfinite(sep).all(axis=1)]
    if len(sep) < MIN_FRAMES:
        return None
    axis = np.linalg.svd(sep - sep.mean(axis=0), full_matrices=False)[2][0]
    return float(np.degrees(np.arctan2(abs(axis[1]), abs(axis[0]))))


def _peak_speeds(k: np.ndarray, fps: float) -> tuple[float, float]:
    """(flexion, extension) peak knee speed, deg/s: 98th percentile of the change over ~0.2 s windows
    (windowed, so frame-to-frame jitter does not read as speed)."""
    w = 2 * max(1, round(0.1 * fps))
    if len(k) <= w:
        return 0.0, 0.0
    v = (k[w:] - k[:-w]) * fps / w
    return float(np.percentile(v, 98)), float(np.percentile(-v, 98))


def _view(xyz: np.ndarray | None, travel: float | None) -> tuple[str, float, dict]:
    """Camera view from the hip line's angle to the camera depth axis (hip width lies along depth when
    side-on, across the image when head-on); the ankle-travel axis, when there is a gait, cross-checks it."""
    hip = _ground(xyz, "left_hip", "right_hip") if xyz is not None else np.empty((0, 2))
    hip = hip[np.isfinite(hip).all(axis=1)]
    if len(hip) < MIN_FRAMES:
        return "unknown", 0.0, {"hip_axis_deg": None, "travel_axis_deg": None, "spread_deg": None, "confidence": 0.0}
    a = np.degrees(np.arctan2(np.abs(hip[:, 0]), np.abs(hip[:, 1])))
    alpha, spread = float(np.median(a)), float(np.subtract(*np.percentile(a, [75, 25])))
    if alpha <= SAGITTAL_MAX_DEG:
        view, margin = "sagittal", SAGITTAL_MAX_DEG - alpha
    elif alpha >= FRONTAL_MIN_DEG:
        view, margin = "frontal", alpha - FRONTAL_MIN_DEG
    else:
        view, margin = "other", min(alpha - SAGITTAL_MAX_DEG, FRONTAL_MIN_DEG - alpha)
    conf = _ramp(margin, 0, 15) * (1 - _ramp(spread, 20, 60))
    if travel is not None:  # a forward-moving athlete's travel axis is perpendicular to the hip line
        conf *= 1 - _ramp(abs(alpha - travel), 30, 70)
    ev = {"hip_axis_deg": round(alpha, 1), "travel_axis_deg": None if travel is None else round(travel, 1),
          "spread_deg": round(spread, 1), "confidence": round(conf, 2)}
    return view, conf, ev


def classify_movement(xyz: np.ndarray | None, series: dict | None, fps: float | None) -> dict:
    """{movement_type, camera_view, confidence, evidence} from kinematics alone.

    `xyz`: cleaned [T,33,3] world landmarks (NaN allowed). `series`: validated metric series, used ONLY
    as a fallback source of knee flexion when `xyz` is unusable (they depend on the declared label, so
    they are never preferred). movement_type is one of the 7 registry types or "unknown"; camera_view
    is sagittal / frontal / other / "unknown". `confidence` = the weaker of the two verdicts (0 if
    either is unknown); the per-verdict values live in `evidence`.
    """
    series = series or {}
    have_xyz = (xyz is not None and getattr(xyz, "ndim", 0) == 3 and xyz.shape[1] >= 33
                and len(xyz) >= MIN_FRAMES)
    xyz = xyz if have_xyz else None
    if not (fps and fps > 0):
        xyz = None
    if xyz is not None:
        kl, kr = (_fill(_knee(xyz, s)) for s in ("left", "right"))
    else:
        kl, kr = (_fill(np.asarray(series[k], float)) if k in series else None
                  for k in ("knee_flexion_angle_left", "knee_flexion_angle_right"))

    gait = analyze_gait(xyz, fps) if xyz is not None else None
    corr = _phase(kl, kr)
    knees = [k for k in (kl, kr) if k is not None]
    knee = np.mean([k[:min(map(len, knees))] for k in knees], axis=0) if knees and fps and fps > 0 else None
    reps = detect_reps_detailed(knee) if knee is not None else []
    rot = _rotation(xyz, fps) if xyz is not None else 0.0

    # one rule-agreement score per candidate group of movements
    throw_c = _ramp(rot, *THROW_ROT_DEG)
    gait_c = 0.0 if gait is None else _ramp(gait["n_steps"], 3, 8) * (0.7 if corr is None else _ramp(-corr, 0, 0.5))
    rep_c = 0.0 if not reps else _ramp(_range(knee), 20, 40) * (0.7 if corr is None else _ramp(corr, 0, 0.5))
    scores = {"throw": throw_c, "gait": gait_c, "rep": rep_c}
    best = max(scores, key=scores.get)
    second = sorted(scores.values())[-2]
    top = scores[best]
    lead = 1 - 0.5 * second / top if top > 0 else 0.0  # a close runner-up (javelin run-up) halves the claim

    mv, mc, gc, reason = "unknown", 0.0, 0.0, "no gait, repetition or trunk-rotation pattern found"
    ev = {"branch": None, "n_steps": None, "cadence_spm": None, "knee_lr_corr": None, "heading_change_deg": None,
          "n_reps": len(reps), "knee_range_deg": None, "peak_knee_speed_deg_s": None,
          "flexion_extension_asymmetry": None, "trunk_rotation_range_deg": round(rot, 1),
          "scores": {k: round(v, 2) for k, v in scores.items()}}
    if corr is not None:
        ev["knee_lr_corr"] = round(corr, 2)

    # gc = how sure we are of the GROUP (gait / squat / explosive / throw); mc = how sure of the exact type
    if top >= 0.2:
        ev["branch"] = best
        if best == "throw":
            mv, gc = "throwing", throw_c * lead
            mc = gc
            reason = f"{rot:.0f} deg shoulder-vs-pelvis rotation swing"
        elif best == "gait":
            cad, turn = gait["cadence_spm"], _turn(xyz)
            cut = _ramp(turn, *CUT_TURN_DEG)
            sprint = _ramp(cad, 170, 230)  # 0 = running ... 1 = sprinting, 0.5 at 200 steps/min
            cand = {"running": _ramp(cad, 115, 140) * (1 - sprint) * (1 - cut),
                    "sprinting": sprint * (1 - cut), "cutting": cut}
            mv = max(cand, key=cand.get)
            gc = gait_c * lead
            mc = gc * max(cand[mv] - 0.5 * sorted(cand.values())[-2], 0.0)
            if mv == "cutting":
                mc = min(mc, WEAK_CAP)  # ponytail: heading change is the only cutting cue; add plant-knee evidence to lift the cap
            ev.update(n_steps=gait["n_steps"], cadence_spm=cad, heading_change_deg=round(turn, 1))
            reason = f"{gait['n_steps']} alternating steps at {cad:.0f} steps/min"
        else:
            flex, ext = _peak_speeds(knee, fps)
            speed = max(flex, ext)
            fast = _ramp(speed, *FAST_DEG_S)
            asym = (flex - ext) / (flex + ext) if flex + ext > 0 else 0.0
            if fast < 0.5:
                mv, gc = "squatting", rep_c * lead * (1 - fast)
                mc = gc
                reason = f"{len(reps)} slow knee-flexion repetition(s), peak knee speed {speed:.0f} deg/s"
            else:  # a jump clip holds a take-off AND a landing, so it reads symmetric; a lone landing does not
                mv, gc = ("landing" if asym > LANDING_ASYM else "jumping"), rep_c * lead * fast
                mc = min(WEAK_CAP, gc) * _ramp(abs(asym - LANDING_ASYM), 0, 0.2)
                reason = f"fast knee flexion (peak {speed:.0f} deg/s) with {len(reps)} repetition(s)"
            ev.update(knee_range_deg=round(_range(knee), 1), peak_knee_speed_deg_s=round(speed, 1),
                      flexion_extension_asymmetry=round(asym, 2))
    if mc <= 0:  # a winner with no support is not a verdict
        mv, gc = "unknown", 0.0
    ev.update(confidence=round(float(mc), 2), group_confidence=round(float(gc), 2), reason=reason)

    view, vc, view_ev = _view(xyz, _travel_deg(xyz) if gait is not None else None)
    return {
        "movement_type": mv,
        "camera_view": view,
        "confidence": round(float(min(mc, vc)), 2),
        "evidence": {"movement": ev, "view": view_ev},
    }


def compare_labels(classification: dict, movement_type: str | None, camera_view: str | None) -> dict:
    """Declared labels vs the classifier's verdict. Advisory only: nothing here is ever applied.

    agrees: True (matches), False (confidently different -> a warning), None (can't tell). A movement
    warning needs the GROUP to differ (gait / squat / jump-landing / throw) with WARN_MIN_CONF in the group;
    `suggested` carries the classifier's exact value wherever it differs with at least SUGGEST_MIN_CONF.
    """
    ev = classification["evidence"]
    mv, mc = classification["movement_type"], ev["movement"]["confidence"]
    cv, vc = classification["camera_view"], ev["view"]["confidence"]
    agrees: dict = {"movement_type": None, "camera_view": None}
    suggested: dict = {"movement_type": None, "camera_view": None}
    warnings: list[dict] = []

    if movement_type in GROUP and mv != "unknown":
        gc = ev["movement"]["group_confidence"]
        if mv == movement_type:
            agrees["movement_type"] = True if mc >= SUGGEST_MIN_CONF else None
        else:
            suggested["movement_type"] = mv if mc >= SUGGEST_MIN_CONF else None
            if gc >= WARN_MIN_CONF and GROUP[mv] != GROUP[movement_type]:
                agrees["movement_type"] = False
                what = mv if mc >= SUGGEST_MIN_CONF else "/".join(t for t, g in GROUP.items() if g == GROUP[mv])
                warnings.append({
                    "code": "classifier_movement_mismatch_suspected",
                    "message": f"This clip is labelled '{movement_type}' but its motion looks like '{what}' "
                               f"({ev['movement']['reason']}). The label was kept; check it before trusting "
                               "this video's metrics or adding it to a baseline.",
                })
    if camera_view in ("sagittal", "frontal", "other") and cv != "unknown":
        if cv == camera_view:
            agrees["camera_view"] = True if vc >= SUGGEST_MIN_CONF else None
        else:
            suggested["camera_view"] = cv if vc >= SUGGEST_MIN_CONF else None
            if vc >= WARN_MIN_CONF and camera_view != "other":  # "other" claims nothing to contradict
                agrees["camera_view"] = False
                warnings.append({
                    "code": "classifier_camera_view_mismatch_suspected",
                    "message": f"This clip is labelled '{camera_view}' but the body orientation looks '{cv}' "
                               f"(hip line {ev['view']['hip_axis_deg']:.0f} deg from the camera's depth axis; "
                               "0 = side-on, 90 = head-on). The label was kept and metrics follow it; "
                               "validated joint angles need a genuinely side-on view.",
                })
    return {"declared": {"movement_type": movement_type, "camera_view": camera_view},
            "agrees": agrees, "suggested": suggested, "warnings": warnings}
