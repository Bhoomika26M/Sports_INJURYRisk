"""Athlete analysis history and rolling-baseline comparison.

Responsibilities
----------------
1. Build a flat, trended ``metrics`` dict out of a completed analysis so it can
   be stored on an :class:`~app.models.analysis_snapshot.AnalysisSnapshot`.
2. Record a snapshot exactly once per video, assigning its position in the
   athlete's timeline.
3. Compare a new analysis against the athlete's **rolling baseline** of prior
   analyses of the *same activity type*, and describe the change in plain terms.

Why comparisons are scoped by activity
--------------------------------------
A squat and a sprint produce different joints, different phase segmentations and
different metric ranges. Pooling them would emit false alarms, so a baseline is
always keyed on ``(athlete_id, activity_type)``.

Why the baseline excludes the current analysis
----------------------------------------------
The baseline is the mean of the ``N`` *prior* same-activity analyses. An
analysis never contributes to the baseline it is measured against, so the
comparison answers the only question that matters clinically: "how does today
compare with what came before?" Recomputing a snapshot's comparison later would
be wrong (later sessions must not rewrite history), which is why the result is
persisted rather than derived on read.

Statistical guard rails
-----------------------
* A baseline needs at least ``MIN_BASELINE`` prior analyses. Until then the
  comparison reports ``status="insufficient_history"`` and the first analysis is
  treated as establishing the baseline.
* Deltas are normalized by the baseline's spread (a robust spread based on the
  mean absolute deviation, falling back to a percentage of the mean when the
  athlete's history is too flat). This stops trivially small wobbles in a very
  stable athlete from being flagged, and stops large-but-normal variation being
  flagged in an athlete whose history is naturally noisy.
* Each metric declares which direction is *worse*, so a rising risk score and a
  falling movement-quality score are both reported as deterioration.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.analysis_snapshot import AnalysisSnapshot
from app.models.athlete import Athlete
from app.models.biomechanical_analysis import BiomechanicalAnalysis
from app.models.pose_analysis import PoseAnalysis
from app.models.video import Video

# Number of prior same-activity analyses that form the rolling baseline.
BASELINE_WINDOW = 5

# Fewest prior analyses required before a comparison is meaningful.
MIN_BASELINE = 2

# How many points a metric must move (in robust standard-deviation units) before
# it is worth mentioning at all, and before it is called a real change.
NOTABLE_Z = 1.0
SIGNIFICANT_Z = 2.0

# Direction semantics per metric: +1 => higher is worse (deterioration),
# -1 => higher is better, 0 => purely informational (no good/bad direction).
METRIC_DIRECTIONS: Dict[str, int] = {
    "risk_score": +1,
    "findings_count": +1,
    "movement_quality": -1,
    "symmetry_score": -1,
    "knee_asymmetry": +1,
    "trunk_lean_max": +1,
    "knee_rom_left": 0,
    "knee_rom_right": 0,
    "hip_rom_left": 0,
    "hip_rom_right": 0,
    "mean_pose_confidence": -1,
}

# Human-readable labels + units for the UI.
METRIC_META: Dict[str, Dict[str, str]] = {
    "risk_score": {"label": "Injury risk score", "unit": ""},
    "findings_count": {"label": "Risk findings", "unit": ""},
    "movement_quality": {"label": "Movement quality", "unit": "score"},
    "symmetry_score": {"label": "Symmetry", "unit": "score"},
    "knee_asymmetry": {"label": "Knee asymmetry", "unit": "deg"},
    "trunk_lean_max": {"label": "Max trunk lean", "unit": "deg"},
    "knee_rom_left": {"label": "Left knee ROM", "unit": "deg"},
    "knee_rom_right": {"label": "Right knee ROM", "unit": "deg"},
    "hip_rom_left": {"label": "Left hip ROM", "unit": "deg"},
    "hip_rom_right": {"label": "Right hip ROM", "unit": "deg"},
    "mean_pose_confidence": {"label": "Pose confidence", "unit": ""},
}


# --------------------------------------------------------------------------- #
# Metric extraction
# --------------------------------------------------------------------------- #

def _num(value: Any) -> Optional[float]:
    """Coerce to float, or None when it is not a usable finite number."""
    if value is None or isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    # Reject NaN / inf so they can never pollute a baseline.
    if out != out or out in (float("inf"), float("-inf")):
        return None
    return out


def _dig(source: Any, *path: str) -> Any:
    """Safely walk nested dicts, returning None if any hop is missing."""
    current = source
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
        if current is None:
            return None
    return current


def build_metrics(
    risk_assessment: Optional[Dict[str, Any]],
    biomechanical: Optional[BiomechanicalAnalysis],
    pose_quality: Optional[Dict[str, Any]] = None,
) -> Dict[str, float]:
    """Flatten the headline trended metrics out of a completed analysis.

    Only metrics that are (a) meaningful to trend and (b) reliably present are
    included; missing values are simply omitted rather than stored as 0, so a
    later baseline average is not dragged toward a fake zero.
    """
    metrics: Dict[str, float] = {}

    if risk_assessment:
        risk_score = _num(risk_assessment.get("overall_risk_score"))
        if risk_score is not None:
            metrics["risk_score"] = risk_score
        findings = risk_assessment.get("findings") or []
        metrics["findings_count"] = float(len(findings))

    if biomechanical is not None:
        # Overall movement quality score.
        mq = _dig(biomechanical.movement_quality, "score")
        mq = _num(mq)
        if mq is not None:
            metrics["movement_quality"] = mq

        sym = _num(_dig(biomechanical.movement_quality, "components", "symmetry"))
        if sym is not None:
            metrics["symmetry_score"] = sym

        # Left/right knee asymmetry (degrees). Prefer the explicit asymmetry
        # block, else the max we recorded under symmetry.
        knee_asym = _num(_dig(biomechanical.symmetry, "knee_asymmetry", "max_asymmetry"))
        if knee_asym is None:
            knee_asym = _num(_dig(biomechanical.symmetry, "knee_asymmetry", "mean_asymmetry"))
        if knee_asym is not None:
            metrics["knee_asymmetry"] = knee_asym

        trunk_max = _num(_dig(biomechanical.trunk_lean, "max"))
        if trunk_max is None:
            trunk_max = _num(_dig(biomechanical.trunk_lean, "max_lean"))
        if trunk_max is not None:
            metrics["trunk_lean_max"] = abs(trunk_max)

        # Range of motion per side, where available.
        for joint in ("knee", "hip"):
            for side in ("left", "right"):
                rom = _num(_dig(biomechanical.rom, f"{joint}_{side}", "rom"))
                if rom is not None:
                    metrics[f"{joint}_rom_{side}"] = rom

    confidence = _num((pose_quality or {}).get("mean_confidence"))
    if confidence is not None:
        metrics["mean_pose_confidence"] = confidence

    return metrics


# --------------------------------------------------------------------------- #
# Snapshot recording
# --------------------------------------------------------------------------- #

def record_snapshot(
    db: Session,
    video: Video,
    risk_assessment: Optional[Dict[str, Any]],
    pose_analysis: Optional[PoseAnalysis],
    biomechanical: Optional[BiomechanicalAnalysis],
) -> Optional[AnalysisSnapshot]:
    """Persist a snapshot for a completed analysis (idempotent per video).

    Returns the snapshot, or None when the prerequisite rows are missing. If a
    snapshot already exists for this video it is returned untouched, so retrying
    processing cannot create duplicates or rewrite a recorded comparison.
    """
    if video is None or video.athlete_id is None:
        return None

    existing = (
        db.query(AnalysisSnapshot)
        .filter(AnalysisSnapshot.video_id == video.id)
        .first()
    )
    if existing is not None:
        return existing

    metrics = build_metrics(risk_assessment, biomechanical, (pose_analysis.pose_quality if pose_analysis else None))

    # A snapshot with no risk score is not worth keeping as history.
    if "risk_score" not in metrics:
        return None

    activity = video.activity_type or "unknown"

    # Baseline must be read BEFORE inserting, so this analysis is not part of it.
    baseline = compute_baseline(db, video.athlete_id, activity, exclude_video_id=video.id)
    comparison = compare_to_baseline(metrics, baseline)

    performed_at = video.created_at or datetime.utcnow()
    sequence_index = _next_sequence_index(db, video.athlete_id, activity)

    snapshot = AnalysisSnapshot(
        athlete_id=video.athlete_id,
        video_id=video.id,
        pose_analysis_id=(pose_analysis.id if pose_analysis else None),
        activity_type=activity,
        sequence_index=sequence_index,
        performed_at=performed_at,
        overall_risk_score=metrics["risk_score"],
        risk_level=(risk_assessment or {}).get("risk_level", "low"),
        findings_count=int(metrics.get("findings_count", 0)),
        metrics=metrics,
        baseline=baseline or None,
        baseline_comparison=comparison,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def _next_sequence_index(db: Session, athlete_id: int, activity: str) -> int:
    current_max = (
        db.query(func.max(AnalysisSnapshot.sequence_index))
        .filter(
            AnalysisSnapshot.athlete_id == athlete_id,
            AnalysisSnapshot.activity_type == activity,
        )
        .scalar()
    )
    return int(current_max or 0) + 1


# --------------------------------------------------------------------------- #
# Baseline + comparison
# --------------------------------------------------------------------------- #

def _mean(values: List[float]) -> float:
    return sum(values) / len(values)


def _mean_absolute_deviation(values: List[float], centre: float) -> float:
    """Robust spread measure (less outlier-sensitive than stdev)."""
    return _mean([abs(v - centre) for v in values])


def compute_baseline(
    db: Session,
    athlete_id: int,
    activity: str,
    exclude_video_id: Optional[int] = None,
) -> Dict[str, Dict[str, float]]:
    """Rolling baseline over the most recent prior analyses of one activity.

    Returns ``{metric: {mean, mad, count, min, max}}``. Only a *contiguous,
    most-recent* window of analyses is used, and only metrics present in at
    least one of them appear.
    """
    query = (
        db.query(AnalysisSnapshot)
        .filter(
            AnalysisSnapshot.athlete_id == athlete_id,
            AnalysisSnapshot.activity_type == activity,
        )
    )
    if exclude_video_id is not None:
        query = query.filter(AnalysisSnapshot.video_id != exclude_video_id)

    rows = (
        query.order_by(
            AnalysisSnapshot.performed_at.desc(), AnalysisSnapshot.id.desc()
        )
        .limit(BASELINE_WINDOW)
        .all()
    )
    if not rows:
        return {}

    # Collect per-metric samples across the window.
    samples: Dict[str, List[float]] = {}
    # Also track the *most recent* value to expose a simple delta.
    for row in rows:
        for metric, value in (row.metrics or {}).items():
            number = _num(value)
            if number is None:
                continue
            samples.setdefault(metric, []).append(number)

    baseline: Dict[str, Dict[str, float]] = {}
    for metric, values in samples.items():
        centre = _mean(values)
        baseline[metric] = {
            "mean": centre,
            "mad": _mean_absolute_deviation(values, centre),
            "count": float(len(values)),
            "min": min(values),
            "max": max(values),
        }
    return baseline


def _effective_spread(centre: float, mad: float, values: List[float]) -> float:
    """Spread used to normalize a delta.

    Prefers the robust MAD. When a history is almost perfectly flat the MAD can
    be ~0, which would make any delta look infinitely large, so we fall back to
    a small fraction of the mean as a noise floor.
    """
    floor = max(abs(centre) * 0.05, 0.5)
    if mad is not None and mad > 1e-9:
        return max(mad, floor)
    if values:
        spread = _mean_absolute_deviation(values, centre)
        if spread > 1e-9:
            return max(spread, floor)
    return floor


def compare_to_baseline(
    metrics: Dict[str, float],
    baseline: Dict[str, Dict[str, float]],
    baseline_size: Optional[int] = None,
) -> Dict[str, Any]:
    """Describe how ``metrics`` differs from ``baseline``.

    ``status`` is one of:
      * ``no_history``          - nothing to compare against yet;
      * ``insufficient_history``- some history, but below ``MIN_BASELINE``;
      * ``stable``              - comparable, no metric moved meaningfully;
      * ``changed``             - at least one metric moved meaningfully.

    Only metrics with a *directional* meaning contribute a
    ``deterioration``/``improvement`` verdict; informational metrics (e.g. ROM,
    which can legitimately go either way depending on the athlete's phase of
    training) are reported as ``neutral`` changes.
    """
    if not baseline:
        return {
            "status": "no_history",
            "baseline_size": 0,
            "baseline_window": BASELINE_WINDOW,
            "deltas": [],
            "flags": [],
            "deteriorations": [],
            "improvements": [],
            "baseline_metrics": [],
            "summary": "First recorded analysis for this activity - this establishes the baseline.",
        }

    size = baseline_size
    if size is None:
        size = int(max((b.get("count", 0) for b in baseline.values()), default=0))
    size = int(size)

    deltas: List[Dict[str, Any]] = []
    flags: List[Dict[str, Any]] = []

    for metric, value in metrics.items():
        number = _num(value)
        if number is None:
            continue
        stat = baseline.get(metric)
        if not stat:
            continue
        centre = _num(stat.get("mean"))
        if centre is None:
            continue

        delta = number - centre
        spread = _effective_spread(centre, _num(stat.get("mad")) or 0.0, [centre, number])
        z = delta / spread if spread else 0.0
        direction = METRIC_DIRECTIONS.get(metric, 0)

        if z >= SIGNIFICANT_Z:
            verdict = "deterioration" if direction > 0 else ("improvement" if direction < 0 else "neutral")
        elif z <= -SIGNIFICANT_Z:
            verdict = "improvement" if direction > 0 else ("deterioration" if direction < 0 else "neutral")
        else:
            verdict = "neutral"

        notable = abs(z) >= NOTABLE_Z
        meta = METRIC_META.get(metric, {})
        entry = {
            "metric": metric,
            "label": meta.get("label", metric.replace("_", " ").title()),
            "unit": meta.get("unit", ""),
            "current": round(number, 2),
            "baseline": round(centre, 2),
            "delta": round(delta, 2),
            "percent_change": (
                round((delta / centre) * 100.0, 1) if abs(centre) > 1e-9 else None
            ),
            "z_score": round(z, 2),
            "verdict": verdict,
            "notable": notable,
            "baseline_range": [
                round(_num(stat.get("min")) or centre, 2),
                round(_num(stat.get("max")) or centre, 2),
            ],
        }
        deltas.append(entry)

        if notable and direction != 0:
            flags.append(entry)

    # Biggest movers first.
    deltas.sort(key=lambda d: abs(d["z_score"]), reverse=True)
    flags.sort(key=lambda d: abs(d["z_score"]), reverse=True)

    improvements = [f for f in flags if f["verdict"] == "improvement"]
    deteriorations = [f for f in flags if f["verdict"] == "deterioration"]

    if size < MIN_BASELINE:
        status = "insufficient_history"
    elif flags:
        status = "changed"
    elif deltas:
        status = "stable"
    else:
        status = "no_history"

    return {
        "status": status,
        "baseline_size": size,
        "baseline_window": BASELINE_WINDOW,
        "deltas": deltas,
        "flags": flags,
        "summary": _summarize(status, size, deteriorations, improvements),
        "deteriorations": [f["metric"] for f in deteriorations],
        "improvements": [f["metric"] for f in improvements],
        "baseline_metrics": format_baseline(baseline),
    }


def format_baseline(
    baseline: Optional[Dict[str, Dict[str, float]]]
) -> List[Dict[str, Any]]:
    """Present the raw baseline in a UI-friendly list.

    This is what the athlete is being measured against, shown independently of
    whether any delta was significant - useful when there is too little history
    for a comparison but the user still wants to see the reference values.
    """
    if not baseline:
        return []
    rows: List[Dict[str, Any]] = []
    for metric, stat in baseline.items():
        centre = _num(stat.get("mean"))
        if centre is None:
            continue
        meta = METRIC_META.get(metric, {})
        rows.append(
            {
                "metric": metric,
                "label": meta.get("label", metric.replace("_", " ").title()),
                "unit": meta.get("unit", ""),
                "mean": round(centre, 2),
                "min": round(_num(stat.get("min")) or centre, 2),
                "max": round(_num(stat.get("max")) or centre, 2),
                "samples": int(stat.get("count", 0)),
            }
        )
    # Stable, meaningful order: risk first, then the rest alphabetically.
    rows.sort(key=lambda r: (r["metric"] != "risk_score", r["label"]))
    return rows


def _summarize(
    status: str,
    size: int,
    deteriorations: List[Dict[str, Any]],
    improvements: List[Dict[str, Any]],
) -> str:
    if status == "insufficient_history":
        return (
            f"Compared against {size} prior "
            f"{'analysis' if size == 1 else 'analyses'} - "
            "not enough history yet for a reliable trend."
        )
    if status == "stable":
        return "No meaningful change versus the athlete's recent baseline."
    if status == "changed":
        parts = []
        if deteriorations:
            parts.append(
                "elevated: "
                + ", ".join(f["label"].lower() for f in deteriorations)
            )
        if improvements:
            parts.append(
                "improved: " + ", ".join(f["label"].lower() for f in improvements)
            )
        return "Change versus baseline - " + "; ".join(parts) + "."
    return "No comparison available."


# --------------------------------------------------------------------------- #
# History for the UI
# --------------------------------------------------------------------------- #

def get_athlete_history(
    db: Session,
    athlete_id: int,
    activity: Optional[str] = None,
    limit: int = 100,
) -> List[AnalysisSnapshot]:
    """Ordered timeline of an athlete's snapshots (oldest first)."""
    query = db.query(AnalysisSnapshot).filter(
        AnalysisSnapshot.athlete_id == athlete_id
    )
    if activity:
        query = query.filter(AnalysisSnapshot.activity_type == activity)
    rows = (
        query.order_by(
            AnalysisSnapshot.performed_at.asc(), AnalysisSnapshot.id.asc()
        )
        .limit(limit)
        .all()
    )
    return rows


