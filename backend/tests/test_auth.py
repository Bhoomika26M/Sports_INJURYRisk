import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_home_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "Sports Injury Risk Detection" in response.json()["message"]


def test_register_and_login():
    import uuid
    rand_email = f"test_{uuid.uuid4().hex[:8]}@sportguard.ai"
    
    # 1. Register
    reg_res = client.post("/auth/register", json={
        "name": "Alex Mercer",
        "email": rand_email,
        "password": "Password123!",
        "role": "COACH"
    })
    assert reg_res.status_code == 200
    assert reg_res.json()["role"] == "COACH"

    # 2. Login
    login_res = client.post("/auth/login", json={
        "email": rand_email,
        "password": "Password123!"
    })
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert data["role"] == "COACH"
