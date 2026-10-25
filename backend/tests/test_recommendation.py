import pytest
from unittest.mock import patch, MagicMock
from app.services.recommendation_service import recommendation_service
from app.schemas.recommendation import RecommendationResponse
from app.schemas.anomaly import AnomalyDetectionResponse, AnomalyEvent

@patch("app.services.recommendation_service.anomaly_service.detect_anomalies")
@patch("app.services.recommendation_service.get_assessment")
def test_recommendation_data_quality(mock_get_assessment, mock_detect_anomalies):
    # Rule B: Missing input/poor quality -> professional assessment
    mock_detect_anomalies.return_value = AnomalyDetectionResponse(
        video_id=1, total_anomalies=1, events=[
            AnomalyEvent(timestamp_ms=0, metric="data_quality", observed_value=None, reference_rule="", severity="high", explanation="", is_data_quality_issue=True)
        ]
    )
    mock_get_assessment.return_value = {"flags": ["trunk lean excessive"], "warnings": []}
    
    response = recommendation_service.generate_recommendations(None, 1)
    
    # Should ONLY recommend data quality reassess, skipping trunk lean because of bad data
    assert len(response.recommendations) == 1
    assert response.recommendations[0].id == "data_quality_reassess"
    assert "not constitute medical advice" in response.disclaimer

@patch("app.services.recommendation_service.anomaly_service.detect_anomalies")
@patch("app.services.recommendation_service.get_assessment")
def test_recommendation_rule_matching(mock_get_assessment, mock_detect_anomalies):
    # Valid input with multiple findings
    mock_detect_anomalies.return_value = AnomalyDetectionResponse(
        video_id=1, total_anomalies=2, events=[
            AnomalyEvent(timestamp_ms=0, metric="movement_variability", observed_value=50.0, reference_rule="", severity="high", explanation="", is_data_quality_issue=False),
            AnomalyEvent(timestamp_ms=0, metric="trunk_lean", observed_value=40.0, reference_rule="", severity="medium", explanation="", is_data_quality_issue=False)
        ]
    )
    mock_get_assessment.return_value = {"flags": ["asymmetrical knee flexion detected"], "warnings": []}
    
    response = recommendation_service.generate_recommendations(None, 1)
    
    ids = [r.id for r in response.recommendations]
    assert "coach_technique_trunk" in ids # From trunk_lean event
    assert "professional_assessment_asymmetry" in ids # From asymmetrical flag
    assert "review_training_load" in ids # From movement_variability event
    
    # Verify no diagnostic claims in recommendations
    for r in response.recommendations:
        assert "diagnos" not in r.title.lower()
        assert "prevent" not in r.description.lower()

@patch("app.services.recommendation_service.anomaly_service.detect_anomalies")
@patch("app.services.recommendation_service.get_assessment")
def test_recommendation_conflicting_findings(mock_get_assessment, mock_detect_anomalies):
    # In this case we just append all relevant recommendations since it's an educational library,
    # ensuring we don't have dupes.
    mock_detect_anomalies.return_value = AnomalyDetectionResponse(
        video_id=1, total_anomalies=1, events=[
            AnomalyEvent(timestamp_ms=0, metric="knee_asymmetry", observed_value=30.0, reference_rule="", severity="high", explanation="", is_data_quality_issue=False)
        ]
    )
    # Both anomaly and assessment trigger asymmetry. Should only show once.
    mock_get_assessment.return_value = {"flags": ["asymmetrical knee flexion detected"], "warnings": []}
    
    response = recommendation_service.generate_recommendations(None, 1)
    
    ids = [r.id for r in response.recommendations]
    assert ids.count("professional_assessment_asymmetry") == 1
