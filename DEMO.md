# Run the demo without Docker Desktop doing the heavy lifting

Needs: **Python 3.12** (3.13 cannot install the pinned numpy), Node 20+, and Postgres.
Docker is used only for Postgres (one small container). Everything else runs on the host.

## One-time setup (needs internet)

```powershell
copy .env.example .env
docker compose up -d                      # Postgres only. No Docker? install Postgres 15+ and create the user/db from .env

cd backend
py -3.12 -m venv .venv ; .venv\Scripts\activate
pip install -r requirements.txt           # downloads torch (~200 MB CPU build on Windows)
python scripts/fetch_models.py            # YOLO + MediaPipe + ffmpeg, so uploads never wait on the network
alembic upgrade head
python -m app.seed

cd ..\frontend
npm install ; npm run build               # a production build is far faster than `npm run dev` on this laptop
```

## Every run

```powershell
# terminal 1
cd backend ; .venv\Scripts\activate ; uvicorn app.main:app --port 8000      # no --reload
# terminal 2
cd frontend ; npm run start
```

Open **http://localhost:3000** (use `localhost`, not 127.0.0.1: the auth cookie is Secure).
Login: `coach@demo.com` / `demo123`.

## For a demo that shows a score

A score needs a comparison group of *other* completed videos of the same movement. Defaults: 10 videos from 3 athletes.
For a demo set `MIN_BASELINE_VIDEOS=3` and `MIN_BASELINE_ATHLETES=2` in `.env` and process at least 3 real clips from 2 different
athletes beforehand (the page labels such a score "provisional"). Without them you get the measurements and a "baseline building" note, by design.

## Faster / slower

`.env`: `YOLO_IMGSZ` (384; 640 if the athlete is small in frame), `YOLO_TRACK_FPS` (15; 0 = every frame, ~5x slower),
`POSE_LANDMARKER_VARIANT` (`lite` is fastest but changes the numbers; do not mix models in one comparison group).
Use a side-on camera, one person, whole body in frame, 480p+ , 2-60 s.

## If a video fails

The video page shows why. `models_unavailable` -> run `python scripts/fetch_models.py` with internet. A video left `processing` by a crash is
re-queued automatically on the next start.
