import io
import pytest
from datetime import timedelta
from fastapi.testclient import TestClient
from app.main import app
from app.core import security
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User
from app.models.athlete import AthleteProfile
from app.models.video import Video

client = TestClient(app)

def test_unauthenticated_requests_fail():
    """Verify that protected API endpoints reject requests lacking credentials with 401."""
    protected_endpoints = [
        ("GET", "/api/v1/users/me"),
        ("GET", "/api/v1/athletes/me"),
        ("GET", "/api/v1/athletes/"),
        ("GET", "/api/v1/notifications"),
        ("GET", "/api/v1/reports/1/data"),
        ("GET", "/api/v1/dashboard/me"),
    ]
    for method, path in protected_endpoints:
        if method == "GET":
            resp = client.get(path)
        elif method == "POST":
            resp = client.post(path)
        assert resp.status_code == 401, f"Expected 401 for {method} {path}, got {resp.status_code}"

def test_tampered_token_rejected():
    """Verify that an altered or forged JWT signature is rejected with 401."""
    token = security.create_access_token(subject="1", role="athlete")
    # Tamper with signature
    tampered_token = token[:-5] + "XXXXX"
    resp = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {tampered_token}"})
    assert resp.status_code == 401

def test_expired_token_rejected():
    """Verify that an expired JWT token is rejected with 401."""
    expired_token = security.create_access_token(
        subject="1", 
        expires_delta=timedelta(seconds=-60), 
        role="athlete"
    )
    resp = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert resp.status_code == 401

def test_rbac_athlete_cannot_access_staff_roster(test_user, auth_headers):
    """Verify that an athlete cannot access staff athlete rosters or coach tools."""
    resp = client.get("/api/v1/athletes/", headers=auth_headers)
    assert resp.status_code == 403

def test_data_isolation_between_athletes():
    """Verify that Athlete A cannot read Athlete B's reports or videos."""
    db = SessionLocal()
    # Create Athlete A
    user_a = User(email="athlete_a@sec.org", hashed_password=security.get_password_hash("Pass123!"), role="athlete", is_active=True)
    db.add(user_a)
    db.commit()
    db.refresh(user_a)
    profile_a = AthleteProfile(user_id=user_a.id, sport_type="Soccer")
    db.add(profile_a)
    db.commit()
    db.refresh(profile_a)

    # Create Athlete B
    user_b = User(email="athlete_b@sec.org", hashed_password=security.get_password_hash("Pass123!"), role="athlete", is_active=True)
    db.add(user_b)
    db.commit()
    db.refresh(user_b)
    profile_b = AthleteProfile(user_id=user_b.id, sport_type="Running")
    db.add(profile_b)
    db.commit()
    db.refresh(profile_b)

    uid_a = user_a.id
    pid_b = profile_b.id
    db.close()

    # Authenticate as Athlete A
    token_a = security.create_access_token(subject=str(uid_a), role="athlete")
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Athlete A attempts to read Athlete B's report data -> 403 Forbidden
    resp = client.get(f"/api/v1/reports/{pid_b}/data", headers=headers_a)
    assert resp.status_code == 403

    # Athlete A attempts to read Athlete B's videos -> 403 Forbidden
    resp_v = client.get(f"/api/v1/videos/athlete/{pid_b}", headers=headers_a)
    assert resp_v.status_code == 403

def test_sql_injection_resilience(auth_headers):
    """Verify that SQL injection patterns in query parameters do not cause errors or data leaks."""
    sqli_payloads = [
        "1' OR '1'='1",
        "'; DROP TABLE users; --",
        "1 UNION SELECT 1, 2, 3 --"
    ]
    for sqli in sqli_payloads:
        resp = client.get(f"/api/v1/notifications?notification_type={sqli}", headers=auth_headers)
        # Should cleanly return empty list or valid response without SQL syntax error (200 OK)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

def test_path_traversal_neutralized(test_user, auth_headers):
    """Verify that attempted path traversal in uploaded filename does not escape upload directory."""
    db = SessionLocal()
    profile = db.query(AthleteProfile).filter(AthleteProfile.user_id == test_user.id).first()
    if not profile:
        profile = AthleteProfile(user_id=test_user.id, sport_type="Soccer", age=22, height_cm=175.0, weight_kg=70.0)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    ath_id = profile.id
    db.close()

    traversal_filename = "../../../etc/passwd.mp4"
    fake_video = io.BytesIO(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00" + b"X" * 1024)
    files = {"file": (traversal_filename, fake_video, "video/mp4")}
    data = {"athlete_id": ath_id, "movement_type": "squatting"}
    
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("app.services.video_service.extract_video_metadata", lambda p: (30.0, 1920, 1080, 2.0))
        mp.setattr("app.api.endpoints.videos.process_video_bg", lambda vid: None)
        resp = client.post("/api/v1/videos/", files=files, data=data, headers=auth_headers)
        
        assert resp.status_code == 200
        stored_filename = resp.json()["filename"]
        # Filename must be sanitized to uuid, not containing ../
        assert ".." not in stored_filename
        assert "/" not in stored_filename
        assert "\\" not in stored_filename

def test_security_headers_present():
    """Verify that essential security headers are attached to all API responses."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("x-xss-protection") == "1; mode=block"
    assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
