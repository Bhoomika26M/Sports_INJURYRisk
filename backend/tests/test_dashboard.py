import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_dashboard_me_unauthorized():
    response = client.get("/api/v1/dashboard/me")
    assert response.status_code == 401

@patch("app.api.endpoints.dashboard.athlete_service.get_profile_by_id")
@patch("app.api.endpoints.dashboard.athlete_service.get_profile_by_user_id")
@patch("app.api.endpoints.dashboard.video_service.get_videos_for_athlete")
def test_dashboard_me_empty(mock_get_videos, mock_get_profile, mock_get_profile_by_id):
    user_mock = MagicMock()
    user_mock.role = "athlete"
    user_mock.id = 1
    
    profile_mock = MagicMock()
    profile_mock.id = 1
    profile_mock.injury_history = []
    profile_mock.training_load = {}
    mock_get_profile.return_value = profile_mock
    mock_get_profile_by_id.return_value = profile_mock
    
    mock_get_videos.return_value = []
    
    from app.api.deps import get_current_user, get_current_active_user
    app.dependency_overrides[get_current_user] = lambda: user_mock
    app.dependency_overrides[get_current_active_user] = lambda: user_mock
    
    response = client.get("/api/v1/dashboard/me")
    app.dependency_overrides.clear()
    
    assert response.status_code == 200
    data = response.json()
    assert data["video_count"] == 0
    assert data["latest_analysis"] is None
    assert "risk_score" in data
    assert data["trend_data"] == []

def test_dashboard_athlete_unauthorized():
    user_mock = MagicMock()
    user_mock.role = "athlete"
    user_mock.id = 1
    
    from app.api.deps import get_current_user, get_current_active_user
    app.dependency_overrides[get_current_user] = lambda: user_mock
    app.dependency_overrides[get_current_active_user] = lambda: user_mock
    
    # allow_staff is an instance of RoleChecker. We can't override it easily.
    # But since user_mock.role = "athlete", RoleChecker will raise 403.
    response = client.get("/api/v1/dashboard/athlete/2")
    app.dependency_overrides.clear()
    
    assert response.status_code == 403
