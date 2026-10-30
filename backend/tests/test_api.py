import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.risk_scoring_engine import RiskScoringEngine

client = TestClient(app)

def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert isinstance(data.get("mediapipe_ready"), bool)

def test_datasets():
    response = client.get("/api/datasets")
    assert response.status_code == 200
    data = response.json()
    assert data["total_datasets"] >= 5
    assert "normative_benchmarks" in data

def test_auth_login():
    # Login with seeded athlete
    response = client.post("/api/auth/login", json={
        "email": "athlete@sportsai.com",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["role"] == "athlete"

def test_athletes_list():
    response = client.get("/api/athletes")
    assert response.status_code == 200
    athletes = response.json()
    assert len(athletes) >= 5
    assert any(a["athlete_code"] == "ATH-101" for a in athletes)

def test_weighted_scoring_formula():
    engine = RiskScoringEngine()
    biomechanics = {
        "knee_valgus_left_max": 16.5,
        "knee_valgus_right_max": 18.0,
        "trunk_lean_lateral_max": 12.0,
        "landing_mechanics_score": 45.0,
        "movement_symmetry_score": 75.0
    }
    athlete_profile = {
        "acwr": 1.45,
        "training_load": 18.0,
        "injury_history": [{"injury_name": "ACL Tear", "severity": "Surgical", "status": "Vulnerable"}]
    }
    scores = engine.compute_scores(biomechanics, athlete_profile, fatigue_drift_pct=22.0)
    
    # Check weighted formula sum:
    # 0.35 * dev + 0.20 * hist + 0.20 * asym + 0.15 * load + 0.10 * fatigue
    expected = (
        0.35 * scores["biomechanical_deviation_score"] +
        0.20 * scores["historical_injury_factor_score"] +
        0.20 * scores["movement_asymmetry_score"] +
        0.15 * scores["training_load_indicator_score"] +
        0.10 * scores["fatigue_indicator_score"]
    )
    assert abs(scores["overall_injury_risk_score"] - round(expected, 1)) < 0.2
    assert scores["risk_category"] in ["High Risk", "Critical Risk"]

def test_dashboards():
    coach_res = client.get("/api/dashboards/coach")
    assert coach_res.status_code == 200
    coach_data = coach_res.json()
    assert "summary" in coach_data
    assert "roster" in coach_data

    physio_res = client.get("/api/dashboards/physiotherapist")
    assert physio_res.status_code == 200
    physio_data = physio_res.json()
    assert "rehab_registry" in physio_data

    scientist_res = client.get("/api/dashboards/sports_scientist")
    assert scientist_res.status_code == 200
    scientist_data = scientist_res.json()
    assert "scientific_overview" in scientist_data

def test_auth_registration_and_rbac():
    import uuid
    unique_email = f"user_{uuid.uuid4().hex[:6]}@kinematix.app"
    
    # 1. Register new user
    reg_res = client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "TestPassword123!",
        "full_name": "Test Athlete",
        "role": "athlete"
    })
    assert reg_res.status_code == 200
    user_data = reg_res.json()
    assert user_data["email"] == unique_email
    assert user_data["role"] == "athlete"

    # 2. Duplicate registration fails
    dup_res = client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "TestPassword123!",
        "full_name": "Test Athlete",
        "role": "athlete"
    })
    assert dup_res.status_code == 400

    # 3. Login with newly registered user
    login_res = client.post("/api/auth/login", json={
        "email": unique_email,
        "password": "TestPassword123!"
    })
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # 4. Athlete is denied access to admin-only user listing
    users_res = client.get("/api/auth/users", headers={"Authorization": f"Bearer {token}"})
    assert users_res.status_code == 403

