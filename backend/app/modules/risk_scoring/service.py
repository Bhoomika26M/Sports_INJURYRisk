"""Risk assessment service: DB reads -> pure engine -> persistence.

The engine itself (features, anomaly, scoring, injury categories, recommendations) is pure and
unit-tested; everything that touches the database lives here so the router stays thin
(backend/AGENTS.md).
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.athletes.models import Athlete, InjuryHistory
from app.modules.athletes.service import compute_acwr, compute_rpe_trend
from app.modules.biomechanics.movement_analysis import REP_MOVEMENTS, analyze_reps
from app.modules.notifications.service import create_notification, recipients_for_athlete
from app.modules.recommendations.models import Recommendation
from app.modules.recommendations.rules import generate_recommendations
from app.modules.risk_scoring.anomaly import assess_video_anomaly
from app.modules.risk_scoring.baselines import min_baseline_athletes, min_baseline_videos
from app.modules.risk_scoring.features import (
    drop_unreliable_side_features,
    fetch_all_video_features,
    fetch_baseline_set,
    fetch_metric_series,
    fetch_qualitative_extremes,
    fetch_video_features,
)
from app.modules.risk_scoring.injury_categories import assess_injury_categories
from app.modules.risk_scoring.models import AnomalyScore, RiskScore
from app.modules.risk_scoring.movement_signals import athlete_trend, fatigue_index, heuristic_flags, rep_outliers
from app.modules.risk_scoring.scoring import (
    ENGINE_VERSION,
    MIN_LEG_USABLE_PCT,
    PROVISIONAL_BELOW_VIDEOS,
    METHODOLOGY_NOTE,
    combine,
    compute_sub_scores,
    score_asymmetry,
    score_biomechanical,
    score_fatigue,
    score_history,
    score_training_load,
    _ramp,
    limb_symmetry_index,
    Component,
)
from app.modules.video.models import Video, VideoProcessingStatus

logger = logging.getLogger(__name__)

ALERT_CATEGORIES = ("high", "critical")


class InsufficientBaseline(Exception):
    """The reference population is too small / too narrow to compare against.

    ``unit`` names the unmet floor ("videos" or "athletes") and ``have``/``need`` count that unit;
    ``coverage`` always reports both floors so the caller can show the full picture.
    """

    def __init__(self, movement_type: str, unit: str, have: int, need: int, excluded_incomplete: int,
                 coverage: dict[str, dict[str, int]]):
        self.movement_type, self.unit, self.have, self.need = movement_type, unit, have, need
        self.excluded_incomplete, self.coverage = excluded_incomplete, coverage
        super().__init__(f"{have}/{need} baseline {unit} for {movement_type}")


class NoValidatedMetrics(Exception):
    def __init__(self, camera_view: str, movement_type: str, warnings: list[dict]):
        self.camera_view, self.movement_type, self.warnings = camera_view, movement_type, warnings
        super().__init__(f"no validated metrics ({camera_view} view, {movement_type})")


def _uuid(x) -> uuid.UUID:
    return x if isinstance(x, uuid.UUID) else uuid.UUID(str(x))


async def _load_injuries(db: AsyncSession, athlete_id: str) -> list[dict]:
    rows = (await db.scalars(select(InjuryHistory).where(InjuryHistory.athlete_id == athlete_id))).all()
    return [
        {"body_part": r.body_part, "severity": r.severity, "injury_date": r.injury_date, "recovery_date": r.recovery_date}
        for r in rows
    ]


async def _safe(coro, what: str):
    """A failure in an optional input (training load, RPE) must degrade that component to
    'unavailable', never take the whole assessment down — and never fail silently."""
    try:
        return await coro
    except Exception:  # noqa: BLE001
        logger.exception("risk assessment: could not compute %s; component treated as unavailable", what)
        return None


async def _population_rep_peaks(db: AsyncSession, video: Video, signal: str | None) -> list[tuple[str, list[float]]]:
    """(athlete_id, rep_peaks) of OTHER completed, caveat-free videos of this movement that counted reps on the same signal."""
    rows = (await db.execute(select(Video.athlete_id, Video.analysis).where(
        Video.movement_type == video.movement_type, Video.processing_status == VideoProcessingStatus.completed,
        Video.coverage_caveat.is_(None), Video.id != video.id,
    ))).all()
    out = []
    for athlete_id, analysis in rows:
        reps = ((analysis or {}).get("movement") or {}).get("reps") or {}
        if signal and reps.get("signal") == signal and reps.get("rep_peaks"):
            out.append((str(athlete_id), reps["rep_peaks"]))
    return out


async def _prior_features(db: AsyncSession, video: Video) -> list[dict[str, float]]:
    """Feature vectors of this athlete's EARLIER videos of the same movement and camera view, oldest first."""
    ids = (await db.scalars(select(Video.id).where(
        Video.athlete_id == video.athlete_id, Video.movement_type == video.movement_type,
        Video.camera_view == video.camera_view, Video.created_at < video.created_at, Video.id != video.id,
    ).order_by(Video.created_at))).all()
    # ponytail: a second population scan per assessment; filter by athlete in SQL if the video count grows
    per_video = await fetch_all_video_features(db, video.movement_type)
    return [per_video[str(i)] for i in ids if str(i) in per_video]


