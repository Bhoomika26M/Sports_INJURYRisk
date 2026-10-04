"""Run a folder of REAL clips through the real pipeline, then score them, and write a report.

    python scripts/real_clip_validation.py MANIFEST.json CLIPS_DIR [--budget SECONDS]     # process (resumable)
    python scripts/real_clip_validation.py MANIFEST.json --score [--out report.json]      # score + report

MANIFEST.json: [{"file", "movement", "view", "athlete", "note"}, ...]   (one athlete per distinct person/source)

What it does, per clip: YOLO tracking -> coverage gate -> MediaPipe pose -> metrics -> quality report,
via the real ``process_video`` worker coroutine. Then, for every clip that completed, it asks the real
risk engine for an assessment under the PRODUCTION baseline floors — so on a small corpus the correct
output is "baseline building", and the report says so rather than inventing a score.

Needs: migrated + seeded DB (DATABASE_URL), yolov8n-pose.pt in backend/ or repo root, /uploads writable.
"""
import asyncio
import json
import os
import shutil
import sys
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import func, select

from app.config import settings
from app.database import async_session_factory
from app.modules.athletes.models import Athlete
from app.modules.risk_scoring.service import InsufficientBaseline, get_risk_assessment
from app.modules.users.models import User
from app.modules.video.models import BiomechanicalMetric, PoseFrame, Video, VideoProcessingStatus

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _weights() -> str:
    for p in (os.path.join(ROOT, "yolov8n-pose.pt"), os.path.join(os.path.dirname(ROOT), "yolov8n-pose.pt")):
        if os.path.exists(p):
            return p
    raise SystemExit("yolov8n-pose.pt not found")


async def _ensure_people(db, names: list[str]):
    coach = await db.scalar(select(User).where(User.email == "coach@demo.com"))
    assert coach, "run `python -m app.seed` first"
    people = {}
    for n in names:
        a = await db.scalar(select(Athlete).where(Athlete.coach_id == coach.id, Athlete.position == f"real-clip:{n}"))
        if not a:
            # one Athlete row per distinct person/source; `position` carries the source label
            a = Athlete(coach_id=coach.id, sport_type="mixed", position=f"real-clip:{n}",
                        date_of_birth=__import__("datetime").date(1995, 1, 1))
            db.add(a)
            await db.commit()
            await db.refresh(a)
        people[n] = a
    return coach, people


async def _summarise(db, it, vid, secs=None, worker=None):
    v = await db.get(Video, vid)
    n_metrics = await db.scalar(select(func.count()).select_from(BiomechanicalMetric).where(BiomechanicalMetric.video_id == vid))
    n_frames = await db.scalar(select(func.count()).select_from(PoseFrame).where(PoseFrame.video_id == vid))
    quality = (v.analysis or {}).get("quality") or {}
    return {
        **it, "video_id": vid, "seconds": secs, "worker_result": worker,
        "status": v.processing_status.value, "error_code": v.error_code, "error_message": v.error_message,
        "detection_rate": float(v.detection_rate) if v.detection_rate is not None else None,
        "persons": v.person_count_detected, "caveat": v.coverage_caveat,
        "pose_frames": n_frames, "metric_rows": n_metrics,
        "quality_grade": quality.get("grade"), "quality_warnings": quality.get("warnings"),
    }


async def process_phase(items, clips_dir, budget_s: float):
    """Process clips not yet in the DB (matched by original_filename); stop cleanly inside the time budget."""
    from ultralytics import YOLO
    from app.modules.pose.tasks import process_video

    t_start = time.time()
    yolo = YOLO(_weights())
    async with async_session_factory() as db:
        coach, people = await _ensure_people(db, sorted({i["athlete"] for i in items}))
        done = {r for (r,) in (await db.execute(select(Video.original_filename))).all()}
    todo = [i for i in items if i["file"] not in done]
    print(f"{len(items) - len(todo)} already processed, {len(todo)} to go", flush=True)
    for it in todo:
        if time.time() - t_start + 150 > budget_s:     # a clip can take ~2.5 min on CPU: don't start one we can't finish
            print("budget reached; re-run to continue", flush=True)
            return False
        async with async_session_factory() as db:
            key = f"{uuid.uuid4()}_{it['file']}"
            shutil.copy(os.path.join(clips_dir, it["file"]), os.path.join("/uploads", key))
            v = Video(athlete_id=people[it["athlete"]].id, uploaded_by=coach.id, movement_type=it["movement"],
                      storage_key=key, original_filename=it["file"], camera_view=it["view"],
                      processing_status=VideoProcessingStatus.pending_upload)
            db.add(v)
            await db.commit()
            await db.refresh(v)
            vid = v.id
        t0 = time.time()
        out = await process_video({"yolo_model": yolo}, vid)
        async with async_session_factory() as db:
            row = await _summarise(db, it, vid, round(time.time() - t0, 1), out)
        print(f"{it['file'][:52]:52s} {row['status']:10s} {str(row['error_code'] or ''):28s} det={row['detection_rate']} "
              f"persons={row['persons']} metrics={row['metric_rows']} grade={row['quality_grade']} {row['seconds']}s", flush=True)
    return True


async def score_phase(items, out_path):
    """Score every completed clip under the PRODUCTION floors (or those set in env) and write the report."""
    report = {"settings": {"min_baseline_videos": settings.min_baseline_videos,
                           "min_baseline_athletes": settings.min_baseline_athletes}, "items": []}
    for it in items:
        async with async_session_factory() as db:
            v = await db.scalar(select(Video).where(Video.original_filename == it["file"]))
            if not v:
                continue
            row = await _summarise(db, it, v.id)
            if row["status"] == "completed":
                a = await db.get(Athlete, v.athlete_id)
                try:
                    r = await get_risk_assessment(db, v, a, recompute=True)
                    row["score"] = {"overall": r["overall_score"], "category": r["risk_category"],
                                    "components": {k: (c.get("score") if c.get("available") else None) for k, c in r["score_breakdown"].items()},
                                    "sub_scores": {k: x.get("score") for k, x in (r.get("sub_scores") or {}).items()},
                                    "injury_categories": {k: c.get("level") for k, c in (r.get("injury_categories") or {}).items()},
                                    "baseline": r.get("baseline"), "movement": r.get("movement")}
                except InsufficientBaseline as e:
                    row["score"] = {"insufficient_baseline": {"unit": e.unit, "have": e.have, "need": e.need, "coverage": e.coverage}}
                except Exception as e:  # report, never hide
                    row["score"] = {"error": f"{type(e).__name__}: {e}"}
            else:
                row["score"] = None
        report["items"].append(row)
    json.dump(report, open(out_path, "w"), indent=1, default=str)
    print("report ->", out_path, f"({len(report['items'])} clips)")


if __name__ == "__main__":
    argv = sys.argv[1:]
    def opt(name, default=None):
        if name in argv:
            k = argv.index(name); v = argv[k + 1]; del argv[k:k + 2]; return v
        return default
    out = opt("--out", "real_clip_report.json")
    budget = float(opt("--budget", "240"))
    score = "--score" in argv
    if score:
        argv.remove("--score")
    items = json.load(open(argv[0]))
    if score:
        asyncio.run(score_phase(items, out))
    else:
        asyncio.run(process_phase(items, argv[1], budget))
