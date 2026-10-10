"""Frame-level analysis orchestration: raw pose frames -> metrics + analysis report.

Kept free of DB/model imports so it runs identically in the worker, in the reprocess
script, and in unit tests against synthetic motion.
"""

from __future__ import annotations

import json
import logging
import math

import numpy as np

from app.modules.biomechanics.classification import (
    AUTO, CLASSIFICATION_VERSION, WARN_MIN_CONF, classify_movement, compare_labels,
)
from app.modules.biomechanics.movement_analysis import GAIT_MOVEMENTS, analyze_movement
from app.modules.biomechanics.registry import get_calculator
from app.modules.pose.analysis import (
    Track,
    build_track,
    clean_track,
    frames_for_metrics,
    quality_report,
)

logger = logging.getLogger(__name__)

ANALYSIS_VERSION = 1


def compute_biomechanics(frame_results: list[dict], calculator, camera_view: str) -> list[dict]:
    """Compute biomechanics using the movement-type-specific calculator.

    Landmarks the cleaning stage marked unusable arrive as NaN; any metric that depends on
    them comes out non-finite and is DROPPED here — a missing measurement must never be
    stored as a value.
    """
    metrics = []
    failed_frames = 0
    dropped_non_finite = 0

    for fr in frame_results:
        landmarks = fr["world_landmarks"]
        f_num = fr["frame_number"]

        try:
            frame_metrics = calculator.compute_all(landmarks, camera_view)
        except KeyError as e:
            failed_frames += 1
            logger.warning(f"Frame {f_num}: missing landmark {e}, skipping this frame's biomechanics")
            continue
        for m in frame_metrics:
            v = m.get("value")
            if v is None or not math.isfinite(v):
                dropped_non_finite += 1
                continue
            m["frame_number"] = f_num
            metrics.append(m)

    if failed_frames:
        logger.info(f"compute_biomechanics: {failed_frames}/{len(frame_results)} frames had missing landmarks")
    if dropped_non_finite:
        logger.info(f"compute_biomechanics: dropped {dropped_non_finite} non-finite metric values (occluded landmarks)")
    if not metrics and frame_results:
        logger.warning(f"compute_biomechanics produced ZERO metrics from {len(frame_results)} frames")

    return metrics


def _dense_series(metrics: list[dict], track: Track) -> dict[str, np.ndarray]:
    """{metric_name: values on the track's uniform grid}, gaps linearly interpolated.

    Only validated metrics: qualitative ones are visual flags and never drive analysis.
    """
    by_name: dict[str, list[tuple[int, float]]] = {}
    for m in metrics:
        if m["confidence"] != "validated":
            continue
        by_name.setdefault(m["name"], []).append((m["frame_number"], m["value"]))
    out = {}
    for name, pairs in by_name.items():
        if len(pairs) < 2:
            continue
        pairs.sort()
        f = np.array([p[0] for p in pairs], dtype=float)
        v = np.array([p[1] for p in pairs], dtype=float)
        out[name] = np.interp(track.grid, f, v)
    return out


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.floating, float)):
        return None if not math.isfinite(float(o)) else float(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.bool_,)):
        return bool(o)
    return o


def identify_labels(frame_results: list[dict], fps: float | None) -> tuple[str, str] | None:
    """(movement_type, camera_view) the footage itself shows, for an upload that declared none (AUTO); else None.

    Both verdicts must clear WARN_MIN_CONF: a guess that is not sure would put the clip in the wrong baseline, so
    it fails instead. The classifier caps jumping / landing / cutting below that bar, so those are always chosen by hand.
    """
    track = build_track(frame_results, fps)
    if track is None:
        return None
    c = classify_movement(clean_track(track), None, track.fps_eff)
    if "unknown" in (c["movement_type"], c["camera_view"]) or c["confidence"] < WARN_MIN_CONF:
        return None
    return c["movement_type"], c["camera_view"]


def analyze_frames(
    frame_results: list[dict],
    movement_type: str,
    camera_view: str,
    fps: float | None,
    diagnostics: dict | None = None,
    auto: bool = False,
) -> tuple[list[dict], dict]:
    """Raw detected frames -> (per-frame metrics, analysis report).

    `diagnostics` is the dict the pose pass filled in (total frames, lighting, whether
    contrast enhancement ran, ...). Returns ([], report-with-poor-grade) when nothing usable.
    `auto`: the labels were identified from the footage (identify_labels), not declared, so there is nothing to agree with.
    """
    diagnostics = diagnostics or {}
    track = build_track(frame_results, fps)
    if track is None:
        return [], {"version": ANALYSIS_VERSION, "quality": {"grade": "poor", "warnings": [
            {"code": "no_pose_data", "message": "No pose data was available to analyse."}]}}

    cleaned = clean_track(track, movement_type)
    frames = frames_for_metrics(track, cleaned)
    metrics = compute_biomechanics(frames, get_calculator(movement_type), camera_view)

    validated = [m for m in metrics if m["confidence"] == "validated"]
    series = _dense_series(metrics, track)
    # gait amplitude (stride length, overstride) is read off peaks the despike would clip: give it a track without that pass
    amp = clean_track(track, movement_type, despike=False) if movement_type in GAIT_MOVEMENTS else None
    movement = analyze_movement(movement_type, camera_view, series, cleaned, track.fps_eff, amp)

    quality = quality_report(
        track, cleaned,
        movement_type=movement_type,
        camera_view=camera_view,
        n_total_frames=diagnostics.get("frames_processed"),
        lighting=diagnostics.get("lighting"),
        clahe_applied=bool(diagnostics.get("contrast_enhanced")),
        has_validated_metrics=bool(validated),
    )
    # movement-level warnings (mislabelled clip, no reps, no stride) belong in the same list
    quality["warnings"].extend(movement.pop("warnings", []))
    if movement_type and any(w["code"] == "movement_type_mismatch_suspected" for w in quality["warnings"]):
        if quality["grade"] == "good":
            quality["grade"] = "fair"

    # What does the clip actually show? Identified from kinematics on a LABEL-NEUTRAL cleaning pass, so the
    # verdict can't be shaped by the label it checks. Advisory: suggests and warns, never relabels or rescores.
    classification = classify_movement(clean_track(track), series, track.fps_eff)
    labels = compare_labels(classification, movement_type, camera_view)
    if auto:  # nothing was declared, so nothing can disagree: the verdict IS the label (the UI says so)
        none = {"movement_type": None, "camera_view": None}
        labels = {"declared": {"movement_type": AUTO, "camera_view": AUTO}, "agrees": dict(none), "suggested": dict(none),
                  "warnings": []}
    legacy_mismatch = any(w["code"] == "movement_type_mismatch_suspected" for w in quality["warnings"])
    # one problem, one warning: the stride-in-a-rep-clip warning above already says it
    quality["warnings"].extend(w for w in labels.pop("warnings")
                               if not (legacy_mismatch and w["code"] == "classifier_movement_mismatch_suspected"))

    analysis = {
        "version": ANALYSIS_VERSION,
        "quality": quality,
        "movement": movement,
        "classification": {"version": CLASSIFICATION_VERSION, **classification, **labels},
        "pipeline": {k: diagnostics.get(k) for k in ("stride", "model", "frames_read", "frame_errors") if k in diagnostics},
    }
    return metrics, _jsonable(analysis)