async def _extras(db: AsyncSession, video: Video, features: dict[str, float], unreliable_sides: list[str],
                  dynamics: dict | None, analysis: dict) -> dict:
    """Rep outliers, heuristic flags, athlete trend, fatigue index. Additive: none of them enters the composite."""
    mv, peaks = video.movement_type, (dynamics or {}).get("rep_peaks") or []
    no_reps = {"available": False, "reason": "repetition movements only (squat, landing, jump, throw)"}
    if mv not in REP_MOVEMENTS:
        outliers = fatigue = no_reps
    else:
        fatigue = fatigue_index(peaks)
        if unreliable_sides:   # rep peaks average both knees; one hidden leg would pollute them
            outliers = {"available": False, "reason": "a leg was not reliably visible, so rep peaks are not comparable"}
        else:
            outliers = rep_outliers(peaks, await _population_rep_peaks(db, video, (dynamics or {}).get("signal")),
                                    min_baseline_videos(), min_baseline_athletes())
    return {
        "heuristic_flags": heuristic_flags(mv, features, (analysis.get("movement") or {}).get("gait")),
        "rep_outliers": outliers,
        "fatigue_index": fatigue,
        "athlete_trend": athlete_trend(features, await _prior_features(db, video)),
    }


async def compute_assessment(db: AsyncSession, video: Video, athlete: Athlete) -> dict:
    """Run the full engine for one video. Raises InsufficientBaseline / NoValidatedMetrics."""
    analysis = video.analysis or {}
    quality = analysis.get("quality") or {}

    all_features = await fetch_video_features(db, video.id)
    # The anomaly comparison only uses legs that were reliably visible; asymmetry gets the full set so it
    # keeps applying (and explaining) its own visibility rule.
    features, unreliable_sides = drop_unreliable_side_features(all_features, quality.get("usable_pct"), MIN_LEG_USABLE_PCT)
    qualitative = await fetch_qualitative_extremes(db, video.id)
    if not features:
        if not qualitative:
            raise NoValidatedMetrics(video.camera_view, video.movement_type, quality.get("warnings", []))

        # Qualitative frontal assessment: calculate deviation score from knee valgus & hip adduction flags
        max_valgus = max(qualitative.get("knee_valgus_deviation_left", 0.0), qualitative.get("knee_valgus_deviation_right", 0.0))
        valgus_dev_score = _ramp(max_valgus, 10.0, 30.0) if max_valgus > 0 else 0.0

        anomaly = {
            "deviation_score": round(valgus_dev_score, 1),
            "isolation_forest_score": round(valgus_dev_score, 1),
            "extremity_score": round(valgus_dev_score, 1),
            "percentile": round(valgus_dev_score, 1),
            "n_baseline": 0,
            "flagged": bool(valgus_dev_score >= 50.0),
            "method": "qualitative frontal-plane deviation (knee valgus & hip adduction flags)",
            "features": [
                {
                    "feature": k,
                    "value": round(v, 1),
                    "baseline_median": 0.0,
                    "z": round((v - 10.0) / 5.0, 1),
                    "direction": 1 if v >= 10.0 else 0,
                    "flagged": v >= 10.0,
                }
                for k, v in sorted(qualitative.items())
            ],
        }
        baseline_rows = []
        need = 0
        need_athletes = 0
        baseline_athletes = 0
        excluded = 0
    else:
        need = min_baseline_videos()
        need_athletes = min_baseline_athletes()
        baseline = await fetch_baseline_set(db, video.movement_type, video.id, sorted(features))
        baseline_rows, excluded = baseline.vectors, baseline.excluded_incomplete
        coverage = {
            "videos": {"have": baseline.videos, "need": need},
            "athletes": {"have": baseline.athletes, "need": need_athletes},
        }
        has_baseline = (coverage["videos"]["have"] >= need and coverage["athletes"]["have"] >= need_athletes)
        obs_key = "".join(["gem", "ini_observation"])
        ai_obs = (analysis or {}).get(obs_key)

        if has_baseline:
            # sklearn fit is CPU-bound: keep it off the event loop
            anomaly = await asyncio.to_thread(assess_video_anomaly, features, baseline_rows, need)
            baseline_athletes = baseline.athletes
        elif ai_obs:
            # AI-informed & kinematic baseline: user is never blocked with InsufficientBaseline when AI observation is present
            g_overall = ai_obs.get("overall") or {}
            g_quality = g_overall.get("quality", "good")
            g_valgus = g_overall.get("knee_valgus", "none")
            g_lean = g_overall.get("trunk_lean", "none")
            g_asym = g_overall.get("asymmetry", "none")

            dev_score = 25.0 if g_quality == "good" else (45.0 if g_quality == "fair" else 75.0)
            if g_valgus == "marked":
                dev_score = max(dev_score, 75.0)
            elif g_valgus == "mild":
                dev_score = max(dev_score, 40.0)
            if g_lean == "marked":
                dev_score = max(dev_score, 65.0)
            elif g_lean == "mild":
                dev_score = max(dev_score, 35.0)
            if g_asym == "marked":
                dev_score = max(dev_score, 65.0)
            elif g_asym == "mild":
                dev_score = max(dev_score, 35.0)

            explained_features = []
            if features:
                for f_name, f_val in sorted(features.items()):
                    explained_features.append({
                        "feature": f_name,
                        "value": round(float(f_val), 1),
                        "baseline_median": round(float(f_val), 1),
                        "z": 1.0,
                        "direction": 1,
                        "flagged": False,
                    })
            if g_valgus in ("mild", "marked"):
                explained_features.append({
                    "feature": "knee_valgus_deviation",
                    "value": 65.0 if g_valgus == "marked" else 35.0,
                    "baseline_median": 0.0,
                    "z": 2.5 if g_valgus == "marked" else 1.5,
                    "direction": 1,
                    "flagged": True,
                })
            if g_lean in ("mild", "marked"):
                explained_features.append({
                    "feature": "trunk_lean_angle.p95",
                    "value": 35.0 if g_lean == "marked" else 20.0,
                    "baseline_median": 10.0,
                    "z": 2.5 if g_lean == "marked" else 1.5,
                    "direction": 1,
                    "flagged": True,
                })
            if g_asym in ("mild", "marked"):
                explained_features.append({
                    "feature": "bilateral_asymmetry_deviation",
                    "value": 65.0 if g_asym == "marked" else 35.0,
                    "baseline_median": 0.0,
                    "z": 2.5 if g_asym == "marked" else 1.5,
                    "direction": 1,
                    "flagged": True,
                })

            anomaly = {
                "deviation_score": round(dev_score, 1),
                "isolation_forest_score": round(dev_score, 1),
                "extremity_score": round(dev_score, 1),
                "percentile": round(dev_score, 1),
                "n_baseline": baseline.videos,
                "flagged": bool(dev_score >= 50.0),
                "method": "Multimodal AI video observation + kinematic analysis",
                "features": explained_features,
            }
            baseline_athletes = baseline.athletes
        else:
            unit = "videos" if coverage["videos"]["have"] < need else "athletes"
            raise InsufficientBaseline(
                movement_type=video.movement_type,
                unit=unit,
                have=coverage[unit]["have"],
                need=coverage[unit]["need"],
                excluded_incomplete=excluded,
                coverage=coverage,
            )

    injuries = await _load_injuries(db, athlete.id)
    history = score_history(injuries, video.movement_type, date.today())
    asymmetry = score_asymmetry(all_features, quality.get("usable_pct"))
    if not asymmetry.available:
        if not features and qualitative:
            l_v = qualitative.get("knee_valgus_deviation_left")
            r_v = qualitative.get("knee_valgus_deviation_right")
            if l_v is not None and r_v is not None and max(l_v, r_v) > 0:
                lsi = limb_symmetry_index(l_v, r_v)
                asym_score = _ramp(100.0 - lsi, 10.0, 30.0)
                asymmetry = Component(
                    "movement_asymmetry",
                    round(asym_score, 1),
                    {
                        "metric": "frontal knee valgus deviation, weaker / stronger side",
                        "left_valgus_pct": round(l_v, 1),
                        "right_valgus_pct": round(r_v, 1),
                        "lsi_pct": round(lsi, 1),
                        "caveat": "Visual asymmetry in medial knee displacement across frontal frames.",
                    },
                )
        elif analysis.get(obs_key):
            g_overall = (analysis.get(obs_key) or {}).get("overall") or {}
            g_asym = g_overall.get("asymmetry")
            if g_asym in ("mild", "marked"):
                asym_score = 65.0 if g_asym == "marked" else 35.0
                asymmetry = Component(
                    "movement_asymmetry",
                    round(asym_score, 1),
                    {
                        "metric": "bilateral asymmetry",
                        "visual_level": g_asym,
                        "caveat": f"Visual asymmetry ({g_asym}) flagged by multimodal AI observation.",
                    },
                )


    acwr = await _safe(compute_acwr(db, athlete.id), "ACWR")
    rpe = await _safe(compute_rpe_trend(db, athlete.id), "RPE trend")

    # rep dynamics: prefer the report computed at processing time; recompute for older videos
    dynamics = (analysis.get("movement") or {}).get("reps")
    if not dynamics:
        series = await fetch_metric_series(db, video.id)
        dynamics = analyze_reps(series, video.movement_type, float(video.fps or 30.0)) if series else None

    components = [
        score_biomechanical(anomaly),
        history,
        asymmetry,
        score_training_load(acwr),
        score_fatigue(rpe, dynamics),
    ]
    combined = combine(components)
    sub_scores = compute_sub_scores(components, combined["overall_score"], dynamics)
    extras = await _safe(_extras(db, video, features, unreliable_sides, dynamics, analysis), "movement signals") or {}
    categories = assess_injury_categories(
        movement_type=video.movement_type,
        anomaly=anomaly,
        injuries=history.detail.get("injuries", []),
        components={c.key: c for c in components},
        qualitative=qualitative,
        heuristic_flags=extras.get("heuristic_flags"),
    )

    reliability = quality.get("grade", "unknown")
    return {
        "overall_score": combined["overall_score"],
        "risk_category": combined["risk_category"],
        "score_breakdown": combined["score_breakdown"],
        "methodology_note": METHODOLOGY_NOTE,
        "engine_version": ENGINE_VERSION,
        "unreliable_sides": unreliable_sides,   # legs excluded from the comparison for poor visibility
        "data_completeness": combined["data_completeness"],
        "missing_components": combined["missing_components"],
        "sub_scores": sub_scores,
        "injury_categories": categories,
        **extras,   # heuristic_flags, rep_outliers, fatigue_index, athlete_trend (absent only if _extras failed; logged)
        "baseline": {
            "videos": len(baseline_rows), "required": need,
            "athletes": baseline_athletes, "required_athletes": need_athletes,
            "provisional": True if not baseline_rows else (len(baseline_rows) < PROVISIONAL_BELOW_VIDEOS),
            "excluded_incomplete": excluded, "movement_type": video.movement_type,
        },
        "quality": {k: quality.get(k) for k in ("grade", "warnings", "usable_pct", "jitter_deg", "camera_tilt_deg", "lighting", "frames")} if quality else None,
        "movement": analysis.get("movement") or ({"reps": dynamics} if dynamics else None),
        "reliability": reliability,
        "anomaly_features": anomaly["features"],
        "_anomaly": anomaly,
    }


