import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.risk_scoring_service import risk_scoring_service
from app.models.athlete import AthleteProfile
from app.models.user import User
from app.models.video import Video
from app.core.security import create_access_token

client = TestClient(app)

def test_injury_risk_prediction_categories():
    # Mock database session with mock athlete profile and video
    mock_db = MagicMock()
    mock_athlete = MagicMock()
    mock_athlete.id = 99
    mock_athlete.user_id = 99
    mock_athlete.name = "Alex Morgan"
    mock_athlete.sport_type = "Soccer"
    mock_athlete.position = "Forward"
    mock_athlete.age = 24
    mock_athlete.injury_history = "Prior left ACL reconstruction"
    mock_athlete.training_load = "High"
    
    mock_video = MagicMock()
    mock_video.id = 101
    mock_video.status = "completed"
    mock_video.athlete_id = 99
    mock_video.movement_type = "landing"
    
    def mock_query(model):
        query_mock = MagicMock()
        if model == AthleteProfile:
            query_mock.filter.return_value.first.return_value = mock_athlete
        elif model == Video:
            query_mock.filter.return_value.order_by.return_value.first.return_value = mock_video
            query_mock.filter.return_value.first.return_value = mock_video
        return query_mock
        
    mock_db.query.side_effect = mock_query
    
    with patch("app.services.risk_scoring_service.generate_biomechanics_analysis") as mock_analysis:
        mock_analysis.return_value = {
            "aggregates": {
                "knee_valgus": {
                    "dynamic_valgus_detected": True,
                    "min_knee_ankle_ratio": 0.78
                },
                "landing_mechanics": {
                    "landing_stiffness": "Stiff (High ACL Impact)",
                    "flexion_depth_deg": 24.5
                },
                "force_estimation": {
                    "peak_vgrf_bw": 2.9,
                    "impact_severity": "High Impact Spike"
                },
                "movement_symmetry": {
                    "knee_flexion_diff_deg": 18.0
                },
                "stride_and_gait": {
                    "overstriding_risk": True,
                    "max_stride_ratio": 1.42
                },
                "posture_assessment": {
                    "max_sagittal_trunk_lean": 28.0,
                    "cervical_forward_head_angle": 26.0
                },
                "balance_metrics": {
                    "balance_stability_score": 62.0
                }
            },
            "metrics_over_time": [
                {
                    "quality_flag": "OK",
                    "timestamp_ms": 1400,
                    "knee_valgus_ratio": 0.75,
                    "trunk_lean": 34.0,
                    "pelvic_drop_angle": 11.0
                }
            ]
        }
        
        prediction = risk_scoring_service.predict_injury_risks(mock_db, athlete_id=99)
        
        assert prediction.athlete_id == 99
        assert "acl_risk" in prediction.categories
        assert "hamstring_risk" in prediction.categories
        assert "ankle_sprain_risk" in prediction.categories
        assert "shoulder_risk" in prediction.categories
        assert "lower_back_risk" in prediction.categories
        assert "overuse_risk" in prediction.categories
        
        # ACL probability should be elevated due to valgus + stiff landing + soccer + prior ACL
        acl = prediction.categories["acl_risk"]
        assert acl.probability_pct > 60.0
        assert acl.risk_level in ("High", "Critical")
        assert any("valgus" in f.lower() for f in acl.risk_factors)
        assert len(acl.high_risk_movements) > 0
        
        # Hamstring risk should be elevated due to overstriding + forward lean
        ham = prediction.categories["hamstring_risk"]
        assert ham.probability_pct > 40.0
        
        # Overuse risk should be high due to training_load=High
        overuse = prediction.categories["overuse_risk"]
        assert overuse.probability_pct > 40.0
        
        # Overall risk
        assert prediction.overall_risk_score > 40.0

def test_risk_trend_monitoring():
    mock_db = MagicMock()
    v1 = Video(id=1, athlete_id=99, status="completed", movement_type="squatting")
    v1.created_at = MagicMock()
    v1.created_at.strftime.return_value = "2026-10-01"
    
    v2 = Video(id=2, athlete_id=99, status="completed", movement_type="landing")
    v2.created_at = MagicMock()
    v2.created_at.strftime.return_value = "2026-10-15"
    
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [v1, v2]
    
    with patch.object(risk_scoring_service, "predict_injury_risks") as mock_predict:
        # Mock first video: high risk
        p1 = MagicMock()
        p1.overall_risk_score = 65.0
        p1.overall_risk_band = "High (Unvalidated Screening Threshold)"
        p1.categories = {
            "acl_risk": MagicMock(probability_pct=70.0),
            "hamstring_risk": MagicMock(probability_pct=50.0),
            "ankle_sprain_risk": MagicMock(probability_pct=40.0),
            "shoulder_risk": MagicMock(probability_pct=30.0),
            "lower_back_risk": MagicMock(probability_pct=45.0),
            "overuse_risk": MagicMock(probability_pct=60.0),
        }
        # Mock second video: improved risk
        p2 = MagicMock()
        p2.overall_risk_score = 42.0
        p2.overall_risk_band = "Moderate (Unvalidated Screening Threshold)"
        p2.categories = {
            "acl_risk": MagicMock(probability_pct=45.0),
            "hamstring_risk": MagicMock(probability_pct=35.0),
            "ankle_sprain_risk": MagicMock(probability_pct=30.0),
            "shoulder_risk": MagicMock(probability_pct=25.0),
            "lower_back_risk": MagicMock(probability_pct=30.0),
            "overuse_risk": MagicMock(probability_pct=40.0),
        }
        mock_predict.side_effect = [p1, p2]
        
        trend = risk_scoring_service.get_risk_trend_history(mock_db, athlete_id=99)
        assert len(trend.trend_points) == 2
        assert trend.overall_trajectory == "improving"
        assert "improved" in trend.trajectory_explanation.lower()
