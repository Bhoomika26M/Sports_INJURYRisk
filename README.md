# Sports Injury Risk Detection from Video

A web platform that turns an ordinary training video into an injury-risk report. It tracks 15 body
joints with MediaPipe, measures the movement, flags problems, scores injury risk from 0 to 100, and
suggests corrective exercises. Each role (athlete, coach, physiotherapist, sports scientist,
administrator) gets its own dashboard, alerts and PDF/Excel reports.

> **Decision-support tool.** Outputs are screening indicators, not medical diagnoses.

## How it works

```
Upload video -> quality check -> pose tracking (15 joints) -> biomechanics -> anomaly detection
   -> injury-risk prediction (6 injury types) -> weighted risk score -> recommendations, alerts, reports
```

Tracked joints: head, shoulders, elbows, wrists, hips, knees, ankles, feet.
Supported activities: running, sprinting, jumping, squatting, landing, throwing, cutting, drills.

## Features

- **Video analysis:** upload, quality validation, frame extraction and enhancement, skeleton overlay
  on the video, and a joint trajectory view (path and height over time for any joint).
- **Biomechanics:** joint angles, range of motion, knee valgus, hip stability, trunk lean, stride,
  balance, symmetry, force estimate, posture, movement quality and efficiency scores.
- **Risk engine:** ACL, hamstring, ankle sprain, shoulder, lower back and overuse risk; movement
  anomaly detection (deviation, inconsistency, fatigue drift, performance decline).
- **Recommendations:** exercises, mobility and strengthening work, recovery plan, training changes.
- **Athlete management:** profile, injury history, training load, physical assessments, and a
  "Shared with" box to give a coach, physiotherapist or sports scientist access.
- **Dashboards:** athlete, coach, physiotherapist, sports scientist and administrator views.
- **Alerts:** high-risk movement, injury risk, training load, recovery and assessment-complete
  notices (in the app only; email is not connected).
- **Reports:** injury risk, biomechanical, movement, performance and rehabilitation reports as PDF or
  Excel; administrators can list, download and delete them; sports scientists can download a
  team-level research export (Excel, athletes identified by code only).
- **Housekeeping:** delete or retry a video; analyses interrupted by a restart are marked failed
  instead of staying on "Analysing" forever.

## Roles

| Role | What they can do |
| --- | --- |
| Athlete | Own profile and data, upload videos, read results, share their data |
| Coach | Create athletes, upload for them, log training load, view team risk |
| Physiotherapist | Record injuries and assessments, review high-risk results, follow recovery |
| Sports scientist | Read-only analytics, team trends, research export |
| Administrator | Manage users and roles, platform analytics, all reports |

Athletes own their data. Coaches and physiotherapists can see and add data for athletes who shared
with them or whom they created; sports scientists can only view. Administrators cannot be created
through self-registration.

## Quick start (Docker)

Requires Docker Desktop. Run these from the project folder (the one containing `docker-compose.yml`).

```bash
cp .env.example .env        # Windows: copy .env.example .env   then edit SECRET_KEY and ADMIN_* values
docker compose up --build -d
docker compose exec backend python seed_demo.py     # optional: demo accounts, development only
```

- Frontend: http://localhost:8080
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

Notes:
- The first build takes several minutes. Later builds reuse Docker's cache and are much faster.
- The first video analysis downloads the MediaPipe pose model (about 9 MB) into `backend/models/`.
- Docker runs PostgreSQL and MongoDB. Your data lives in Docker volumes and survives restarts.
  **Never run `docker compose down -v`**: the `-v` deletes the volumes and all data.
- Stop with `docker compose down`; start again with `docker compose up -d`.
- Do not run the local setup and Docker at the same time: both use port 8000.

## Local development

Backend (SQLite by default, no extra services needed):

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend (in a second terminal):

```bash
cd frontend
npm install
npm run dev                     # http://localhost:5173, proxies /api to port 8000
```

Start the backend first, then the frontend. Activate the virtual environment in every new backend
terminal.

### Demo accounts (development only)

```bash
cd backend
python seed_demo.py
```

