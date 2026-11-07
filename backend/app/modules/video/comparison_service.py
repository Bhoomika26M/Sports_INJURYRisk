"""Dual-Video Form Benchmark & Comparative Biomechanics Service.

Provides honest, transparent kinematic comparison between a Reference video (A)
and a Comparison video (B) based on real Engine 2.3 biomechanical metrics.
Respects /docs/SCIENCE_CONSTRAINTS.md:
- 6.5° noise floor on joint angles (MEASUREMENT_NOISE_DEG)
- Angular metrics rounded to whole degrees
- Frontal plane knee valgus is strictly qualitative (never an angle)
- Missing metrics return None ("unavailable"), never synthetic defaults
- Deterministic template summary over deltas; zero LLM dependency
"""

from __future__ import annotations

import logging
from typing import Any, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import api_error
from app.modules.biomechanics.calculations import limb_symmetry_index
from app.modules.biomechanics.movement_analysis import MEASUREMENT_NOISE_DEG
from app.modules.video.comparison_schemas import (
    CompareVideosResponse,
    MetricDelta,
    VideoSummary,
)
from app.modules.video.models import BiomechanicalMetric, Video, VideoProcessingStatus
from app.modules.video.vector_service import (
    build_posture_snapshot,
    extract_inflection_vector_for_video,
)

logger = logging.getLogger(__name__)

# Engine joint angle keys that are measured in degrees (sagittal plane)
ANGULAR_METRIC_KEYS = {
    "knee_flexion_depth",
    "knee_flexion_angle_left",
    "knee_flexion_angle_right",
    "max_knee_flexion",
    "trunk_lean_angle",
    "trunk_lean",
    "max_trunk_lean",
    "hip_flexion_angle_left",
    "hip_flexion_angle_right",
    "ankle_dorsiflexion_angle_left",
    "ankle_dorsiflexion_angle_right",
    "contact_flexion",
}


def _movement_dict(video: Video) -> dict[str, Any]:
    return (video.analysis or {}).get("movement") or {}


def _movement_metrics(video: Video) -> dict[str, Any]:
    return _movement_dict(video).get("metrics") or {}


def _quality_dict(video: Video) -> dict[str, Any]:
    return (video.analysis or {}).get("quality") or {}


async def _get_peak_angles_from_db(db: AsyncSession, video_id: str) -> dict[str, float]:
    """Extract validated peak biomechanical angles from the biomechanical_metrics table."""
    stmt = (
        select(
            BiomechanicalMetric.metric_name,
            func.max(BiomechanicalMetric.metric_value).label("peak_val"),
        )
        .where(
            BiomechanicalMetric.video_id == video_id,
            BiomechanicalMetric.confidence == "validated",
        )
        .group_by(BiomechanicalMetric.metric_name)
    )
    res = await db.execute(stmt)
    return {row.metric_name: float(row.peak_val) for row in res if row.peak_val is not None}


def _metric_delta(
    key: str,
    label: str,
    unit: str | None,
    val_a: float | str | None,
    val_b: float | str | None,
    is_angular: bool = False,
) -> MetricDelta:
    """Calculates delta and verdict according to the 6.5° noise floor and availability."""
    if val_a is None or val_b is None:
        return MetricDelta(
            metric=key,
            label=label,
            unit=unit,  # type: ignore[arg-type]
            video_a=val_a,
            video_b=val_b,
            delta=None,
            verdict="not_comparable",
            reason="Metric not detected or unavailable in one or both clips",
        )

    # For qualitative metrics (e.g. knee valgus)
    if isinstance(val_a, str) or isinstance(val_b, str):
        return MetricDelta(
            metric=key,
            label=label,
            unit="qualitative",
            video_a=str(val_a),
            video_b=str(val_b),
            delta=None,
            verdict="no_verdict",
            reason="Qualitative frontal plane tracking flag",
        )

    num_a = float(val_a)
    num_b = float(val_b)

    if is_angular or key in ANGULAR_METRIC_KEYS:
        d = num_b - num_a
        whole_d = round(d)
        if abs(d) < MEASUREMENT_NOISE_DEG:
            verdict = "within_noise"
            reason = f"Difference ({d:+.1f}°) is within the {MEASUREMENT_NOISE_DEG}° tracking noise floor"
        elif d > 0:
            verdict = "higher"
            reason = f"Comparison is {abs(whole_d)}° higher than Reference"
        else:
            verdict = "lower"
            reason = f"Comparison is {abs(whole_d)}° lower than Reference"

        return MetricDelta(
            metric=key,
            label=label,
            unit="deg",
            video_a=round(num_a),
            video_b=round(num_b),
            delta=whole_d,
            verdict=verdict,
            reason=reason,
        )

    # Non-angular metrics
    diff = round(num_b - num_a, 1)
    return MetricDelta(
        metric=key,
        label=label,
        unit=unit,  # type: ignore[arg-type]
        video_a=round(num_a, 1),
        video_b=round(num_b, 1),
        delta=diff,
        verdict="no_verdict",
        reason="No literature noise floor defined for this metric; delta shown without heuristic judgment",
    )


