"""Regression tests for the 2026-10-27 audit: Gemini observation IS the fallback for insufficient baseline
(per user design), upload limits come from settings and are enforced while streaming, and a deployment
cannot run with the placeholder JWT secret."""

import pytest
from pydantic import ValidationError

from app.config import _DEFAULT_JWT_SECRET, Settings, settings
from tests.conftest import auth_header, register_and_login
from tests.synth import squat_frames
from tests.test_risk_assessment_api import _athlete, _score, _user, _video
from tests.test_upload_formats import _ffmpeg
from tests.test_video_api import _coach_with_athlete

import subprocess


# ------------------------------------------------------------------ scoring

@pytest.mark.asyncio
async def test_gemini_observation_can_score_below_baseline_floor(client, db_session):
    """Gemini observation IS the fallback for insufficient baseline — it produces a provisional score
    when no population baseline exists. That is why Gemini was integrated in the first place."""
    token = await register_and_login(client, "coach@t.com", "coach")
    coach = await _user(db_session, "coach@t.com")
    ath = await _athlete(db_session, coach.id)
    v = await _video(db_session, coach.id, ath.id, squat_frames(n_reps=4, seed=3, noise_m=0.004))
    v.analysis = {**v.analysis, "gemini_observation": {"overall": {"quality": "poor", "knee_valgus": "marked",
                                                                    "trunk_lean": "marked", "asymmetry": "marked"}}}
    await db_session.commit()
    r = await _score(client, token, v.id)
    assert r.status_code == 200, r.text           # Gemini supplies the provisional score below baseline floor
    assert "overall_score" in r.json()


@pytest.mark.asyncio
async def test_frontal_only_clip_gets_qualitative_composite_score(client, db_session):
    """Frontal-plane clips receive a qualitative composite score (knee valgus / hip adduction flags)
    when no sagittal validated metrics are available — the qualitative path is retained per
    SCIENCE_CONSTRAINTS.md for flagging."""
    token = await register_and_login(client, "coach@t.com", "coach")
    coach = await _user(db_session, "coach@t.com")
    ath = await _athlete(db_session, coach.id)
    v = await _video(db_session, coach.id, ath.id, squat_frames(), view="frontal")
    r = await _score(client, token, v.id)
    assert r.status_code == 200, r.text           # Qualitative frontal-plane score generated from flags


# ------------------------------------------------------------------ upload

async def _ticket(client, token, athlete_id, name="clip.mp4"):
    up = await client.post("/api/v1/videos/upload-url", headers=auth_header(token), json={
        "athlete_id": athlete_id, "movement_type": "squatting", "camera_view": "sagittal", "original_filename": name})
    assert up.status_code == 200, up.text
    return up.json()


async def test_oversized_upload_is_refused_with_413_and_leaves_no_file(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    monkeypatch.setattr(settings, "max_upload_mb", 1)
    token, athlete_id = await _coach_with_athlete(client)
    t = await _ticket(client, token, athlete_id)
    url = f"/api/v1/local-storage/{t['storage_key']}"

    declared = await client.put(url, headers=auth_header(token), content=b"x" * (2 * 1024 * 1024))   # Content-Length says too big
    assert declared.status_code == 413 and not (tmp_path / t["storage_key"]).exists()

    async def chunks():                                                                             # no Content-Length: counted as it streams
        for _ in range(3):
            yield b"x" * (512 * 1024)
    streamed = await client.put(url, headers=auth_header(token), content=chunks())
    assert streamed.status_code == 413 and not (tmp_path / t["storage_key"]).exists()

    ok = await client.put(url, headers=auth_header(token), content=b"x" * 1024)                     # the ticket is still usable
    assert ok.status_code == 200


async def test_confirming_without_a_stored_file_is_404_not_400(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    token, athlete_id = await _coach_with_athlete(client)
    t = await _ticket(client, token, athlete_id)
    r = await client.post(f"/api/v1/videos/{t['video_id']}/confirm-upload", headers=auth_header(token))
    assert r.status_code == 404


async def test_duration_limit_comes_from_settings(client, tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    monkeypatch.setattr("app.modules.video.router.enqueue", lambda _id: None)
    monkeypatch.setattr(settings, "max_video_seconds", 2.0)
    clip = tmp_path / "src.mp4"
    subprocess.run([_ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=duration=3:size=854x480:rate=30",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(clip)], check=True, capture_output=True)
    token, athlete_id = await _coach_with_athlete(client)
    t = await _ticket(client, token, athlete_id)
    await client.put(f"/api/v1/local-storage/{t['storage_key']}", headers=auth_header(token), content=clip.read_bytes())
    r = await client.post(f"/api/v1/videos/{t['video_id']}/confirm-upload", headers=auth_header(token))
    assert r.status_code == 400 and "duration_out_of_range" in r.text and "2 and 2" in r.text


# ------------------------------------------------------------------ configuration

def test_production_refuses_the_placeholder_jwt_secret():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="production", jwt_secret_key=_DEFAULT_JWT_SECRET)
    assert Settings(_env_file=None, environment="production", jwt_secret_key="x" * 48).environment == "production"
    assert Settings(_env_file=None, environment="development").jwt_secret_key == _DEFAULT_JWT_SECRET   # local dev still starts


def test_gemini_auto_observation_is_off_by_default():
    assert Settings(_env_file=None).auto_gemini_observation is False
