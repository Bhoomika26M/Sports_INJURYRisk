from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_liveness_probe():
    response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "alive"
    assert "uptime_seconds" in data
    assert data["uptime_seconds"] >= 0

def test_readiness_probe():
    response = client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert "checks" in data
    assert data["checks"]["database"]["status"] == "connected"
    assert data["checks"]["storage"]["status"] == "writable"

def test_metrics_endpoint():
    response = client.get("/api/v1/health/metrics")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "AthletiQ"
    assert "uptime_seconds" in data
    assert "storage" in data
    assert "runtime" in data
    assert "database_metrics" in data

def test_security_and_monitoring_headers():
    response = client.get("/")
    assert response.status_code == 200
    # Process time and Request ID
    assert "x-request-id" in response.headers
    assert "x-process-time" in response.headers
    # Security headers
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("x-xss-protection") == "1; mode=block"
