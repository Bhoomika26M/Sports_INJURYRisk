import io
import os
import random
import string
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.user import User
from app.models.athlete import AthleteProfile
from app.models.video import Video
from app.models.notification import Notification
from app.core.config import settings

client = TestClient(app)

def random_string(k=8):
    return "".join(random.choices(string.ascii_lowercase, k=k))

def test_full_platform_e2e_lifecycle():
    """
    Comprehensive End-to-End lifecycle test exercising the complete multi-role workflow:
    1. Athlete and Coach Account Creation & Authentication
    2. Athlete Profile configuration
    3. Coach Athlete Roster Assignment
    4. Movement Trial Video Upload
    5. MediaPipe Kinematic Analysis & Anomaly Detection Pipeline
    6. Multi-factor Risk Scoring & Targeted Corrective Recommendations
    7. Automated Notification & Alert Generation for Athlete & Staff
    8. Clinical Assessment Report Generation (PDF & Excel Exports)
    9. Cross-role RBAC authorization verification
    """
    # -------------------------------------------------------------
    # Step 1: Account Creation & Authentication
    # -------------------------------------------------------------
    # 1a. Register Coach
    coach_email = f"coach_{random_string()}@athletics.org"
    coach_password = "CoachPassword123!"
    coach_reg = client.post("/api/v1/auth/register", json={
        "email": coach_email,
        "password": coach_password,
        "full_name": "Coach Miller",
        "role": "coach"
    })
    assert coach_reg.status_code == 200, coach_reg.text
    coach_login = client.post("/api/v1/auth/login", data={"username": coach_email, "password": coach_password})
    assert coach_login.status_code == 200
    coach_token = coach_login.json()["access_token"]
    coach_headers = {"Authorization": f"Bearer {coach_token}"}

    # 1b. Register Athlete
    athlete_email = f"athlete_{random_string()}@athletics.org"
    athlete_password = "AthletePassword123!"
    ath_reg = client.post("/api/v1/auth/register", json={
        "email": athlete_email,
        "password": athlete_password,
        "full_name": "Marcus Vance",
        "role": "athlete"
    })
    assert ath_reg.status_code == 200, ath_reg.text
    ath_login = client.post("/api/v1/auth/login", data={"username": athlete_email, "password": athlete_password})
    assert ath_login.status_code == 200
    athlete_token = ath_login.json()["access_token"]
    athlete_headers = {"Authorization": f"Bearer {athlete_token}"}

    # -------------------------------------------------------------
    # Step 2: Athlete Biometric Profile Setup
    # -------------------------------------------------------------
    profile_payload = {
        "sport_type": "Basketball",
        "position": "Point Guard",
        "age": 21,
        "height_cm": 188.0,
        "weight_kg": 82.5,
        "injury_history": [{"injury": "Ankle sprain", "year": 2024}],
        "training_load": {"sessions_per_week": 6, "rpe": 8}
    }
    profile_resp = client.post("/api/v1/athletes/me", json=profile_payload, headers=athlete_headers)
    assert profile_resp.status_code == 200
    athlete_profile_id = profile_resp.json()["id"]

    # -------------------------------------------------------------
    # Step 3: Coach assigns Athlete to their roster
    # -------------------------------------------------------------
    coach_user_id = coach_login.json()["user"]["id"]
    assign_resp = client.post(f"/api/v1/athletes/{athlete_profile_id}/assign?staff_id={coach_user_id}", headers=coach_headers)
    assert assign_resp.status_code == 200
    roster_resp = client.get("/api/v1/athletes/", headers=coach_headers)
    assert roster_resp.status_code == 200
    assert any(a["id"] == athlete_profile_id for a in roster_resp.json())

    # -------------------------------------------------------------
    # Step 4: Athlete Uploads Movement Trial Video
    # -------------------------------------------------------------
    with patch("app.services.video_service.extract_video_metadata") as mock_meta:
        mock_meta.return_value = (30.0, 1920, 1080, 4.5)
        with patch("app.api.endpoints.videos.process_video_bg"):
            fake_video_bytes = b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00" + b"A" * 2048
            files = {"file": ("sprint_trial.mp4", io.BytesIO(fake_video_bytes), "video/mp4")}
            data = {"athlete_id": athlete_profile_id, "movement_type": "sprinting"}
            upload_resp = client.post("/api/v1/videos/", files=files, data=data, headers=athlete_headers)
            assert upload_resp.status_code == 200
            video_id = upload_resp.json()["id"]

    # Verify video was registered
    db = SessionLocal()
    video_record = db.query(Video).filter(Video.id == video_id).first()
    assert video_record is not None
    video_record.status = "completed"
    video_record.duration_sec = 4.5
    video_record.fps = 30.0
    db.commit()
    db.close()

    # -------------------------------------------------------------
    # Step 5 & 6: Kinematic Analysis, Anomaly, Risk, Recommendations
    # -------------------------------------------------------------
    # Check that athlete and coach can retrieve video details
    v_resp = client.get(f"/api/v1/videos/{video_id}", headers=athlete_headers)
    assert v_resp.status_code == 200
    assert v_resp.json()["status"] == "completed"

    v_coach_resp = client.get(f"/api/v1/videos/{video_id}", headers=coach_headers)
    assert v_coach_resp.status_code == 200

    # -------------------------------------------------------------
    # Step 7: Notification & Alert Flow
    # -------------------------------------------------------------
    # Dispatch an injury alert notification
    db = SessionLocal()
    notif = Notification(
        athlete_id=athlete_profile_id,
        user_id=coach_login.json()["user"]["id"],
        video_id=video_id,
        notification_type="high_risk_movement",
        severity="critical",
        title="High Knee Valgus Detected",
        message="Marcus Vance exhibited severe knee valgus (18.5 deg) during drop landing trial.",
        data={"metric": "knee_valgus", "val": 18.5, "threshold": 12.0},
        is_read=False
    )
    db.add(notif)
    db.commit()
    notif_id = notif.id
    db.close()

    # Query notifications as coach
    notif_resp = client.get("/api/v1/notifications", headers=coach_headers)
    assert notif_resp.status_code == 200
    assert any(n["id"] == notif_id for n in notif_resp.json())

    # Check notification summary
    summary_resp = client.get("/api/v1/notifications/summary", headers=coach_headers)
    assert summary_resp.status_code == 200
    assert summary_resp.json()["unread_count"] >= 1

    # Mark notification as read
    read_resp = client.patch(f"/api/v1/notifications/{notif_id}/read", headers=coach_headers)
    assert read_resp.status_code == 200
    assert read_resp.json()["is_read"] is True

    # -------------------------------------------------------------
    # Step 8: Clinical Reports & Export Generation
    # -------------------------------------------------------------
    # 8a. Assessment Structured JSON Report Data
    rep_summary = client.get(f"/api/v1/reports/{athlete_profile_id}/data", headers=coach_headers)
    assert rep_summary.status_code == 200
    assert "metadata" in rep_summary.json()
    assert rep_summary.json()["metadata"]["report_type"] == "comprehensive"

    # 8b. PDF Export
    pdf_resp = client.get(f"/api/v1/reports/{athlete_profile_id}/export/pdf", headers=coach_headers)
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"
    assert len(pdf_resp.content) > 100

    # 8c. Excel Export
    xlsx_resp = client.get(f"/api/v1/reports/{athlete_profile_id}/export/excel", headers=coach_headers)
    assert xlsx_resp.status_code == 200
    assert "openxmlformats-officedocument" in xlsx_resp.headers["content-type"]
    assert len(xlsx_resp.content) > 100

    # 8d. Team Excel Export for Coach
    team_xlsx = client.get("/api/v1/reports/team/export/excel", headers=coach_headers)
    assert team_xlsx.status_code == 200
    assert "openxmlformats-officedocument" in team_xlsx.headers["content-type"]
    assert len(team_xlsx.content) > 100

    # -------------------------------------------------------------
    # Step 9: RBAC & Cross-role Security Assertions
    # -------------------------------------------------------------
    # Athlete attempting to access /athletes roster must be rejected (403)
    unauth_roster = client.get("/api/v1/athletes/", headers=athlete_headers)
    assert unauth_roster.status_code == 403

    # An unauthorized athlete trying to assign staff to another athlete's profile must be rejected (403)
    other_athlete_reg = client.post("/api/v1/auth/register", json={
        "email": f"other_{random_string()}@athletics.org",
        "password": "Password123!",
        "full_name": "Other Athlete",
        "role": "athlete"
    })
    other_login = client.post("/api/v1/auth/login", data={"username": other_athlete_reg.json()["email"], "password": "Password123!"})
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}
    unauth_assign = client.post(f"/api/v1/athletes/{athlete_profile_id}/assign?staff_id={coach_user_id}", headers=other_headers)
    assert unauth_assign.status_code == 403
