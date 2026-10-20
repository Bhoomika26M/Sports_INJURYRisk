import cv2
import numpy as np

from app.models.user import Role, User
from app.core.security import hash_password
from tests.conftest import ATHLETE_PAYLOAD, login, register


def make_video(path, frames=45, fps=30, size=(320, 240)):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
    rng = np.random.default_rng(0)
    for i in range(frames):
        frame = (rng.random((size[1], size[0], 3)) * 255).astype(np.uint8)
        cv2.rectangle(frame, (50 + i, 50), (120 + i, 200), (200, 200, 200), -1)
        writer.write(frame)
    writer.release()


# --- Authentication -----------------------------------------------------------


def test_register_login_me(client):
    register(client, "a@example.com")
    headers = login(client, "a@example.com")
    me = client.get("/api/v1/auth/me", headers=headers).json()
    assert me["email"] == "a@example.com" and me["role"] == "athlete"


def test_duplicate_email_and_bad_password(client):
    register(client, "a@example.com")
    assert client.post("/api/v1/auth/register", json={"email": "a@example.com", "password": "Passw0rd!x", "full_name": "Dup Test"}).status_code == 409
    assert client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "wrong-password"}).status_code == 401


def test_cannot_self_register_as_admin(client):
    r = client.post("/api/v1/auth/register", json={"email": "x@example.com", "password": "Passw0rd!x", "full_name": "Evil Admin", "role": "administrator"})
    assert r.status_code == 422


def test_oauth2_password_form_flow(client):
    register(client, "a@example.com")
    r = client.post("/api/v1/auth/token", data={"username": "a@example.com", "password": "Passw0rd!x"})
    assert r.status_code == 200 and r.json()["token_type"] == "bearer"