def test_forgot_and_reset_password_flow():
    import hashlib
    from datetime import datetime, timedelta
    from app.database import SessionLocal
    from app.models.user import User, PasswordResetToken

    # 1. Forgot password request (never exposes token in response)
    res = client.post("/api/auth/forgot-password", json={"email": "coach@sportsai.com"})
    assert res.status_code == 200
    assert "token" not in res.json()
    assert "password reset instructions" in res.json()["message"]
    assert "email delivery is configured" in res.json()["message"]

    # 2. Simulate secure token generation in DB
    raw_token = "secret_reset_token_xyz_987"
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    with SessionLocal() as db:
        user = db.query(User).filter(User.email == "coach@sportsai.com").first()
        assert user is not None
        # Add active reset token
        reset_record = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.utcnow() + timedelta(minutes=15),
            used=False
        )
        db.add(reset_record)
        db.commit()

    # 3. Perform password reset with valid token
    reset_res = client.post("/api/auth/reset-password", json={
        "token": raw_token,
        "new_password": "NewCoachPassword456!"
    })
    assert reset_res.status_code == 200
    assert "successfully updated" in reset_res.json()["message"]

    # 4. Single-use enforcement: using the same token again must fail
    replay_res = client.post("/api/auth/reset-password", json={
        "token": raw_token,
        "new_password": "AnotherPassword789!"
    })
    assert replay_res.status_code == 400
    assert "previously used" in replay_res.json()["detail"] or "Invalid" in replay_res.json()["detail"]

    # 5. Verify new password works for login
    login_new = client.post("/api/auth/login", json={
        "email": "coach@sportsai.com",
        "password": "NewCoachPassword456!"
    })
    assert login_new.status_code == 200