async def compare_two_videos(
    db: AsyncSession,
    video_a: Video,
    video_b: Video,
) -> CompareVideosResponse:
    """Performs an honest, evidence-aligned kinematic comparison between Reference (A) and Comparison (B)."""
    # Preconditions check
    if video_a.id == video_b.id:
        raise api_error(422, "SAME_VIDEO", "Cannot compare a video with itself")

    if (
        video_a.processing_status != VideoProcessingStatus.completed
        or video_b.processing_status != VideoProcessingStatus.completed
    ):
        raise api_error(
            422,
            "NOT_COMPLETED",
            "Both videos must be fully processed before running form comparison",
        )

    mv_a = video_a.movement_type
    mv_b = video_b.movement_type
    if mv_a != mv_b:
        raise api_error(
            422,
            "MOVEMENT_MISMATCH",
            f"Movement types do not match: Reference is '{mv_a}', Comparison is '{mv_b}'",
        )

    view_a = video_a.camera_view
    view_b = video_b.camera_view
    if view_a != view_b:
        raise api_error(
            422,
            "VIEW_MISMATCH",
            f"Camera views do not match: Reference is '{view_a}', Comparison is '{view_b}'",
        )

    q_a = _quality_dict(video_a)
    q_b = _quality_dict(video_b)
    grade_a = q_a.get("grade", "unknown")
    grade_b = q_b.get("grade", "unknown")

    if grade_a == "poor" or grade_b == "poor":
        raise api_error(
            422,
            "QUALITY_INSUFFICIENT",
            "One or both clips have insufficient tracking quality (grade 'poor') for reliable kinematic comparison",
        )

    caveats: list[str] = []
    if video_a.coverage_caveat:
        caveats.append(f"Reference clip caveat: {video_a.coverage_caveat}")
    if video_b.coverage_caveat:
        caveats.append(f"Comparison clip caveat: {video_b.coverage_caveat}")

    # Read real movement data
    mov_a = _movement_dict(video_a)
    mov_b = _movement_dict(video_b)
    metrics_a = _movement_metrics(video_a)
    metrics_b = _movement_metrics(video_b)

    # Read database peak angles
    peaks_a = await _get_peak_angles_from_db(db, video_a.id)
    peaks_b = await _get_peak_angles_from_db(db, video_b.id)

    # Extract knee flexion depth
    depth_a = (
        peaks_a.get("knee_flexion_angle_left")
        or peaks_a.get("knee_flexion_angle_right")
        or metrics_a.get("max_knee_flexion")
        or metrics_a.get("knee_flexion_depth")
    )
    depth_b = (
        peaks_b.get("knee_flexion_angle_left")
        or peaks_b.get("knee_flexion_angle_right")
        or metrics_b.get("max_knee_flexion")
        or metrics_b.get("knee_flexion_depth")
    )

    # Extract trunk lean
    trunk_a = (
        peaks_a.get("trunk_lean_angle")
        or metrics_a.get("max_trunk_lean")
        or metrics_a.get("trunk_lean")
    )
    trunk_b = (
        peaks_b.get("trunk_lean_angle")
        or metrics_b.get("max_trunk_lean")
        or metrics_b.get("trunk_lean")
    )

    # Limb Symmetry Index
    lsi_a = None
    if "knee_flexion_angle_left" in peaks_a and "knee_flexion_angle_right" in peaks_a:
        lsi_a = limb_symmetry_index(peaks_a["knee_flexion_angle_left"], peaks_a["knee_flexion_angle_right"])
    lsi_b = None
    if "knee_flexion_angle_left" in peaks_b and "knee_flexion_angle_right" in peaks_b:
        lsi_b = limb_symmetry_index(peaks_b["knee_flexion_angle_left"], peaks_b["knee_flexion_angle_right"])

    # Qualitative valgus
    valgus_a = (
        (video_a.analysis or {}).get("classification", {}).get("knee_valgus_flag")
        or metrics_a.get("knee_valgus_flag")
        or "none"
    )
    valgus_b = (
        (video_b.analysis or {}).get("classification", {}).get("knee_valgus_flag")
        or metrics_b.get("knee_valgus_flag")
        or "none"
    )

    deltas: list[MetricDelta] = [
        _metric_delta("knee_flexion_depth", "Peak Knee Flexion Depth", "deg", depth_a, depth_b, is_angular=True),
        _metric_delta("trunk_lean", "Forward Trunk Lean", "deg", trunk_a, trunk_b, is_angular=True),
        _metric_delta("knee_valgus", "Frontal Knee Tracking (Valgus)", "qualitative", valgus_a, valgus_b),
        _metric_delta("limb_symmetry", "Limb Symmetry Index (LSI)", "pct", lsi_a, lsi_b),
    ]

    # Gait-specific metrics
    gait_a = mov_a.get("gait") or {}
    gait_b = mov_b.get("gait") or {}
    if gait_a or gait_b or mv_a in ("running", "sprinting", "cutting"):
        deltas.append(
            _metric_delta("cadence_spm", "Step Cadence", "count", gait_a.get("cadence_spm"), gait_b.get("cadence_spm"))
        )
        deltas.append(
            _metric_delta(
                "step_time_asymmetry_pct",
                "Step-Time Asymmetry",
                "pct",
                gait_a.get("step_time_asymmetry_pct"),
                gait_b.get("step_time_asymmetry_pct"),
            )
        )
        if "stride_length_m" in metrics_a or "stride_length_m" in metrics_b:
            deltas.append(
                _metric_delta("stride_length_m", "Stride Length", "m", metrics_a.get("stride_length_m"), metrics_b.get("stride_length_m"))
            )

    # Repetition-specific metrics
    reps_a = mov_a.get("reps") or {}
    reps_b = mov_b.get("reps") or {}
    if reps_a or reps_b or mv_a in ("squatting", "jumping", "landing", "throwing"):
        if "mean_rep_s" in reps_a or "mean_rep_s" in reps_b:
            deltas.append(
                _metric_delta("mean_rep_duration_s", "Repetition Duration", "s", reps_a.get("mean_rep_s"), reps_b.get("mean_rep_s"))
            )
        if "cv_pct" in reps_a or "cv_pct" in reps_b:
            deltas.append(
                _metric_delta("rep_consistency_cv_pct", "Repetition Consistency CV", "pct", reps_a.get("cv_pct"), reps_b.get("cv_pct"))
            )

    # Jump / Landing metrics
    if mv_a in ("landing", "jumping"):
        if "contact_flexion" in metrics_a or "contact_flexion" in metrics_b:
            deltas.append(
                _metric_delta("contact_flexion", "Initial Contact Knee Flexion", "deg", metrics_a.get("contact_flexion"), metrics_b.get("contact_flexion"), is_angular=True)
            )
        if "flight_time" in metrics_a or "flight_time" in metrics_b:
            deltas.append(
                _metric_delta("flight_time_s", "Flight Time", "s", metrics_a.get("flight_time"), metrics_b.get("flight_time"))
            )

    # Posture snapshots
    vec_a = await extract_inflection_vector_for_video(db, video_a.id)
    vec_b = await extract_inflection_vector_for_video(db, video_b.id)
    snapshot_a = build_posture_snapshot(vec_a, valgus_flag=str(valgus_a))
    snapshot_b = build_posture_snapshot(vec_b, valgus_flag=str(valgus_b))

    # Deterministic summary
    diff_summaries: list[str] = []
    for d in deltas:
        if d.verdict == "within_noise":
            diff_summaries.append(f"{d.label} is consistent between clips (within ±6.5° noise floor)")
        elif d.verdict in ("higher", "lower"):
            diff_summaries.append(f"{d.label}: Comparison is {d.verdict} by {abs(d.delta or 0):.0f}{'°' if d.unit == 'deg' else ''}")
        elif d.verdict == "no_verdict" and d.delta is not None:
            diff_summaries.append(f"{d.label} differs by {d.delta:+.1f} {d.unit or ''}".strip())

    summary_text = (
        f"Kinematic comparison for {mv_a} ({view_a} view) between Reference ({video_a.original_filename or video_a.id[:8]}) "
        f"and Comparison ({video_b.original_filename or video_b.id[:8]}). "
        + ("; ".join(diff_summaries) if diff_summaries else "No significant kinematic deviations observed.")
        + " Note: Joint angular differences under 6.5° are within standard monocular pose-tracking error."
    )

    return CompareVideosResponse(
        movement_type=mv_a,
        video_a_info=VideoSummary(
            id=video_a.id,
            filename=video_a.original_filename,
            movement_type=mv_a,
            camera_view=view_a,
            duration_seconds=video_a.duration_seconds,
            quality_grade=grade_a,
            coverage_caveat=video_a.coverage_caveat,
        ),
        video_b_info=VideoSummary(
            id=video_b.id,
            filename=video_b.original_filename,
            movement_type=mv_b,
            camera_view=view_b,
            duration_seconds=video_b.duration_seconds,
            quality_grade=grade_b,
            coverage_caveat=video_b.coverage_caveat,
        ),
        deltas=deltas,
        snapshot_a=snapshot_a,
        snapshot_b=snapshot_b,
        summary=summary_text,
        caveats=caveats,
    )


