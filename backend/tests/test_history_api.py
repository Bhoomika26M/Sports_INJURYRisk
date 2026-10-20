"""API-level tests for athlete history and per-video comparison endpoints.

Uses the same per-test ``get_db`` override isolation as test_video_upload.py
(module-level overrides get cleared by other test modules).
"""

import secrets
from datetime import datetime, timedelta
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.database import Base, get_db
from app.models.user import User
from app.models.athlete import Athlete
from app.models.video import Video, ProcessingStatus
from app.models.pose_analysis import PoseAnalysis
from app.models.analysis_snapshot import AnalysisSnapshot
from app.core.security import (
    create_access_token,
    create_user_session,
    get_password_hash,
)

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_history_api.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    previous = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    from app.core.rate_limit import rate_limiter
    with rate_limiter.lock:
        rate_limiter.requests.clear()
    yield
    with rate_limiter.lock:
        rate_limiter.requests.clear()


def _user(db, role="athlete"):
    u = User(
        email=f"h{secrets.token_hex(6)}@example.com",
        password_hash=get_password_hash("password123"),
        full_name="H User",
        role=role,
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _headers(db, user):
    token_data = create_access_token(
        data={"sub": user.email}, expires_delta=timedelta(minutes=30)
    )
    create_user_session(db, user, token_data["jti"], token_data["expires_at"])
    return {"Authorization": f"Bearer {token_data['access_token']}"}


def _athlete(db, user=None):
    a = Athlete(
        athlete_id=f"ATH{secrets.token_hex(4)}",
        user_id=(user.id if user else None),
        sport_type="Basketball",
        age=24,
        height=180.0,
        weight=75.0,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


def _video(db, athlete, activity="squat", days_ago=0):
    v = Video(
        athlete_id=athlete.id,
        uploaded_by=1,
        filename=f"{secrets.token_hex(8)}.mp4",
        original_filename="in.mp4",
        storage_path="uploads/in.mp4",
        activity_type=activity,
        processing_status=ProcessingStatus.COMPLETED,
        created_at=datetime.utcnow() - timedelta(days=days_ago),
    )
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


def _snap(db, athlete, score, activity="squat", days_ago=0, comparison=None):
    v = _video(db, athlete, activity, days_ago=days_ago)
    s = AnalysisSnapshot(
        athlete_id=athlete.id,
        video_id=v.id,
        activity_type=activity,
        sequence_index=1,
        performed_at=v.created_at,
        overall_risk_score=score,
        risk_level="low",
        findings_count=0,
        metrics={"risk_score": score},
        baseline_comparison=comparison,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


# --------------------------------------------------------------------------- #
# History endpoint
# --------------------------------------------------------------------------- #

def test_history_returns_entries_and_trends(client, db):
    user = _user(db)
    athlete = _athlete(db, user)
    for i, score in enumerate([10.0, 20.0, 40.0]):
        _snap(db, athlete, score, days_ago=5 - i)

    resp = client.get(
        f"/api/v1/athletes/{athlete.id}/history", headers=_headers(db, user)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["athlete_id"] == athlete.id
    assert body["total_analyses"] == 3
    # Chronological, oldest first.
    assert [e["overall_risk_score"] for e in body["entries"]] == [10.0, 20.0, 40.0]
    assert body["trends"][0]["direction"] == "worsening"


def test_history_empty_for_new_athlete(client, db):
    user = _user(db)
    athlete = _athlete(db, user)

    resp = client.get(
        f"/api/v1/athletes/{athlete.id}/history", headers=_headers(db, user)
    )
    assert resp.status_code == 200
    assert resp.json()["total_analyses"] == 0
    assert resp.json()["entries"] == []


def test_history_filter_by_activity(client, db):
    user = _user(db)
    athlete = _athlete(db, user)
    _snap(db, athlete, 10.0, activity="squat", days_ago=3)
    _snap(db, athlete, 90.0, activity="running", days_ago=2)

    resp = client.get(
        f"/api/v1/athletes/{athlete.id}/history?activity=running",
        headers=_headers(db, user),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_analyses"] == 1
    assert body["entries"][0]["activity_type"] == "running"


def test_history_requires_auth(client, db):
    athlete = _athlete(db)
    resp = client.get(f"/api/v1/athletes/{athlete.id}/history")
    assert resp.status_code == 401


def test_history_idor_athlete_cannot_read_others(client, db):
    """An athlete must not be able to read another athlete's history."""
    me = _user(db)
    other_user = _user(db)
    my_athlete = _athlete(db, me)
    other_athlete = _athlete(db, other_user)
    _snap(db, other_athlete, 50.0)

    resp = client.get(
        f"/api/v1/athletes/{other_athlete.id}/history", headers=_headers(db, me)
    )
    assert resp.status_code == 403
    # Sanity: my own history is reachable.
    ok = client.get(
        f"/api/v1/athletes/{my_athlete.id}/history", headers=_headers(db, me)
    )
    assert ok.status_code == 200


def test_history_professional_can_read_any(client, db):
    coach = _user(db, role="coach")
    athlete = _athlete(db)
    _snap(db, athlete, 50.0)

    resp = client.get(
        f"/api/v1/athletes/{athlete.id}/history", headers=_headers(db, coach)
    )
    assert resp.status_code == 200
    assert resp.json()["total_analyses"] == 1


# --------------------------------------------------------------------------- #
# Comparison endpoint
# --------------------------------------------------------------------------- #

def test_comparison_returns_recorded_result(client, db):
    user = _user(db)
    athlete = _athlete(db, user)
    recorded = {
        "status": "changed",
        "baseline_size": 4,
        "baseline_window": 5,
        "summary": "Change versus baseline - elevated: injury risk score.",
        "deltas": [],
        "flags": [],
        "deteriorations": ["risk_score"],
        "improvements": [],
    }
    snap = _snap(db, athlete, 70.0, days_ago=1, comparison=recorded)

    resp = client.get(
        f"/api/v1/videos/{snap.video_id}/comparison", headers=_headers(db, user)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "changed"
    assert body["deteriorations"] == ["risk_score"]


def test_comparison_404_before_processing(client, db):
    user = _user(db)
    athlete = _athlete(db, user)
    video = _video(db, athlete)

    resp = client.get(
        f"/api/v1/videos/{video.id}/comparison", headers=_headers(db, user)
    )
    assert resp.status_code == 404


def test_comparison_returns_no_history_when_unrecorded(client, db):
    user = _user(db)
    athlete = _athlete(db, user)
    snap = _snap(db, athlete, 20.0, comparison=None)

    resp = client.get(
        f"/api/v1/videos/{snap.video_id}/comparison", headers=_headers(db, user)
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "no_history"


def test_comparison_idor_other_athlete_blocked(client, db):
    me = _user(db)
    other_user = _user(db)
    _athlete(db, me)
    other_athlete = _athlete(db, other_user)
    snap = _snap(db, other_athlete, 50.0)

    resp = client.get(
        f"/api/v1/videos/{snap.video_id}/comparison", headers=_headers(db, me)
    )
    assert resp.status_code == 403
