import pytest
from app.services.injury_predictor import InjuryPredictor
from app.services.recommendations import RecommendationEngine


def test_injury_predictor_risk_calculation():
    predictor = InjuryPredictor()

    # Biomechanical input with high valgus and asymmetry
    biomech = {
        "overall_score": 62.0,
        "metrics_summary": {
            "peak_valgus_overall": 14.5,
            "mean_asymmetry_index": 18.2,
            "peak_flexion_overall": 65.0,
            "peak_trunk_lean": 22.0
        }
    }

    profile = {
        "training_load": 85.0,
        "age": 23,
        "height": 185.0,
        "weight": 80.0,
        "injury_history": "Previous ACL tear right knee"
    }

    result = predictor.assess_injury_risk(biomech, profile)

    assert "overall_risk_score" in result
    assert result["risk_level"] in ["LOW", "MODERATE", "HIGH"]
    assert "risk_breakdown" in result
    assert result["risk_breakdown"]["acl_risk"] > 50.0  # high valgus & ACL history should push risk high
    assert len(result["early_warnings"]) > 0


def test_recommendation_engine():
    recommender = RecommendationEngine()
    
    risk_breakdown = {
        "acl_risk": 75.0,
        "hamstring_risk": 68.0,
        "ankle_risk": 30.0,
        "patellar_risk": 40.0
    }
    
    anomalies = [
        "Knee Valgus > 10°"
    ]
    
    plan = recommender.generate_recommendations(
        risk_breakdown=risk_breakdown,
        training_load=86.0,
        anomalies=anomalies
    )
    
    assert "prescribed_exercises" in plan
    assert len(plan["prescribed_exercises"]) >= 2
    assert "DELOAD" in plan["training_load_recommendation"].upper()
    assert len(plan["recovery_guidelines"]) > 0
