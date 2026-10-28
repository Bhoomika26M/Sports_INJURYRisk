import pytest
from unittest.mock import MagicMock, patch
from app.services.anomaly_service import anomaly_service
from app.services.risk_scoring_service import risk_scoring_service
from app.services.recommendation_service import recommendation_service
from app.schemas.risk import RiskScoreInput, RiskComponentInput
from app.schemas.anomaly import AnomalyEvent
from app.models.video import Video
from app.models.athlete import AthleteProfile


# ==============================================================================
# Module 7: Movement Anomaly Detection Engine Tests
# ==============================================================================
def test_engine_7_movement_anomaly_and_technique_assessment():
    mock_db = MagicMock()
    
    # Create synthetic metrics over time with noticeable intra-trial drift and execution faults
    # 20 frames total: first 7 frames have high knee flexion (60 deg), last 7 frames have degraded flexion (44 deg -> ~16 deg drift)
    # and trunk sway increasing
    metrics_over_time = []
    for i in range(20):
        flex = 60.0 - (i * 0.8)  # Drops from 60 to ~44.8 (>15 deg drop)
        sway = 2.0 + (i * 0.6)   # Increases from 2.0 to ~13.4 (>10 deg drift)
        metrics_over_time.append({
            "timestamp_ms": i * 33,
            "quality_flag": "OK",
            "trunk_lean": 32.0 if i > 10 else 18.0,       # >30 triggers trunk_lean anomaly
            "left_knee_angle": flex,
            "right_knee_angle": flex - 28.0,              # diff > 25 triggers knee_asymmetry anomaly
            "knee_valgus_ratio": 0.72 if i > 12 else 0.95, # <0.85 triggers knee_valgus anomaly
            "lateral_trunk_lean": sway,                   # >12 triggers lateral_trunk_sway anomaly
            "pelvic_drop_angle": 9.5 if i > 14 else 3.0    # >8 triggers pelvic_drop anomaly
        })
        
    analysis_data = {
        "metrics_over_time": metrics_over_time,
        "aggregates": {}
    }
    
    with patch("app.services.anomaly_service.generate_biomechanics_analysis", return_value=analysis_data):
        result = anomaly_service.detect_anomalies(mock_db, video_id=42)
        
        assert result is not None
        assert result.video_id == 42
        
        # 1. Movement deviations & anomalies detected
        assert len(result.events) > 0
        assert result.movement_deviations_count >= 1
        
        # Verify specific deviation metrics are detected
        event_metrics = [e.metric for e in result.events]
        assert "trunk_lean" in event_metrics
        assert "knee_asymmetry" in event_metrics
        assert "knee_valgus" in event_metrics
        assert "pelvic_drop" in event_metrics
        assert "lateral_trunk_sway" in event_metrics
        
        # 2. Technique assessment
        assert result.technique_assessment is not None
        assert 0 <= result.technique_assessment.technique_score <= 100
        assert result.technique_assessment.technique_grade in ["Optimal", "Good", "Suboptimal", "High Risk"]
        assert isinstance(result.technique_assessment.execution_faults, list)
        assert len(result.technique_assessment.execution_faults) > 0
        
        # 3. Motion inconsistency analysis
        assert result.motion_inconsistency is not None
        assert result.motion_inconsistency.coefficient_of_variation_pct >= 0.0
        assert result.motion_inconsistency.smoothness_jerk_score >= 0.0
        assert result.motion_inconsistency.consistency_rating in ["Consistent", "Mild Inconsistency", "High Inconsistency"]
        
        # 4. Fatigue-related movement monitoring (intra-trial kinematic drift)
        assert isinstance(result.fatigue_indicators, list)
        assert len(result.fatigue_indicators) > 0
        assert any("fatigue" in ind.lower() or "loss" in ind.lower() or "drift" in ind.lower() for ind in result.fatigue_indicators)
        
        # 5. Performance decline alerts
        assert isinstance(result.performance_decline_alerts, list)
        assert len(result.performance_decline_alerts) > 0
        assert any("degradation" in alert.lower() or "declined" in alert.lower() or "compensatory" in alert.lower() or "fatigue" in alert.lower() for alert in result.performance_decline_alerts)


