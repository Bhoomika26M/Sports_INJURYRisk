"""End-to-end proof: the annotated video is playable DURING analysis.

Runs the real pipeline in a background thread and, from the main thread, keeps
opening the annotated output with a fresh reader - exactly what a browser does
when it hits the range-capable endpoint. Reports how many frames were already
decodable at each point, plus the wall-clock time until the first playable
frame.

Usage (from backend/):
    $env:PYTHONPATH="."
    python scripts/check_live_playback.py uploads/<clip>.mp4 squat
"""

import os
import sys
import threading
import time
from pathlib import Path

SCRATCH_DIR = Path(os.environ.get("TEMP", "/tmp")) / "opencode"
SCRATCH_DIR.mkdir(parents=True, exist_ok=True)
SCRATCH_DB = SCRATCH_DIR / "live_playback.db"
if SCRATCH_DB.exists():
    SCRATCH_DB.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{SCRATCH_DB.as_posix()}"

import cv2  # noqa: E402
import shutil  # noqa: E402
import tempfile  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.db.database import Base, SessionLocal, engine  # noqa: E402


def decodable_frames(path: Path) -> int:
    if not path.exists():
        return 0
    cap = cv2.VideoCapture(str(path))
    n = 0
    while cap.isOpened():
        ok, _ = cap.read()
        if not ok:
            break
        n += 1
    cap.release()
    return n


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python scripts/check_live_playback.py <video> [activity]")
        return 2
    src = Path(sys.argv[1])
    activity = sys.argv[2] if len(sys.argv) > 2 else "squat"
    if not src.exists():
        print("no such video:", src)
        return 2

    workdir = Path(tempfile.gettempdir()) / "opencode" / "live_run"
    workdir.mkdir(parents=True, exist_ok=True)
    local = workdir / src.name
    if not local.exists():
        print("copying source ...")
        shutil.copy2(src, local)

    import app.models  # noqa: F401
    from app.models.user import User
    from app.models.athlete import Athlete
    from app.models.video import Video, ProcessingStatus
    from app.services.processing_service import VideoProcessingService

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        user = User(email="live@example.com", password_hash="x", full_name="Live", role="athlete", is_active=True)
        db.add(user); db.commit(); db.refresh(user)
        athlete = Athlete(athlete_id="LIVE-1", user_id=user.id, sport_type="general", age=25, height=180.0, weight=75.0)
        db.add(athlete); db.commit(); db.refresh(athlete)
        video = Video(
            athlete_id=athlete.id, uploaded_by=user.id, filename=local.name,
            original_filename=local.name, storage_path=str(local.resolve()),
            file_size=local.stat().st_size, activity_type=activity,
            processing_status=ProcessingStatus.UPLOADED,
        )
        db.add(video); db.commit(); db.refresh(video)
        video_id = video.id
    finally:
        db.close()

    annotated = local.parent / f"annotated_{local.name}"
    if annotated.exists():
        annotated.unlink()

    print(f"streaming enabled: {settings.ANNOTATED_STREAM}")
    done = {"ok": False, "err": None}

    def run():
        d = SessionLocal()
        try:
            VideoProcessingService().process_video(video_id, d, activity=activity)
            done["ok"] = True
        except Exception as exc:  # noqa: BLE001
            done["err"] = exc
        finally:
            d.close()

    t0 = time.perf_counter()
    thread = threading.Thread(target=run, daemon=True)
    thread.start()

    first_playable = None
    samples = []
    while thread.is_alive():
        time.sleep(1.0)
        n = decodable_frames(annotated)
        elapsed = time.perf_counter() - t0
        size = annotated.stat().st_size if annotated.exists() else 0
        samples.append((round(elapsed, 1), size, n))
        if n > 0 and first_playable is None:
            first_playable = elapsed
            print(f"  >>> FIRST PLAYABLE FRAME at {elapsed:.1f}s ({n} frames, {size} bytes)")

    thread.join()
    total_time = time.perf_counter() - t0
    final = decodable_frames(annotated)

    print("\nsamples (seconds, bytes, decodable_frames):")
    for s in samples[:8]:
        print("  ", s)
    if len(samples) > 8:
        print("   ...")

    print(f"\nanalysis finished: {done['ok']}, error: {done['err']}")
    print(f"total analysis time: {total_time:.1f}s")
    print(f"first playable at:   {first_playable:.1f}s" if first_playable else "NEVER PLAYABLE MID-RUN")
    print(f"final decodable:     {final}")
    if first_playable:
        print(f"played {first_playable / total_time * 100:.0f}% of the way through analysis")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