All demo accounts use the password `Demo@1234`: `athlete@demo.com`, `coach@demo.com`,
`physio@demo.com`, `scientist@demo.com`, `admin@demo.com`.
**Never create these on a public server.**

## Check that pose detection works on your video

```bash
cd backend
python check_pose.py squat.mp4 --save tracked.mp4
```

Prints how often each body point is found and saves a copy of the video with the joints drawn.
Use a different file name for `--save` than the input, or the original is overwritten.
Film one person, whole body in frame, steady camera, good light, at least 15 fps.

## Measure accuracy on the COCO dataset (optional)

```bash
cd backend
python evaluate_pose_coco.py --annotations person_keypoints_val2017.json --limit 100
```

Download `person_keypoints_val2017.json` (inside `annotations_trainval2017.zip`) from
https://cocodataset.org/#download. The script reports the share of joints found within 5% and 10%
of the person's size (PCK) on single-person images.

## Tests

```bash
cd backend && pytest -q          # 54 tests: scoring, API, access rules, video pipeline, exports
cd frontend && npm run build
```

The pose model is replaced by a stand-in in the automated tests, so they need no download.

## Risk score

`Injury Risk Score = 35% biomechanical deviations + 20% injury history + 20% movement asymmetry
+ 15% training load + 10% fatigue`

Categories: Low < 25, Moderate < 50, High < 75, Critical >= 75.

- **Injury history:** weighted by severity and recency (older injuries fade over about 18 months;
  active injuries count fully).
- **Training load:** acute-to-chronic workload ratio from session length x effort (RPE). Needs at
  least 14 days of entries, otherwise it is left out and the other parts are re-weighted.
- **Fatigue:** needs at least 4 repetitions in the clip, otherwise it is left out.
- **Landing mechanics** are only assessed for jumping, landing, running, sprinting, cutting and drills.

## Limitations

- Risk prediction is **rule-based**. Thresholds are screening guidelines written in code, not a model
  trained on real injury data, and they have not been clinically validated. An optional training
  script exists (`python -m ml.train_injury_model --help`); if a model is present at `MODEL_PATH`
  it adds an ML probability alongside the rule-based score.
- Accuracy depends on video quality: camera angle, lighting, clothing and a fully visible body.
- Alerts are shown in the app only; email and push delivery are not connected.
- Google sign-in code exists but needs `GOOGLE_CLIENT_ID` and has not been tested.

## Configuration

Copy `.env.example` to `.env`. Important values: `SECRET_KEY` (use a long random string),
`ADMIN_EMAIL` and `ADMIN_PASSWORD` (the first administrator, created on startup),
`POSTGRES_*`, `RATE_LIMIT_PER_MINUTE`, `MAX_UPLOAD_MB`. Never commit the real `.env`.

## Project layout

```
backend/    FastAPI app (app/api, app/services, app/models), tests, seed_demo.py, check_pose.py,
            evaluate_pose_coco.py, ml/ (optional training)
frontend/   React 18 + Vite + Tailwind (src/pages, src/components)
docker-compose.yml   PostgreSQL, MongoDB, backend, frontend (nginx)
```

Backend: Python, FastAPI, SQLAlchemy, OpenCV, MediaPipe, NumPy, ReportLab, openpyxl.
Frontend: React, Chart.js. Data: SQLite (development) or PostgreSQL (Docker); joint positions as JSON
files, or MongoDB when `MONGO_URL` is set.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `uvicorn` is not recognized | Activate the virtual environment first (`.venv\Scripts\activate`) |
| Frontend shows `ECONNREFUSED` | The backend is not running on port 8000; start it first |
| `libEGL.so.1` error in Docker | Rebuild the image: `docker compose up --build -d` |

## Cloud deployment

Not deployed yet. The images are plain Docker: the simplest route is one small virtual machine running
`docker compose up -d`. Managed options (for example ECR/ACR with ECS/App Service, managed PostgreSQL
and object storage) also work. Before going online: set a strong `SECRET_KEY`, change the admin
password, do not run `seed_demo.py`, and restrict `CORS_ORIGINS` to your own site.