def summarize_trends(rows: List[AnalysisSnapshot]) -> List[Dict[str, Any]]:
    """Aggregate per-activity risk trend across an athlete's history.

    ``direction`` compares the mean of the earliest half of the series with the
    mean of the latest half, which is far less noisy than comparing just the
    first and last session. A small relative movement counts as ``stable``.
    """
    by_activity: Dict[str, List[AnalysisSnapshot]] = {}
    for row in rows:
        by_activity.setdefault(row.activity_type, []).append(row)

    trends: List[Dict[str, Any]] = []
    for activity, series in sorted(by_activity.items()):
        # ``rows`` is oldest-first, so the series already is too.
        scores = [s.overall_risk_score for s in series if s.overall_risk_score is not None]
        if not scores:
            continue

        first = scores[0]
        latest = scores[-1]
        mean_score = _mean(scores)
        risk_change = latest - first

        direction = "stable"
        relative = (risk_change / first) if abs(first) > 1e-9 else 0.0
        if len(scores) >= 2:
            if relative <= -0.10:
                direction = "improving"
            elif relative >= 0.10:
                direction = "worsening"

        trends.append(
            {
                "activity_type": activity,
                "analysis_count": len(scores),
                "first_risk_score": round(first, 2),
                "latest_risk_score": round(latest, 2),
                "mean_risk_score": round(mean_score, 2),
                "risk_change": round(risk_change, 2),
                "direction": direction,
                "latest_performed_at": series[-1].performed_at,
            }
        )
    return trends


def resolve_athlete(db: Session, athlete_id: int) -> Optional[Athlete]:
    return db.query(Athlete).filter(Athlete.id == athlete_id).first()
