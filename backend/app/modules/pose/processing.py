"""Frame-level analysis orchestration: raw pose frames -> metrics + analysis report.

Kept free of DB/model imports so it runs identically in the worker, in the reprocess
script, and in unit tests against synthetic motion.
"""

from __future__ import annotations

import json
import logging
import math

import numpy as np

from app.modules.biomechanics.movement_analysis import analyze_movement
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


def analyze_frames(
    frame_results: list[dict],
    movement_type: str,
    camera_view: str,
    fps: float | None,
    diagnostics: dict | None = None,
) -> tuple[list[dict], dict]:
    """Raw detected frames -> (per-frame metrics, analysis report).

    `diagnostics` is the dict the pose pass filled in (total frames, lighting, whether
    contrast enhancement ran, ...). Returns ([], report-with-poor-grade) when nothing usable.
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
    movement = analyze_movement(movement_type, camera_view, series, cleaned, track.fps_eff)

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

    analysis = {
        "version": ANALYSIS_VERSION,
        "quality": quality,
        "movement": movement,
        "pipeline": {k: diagnostics.get(k) for k in ("stride", "model", "frames_read", "frame_errors") if k in diagnostics},
    }
    return metrics, _jsonable(analysis)
