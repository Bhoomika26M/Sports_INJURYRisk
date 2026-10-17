import pytest
from app.services.injury_predictor import InjuryPredictor
from app.services.recommendations import RecommendationEngine
from app.database import SessionLocal
from app.models.prediction import InjuryAssessmentRecord
from app.routes.prediction import assess_risk_endpoint, get_latest_risk_assessment
from app.schemas.prediction import InjuryAssessmentRequest


def test_injury_predictor_model_training_and_inference():
    predictor = InjuryPredictor()
    assert predictor.model is not None

    sample_biomech = {
        "overall_score": 65.0,
        "metrics_summary": {
            "peak_valgus_overall": 14.5,
            "mean_asymmetry_index": 16.2,
            "peak_flexion_overall": 68.0,
            "peak_trunk_lean": 26.0
        }
    }
    athlete_data = {
        "age": 21,
        "height": 175,
        "weight": 68,
        "injury_history": "Previous ankle injury, knee strain",
        "training_load": 82.0
    }

    result = predictor.assess_injury_risk(sample_biomech, athlete_data)

    assert "overall_risk_score" in result
    assert 0 <= result["overall_risk_score"] <= 100
    assert result["risk_level"] in ["LOW", "MODERATE", "HIGH"]
    assert "acl_risk" in result["risk_breakdown"]
    assert "hamstring_risk" in result["risk_breakdown"]
    assert "ankle_risk" in result["risk_breakdown"]
    assert len(result["early_warnings"]) > 0


def test_recommendation_engine():
    recommender = RecommendationEngine()
    risk_breakdown = {
        "acl_risk": 55.0,
        "hamstring_risk": 48.0,
        "ankle_risk": 20.0,
        "patellar_risk": 60.0
    }
    training_load = 85.0
    anomalies = [
        "Severe Dynamic Knee Valgus Collapse",
        "High bilateral load asymmetry"
    ]

    rec_plan = recommender.generate_recommendations(
        risk_breakdown=risk_breakdown,
        training_load=training_load,
        anomalies=anomalies
    )

    assert len(rec_plan["prescribed_exercises"]) > 0
    # Must recommend deload due to load >= 80%
    assert "DELOAD" in rec_plan["training_load_recommendation"]
    assert rec_plan["recovery_status"] == "DELOAD_REQUIRED"
    assert len(rec_plan["recovery_guidelines"]) > 0


def test_prediction_api_endpoint_and_db_storage():
    db = SessionLocal()
    req = InjuryAssessmentRequest(
        athlete_id="ATH001",
        movement_type="SQUAT"
    )

    response = assess_risk_endpoint(req, db=db)

    assert response.overall_risk_score >= 0
    assert response.risk_level in ["LOW", "MODERATE", "HIGH"]
    assert len(response.recommendations.prescribed_exercises) > 0

    # Verify saved in SQLite database
    record = db.query(InjuryAssessmentRecord).filter(
        InjuryAssessmentRecord.athlete_id == "ATH001"
    ).order_by(InjuryAssessmentRecord.id.desc()).first()

    assert record is not None
    assert record.overall_risk_score == response.overall_risk_score
    db.close()


def test_get_latest_risk_assessment_endpoint():
    db = SessionLocal()
    latest = get_latest_risk_assessment("ATH001", db=db)
    assert latest.athlete_id == "ATH001"
    assert latest.risk_level in ["LOW", "MODERATE", "HIGH"]
    db.close()