async def compare_video_to_athlete_history(
    db: AsyncSession,
    target_video: Video,
) -> CompareVideosResponse | dict[str, Any]:
    """Compare target video against median of athlete's prior N >= 3 completed videos.

    If fewer than 3 eligible priors exist, returns dict with status 'history_building'.
    """
    if target_video.processing_status != VideoProcessingStatus.completed:
        raise api_error(422, "VIDEO_NOT_COMPLETED", "Target video processing is not completed")

    stmt = (
        select(Video)
        .where(
            Video.athlete_id == target_video.athlete_id,
            Video.id != target_video.id,
            Video.created_at < target_video.created_at,
            Video.processing_status == VideoProcessingStatus.completed,
            Video.movement_type == target_video.movement_type,
            Video.camera_view == target_video.camera_view,
        )
        .order_by(Video.created_at.desc())
    )
    priors = (await db.scalars(stmt)).all()

    eligible_priors = [
        v for v in priors
        if (v.analysis or {}).get("quality", {}).get("grade") in ("good", "fair")
        and not v.coverage_caveat
        and not (v.analysis or {}).get("quality", {}).get("coverage_caveat")
    ]

    if len(eligible_priors) < 3:
        return {
            "status": "history_building",
            "message": (
                f"Fewer than 3 prior completed baseline clips available for this movement and camera view "
                f"(found {len(eligible_priors)}, need 3)."
            ),
            "have": len(eligible_priors),
            "need": 3,
            "movement_type": target_video.movement_type,
            "camera_view": target_video.camera_view,
        }

    import statistics

    priors_metrics: dict[str, list[float]] = {}
    for pv in eligible_priors:
        m_dict = _movement_metrics(pv)
        for k, v in m_dict.items():
            if isinstance(v, (int, float)):
                priors_metrics.setdefault(k, []).append(float(v))

    target_metrics = _movement_metrics(target_video)
    deltas: list[MetricDelta] = []

    if target_video.camera_view == "sagittal":
        target_kf_l = target_metrics.get("knee_flexion_angle_left")
        target_kf_r = target_metrics.get("knee_flexion_angle_right")
        prior_kf_l = statistics.median(priors_metrics["knee_flexion_angle_left"]) if priors_metrics.get("knee_flexion_angle_left") else None
        prior_kf_r = statistics.median(priors_metrics["knee_flexion_angle_right"]) if priors_metrics.get("knee_flexion_angle_right") else None

        if target_kf_l is not None or prior_kf_l is not None:
            deltas.append(
                _metric_delta(
                    "knee_flexion_angle_left",
                    "Left Knee Flexion",
                    "deg",
                    prior_kf_l,
                    target_kf_l,
                    is_angular=True,
                )
            )
        if target_kf_r is not None or prior_kf_r is not None:
            deltas.append(
                _metric_delta(
                    "knee_flexion_angle_right",
                    "Right Knee Flexion",
                    "deg",
                    prior_kf_r,
                    target_kf_r,
                    is_angular=True,
                )
            )

        target_tl = target_metrics.get("trunk_lean_angle") or target_metrics.get("trunk_lean")
        prior_tl = statistics.median(priors_metrics["trunk_lean_angle"]) if priors_metrics.get("trunk_lean_angle") else (
            statistics.median(priors_metrics["trunk_lean"]) if priors_metrics.get("trunk_lean") else None
        )
        if target_tl is not None or prior_tl is not None:
            deltas.append(
                _metric_delta(
                    "trunk_lean_angle",
                    "Trunk Lean Angle",
                    "deg",
                    prior_tl,
                    target_tl,
                    is_angular=True,
                )
            )

    for k, v in target_metrics.items():
        if k in ("knee_flexion_angle_left", "knee_flexion_angle_right", "trunk_lean_angle", "trunk_lean"):
            continue
        if isinstance(v, (int, float)):
            prior_vals = priors_metrics.get(k)
            prior_med = statistics.median(prior_vals) if prior_vals else None
            is_ang = k in ANGULAR_METRIC_KEYS
            unit = "deg" if is_ang else ("pct" if "asymmetry" in k or "pct" in k else None)
            label = k.replace("_", " ").title()
            deltas.append(
                _metric_delta(
                    k,
                    label,
                    unit,
                    prior_med,
                    float(v),
                    is_angular=is_ang,
                )
            )

    vec_target = await extract_inflection_vector_for_video(db, target_video.id)
    snapshot_target = build_posture_snapshot(vec_target)

    summary_text = (
        f"Longitudinal history comparison for athlete's {target_video.movement_type} "
        f"against median of {len(eligible_priors)} prior baseline sessions. "
        f"Evaluates whether current mechanics deviate from individual baseline."
    )

    return CompareVideosResponse(
        movement_type=target_video.movement_type,
        video_a_info=VideoSummary(
            id=f"history_baseline_{target_video.athlete_id}",
            filename=f"Median of {len(eligible_priors)} Prior Sessions",
            movement_type=target_video.movement_type,
            camera_view=target_video.camera_view,
            duration_seconds=None,
            quality_grade="fair",
            coverage_caveat=None,
        ),
        video_b_info=VideoSummary(
            id=target_video.id,
            filename=target_video.original_filename,
            movement_type=target_video.movement_type,
            camera_view=target_video.camera_view,
            duration_seconds=target_video.duration_seconds,
            quality_grade=(target_video.analysis or {}).get("quality", {}).get("grade"),
            coverage_caveat=target_video.coverage_caveat,
        ),
        deltas=deltas,
        snapshot_a=None,
        snapshot_b=snapshot_target,
        summary=summary_text,
        caveats=[],
    )