def test_admin_user_management():
    # Login as admin
    admin_login = client.post("/api/auth/login", json={
        "email": "admin@sportsai.com",
        "password": "password123"
    })
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["access_token"]

    # Administrator can view user list
    users_res = client.get("/api/auth/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert users_res.status_code == 200
    users = users_res.json()
    assert len(users) >= 5
    roles = {u["role"] for u in users}
    assert "administrator" in roles
    assert "athlete" in roles
    assert "coach" in roles

def test_video_upload_validation():
    # Movement metadata is mandatory and must use a supported label.
    missing_movement = client.post(
        "/api/videos/upload",
        files={"file": ("demo.mp4", b"not a video", "video/mp4")},
        data={"title": "Missing Movement"},
    )
    assert missing_movement.status_code == 422

    invalid_movement = client.post(
        "/api/videos/upload",
        files={"file": ("demo.mp4", b"not a video", "video/mp4")},
        data={"title": "Unsupported Movement", "activity_type": "Basketball"},
    )
    assert invalid_movement.status_code == 400
    assert "Select a supported movement" in invalid_movement.json()["detail"]
    # 1. Unsupported format rejection
    invalid_file = ("test.txt", b"not a video", "text/plain")
    res = client.post("/api/videos/upload", files={"file": invalid_file}, data={"title": "Test Invalid", "activity_type": "Drop Jump"})
    assert res.status_code == 400
    assert "Unsupported video format" in res.json()["detail"]

    # 2. Empty file rejection
    empty_file = ("empty.mp4", b"", "video/mp4")
    res_empty = client.post("/api/videos/upload", files={"file": empty_file}, data={"title": "Empty File", "activity_type": "Drop Jump"})
    assert res_empty.status_code == 400
    assert "empty" in res_empty.json()["detail"] or "0 bytes" in res_empty.json()["detail"]

def test_video_endpoints_and_streaming():
    videos_res = client.get("/api/videos")
    assert videos_res.status_code == 200
    videos = videos_res.json()
    assert len(videos) > 0
    vid_id = videos[0]["id"]

    vid_detail = client.get(f"/api/videos/{vid_id}")
    assert vid_detail.status_code == 200
    assert vid_detail.json()["id"] == vid_id

    # Test stream endpoint
    stream_res = client.get(f"/api/videos/{vid_id}/stream")
    assert stream_res.status_code in [200, 206]

def test_missed_detections_safe_handling():
    from app.services.biomechanics_engine import BiomechanicsEngine
    from app.services.anomaly_detection_engine import AnomalyDetectionEngine

    engine = BiomechanicsEngine()

    # 1. Case: Complete missed detection / occlusion (must NOT fabricate metrics)
    occluded_series = [
        {"frame": 0, "time": 0.0, "detected": False, "knee_valgus_l": None, "knee_valgus_r": None},
        {"frame": 1, "time": 0.033, "detected": False, "knee_valgus_l": None, "knee_valgus_r": None},
    ]
    summary = engine.analyze(occluded_series, fps=30.0)
    assert summary["detection_rate_pct"] == 0.0
    assert summary["knee_valgus_left_max"] == 0.0
    assert summary["knee_valgus_right_max"] == 0.0
    assert summary["tracking_status"] == "No athlete landmarks detected"

    # 2. Case: Partial detection (metrics computed strictly from detected frames)
    mixed_series = [
        {"frame": 0, "time": 0.0, "detected": False, "knee_valgus_l": None, "knee_valgus_r": None},
        {"frame": 1, "time": 0.033, "detected": True, "knee_angle_l": 120.0, "knee_angle_r": 125.0, "knee_valgus_l": 14.5, "knee_valgus_r": 16.0, "trunk_lateral_lean": 7.0, "pelvic_drop": 2.0, "bilateral_asymmetry": 10.0},
        {"frame": 2, "time": 0.067, "detected": False, "knee_valgus_l": None, "knee_valgus_r": None},
    ]
    mixed_summary = engine.analyze(mixed_series, fps=30.0)
    assert mixed_summary["knee_valgus_left_max"] == 14.5
    assert mixed_summary["knee_valgus_right_max"] == 16.0

    # 3. Anomaly detection ignores occluded frames
    anomaly_engine = AnomalyDetectionEngine()
    anomalies = anomaly_engine.detect_anomalies(mixed_series)
    # The single detected frame has valgus_r = 16.0 >= 15.0, so exactly 1 anomaly is detected
    assert len(anomalies["events"]) == 1
    assert anomalies["events"][0]["frame_index"] == 1

def test_admin_dashboard_endpoint():
    res = client.get("/api/dashboards/admin")
    assert res.status_code == 200
    data = res.json()
    assert "system_metrics" in data
    assert "role_breakdown" in data
    assert "users" in data
    assert "audit_logs" in data
    assert "methodology_notice" in data
    assert data["system_metrics"]["total_registered_users"] >= 5
    assert "athlete" in data["role_breakdown"]
    assert "administrator" in data["role_breakdown"]

def test_reports_pdf_and_excel_export():
    # 1. Successful PDF report export
    pdf_res = client.get("/api/reports/1/pdf")
    assert pdf_res.status_code == 200
    assert pdf_res.headers["content-type"] == "application/pdf"
    assert pdf_res.content.startswith(b"%PDF-")
    assert "kinematix" in pdf_res.headers.get("content-disposition", "").lower()

    # 2. Successful Excel spreadsheet export
    excel_res = client.get("/api/reports/1/excel")
    assert excel_res.status_code == 200
    assert "spreadsheet" in excel_res.headers["content-type"] or "vnd.openxmlformats" in excel_res.headers["content-type"]
    assert excel_res.content.startswith(b"PK\x03\x04")  # XLSX zip magic bytes

    # 3. Nonexistent video ID returns 404
    err_res = client.get("/api/reports/999999/pdf")
    assert err_res.status_code == 404

def test_athlete_risk_trends_endpoint():
    res = client.get("/api/injury_risk/athlete/1/trends")
    assert res.status_code == 200
    data = res.json()
    assert data["athlete_id"] == 1
    assert "trends" in data
    assert isinstance(data["trends"], list)
    if len(data["trends"]) > 0:
        first = data["trends"][0]
        assert "overall_injury_risk_score" in first
        assert "movement_quality_score" in first
        assert "biomechanical_deviation_score" in first

def test_demo_samples_endpoints():
    res = client.get("/api/videos/demo_samples")
    assert res.status_code == 200
    samples = res.json()
    assert isinstance(samples, list)
    if len(samples) > 0:
        first = samples[0]
        assert "filename" in first
        assert "file_size" in first
        assert "suggested_activity" in first

        load_res = client.post(f"/api/videos/demo_samples/load?filename={first['filename']}")
        assert load_res.status_code == 200
        video_data = load_res.json()
        assert video_data["status"] == "uploaded"
        assert video_data["duration_seconds"] > 0
