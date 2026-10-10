"""Every advertised upload format must survive the WHOLE upload path: upload-url -> storage PUT -> confirm-upload.

The 2026-10-07 format change was only tested at the filename gate, so `.webm` / `.mkv` still failed twice later:
the storage PUT whitelisted mp4|mov only, and ffprobe reports no per-stream duration for WebM / Matroska.
"""

import shutil
import subprocess

import pytest

from app.config import settings
from tests.conftest import auth_header
from tests.test_video_api import _coach_with_athlete

CODEC = {"webm": ["-c:v", "libvpx-vp9", "-b:v", "200k"], "avi": ["-c:v", "mpeg4"]}  # the rest: H.264


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if exe is None:
        try:
            from static_ffmpeg.run import get_or_fetch_platform_executables_else_raise
            exe = get_or_fetch_platform_executables_else_raise()[0]
        except Exception:
            pytest.skip("no ffmpeg on this host (the Docker image ships one)")
    return exe


class _Job:
    job_id = "test-job"


class _Pool:
    async def enqueue_job(self, name, video_id):
        return _Job()


@pytest.mark.parametrize("ext", ["mp4", "mov", "webm", "avi", "mkv", "m4v"])
async def test_every_advertised_format_uploads_and_confirms(client, tmp_path, monkeypatch, ext):
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))

    async def fake_pool():
        return _Pool()

    monkeypatch.setattr("app.modules.video.router.get_arq_pool", fake_pool)
    clip = tmp_path / f"src.{ext}"
    try:
        subprocess.run([_ffmpeg(), "-v", "error", "-y", "-f", "lavfi", "-i", "testsrc=duration=3:size=854x480:rate=30",
                        *CODEC.get(ext, ["-c:v", "libx264", "-pix_fmt", "yuv420p"]), str(clip)], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:   # an ffmpeg build without that encoder cannot make the test clip: not a product bug
        pytest.skip(f"this ffmpeg cannot make a .{ext} test clip: {e.stderr.decode(errors='replace')[-120:]}")

    token, athlete_id = await _coach_with_athlete(client)
    H = auth_header(token)
    up = await client.post("/api/v1/videos/upload-url", headers=H, json={
        "athlete_id": athlete_id, "movement_type": "squatting", "camera_view": "sagittal",
        "original_filename": f"my clip.{ext}"})
    assert up.status_code == 200, up.text
    body = up.json()
    put = await client.put(f"/api/v1/local-storage/{body['storage_key']}", headers=H, content=clip.read_bytes())
    assert put.status_code == 200, put.text  # was 400 invalid_key for everything but mp4 / mov
    done = await client.post(f"/api/v1/videos/{body['video_id']}/confirm-upload", headers=H)
    assert done.status_code == 200, done.text  # was 400 invalid_format for WebM / Matroska (no stream duration)
    video = (await client.get(f"/api/v1/videos/{body['video_id']}", headers=H)).json()
    assert video["processing_status"] == "processing"
    assert video["duration_seconds"] == pytest.approx(3.0, abs=0.1)
    assert (video["resolution_width"], video["resolution_height"]) == (854, 480)