# ==============================================================================
# Module 8: Risk Scoring Engine Tests
# ==============================================================================
def test_engine_8_weighted_scoring_model_and_categories():
    # 1. Critical Risk Scenario:
    # Bio: 90, Hist: 85, Asym: 80, Load: 90, Fatigue: 85
    # Weighted: 0.35*90 + 0.20*85 + 0.20*80 + 0.15*90 + 0.10*85
    # = 31.5 + 17.0 + 16.0 + 13.5 + 8.5 = 86.5 -> Critical Risk (>= 85)
    crit_input = RiskScoreInput(
        biomechanical_deviations=RiskComponentInput(value=90.0),
        historical_injury_factors=RiskComponentInput(value=85.0),
        movement_asymmetry=RiskComponentInput(value=80.0),
        training_load=RiskComponentInput(value=90.0),
        fatigue_indicators=RiskComponentInput(value=85.0)
    )
    crit_res = risk_scoring_service.calculate_risk_score(crit_input)
    assert crit_res.injury_risk_score == 86.5
    assert crit_res.composite_score == 86.5
    assert "critical" in crit_res.risk_band.lower()
    assert crit_res.risk_category == "Critical Risk"
    assert crit_res.movement_quality_score <= 25.0
    assert crit_res.biomechanical_efficiency_score <= 25.0
    assert crit_res.fatigue_risk_score == 87.0
    assert crit_res.overall_athlete_health_score <= 30.0

    # 2. High Risk Scenario:
    # Bio: 70, Hist: 70, Asym: 70, Load: 70, Fatigue: 70 -> Score: 70.0 -> High Risk (65-85)
    high_input = RiskScoreInput(
        biomechanical_deviations=RiskComponentInput(value=70.0),
        historical_injury_factors=RiskComponentInput(value=70.0),
        movement_asymmetry=RiskComponentInput(value=70.0),
        training_load=RiskComponentInput(value=70.0),
        fatigue_indicators=RiskComponentInput(value=70.0)
    )
    high_res = risk_scoring_service.calculate_risk_score(high_input)
    assert high_res.injury_risk_score == 70.0
    assert "high" in high_res.risk_band.lower()
    assert high_res.risk_category == "High Risk"

    # 3. Moderate Risk Scenario:
    # Bio: 45, Hist: 50, Asym: 40, Load: 50, Fatigue: 40
    # = 0.35*45 + 0.20*50 + 0.20*40 + 0.15*50 + 0.10*40
    # = 15.75 + 10.0 + 8.0 + 7.5 + 4.0 = 45.25 -> Moderate Risk (35-65)
    mod_input = RiskScoreInput(
        biomechanical_deviations=RiskComponentInput(value=45.0),
        historical_injury_factors=RiskComponentInput(value=50.0),
        movement_asymmetry=RiskComponentInput(value=40.0),
        training_load=RiskComponentInput(value=50.0),
        fatigue_indicators=RiskComponentInput(value=40.0)
    )
    mod_res = risk_scoring_service.calculate_risk_score(mod_input)
    assert 35.0 <= mod_res.injury_risk_score < 65.0
    assert "moderate" in mod_res.risk_band.lower()
    assert mod_res.risk_category == "Moderate Risk"

    # 4. Low Risk Scenario:
    # Bio: 15, Hist: 10, Asym: 20, Load: 15, Fatigue: 10
    # = 0.35*15 + 0.20*10 + 0.20*20 + 0.15*15 + 0.10*10
    # = 5.25 + 2.0 + 4.0 + 2.25 + 1.0 = 14.5 -> Low Risk (< 35)
    low_input = RiskScoreInput(
        biomechanical_deviations=RiskComponentInput(value=15.0),
        historical_injury_factors=RiskComponentInput(value=10.0),
        movement_asymmetry=RiskComponentInput(value=20.0),
        training_load=RiskComponentInput(value=15.0),
        fatigue_indicators=RiskComponentInput(value=10.0)
    )
    low_res = risk_scoring_service.calculate_risk_score(low_input)
    assert low_res.injury_risk_score < 35.0
    assert "low" in low_res.risk_band.lower()
    assert low_res.risk_category == "Low Risk"
    assert low_res.movement_quality_score > 70.0
    assert low_res.overall_athlete_health_score > 70.0


