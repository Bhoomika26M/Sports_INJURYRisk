import os

# Must be set before the app is imported
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "100000")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.main import app


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    from app import models  # noqa: F401

    Base.metadata.create_all(engine)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setattr(settings, "REPORT_DIR", str(tmp_path / "reports"))
    monkeypatch.setattr(settings, "POSE_DIR", str(tmp_path / "pose"))
    # Don't run the heavy pose pipeline during API tests
    monkeypatch.setattr("app.api.videos.run_analysis", lambda video_id: None)
    app.state.testing_session = TestingSession
    yield TestClient(app)
    app.dependency_overrides.clear()


def register(client, email, role="athlete", password="Passw0rd!x", name=None):
    r = client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": name or email.split("@")[0].title() + " Test", "role": role})
    assert r.status_code == 201, r.text
    return r.json()


def login(client, email, password="Passw0rd!x"):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


ATHLETE_PAYLOAD = {"sport_type": "football", "position": "midfielder", "age": 22, "height_cm": 178, "weight_kg": 72}