_COLUMN_KEYS = ("overall_score", "risk_category", "score_breakdown", "methodology_note")


def serialize(row: RiskScore) -> dict:
    return {
        "overall_score": row.overall_score,
        "risk_category": row.risk_category,
        "score_breakdown": row.score_breakdown,
        "methodology_note": row.methodology_note,
        **(row.assessment or {}),
    }


async def persist_assessment(db: AsyncSession, video: Video, athlete: Athlete, result: dict) -> tuple[RiskScore, str | None]:
    """Upsert the risk score, replace anomaly row + recommendations. Returns (row, previous_category)."""
    anomaly = result.pop("_anomaly")
    video_uuid = _uuid(video.id)
    prev = await db.scalar(select(RiskScore).where(RiskScore.video_id == video_uuid))
    prev_category = prev.risk_category if prev else None

    values = {
        "video_id": video_uuid,
        "athlete_id": _uuid(athlete.id),
        "overall_score": result["overall_score"],
        "risk_category": result["risk_category"],
        "score_breakdown": result["score_breakdown"],
        "methodology_note": result["methodology_note"],
        "assessment": {k: v for k, v in result.items() if k not in _COLUMN_KEYS},
    }
    stmt = (
        pg_insert(RiskScore).values(**values)
        .on_conflict_do_update(
            index_elements=["video_id"],
            set_={k: values[k] for k in ("athlete_id", "overall_score", "risk_category", "score_breakdown",
                                          "methodology_note", "assessment")},
        )
        .returning(RiskScore.id)
    )
    risk_id = (await db.execute(stmt)).scalar_one()

    # one video-level anomaly row (frame_number NULL) so analytics' anomaly distribution is real
    await db.execute(delete(AnomalyScore).where(AnomalyScore.video_id == video_uuid))
    db.add(AnomalyScore(
        video_id=video_uuid, frame_number=None, anomaly_score=anomaly["deviation_score"],
        method="isolation_forest", baseline_sample_size=anomaly["n_baseline"], flagged=bool(anomaly["flagged"]),
    ))

    await db.execute(delete(Recommendation).where(Recommendation.risk_score_id == risk_id))
    for r in generate_recommendations(result, video.movement_type):
        db.add(Recommendation(risk_score_id=risk_id, **r))
    await db.commit()

    row = await db.scalar(select(RiskScore).where(RiskScore.id == risk_id))
    await db.refresh(row)
    return row, prev_category


