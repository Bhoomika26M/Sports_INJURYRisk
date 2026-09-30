"""End-to-end video check (local dev, no worker needed).

Copies a sample clip into /uploads, inserts a Video row, runs the real
arQ worker coroutine process_video, then verifies pose_frames +
biomechanical_metrics rows and exercises the risk-score endpoint over ASGI.

Usage: python scripts/e2e_video_check.py [clip_path]
"""
import asyncio
import os
import shutil
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, select

from app.database import async_session_factory
from app.modules.athletes.models import Athlete
from app.modules.users.models import User
from app.modules.video.models import BiomechanicalMetric, PoseFrame, Video, VideoProcessingStatus

CLIP = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "test-assets", "sample-clips", "squat_sample.mp4",
)
MOVEMENT = sys.argv[2] if len(sys.argv) > 2 else "squatting"


async def main():
    from ultralytics import YOLO
    from app.modules.pose.tasks import process_video

    weights = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "yolov8n-pose.pt",
    )
    assert os.path.exists(weights), f"missing weights: {weights}"
    assert os.path.exists(CLIP), f"missing clip: {CLIP}"

    clip_name = os.path.basename(CLIP)
    storage_key = f"{uuid.uuid4()}_{clip_name}"
    shutil.copy(CLIP, os.path.join("/uploads", storage_key))
    print(f"clip copied -> /uploads/{storage_key}", flush=True)

    async with async_session_factory() as db:
        coach = (await db.scalars(select(User).where(User.email == "coach@demo.com"))).one()
        athlete = (await db.scalars(select(Athlete).where(Athlete.coach_id == coach.id))).first()
        assert athlete, "seed athletes missing — run python -m app.seed first"
        video = Video(
            athlete_id=athlete.id, uploaded_by=coach.id, movement_type=MOVEMENT,
            storage_key=storage_key, original_filename=clip_name,
            camera_view="sagittal", processing_status=VideoProcessingStatus.pending_upload,
        )
        db.add(video)
        await db.commit()
        await db.refresh(video)
        video_id = video.id
        print(f"video row: {video_id}", flush=True)

    print("loading YOLO + running process_video ...", flush=True)
    model = YOLO(weights)
    result = await process_video({"yolo_model": model}, video_id)
    print(f"process_video -> {result}", flush=True)

    async with async_session_factory() as db:
        n_frames = await db.scalar(select(func.count()).select_from(PoseFrame).where(PoseFrame.video_id == video_id))
        n_metrics = await db.scalar(select(func.count()).select_from(BiomechanicalMetric).where(BiomechanicalMetric.video_id == video_id))
        names = (await db.scalars(select(BiomechanicalMetric.metric_name).where(BiomechanicalMetric.video_id == video_id).distinct())).all()
        video = await db.get(Video, video_id)
        print(f"pose_frames={n_frames} metrics={n_metrics} names={sorted(names)}", flush=True)
        print(f"status={video.processing_status} detection_rate={video.detection_rate} persons={video.person_count_detected}", flush=True)
        assert video.processing_status == VideoProcessingStatus.completed, video.error_message
        assert n_frames and n_frames > 0
        assert n_metrics and n_metrics > 0

    print("exercising GET risk-score over ASGI ...", flush=True)
    from httpx import ASGITransport, AsyncClient
    from app.main import app as fastapi_app

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login = await client.post("/api/v1/auth/login", json={"email": "coach@demo.com", "password": "demo123"})
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        rs = await client.get(f"/api/v1/videos/{video_id}/risk-score",
                              headers={"Authorization": f"Bearer {token}"})
        print(f"risk-score -> {rs.status_code} {rs.text[:300]}", flush=True)
        # A single video scores against its own frames as baseline history
        # (the history query includes this completed video), so 200 with a
        # real composite score is the correct outcome here.
        assert rs.status_code == 200, rs.text
        body = rs.json()
        assert 0 <= body["overall_score"] <= 100
        assert body["risk_category"] in ("low", "moderate", "high", "critical")
        assert set(body["score_breakdown"]) >= {"movement_anomaly", "asymmetry_flag", "prior_injury_flag"}
        assert "Not a trained injury-prediction model" in body["methodology_note"]
        recs = await client.get(f"/api/v1/videos/{video_id}/recommendations",
                                headers={"Authorization": f"Bearer {token}"})
        print(f"recommendations -> {recs.status_code} {recs.text[:300]}", flush=True)
        assert recs.status_code == 200

    print("E2E VIDEO CHECK PASSED", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
