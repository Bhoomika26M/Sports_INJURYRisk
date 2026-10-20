"""End-to-end analysis: video -> pose -> biomechanics -> anomalies -> risk -> recommendations."""

import logging
from datetime import date

import numpy as np
from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models.athlete import Athlete
from app.models.video import Analysis, Video
from app.services.anomaly_detection import (
    evaluate_metrics,
    fatigue_trend,
    movement_inconsistency,
    performance_decline,
)
from app.services.biomechanics import analyze_biomechanics
from app.services.injury_risk import (
    extract_features,
    overall_probability,
    predict_category_risks,
    prior_injury_factor,
)
from app.services.notification_service import notify_analysis_complete
from app.services.pose_store import save_pose
from app.services.recommendations import build_recommendations
from app.services.risk_scoring import (
    asymmetry_score,
    biomech_deviation_score,
    compute_aux_scores,
    compute_load_stats,
    compute_risk_score,
    fatigue_score,
    historical_injury_score,
    training_load_score,
)

logger = logging.getLogger(__name__)


def analyze_pose(
    positions: np.ndarray,
    fps: float,
    activity: str,
    height_cm: float | None = None,
    weight_kg: float | None = None,
    injuries: list[dict] | None = None,
    training_entries: list[dict] | None = None,
    quality_history: list[float] | None = None,
    today: date | None = None,
) -> dict:
    """Pure analysis of a keypoint array. No database or video access, so it is easy to test."""
    injuries = injuries or []
    bio = analyze_biomechanics(positions, fps, activity, height_cm, weight_kg)
    items = evaluate_metrics(bio, activity)
    inconsistency = movement_inconsistency(bio["repetitions"])
    fatigue = fatigue_trend(bio["repetitions"])
    load_stats = compute_load_stats(training_entries or [], today)

    components = {
        "biomechanical_deviations": biomech_deviation_score(items),
        "historical_injury": historical_injury_score(injuries, today),
        "movement_asymmetry": asymmetry_score(bio["symmetry"]),
        "training_load": training_load_score(load_stats),
        "fatigue": fatigue_score(fatigue),
    }
    risk = compute_risk_score(components)
    aux = compute_aux_scores(components["biomechanical_deviations"], inconsistency, bio, fatigue, risk["score"])
    decline = performance_decline(quality_history or [], aux["movement_quality"])

    def frac(v):  # component score (0-100) -> severity (0-1)
        return None if v is None else v / 100.0

    categories = predict_category_risks(
        items,
        injuries,
        load_sev=frac(components["training_load"]),
        fatigue_sev=fatigue["fatigue_index"] if fatigue else None,
        mean_si_sev=frac(components["movement_asymmetry"]),
        today=today,
    )
    features = extract_features(items, fatigue, load_stats, prior_injury_factor(injuries, [], today))
    probability = overall_probability(categories, features)
    recommendations = build_recommendations(items, risk["category"], load_stats, fatigue, categories)

    return {
        "biomechanics": bio,
        "deviations": items,
        "anomalies": {"inconsistency": inconsistency, "fatigue": fatigue, "performance_decline": decline},
        "injury_risks": categories,
        "scores": {**aux, "risk": risk, "load_stats": load_stats, "injury_probability": probability},
        "risk_score": risk["score"],
        "risk_category": risk["category"],
        "movement_quality": aux["movement_quality"],
        "recommendations": recommendations,
    }


def run_analysis(video_id: int) -> None:
    """Background job. Opens its own DB session because it outlives the request."""
    from app.services.pose_estimation import PoseEstimator  # lazy: heavy import

    db = SessionLocal()
    try:
        video = db.get(Video, video_id)
        if video is None:
            return
        athlete = db.get(Athlete, video.athlete_id)
        video.status, video.error = "processing", None
        db.commit()

        sequence = PoseEstimator().process_video(video.stored_path)
        if sequence.detection_rate < 0.5:
            raise ValueError(
                f"Athlete detected in only {sequence.detection_rate:.0%} of frames. "
                "Use a clearer, full-body, well-lit recording with one athlete in frame."
            )
        save_pose(video.id, sequence.to_payload())

        injuries = [
            {"body_part": i.body_part, "injury_type": i.injury_type, "injury_date": i.injury_date,
             "severity": i.severity, "status": i.status}
            for i in athlete.injuries
        ]
        entries = [{"entry_date": e.entry_date, "load_au": e.load_au} for e in athlete.training_loads]
        previous = db.scalars(
            select(Analysis).where(Analysis.athlete_id == athlete.id, Analysis.video_id != video.id)
            .order_by(Analysis.created_at.desc()).limit(5)
        ).all()
        quality_history = [a.movement_quality for a in reversed(previous)]

        result = analyze_pose(
            sequence.positions, sequence.fps, video.activity, athlete.height_cm, athlete.weight_kg,
            injuries, entries, quality_history,
        )
        result["biomechanics"]["detection_rate"] = round(sequence.detection_rate, 3)

        db.execute(delete(Analysis).where(Analysis.video_id == video.id))
        analysis = Analysis(video_id=video.id, athlete_id=athlete.id, activity=video.activity, **result)
        db.add(analysis)
        video.status = "completed"
        db.commit()
        db.refresh(analysis)
        notify_analysis_complete(db, analysis, athlete, video)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Analysis of video %s failed", video_id)
        db.rollback()
        video = db.get(Video, video_id)
        if video:
            video.status, video.error = "failed", str(exc)[:500]
            db.commit()
    finally:
        db.close()