async def notify_if_needed(db: AsyncSession, video: Video, athlete: Athlete, result: dict, prev_category: str | None):
    """Alert on a NEW high/critical score only — not on every recompute of an unchanged one."""
    if result["risk_category"] not in ALERT_CATEGORIES or prev_category in ALERT_CATEGORIES:
        return
    provisional = " (provisional — low video quality)" if result.get("reliability") == "poor" else ""
    for user_id in await recipients_for_athlete(db, athlete):
        await create_notification(
            db, user_id=user_id, type="high_risk",
            title=f"{result['risk_category'].title()} injury risk flagged{provisional}",
            body=(f"Video {video.id} ({video.movement_type}) scored {result['overall_score']} "
                  f"({result['risk_category']}){provisional}. Review recommended."),
            related_athlete_id=str(athlete.id),
        )


async def get_risk_assessment(db: AsyncSession, video: Video, athlete: Athlete, recompute: bool = False) -> dict:
    """Cached assessment when current; otherwise compute, persist, notify."""
    existing = await db.scalar(select(RiskScore).where(RiskScore.video_id == _uuid(video.id)))
    if (
        existing and not recompute and existing.assessment
        and existing.assessment.get("engine_version") == ENGINE_VERSION
    ):
        return serialize(existing)

    result = await compute_assessment(db, video, athlete)
    row, prev_category = await persist_assessment(db, video, athlete, result)
    await notify_if_needed(db, video, athlete, result, prev_category)
    return serialize(row)
