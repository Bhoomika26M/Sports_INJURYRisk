import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.risk_scoring_service import risk_scoring_service
from app.schemas.risk import RiskScoreInput, RiskComponentInput, DataSource

client = TestClient(app)

def create_valid_input(
    bio=50, hist=50, asym=50, train=50, fatigue=50,
    source=DataSource.MEASURED
):
    return RiskScoreInput(
        biomechanical_deviations=RiskComponentInput(value=bio, source=source),
        historical_injury_factors=RiskComponentInput(value=hist, source=source),
        movement_asymmetry=RiskComponentInput(value=asym, source=source),
        training_load=RiskComponentInput(value=train, source=source),
        fatigue_indicators=RiskComponentInput(value=fatigue, source=source)
    )

def test_risk_scoring_service_weighting():
    # If all inputs are 100, score should be 100
    inputs = create_valid_input(100, 100, 100, 100, 100)
    response = risk_scoring_service.calculate_risk_score(inputs)
    assert response.composite_score == 100.0
    assert response.risk_band.startswith("Critical")
    assert response.data_completeness == 100.0
    
    # Custom weighting test
    # weights: bio 0.35, hist 0.20, asym 0.20, train 0.15, fatigue 0.10
    inputs2 = create_valid_input(100, 0, 0, 0, 0) # Only bio is 100
    response2 = risk_scoring_service.calculate_risk_score(inputs2)
    # Expected: 100 * 0.35 = 35.0
    assert pytest.approx(response2.composite_score, 0.01) == 35.0
    assert response2.risk_band.startswith("Moderate")

def test_risk_scoring_service_boundary_values():
    # Test 0
    inputs = create_valid_input(0, 0, 0, 0, 0)
    response = risk_scoring_service.calculate_risk_score(inputs)
    assert response.composite_score == 0.0
    assert response.risk_band.startswith("Low")
    
    # Pydantic should prevent <0 and >100 in the API, but let's test exactly 100
    inputs2 = create_valid_input(100, 100, 100, 100, 100)
    response2 = risk_scoring_service.calculate_risk_score(inputs2)
    assert response2.composite_score == 100.0
    assert response2.risk_band.startswith("Critical")

def test_risk_scoring_service_missing_inputs():
    # Suppose biomechanical is missing (is_missing=True)
    inputs = create_valid_input(100, 100, 100, 100, 100)
    inputs.biomechanical_deviations.is_missing = True
    inputs.biomechanical_deviations.value = None
    
    response = risk_scoring_service.calculate_risk_score(inputs)
    
    # Missing bio (weight 0.35). Remaining weight = 0.65
    # Weighted sum = 100 * 0.65 = 65
    # Composite = 65 / 0.65 = 100
    assert pytest.approx(response.composite_score, 0.01) == 100.0
    assert response.data_completeness == 80.0
    
    # Confidence score should drop because of missing data
    assert response.confidence_score < 100.0
    assert "Incomplete data" in [f for f in response.contributing_factors if "Incomplete" in f][0]

    # All missing
    inputs_all_missing = RiskScoreInput(
        biomechanical_deviations=RiskComponentInput(is_missing=True),
        historical_injury_factors=RiskComponentInput(is_missing=True),
        movement_asymmetry=RiskComponentInput(is_missing=True),
        training_load=RiskComponentInput(is_missing=True),
        fatigue_indicators=RiskComponentInput(is_missing=True)
    )
    response_all_missing = risk_scoring_service.calculate_risk_score(inputs_all_missing)
    assert response_all_missing.composite_score is None
    assert response_all_missing.data_completeness == 0.0
    assert response_all_missing.confidence_score == 0.0

def test_risk_scoring_service_confidence():
    inputs = create_valid_input(50, 50, 50, 50, 50, source=DataSource.MEASURED)
    response_measured = risk_scoring_service.calculate_risk_score(inputs)
    assert response_measured.confidence_score == 100.0
    
    inputs_estimated = create_valid_input(50, 50, 50, 50, 50, source=DataSource.ESTIMATED)
    response_estimated = risk_scoring_service.calculate_risk_score(inputs_estimated)
    assert pytest.approx(response_estimated.confidence_score, 0.01) == 70.0

def test_api_integration():
    payload = {
        "biomechanical_deviations": {"value": 80, "source": "measured"},
        "historical_injury_factors": {"value": 40, "source": "estimated"},
        "movement_asymmetry": {"value": 20, "source": "manual"},
        "training_load": {"value": 60, "source": "measured"},
        "fatigue_indicators": {"value": 90, "source": "measured"}
    }
    response = client.post("/api/v1/risk/score", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "composite_score" in data
    assert "risk_band" in data
    assert "disclaimer" in data
    assert "confidence_score" in data
    assert "This score is NOT an injury probability" in data["disclaimer"]

def test_api_invalid_values():
    payload = {
        "biomechanical_deviations": {"value": 150, "source": "measured"}, # Invalid > 100
        "historical_injury_factors": {"value": 40, "source": "estimated"},
        "movement_asymmetry": {"value": 20, "source": "manual"},
        "training_load": {"value": 60, "source": "measured"},
        "fatigue_indicators": {"value": 90, "source": "measured"}
    }
    response = client.post("/api/v1/risk/score", json=payload)
    assert response.status_code == 422 # Unprocessable Entity (Validation Error)
    
    payload2 = {
        "biomechanical_deviations": {"value": -10, "source": "measured"}, # Invalid < 0
        "historical_injury_factors": {"value": 40, "source": "estimated"},
        "movement_asymmetry": {"value": 20, "source": "manual"},
        "training_load": {"value": 60, "source": "measured"},
        "fatigue_indicators": {"value": 90, "source": "measured"}
    }
    response2 = client.post("/api/v1/risk/score", json=payload2)
    assert response2.status_code == 422
