"""Share box API, research export, admin report list, squat landing rule."""

import io

from openpyxl import load_workbook

from app.services.analysis_pipeline import analyze_pose
from app.services.analysis_pipeline import run_analysis
from tests.synthetic import make_sequence
from tests.test_api import ATHLETE_PAYLOAD, login, register
from tests.test_pose_pipeline import FakeBackend, _upload


def test_squat_has_no_landing_metric_but_jump_check_still_runs():
    seq = make_sequence(frames=120)
    squat = analyze_pose(seq, 30.0, "squatting")
    assert squat["biomechanics"]["metrics"]["landing_knee_flexion_deg"] is None
    assert all(i["metric"] != "landing_knee_flexion_deg" for i in squat["deviations"])


def test_athlete_can_share_and_revoke_access(client):
    register(client, "ath@example.com")
    register(client, "sci@example.com", role="sports_scientist")
    h, hs = login(client, "ath@example.com"), login(client, "sci@example.com")
    a = client.post("/api/v1/athletes", json=ATHLETE_PAYLOAD, headers=h).json()
    assert client.get(f"/api/v1/athletes/{a['id']}", headers=hs).status_code == 404
    r = client.post(f"/api/v1/athletes/{a['id']}/access", json={"email": "sci@example.com"}, headers=h)
    assert r.status_code == 201
    assert client.get(f"/api/v1/athletes/{a['id']}", headers=hs).status_code == 200
    listed = client.get(f"/api/v1/athletes/{a['id']}/access", headers=h).json()
    assert [p["email"] for p in listed] == ["sci@example.com"]
    assert client.delete(f"/api/v1/athletes/{a['id']}/access/{r.json()['user_id']}", headers=h).status_code == 204
    assert client.get(f"/api/v1/athletes/{a['id']}", headers=hs).status_code == 404


def test_research_export_is_role_limited_and_hides_names(client, tmp_path, monkeypatch):
    h, vid = _upload(client, tmp_path, monkeypatch, FakeBackend())
    run_analysis(vid)
    assert client.get("/api/v1/reports/research", headers=h).status_code == 403  # the athlete themself

    register(client, "sci@example.com", role="sports_scientist")
    hs = login(client, "sci@example.com")
    athlete = client.get("/api/v1/athletes", headers=h).json()[0]
    # nothing shared yet: the export is empty but valid
    empty = client.get("/api/v1/reports/research", headers=hs)
    assert empty.status_code == 200
    wb = load_workbook(io.BytesIO(empty.content))
    assert wb["Athletes"].max_row == 1

    client.post(f"/api/v1/athletes/{athlete['id']}/access", json={"email": "sci@example.com"}, headers=h)
    full = client.get("/api/v1/reports/research", headers=hs)
    wb = load_workbook(io.BytesIO(full.content))
    assert wb.sheetnames == ["Athletes", "Analyses"]
    assert wb["Athletes"].max_row == 2 and wb["Analyses"].max_row == 2
    cells = [str(c.value) for sheet in wb for row in sheet.iter_rows() for c in row if c.value is not None]
    assert athlete["athlete_code"] in cells
    assert not any(athlete["full_name"] in c for c in cells)


def test_admin_sees_all_reports(client, tmp_path, monkeypatch):
    h, vid = _upload(client, tmp_path, monkeypatch, FakeBackend())
    run_analysis(vid)
    analysis = client.get("/api/v1/analyses", headers=h).json()[0]
    assert client.post(f"/api/v1/reports/generate?analysis_id={analysis['id']}&report_type=injury_risk&file_format=xlsx", headers=h).status_code == 201
    from app.core.config import settings
    register(client, "boss@example.com")
    # promote to admin directly in the test database
    from app.models.user import User
    from sqlalchemy import select
    with client.app.state.testing_session() as db:
        u = db.scalar(select(User).where(User.email == "boss@example.com"))
        u.role = "administrator"
        db.commit()
    hb = login(client, "boss@example.com")
    assert len(client.get("/api/v1/reports", headers=hb).json()) == 1
