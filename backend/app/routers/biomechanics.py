import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import UPLOAD_DIR
from app.models.video import VideoRecord
from app.models.athlete import Athlete
from app.models.biomechanics import BiomechanicalAnalysis
from app.models.injury_risk import InjuryRiskAssessment
from app.services.pose_engine import PoseEstimationEngine
from app.services.biomechanics_engine import BiomechanicsEngine
from app.services.anomaly_detection_engine import AnomalyDetectionEngine
from app.services.risk_scoring_engine import RiskScoringEngine
from app.services.injury_prediction_engine import InjuryPredictionEngine
from app.services.recommendation_engine import CorrectiveRecommendationEngine

router = APIRouter(prefix="/biomechanics", tags=["Biomechanical Analysis"])

pose_engine = PoseEstimationEngine()
biomech_engine = BiomechanicsEngine()
anomaly_engine = AnomalyDetectionEngine()
risk_engine = RiskScoringEngine()
prediction_engine = InjuryPredictionEngine()
recommend_engine = CorrectiveRecommendationEngine()

@router.post("/analyze/{video_id}")
def run_full_analysis(video_id: int, db: Session = Depends(get_db)):
    video = db.query(VideoRecord).filter(VideoRecord.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")

    if not os.path.exists(video.file_path):
        raise HTTPException(status_code=400, detail="Video file missing on disk")

    video.status = "processing"
    db.commit()

    processed_filename = f"analyzed_{Path(video.file_path).stem}.mp4"
    processed_path = str(UPLOAD_DIR / processed_filename)

    try:
        # 1. Pose Estimation & Frame Tracking
        tracking_result = pose_engine.process_video(
            video_input_path=video.file_path,
            video_output_path=processed_path,
            max_frames=300
        )
        time_series = tracking_result["time_series"]

        # 2. Biomechanical Analysis
        biomech_metrics = biomech_engine.analyze(time_series, fps=tracking_result["fps"])

        # 3. Retrieve Athlete Profile (or create default)
        athlete_profile = {}
        if video.athlete_id:
            athlete = db.query(Athlete).filter(Athlete.id == video.athlete_id).first()
            if athlete:
                athlete_profile = {
                    "sport_type": athlete.sport_type,
                    "injury_history": athlete.injury_history or [],
                    "acwr": athlete.acwr or 1.15,
                    "training_load": athlete.training_load or 12.0
                }

        # 4. Movement Anomaly Detection
        anomalies_res = anomaly_engine.detect_anomalies(time_series, activity_type=video.activity_type)
        fatigue_drift_pct = anomalies_res["fatigue_drift_pct"]

        # 5. Risk Scoring (Exact formula from PDF)
        scores = risk_engine.compute_scores(
            biomechanics=biomech_metrics,
            athlete_profile=athlete_profile,
            fatigue_drift_pct=fatigue_drift_pct
        )

        # 6. Injury Risk Category Predictions (ACL, Hamstring, Ankle, Shoulder, Lower Back, Overuse)
        category_risks = prediction_engine.predict_categories(
            biomechanics=biomech_metrics,
            athlete_profile=athlete_profile,
            weighted_scores=scores
        )

        # 7. Corrective Recommendations
        recommendations = recommend_engine.generate_recommendations(
            biomechanics=biomech_metrics,
            category_risks=category_risks,
            risk_category=scores["risk_category"]
        )

        # 8. Save or Update BiomechanicalAnalysis in DB
        analysis = db.query(BiomechanicalAnalysis).filter(BiomechanicalAnalysis.video_id == video.id).first()
        if not analysis:
            analysis = BiomechanicalAnalysis(video_id=video.id, athlete_id=video.athlete_id)
            db.add(analysis)

        analysis.total_frames_analyzed = tracking_result["total_frames"]
        analysis.mean_fps = tracking_result["fps"]
        analysis.knee_valgus_left_max = biomech_metrics["knee_valgus_left_max"]
        analysis.knee_valgus_right_max = biomech_metrics["knee_valgus_right_max"]
        analysis.knee_valgus_avg = biomech_metrics["knee_valgus_avg"]
        analysis.hip_stability_score = biomech_metrics["hip_stability_score"]
        analysis.pelvic_drop_deg = biomech_metrics["pelvic_drop_deg"]
        analysis.trunk_lean_lateral_max = biomech_metrics["trunk_lean_lateral_max"]
        analysis.trunk_lean_forward_max = biomech_metrics["trunk_lean_forward_max"]
        analysis.landing_mechanics_score = biomech_metrics["landing_mechanics_score"]
        analysis.initial_contact_knee_flexion_deg = biomech_metrics["initial_contact_knee_flexion_deg"]
        analysis.stride_length_est = biomech_metrics["stride_length_est"]
        analysis.joint_alignment_score = biomech_metrics["joint_alignment_score"]
        analysis.balance_stability_index = biomech_metrics["balance_stability_index"]
        analysis.movement_symmetry_score = biomech_metrics["movement_symmetry_score"]
        analysis.range_of_motion_score = biomech_metrics["range_of_motion_score"]
        analysis.force_impact_estimation_g = biomech_metrics["force_impact_estimation_g"]
        # Save a sampled time series (max 100 points) to keep response fast
        sample_step = max(1, len(time_series) // 100)
        analysis.time_series_data = time_series[::sample_step]
        db.commit()
        db.refresh(analysis)

        # 9. Save or Update InjuryRiskAssessment in DB
        risk_record = db.query(InjuryRiskAssessment).filter(InjuryRiskAssessment.video_id == video.id).first()
        if not risk_record:
            risk_record = InjuryRiskAssessment(video_id=video.id, athlete_id=video.athlete_id, analysis_id=analysis.id)
            db.add(risk_record)

        risk_record.analysis_id = analysis.id
        risk_record.overall_injury_risk_score = scores["overall_injury_risk_score"]
        risk_record.risk_category = scores["risk_category"]
        risk_record.biomechanical_deviation_score = scores["biomechanical_deviation_score"]
        risk_record.historical_injury_factor_score = scores["historical_injury_factor_score"]
        risk_record.movement_asymmetry_score = scores["movement_asymmetry_score"]
        risk_record.training_load_indicator_score = scores["training_load_indicator_score"]
        risk_record.fatigue_indicator_score = scores["fatigue_indicator_score"]
        risk_record.movement_quality_score = scores["movement_quality_score"]
        risk_record.biomechanical_efficiency_score = scores["biomechanical_efficiency_score"]
        risk_record.fatigue_risk_score = scores["fatigue_risk_score"]
        risk_record.overall_athlete_health_score = scores["overall_athlete_health_score"]
        risk_record.category_risks = category_risks
        risk_record.anomalies_detected = anomalies_res["events"]
        risk_record.corrective_recommendations = recommendations

        # Update video record status
        video.processed_video_path = processed_path
        video.status = "analyzed"
        db.commit()

        return {
            "message": "Analysis completed successfully",
            "video_id": video.id,
            "status": "analyzed",
            "biomechanics": biomech_metrics,
            "risk_assessment": {
                "overall_injury_risk_score": scores["overall_injury_risk_score"],
                "risk_category": scores["risk_category"],
                "weighted_components": {
                    "biomechanical_deviations_35": scores["biomechanical_deviation_score"],
                    "historical_injury_factors_20": scores["historical_injury_factor_score"],
                    "movement_asymmetry_20": scores["movement_asymmetry_score"],
                    "training_load_15": scores["training_load_indicator_score"],
                    "fatigue_indicators_10": scores["fatigue_indicator_score"]
                },
                "category_risks": category_risks,
                "anomalies": anomalies_res["events"],
                "recommendations": recommendations
            }
        }

    except Exception as e:
        video.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Analysis pipeline error: {str(e)}")

@router.get("/{video_id}")
def get_biomechanics_data(video_id: int, db: Session = Depends(get_db)):
    analysis = db.query(BiomechanicalAnalysis).filter(BiomechanicalAnalysis.video_id == video_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Biomechanical analysis not found for this video")
    
    return {
        "id": analysis.id,
        "video_id": analysis.video_id,
        "athlete_id": analysis.athlete_id,
        "total_frames_analyzed": analysis.total_frames_analyzed,
        "mean_fps": analysis.mean_fps,
        "metrics": {
            "knee_valgus_left_max": analysis.knee_valgus_left_max,
            "knee_valgus_right_max": analysis.knee_valgus_right_max,
            "knee_valgus_avg": analysis.knee_valgus_avg,
            "hip_stability_score": analysis.hip_stability_score,
            "pelvic_drop_deg": analysis.pelvic_drop_deg,
            "trunk_lean_lateral_max": analysis.trunk_lean_lateral_max,
            "trunk_lean_forward_max": analysis.trunk_lean_forward_max,
            "landing_mechanics_score": analysis.landing_mechanics_score,
            "initial_contact_knee_flexion_deg": analysis.initial_contact_knee_flexion_deg,
            "stride_length_est": analysis.stride_length_est,
            "joint_alignment_score": analysis.joint_alignment_score,
            "balance_stability_index": analysis.balance_stability_index,
            "movement_symmetry_score": analysis.movement_symmetry_score,
            "range_of_motion_score": analysis.range_of_motion_score,
            "force_impact_estimation_g": analysis.force_impact_estimation_g
        },
        "time_series_data": analysis.time_series_data
    }