# ==============================================================================
# Module 9: Corrective Recommendation Engine Tests
# ==============================================================================
def test_engine_9_corrective_recommendation_categories():
    mock_db = MagicMock()
    mock_video = MagicMock(spec=Video)
    mock_video.id = 55
    mock_video.athlete_id = 12
    
    mock_athlete = MagicMock(spec=AthleteProfile)
    mock_athlete.id = 12
    mock_athlete.training_load = "High"

    def mock_query(model):
        q = MagicMock()
        if model == Video:
            q.filter.return_value.first.return_value = mock_video
        elif model == AthleteProfile:
            q.filter.return_value.first.return_value = mock_athlete
        return q

    mock_db.query.side_effect = mock_query

    # Mock assessment and anomaly results triggering valgus, asymmetry, and trunk lean
    mock_assessment = {
        "flags": ["Asymmetrical knee flexion", "Excessive trunk lean"],
        "warnings": [],
        "data_quality_score": 92.0
    }
    
    mock_anomaly_res = MagicMock()
    mock_anomaly_res.events = [
        AnomalyEvent(
            timestamp_ms=100,
            metric="knee_valgus",
            observed_value=0.75,
            reference_rule=">= 0.85",
            severity="high",
            explanation="Dynamic valgus collapse",
            is_data_quality_issue=False
        ),
        AnomalyEvent(
            timestamp_ms=200,
            metric="knee_asymmetry",
            observed_value=28.0,
            reference_rule="<= 25.0 deg",
            severity="medium",
            explanation="Asymmetric loading",
            is_data_quality_issue=False
        ),
        AnomalyEvent(
            timestamp_ms=300,
            metric="movement_variability",
            observed_value=50.0,
            reference_rule="<= 45.0 deg/frame",
            severity="medium",
            explanation="Movement jitter",
            is_data_quality_issue=False
        )
    ]

    with patch("app.services.recommendation_service.get_assessment", return_value=mock_assessment), \
         patch("app.services.recommendation_service.anomaly_service.detect_anomalies", return_value=mock_anomaly_res):
         
        res = recommendation_service.generate_recommendations(mock_db, video_id=55, activity="jumping")
        
        assert res is not None
        assert res.video_id == 55
        assert res.athlete_id == 12
        assert len(res.recommendations) > 0

        # Verify all 5 requested categories are populated
        # 1. Exercise recommendations
        assert len(res.exercise_recommendations) > 0
        for r in res.exercise_recommendations:
            assert r.category == "exercise"
            assert r.target_region is not None

        # 2. Mobility improvement suggestions
        assert len(res.mobility_suggestions) > 0
        for r in res.mobility_suggestions:
            assert r.category == "mobility"
            assert r.target_region is not None

        # 3. Strengthening recommendations
        assert len(res.strengthening_recommendations) > 0
        for r in res.strengthening_recommendations:
            assert r.category == "strengthening"
            assert r.sets_and_reps is not None

        # 4. Recovery planning
        assert len(res.recovery_plan) > 0
        for r in res.recovery_plan:
            assert r.category == "recovery"

        # 5. Training modification suggestions
        assert len(res.training_modifications) > 0
        for r in res.training_modifications:
            assert r.category == "training_modification"

        # Verify clinical compliance rule: no diagnosis or prevention claims
        for r in res.recommendations:
            assert "diagnos" not in r.title.lower()
            assert "prevent" not in r.description.lower()
