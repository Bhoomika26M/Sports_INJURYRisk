"""Pipeline profiler harness - find out where an analysis actually spends time.

Runs the *real* processing pipeline against a real video with POSE_PROFILING
forced on, using an isolated scratch database and a scratch copy of the video,
so neither the dev database nor the uploads directory is touched. Prints a
per-stage breakdown and writes a machine-readable JSON report.

Use this before changing any tuning knob (POSE_FPS, POSE_WORKERS, DETECT_*):
on different footage the bottleneck genuinely moves, and guessing wastes runs.

Usage (from the backend directory):
    $env:PYTHONPATH="."
    python scripts/profile_pipeline.py uploads/<clip>.mp4 squat

The same breakdown is logged by the server itself whenever settings.POSE_PROFILING
is true, and is returned in the processing result under the "profile" key.
"""

import os
import sys
import time
from pathlib import Path

SCRATCH_DIR = Path(os.environ.get("TEMP", "/tmp")) / "opencode"
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
SCRATCH_DB = SCRATCH_DIR / "profile_scratch.db"
if SCRATCH_DB.exists():
    SCRATCH_DB.unlink()

# Must be set before importing app modules that build the engine.
os.environ["DATABASE_URL"] = f"sqlite:///{SCRATCH_DB.as_posix()}"

from app.core import profiling  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.database import Base, SessionLocal, engine  # noqa: E402


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python profile_pipeline.py <video_path> [activity]")
        return 2
    video_path = sys.argv[1]
    activity = sys.argv[2] if len(sys.argv) > 2 else "squat"

    if not Path(video_path).exists():
        print(f"no such video: {video_path}")
        return 2

    # Work on a copy in a scratch dir: the pipeline writes annotated_*.jpg/mp4
    # and preview files next to the source, and we must not pollute uploads/.
    import shutil
    import tempfile

    workdir = Path(tempfile.gettempdir()) / "opencode" / "profile_run"
    workdir.mkdir(parents=True, exist_ok=True)
    local_video = workdir / Path(video_path).name
    if not local_video.exists():
        print(f"copying source to {local_video} ...")
        shutil.copy2(video_path, local_video)
    video_path = str(local_video)

    # Force profiling regardless of ambient .env
    settings.POSE_PROFILING = True

    import app.models  # noqa: F401 - register all models on Base
    from app.models.user import User
    from app.models.athlete import Athlete
    from app.models.video import Video, ProcessingStatus
    from app.services.processing_service import VideoProcessingService

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        user = User(
            email="profile@example.com",
            password_hash="x",
            full_name="Profiler",
            role="athlete",
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        athlete = Athlete(
            athlete_id="PROFILE-0001",
            user_id=user.id,
            sport_type="general",
            age=25,
            height=180.0,
            weight=75.0,
        )
        db.add(athlete)
        db.commit()
        db.refresh(athlete)

        video = Video(
            athlete_id=athlete.id,
            uploaded_by=user.id,
            filename=Path(video_path).name,
            original_filename=Path(video_path).name,
            storage_path=str(Path(video_path).resolve()),
            file_size=Path(video_path).stat().st_size,
            activity_type=activity,
            processing_status=ProcessingStatus.UPLOADED,
        )
        db.add(video)
        db.commit()
        db.refresh(video)
        video_id = video.id
    finally:
        db.close()

    print(f"profiling {Path(video_path).name} (activity={activity}) ...")
    wall_start = time.perf_counter()
    db = SessionLocal()
    try:
        service = VideoProcessingService()
        result = service.process_video(video_id, db, activity=activity)
    finally:
        db.close()
    wall = time.perf_counter() - wall_start

    print()
    print(profiling.format_report(result.get("profile")))
    print()
    print(f"wall clock: {wall:.2f}s")
    perf = result.get("performance", {})
    print(f"frames processed: {perf.get('pose_frames')} "
          f"(valid {perf.get('valid_pose_frames')})")
    print(f"processed fps: {perf.get('processed_fps'):.2f}")

    # Also dump the machine-readable report next to the scratch DB.
    import json

    report_path = SCRATCH_DB.with_suffix(".profile.json")
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(
            {"wall_seconds": wall, "report": result.get("profile")},
            fh,
            indent=2,
        )
    print(f"report written to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
