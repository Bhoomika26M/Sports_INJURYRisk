import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_register_invalid_email():
    """Validates that malformed email addresses are rejected with 422."""
    payload = {
        "email": "not-an-email",
        "password": "Password123!",
        "full_name": "Test User",
        "role": "athlete"
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422

def test_register_missing_fields():
    """Validates that payloads missing required fields are rejected with 422."""
    payload = {"full_name": "Incomplete User"}
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 422

def test_admin_registration_demotes_unauthorized():
    """Validates that registering as administrator without valid secret code safely defaults to athlete."""
    payload = {
        "email": "unauth_admin@athletiq.com",
        "password": "AdminPassword123!",
        "full_name": "Fake Admin",
        "role": "administrator",
        "admin_code": "wrong-secret-code"
    }
    resp = client.post("/api/v1/auth/register", json=payload)
    assert resp.status_code == 200
    assert resp.json()["role"] == "athlete"

def test_login_invalid_credentials():
    """Validates that non-existent or wrong password returns 401."""
    resp = client.post("/api/v1/auth/login", data={"username": "nonexistent@example.com", "password": "WrongPassword!"})
    assert resp.status_code == 401
    assert "detail" in resp.json()

def test_login_missing_credentials():
    """Validates that missing form parameters returns 422."""
    resp = client.post("/api/v1/auth/login", data={})
    assert resp.status_code == 422

def test_video_upload_unsupported_format(test_user, auth_headers):
    """Validates that uploading unsupported file formats (.txt/.sh) is rejected with 400."""
    from app.models.athlete import AthleteProfile
    from app.db.session import SessionLocal
    db = SessionLocal()
    profile = db.query(AthleteProfile).filter(AthleteProfile.user_id == test_user.id).first()
    if not profile:
        profile = AthleteProfile(user_id=test_user.id, sport_type="Soccer", age=22, height_cm=175.0, weight_kg=70.0)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    athlete_id = profile.id
    db.close()

    fake_file = io.BytesIO(b"malicious script or invalid file contents")
    files = {"file": ("script.sh", fake_file, "text/x-sh")}
    data = {"athlete_id": athlete_id, "movement_type": "squatting"}
    resp = client.post("/api/v1/videos/", files=files, data=data, headers=auth_headers)
    assert resp.status_code == 400
    assert "Unsupported file format" in resp.json().get("detail", "")

def test_video_upload_empty_file(test_user, auth_headers):
    """Validates that empty 0-byte video files are rejected with 400."""
    from app.models.athlete import AthleteProfile
    from app.db.session import SessionLocal
    db = SessionLocal()
    profile = db.query(AthleteProfile).filter(AthleteProfile.user_id == test_user.id).first()
    if not profile:
        profile = AthleteProfile(user_id=test_user.id, sport_type="Soccer", age=22, height_cm=175.0, weight_kg=70.0)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    athlete_id = profile.id
    db.close()

    empty_file = io.BytesIO(b"")
    files = {"file": ("empty.mp4", empty_file, "video/mp4")}
    data = {"athlete_id": athlete_id, "movement_type": "squatting"}
    resp = client.post("/api/v1/videos/", files=files, data=data, headers=auth_headers)
    assert resp.status_code == 400
    assert "empty" in resp.json().get("detail", "").lower()

def test_video_upload_nonexistent_athlete(auth_headers):
    """Validates that uploading video for a non-existent athlete ID returns 404."""
    fake_video = io.BytesIO(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00" + b"x" * 1000)
    files = {"file": ("test.mp4", fake_video, "video/mp4")}
    data = {"athlete_id": 999999, "movement_type": "running"}
    resp = client.post("/api/v1/videos/", files=files, data=data, headers=auth_headers)
    assert resp.status_code == 404

def test_dataset_simulator_invalid_id():
    """Validates that simulator returns 404 for unknown dataset identifier."""
    resp = client.get("/api/v1/datasets/non_existent_dataset_xyz/sample")
    assert resp.status_code == 404

def test_notification_mark_nonexistent(auth_headers):
    """Validates that marking a non-existent notification returns 404."""
    resp = client.patch("/api/v1/notifications/999999/read", headers=auth_headers)
    assert resp.status_code == 404

def test_report_export_invalid_format(test_user, auth_headers):
    """Validates that requesting an unsupported report type returns 422 Unprocessable Entity."""
    from app.models.athlete import AthleteProfile
    from app.db.session import SessionLocal
    db = SessionLocal()
    profile = db.query(AthleteProfile).filter(AthleteProfile.user_id == test_user.id).first()
    if not profile:
        profile = AthleteProfile(user_id=test_user.id, sport_type="Soccer", age=22, height_cm=175.0, weight_kg=70.0)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    athlete_id = profile.id
    db.close()

    resp = client.get(f"/api/v1/reports/{athlete_id}/export/pdf?report_type=invalid_report_xyz", headers=auth_headers)
    assert resp.status_code == 422