def test_protected_routes_require_token(client):
    assert client.get("/api/v1/athletes").status_code == 401
    assert client.get("/api/v1/athletes", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_google_login_disabled_without_client_id(client):
    assert client.post("/api/v1/auth/oauth/google", json={"id_token": "x"}).status_code == 501


# --- Roles and athlete-level access -------------------------------------------


def test_admin_endpoints_forbidden_for_non_admin(client):
    register(client, "a@example.com")
    headers = login(client, "a@example.com")
    assert client.get("/api/v1/users", headers=headers).status_code == 403
    assert client.get("/api/v1/dashboards/admin", headers=headers).status_code == 403
    assert client.get("/api/v1/dashboards/coach", headers=headers).status_code == 403


def test_athlete_privacy_and_consented_sharing(client):
    register(client, "ath1@example.com")
    register(client, "ath2@example.com")
    register(client, "coach@example.com", role="coach")
    h1, h2, hc = login(client, "ath1@example.com"), login(client, "ath2@example.com"), login(client, "coach@example.com")

    a1 = client.post("/api/v1/athletes", json=ATHLETE_PAYLOAD, headers=h1).json()
    a2 = client.post("/api/v1/athletes", json=ATHLETE_PAYLOAD, headers=h2).json()
    assert client.post("/api/v1/athletes", json=ATHLETE_PAYLOAD, headers=h1).status_code == 409  # one profile each

    # Other athletes and unauthorised coaches get 404, not 403
    assert client.get(f"/api/v1/athletes/{a1['id']}", headers=h2).status_code == 404
    assert client.get(f"/api/v1/athletes/{a1['id']}", headers=hc).status_code == 404
    assert client.get("/api/v1/athletes", headers=hc).json() == []

    # Athlete 1 grants the coach access; athlete 2 is still hidden
    assert client.post(f"/api/v1/athletes/{a1['id']}/access", json={"email": "coach@example.com"}, headers=h1).status_code == 201
    assert [a["id"] for a in client.get("/api/v1/athletes", headers=hc).json()] == [a1["id"]]
    assert client.get(f"/api/v1/athletes/{a2['id']}", headers=hc).status_code == 404

    # Only the owner may change sharing
    assert client.post(f"/api/v1/athletes/{a1['id']}/access", json={"email": "coach@example.com"}, headers=hc).status_code in (403, 409)

    # Revoke
    coach_id = client.get("/api/v1/auth/me", headers=hc).json()["id"]
    assert client.delete(f"/api/v1/athletes/{a1['id']}/access/{coach_id}", headers=h1).status_code == 204
    assert client.get(f"/api/v1/athletes/{a1['id']}", headers=hc).status_code == 404


def test_scientist_is_read_only(client):
    register(client, "ath@example.com")
    register(client, "sci@example.com", role="sports_scientist")
    ha, hs = login(client, "ath@example.com"), login(client, "sci@example.com")
    a = client.post("/api/v1/athletes", json=ATHLETE_PAYLOAD, headers=ha).json()
    client.post(f"/api/v1/athletes/{a['id']}/access", json={"email": "sci@example.com"}, headers=ha)
    assert client.get(f"/api/v1/athletes/{a['id']}", headers=hs).status_code == 200
    r = client.post(f"/api/v1/athletes/{a['id']}/injuries", json={"injury_type": "Sprain", "body_part": "ankle", "injury_date": "2025-01-01"}, headers=hs)
    assert r.status_code == 404


def test_coach_creates_athlete_and_records_history(client):
    register(client, "coach@example.com", role="coach")
    hc = login(client, "coach@example.com")
    a = client.post("/api/v1/athletes", json={**ATHLETE_PAYLOAD, "full_name": "Sam Runner"}, headers=hc)
    assert a.status_code == 201
    aid = a.json()["id"]
    assert client.post(f"/api/v1/athletes/{aid}/injuries", json={"injury_type": "ACL tear", "body_part": "knee", "injury_date": "2024-05-01", "severity": "severe"}, headers=hc).status_code == 201
    load = client.post(f"/api/v1/athletes/{aid}/training-load", json={"entry_date": "2026-01-10", "duration_min": 60, "rpe": 7}, headers=hc).json()
    assert load["load_au"] == 420
    assert client.post(f"/api/v1/athletes/{aid}/assessments", json={"notes": "baseline", "metrics": {"sit_and_reach_cm": 24}}, headers=hc).status_code == 201
    assert len(client.get(f"/api/v1/athletes/{aid}/injuries", headers=hc).json()) == 1


def test_athlete_input_validation(client):
    register(client, "a@example.com")
    h = login(client, "a@example.com")
    assert client.post("/api/v1/athletes", json={**ATHLETE_PAYLOAD, "age": 3}, headers=h).status_code == 422
    assert client.post("/api/v1/athletes", json={**ATHLETE_PAYLOAD, "height_cm": 500}, headers=h).status_code == 422


# --- Video upload ---------------------------------------------------------------


def _setup_athlete(client):
    register(client, "a@example.com")
    h = login(client, "a@example.com")
    a = client.post("/api/v1/athletes", json=ATHLETE_PAYLOAD, headers=h).json()
    return h, a


def test_upload_valid_video(client, tmp_path):
    h, a = _setup_athlete(client)
    path = tmp_path / "clip.mp4"
    make_video(path)
    with path.open("rb") as f:
        r = client.post("/api/v1/videos/upload", headers=h, data={"athlete_id": a["id"], "activity": "squatting"}, files={"file": ("../../evil name.mp4", f, "video/mp4")})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["width"] == 320 and body["frame_count"] > 0 and body["status"] == "uploaded"
    assert ".." not in body["original_filename"] and "/" not in body["original_filename"]
    assert client.get(f"/api/v1/videos/{body['id']}", headers=h).status_code == 200


def test_upload_rejects_bad_files(client, tmp_path):
    h, a = _setup_athlete(client)
    data = {"athlete_id": a["id"], "activity": "squatting"}
    r = client.post("/api/v1/videos/upload", headers=h, data=data, files={"file": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 415
    r = client.post("/api/v1/videos/upload", headers=h, data=data, files={"file": ("fake.mp4", b"not really a video", "video/mp4")})
    assert r.status_code == 422
    r = client.post("/api/v1/videos/upload", headers=h, data={**data, "activity": "knitting"}, files={"file": ("a.mp4", b"x", "video/mp4")})
    assert r.status_code == 422
    assert not list((tmp_path / "uploads").glob("*"))  # rejected files are cleaned up


def test_upload_rejects_low_resolution(client, tmp_path):
    h, a = _setup_athlete(client)
    path = tmp_path / "tiny.mp4"
    make_video(path, size=(160, 120))
    with path.open("rb") as f:
        r = client.post("/api/v1/videos/upload", headers=h, data={"athlete_id": a["id"], "activity": "running"}, files={"file": ("tiny.mp4", f, "video/mp4")})
    assert r.status_code == 422 and "Resolution" in str(r.json())


def test_cannot_upload_for_someone_elses_athlete(client, tmp_path):
    _, a = _setup_athlete(client)
    register(client, "other@example.com")
    ho = login(client, "other@example.com")
    path = tmp_path / "clip.mp4"
    make_video(path)
    with path.open("rb") as f:
        r = client.post("/api/v1/videos/upload", headers=ho, data={"athlete_id": a["id"], "activity": "squatting"}, files={"file": ("clip.mp4", f, "video/mp4")})
    assert r.status_code == 404


# --- Analysis, dashboards, notifications, reports ---------------------------------


def _seed_analysis(client, athlete_id, uploader_email="a@example.com"):
    """Store an analysis computed from synthetic keypoints (skips the video/pose stage)."""
    from datetime import date

    from app.models.video import Analysis, Video
    from app.services.analysis_pipeline import analyze_pose
    from app.services.notification_service import notify_analysis_complete
    from tests.synthetic import make_sequence

    Session = client.app.state.testing_session
    with Session() as db:
        from app.models.athlete import Athlete
        from sqlalchemy import select

        athlete = db.get(Athlete, athlete_id)
        uploader = db.scalar(select(User).where(User.email == uploader_email))
        video = Video(athlete_id=athlete_id, uploaded_by=uploader.id, activity="squatting", original_filename="s.mp4", stored_path="/nonexistent", status="completed", quality={})
        db.add(video)
        db.flush()
        result = analyze_pose(
            make_sequence(valgus_offset=0.05, pelvic_drop=0.04, left_rom_scale=0.4), 30, "squatting", athlete.height_cm, athlete.weight_kg,
            injuries=[{"body_part": "knee", "injury_type": "ACL", "severity": "severe", "status": "recovering", "injury_date": date.today()}],
        )
        analysis = Analysis(video_id=video.id, athlete_id=athlete_id, activity="squatting", **result)
        db.add(analysis)
        db.commit()
        db.refresh(analysis)
        notify_analysis_complete(db, analysis, athlete, video)
        return analysis.id, analysis.risk_category


def test_analysis_dashboard_notifications_and_reports(client):
    h, a = _setup_athlete(client)
    analysis_id, category = _seed_analysis(client, a["id"])

    detail = client.get(f"/api/v1/analyses/{analysis_id}", headers=h).json()
    assert detail["risk_category"] == category and detail["recommendations"]["corrective_exercises"]
    assert client.get(f"/api/v1/analyses/athlete/{a['id']}/trend", headers=h).json()[0]["analysis_id"] == analysis_id

    dash = client.get("/api/v1/dashboards/athlete", headers=h).json()
    assert dash["latest"]["analysis_id"] == analysis_id and dash["unread_notifications"] >= 1

    notes = client.get("/api/v1/notifications", headers=h).json()
    assert any(n["type"] == "assessment_complete" for n in notes)
    assert client.post("/api/v1/notifications/read-all", headers=h).status_code == 200
    assert client.get("/api/v1/notifications/unread-count", headers=h).json()["unread"] == 0

    for rtype in ("injury_risk", "biomechanical", "movement", "performance", "rehabilitation"):
        for fmt in ("pdf", "xlsx"):
            r = client.post(f"/api/v1/reports/generate?analysis_id={analysis_id}&report_type={rtype}&file_format={fmt}", headers=h)
            assert r.status_code == 201, r.text
            dl = client.get(f"/api/v1/reports/{r.json()['id']}/download", headers=h)
            assert dl.status_code == 200 and len(dl.content) > 500
            if fmt == "pdf":
                assert dl.content.startswith(b"%PDF")
            else:
                assert dl.content.startswith(b"PK")  # xlsx is a zip container


def test_other_users_cannot_read_analysis_or_reports(client):
    h, a = _setup_athlete(client)
    analysis_id, _ = _seed_analysis(client, a["id"])
    register(client, "other@example.com")
    ho = login(client, "other@example.com")
    assert client.get(f"/api/v1/analyses/{analysis_id}", headers=ho).status_code == 404
    assert client.post(f"/api/v1/reports/generate?analysis_id={analysis_id}", headers=ho).status_code == 404


def test_role_dashboards(client):
    h, a = _setup_athlete(client)
    _seed_analysis(client, a["id"])
    for email, role, path in (
        ("coach@example.com", "coach", "coach"),
        ("physio@example.com", "physiotherapist", "physiotherapist"),
        ("sci@example.com", "sports_scientist", "scientist"),
    ):
        register(client, email, role=role)
        hr = login(client, email)
        assert client.post(f"/api/v1/athletes/{a['id']}/access", json={"email": email}, headers=h).status_code == 201
        r = client.get(f"/api/v1/dashboards/{path}", headers=hr)
        assert r.status_code == 200, r.text
    coach = client.get("/api/v1/dashboards/coach", headers=login(client, "coach@example.com")).json()
    assert coach["team_overview"]["assessed"] == 1 and coach["athletes"][0]["athlete_id"] == a["id"]
    sci = client.get("/api/v1/dashboards/scientist", headers=login(client, "sci@example.com")).json()
    assert sci["dataset"]["analyses"] == 1 and "squatting" in sci["biomechanical_analytics"]


def test_admin_user_management_and_dashboard(client):
    Session = client.app.state.testing_session
    with Session() as db:
        db.add(User(email="admin@example.com", full_name="Admin", hashed_password=hash_password("Passw0rd!x"), role=Role.administrator.value))
        db.commit()
    register(client, "a@example.com")
    ha = login(client, "admin@example.com")
    users = client.get("/api/v1/users", headers=ha).json()
    target = next(u for u in users if u["email"] == "a@example.com")
    assert client.patch(f"/api/v1/users/{target['id']}", json={"role": "coach"}, headers=ha).json()["role"] == "coach"
    assert client.patch(f"/api/v1/users/{target['id']}", json={"is_active": False}, headers=ha).json()["is_active"] is False
    assert client.post("/api/v1/auth/login", json={"email": "a@example.com", "password": "Passw0rd!x"}).status_code == 403
    me_id = next(u["id"] for u in users if u["email"] == "admin@example.com")
    assert client.patch(f"/api/v1/users/{me_id}", json={"is_active": False}, headers=ha).status_code == 400
    dash = client.get("/api/v1/dashboards/admin", headers=ha).json()
    assert dash["users"]["total"] == 2 and dash["system"]["database_ok"] is True


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}
