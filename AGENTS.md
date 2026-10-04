# AGENTS.md — Sports Injury Risk Detection Platform

Read this before any task, in full, every time. If your task touches backend code, also read `/backend/AGENTS.md`. If it touches frontend code, also read `/frontend/AGENTS.md`. Deep reference material lives in `/docs/` — it is linked below, not duplicated here. Do not skip the links because this file looks complete; it is deliberately short and the links are not optional reading.

## Project overview

A platform where coaches, physiotherapists, and sports scientists upload athlete movement videos and receive pose-derived movement-quality metrics and heuristic risk flags. Built for an 8-week, milestone-gated internship (Infosys Springboard) — 4 milestones, 2 weeks each. Five roles: `athlete`, `coach`, `physiotherapist`, `sports_scientist`, `admin`.

Full module map, milestone breakdown, tech stack rationale, directory tree: **`/docs/ARCHITECTURE.md`**

## Current System State (Engine 2.2 & Full Stack)

- **Database**: PostgreSQL with 5 Alembic migrations (`0001` → `0005`) managing 17 schema tables (including `videos.analysis` and `risk_scores.assessment` JSONB fields).
- **AI Engine (v2.2)**: Video-level cross-fitted Isolation Forest + robust-z tail anomaly scoring. 5 weighted components (35% biomechanical deviation, 20% prior injury history, 20% bilateral asymmetry, 15% training load ACWR, 10% fatigue/consistency).
- **6 Injury Categories**: ACL, hamstring, ankle sprain, shoulder, lower back, overuse — assessed as risk *levels* with named drivers, never ML probability.
- **Baseline Sufficiency Gate**: Requires `MIN_BASELINE_VIDEOS=10` completed videos across `MIN_BASELINE_ATHLETES=3` distinct athletes before computing a population score. Below floor returns HTTP 202 ("baseline building", never fabricated scores).
- **Pose & Quality Pipeline**: YOLOv8n-pose person detection and persistent tracking (`track_persons`) with main-subject lock. MediaPipe landmarks gated at <0.5 visibility. Clips with 40–70% coverage get an explicit `coverage_caveat` (excluded from population baselines); <40% rejected.
- **Frontend**: Next.js 16 App Router (21 routes), Tailwind CSS, TanStack Query, role-aware dashboard shells, and mobile-responsive layouts.

## Before you touch anything

1. Read **`/docs/STATE.md`** — this is what actually exists right now, verified, not assumed. If it disagrees with what you observe in the repo, trust the repo and fix `STATE.md` after your task, don't trust stale claims in this doc.
2. Read **`/docs/DECISIONS.md`** for context on architectural decisions and calibration parameters.
3. If your task touches pose estimation, biomechanics, or risk scoring, read **`/docs/SCIENCE_CONSTRAINTS.md` first.** This isn't optional — violating it means shipping a false medical claim, not a style nitpick.
4. Genuinely blocked or facing a decision this doc doesn't cover? Add it to `/docs/DECISIONS.md` under "Open Questions" and stop there. Do not guess and quietly move on — a wrong guess baked into code is far more expensive than a flagged question.

## The non-negotiable laws

- **One deployable backend** (modular monolith). No microservices, no independently networked services, ever — not even "just this one small one."
- **PostgreSQL is the only database engine.** No MongoDB, no vector DB, no data warehouse. Time-series/vector needs, if they ever arise, go through Postgres extensions (TimescaleDB, pgvector) on the same instance.
- **Never claim ML-based injury *prediction*.** No dataset exists that a student team can access linking video biomechanics to confirmed injury outcomes. Risk output is either a literature-cited heuristic score or unsupervised anomaly detection against a movement baseline — never a supervised "this athlete has an X% chance of injury" claim.
- **Never train a pose model from scratch.** Pretrained MediaPipe Pose and Ultralytics YOLO checkpoints only.
- **Frontal-plane measurements (knee valgus) are qualitative flags, never precise angles** — in UI copy, API responses, and reports alike. Confidence is `'qualitative'` (`VARCHAR(20)`). Full numbers and sources: `/docs/SCIENCE_CONSTRAINTS.md`.

Full rationale for every law above: `/docs/ARCHITECTURE.md` §1.

## Setup & Running the Stack

The platform supports both Docker Compose and direct native host execution:

### Option A: Docker Compose
```bash
docker compose up --build
```
*Windows Troubleshooting*: If Docker commands hang, check for orphaned background `com.docker.backend` or stale `docker` CLI processes holding named pipes (`//./pipe/dockerDesktopLinuxEngine`). Terminate zombie processes before launching Docker Desktop.

### Option B: Native Host Execution
1. **PostgreSQL**: Ensure PostgreSQL is running (default port 5432 or 5433). Database: `injury_detection`, User: `injury_user`, Password: `changeme_in_production`.
2. **Migrations**:
   ```bash
   cd backend && python -m alembic upgrade head
   ```
3. **Seed Demo Data**:
   ```bash
   cd backend && python -m app.seed
   ```
   *Creates 5 demo accounts (all password `demo123`): `coach@demo.com`, `athlete@demo.com`, `physio@demo.com`, `scientist@demo.com`, `admin@demo.com`.*
4. **Backend Server**:
   ```bash
   cd backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
   *Health endpoint: `http://localhost:8000/health`, Swagger docs: `http://localhost:8000/docs`.*
5. **Frontend App**:
   ```bash
   cd frontend && npx next start -p 3000
   # or for development: npm run dev
   ```
   *App available at `http://localhost:3000`.*
6. **Async Pose Worker** (for video processing):
   ```bash
   cd backend && arq app.modules.pose.worker_settings.WorkerSettings
   ```

## Key Verification Commands

- **Backend Test Suite**:
  ```bash
  cd backend && pytest   # 384 passed
  ```
- **Frontend Type & Lint Check**:
  ```bash
  cd frontend && npx tsc --noEmit && npx eslint src && npm run build
  ```
- **End-to-End HTTP Pipeline**:
  ```bash
  python backend/scripts/e2e_http_check.py http://localhost:8000 path/to/clip.mp4 squatting sagittal
  ```
- **Real Clip Validation**:
  ```bash
  python backend/scripts/real_clip_validation.py docs/real-data/manifest.json data/real-corpus/
  ```
- **Mutation Testing**:
  ```bash
  python backend/scripts/mutation/run.py backend/scripts/mutation/mutants.py
  ```

## Naming (deliberately simple, cross-cutting)

`snake_case` everywhere — Python, SQL, DB columns/tables, **and JSON wire keys.** `kebab-case` only for URL paths (`/athletes/{id}/training-load`). We are intentionally *not* converting to camelCase at the API boundary: one casing convention end-to-end removes an entire class of bugs, at the minor cost of TypeScript interfaces reading as `athlete_id` instead of `athleteId`. Do not "fix" this later — it's deliberate, see `/docs/DECISIONS.md`.

Full request/response envelope, error shape, versioning: `/docs/API_CONVENTIONS.md`

## Anti-patterns — do not do these

- Don't invent a file, function, or endpoint that isn't in this repo or these docs. Grep the actual codebase first. Not found means it doesn't exist yet.
- Don't silently add a dependency. Pin it in the real requirements/package file **and** log it with a reason in `/docs/DECISIONS.md`.
- Don't refactor or restructure working code unless the task explicitly asks for it.
- Don't report a task "done" without having actually run its verification commands and read the real output. Template: `/docs/STATE.md`.
- Don't leave TODO/stub/`pass`-only functions in anything you're claiming is complete.
- Don't change a locked schema (`/docs/SCHEMA.md`) or API contract (`/docs/API_CONVENTIONS.md`) without a same-change entry in `/docs/DECISIONS.md`.

## Security considerations

- Passwords: argon2 only. Never plaintext, never reversible encryption.
- Refresh tokens: httpOnly, secure, SameSite=Lax cookie. **Never localStorage, for any token, ever.**
- Client-side auth hints: `session_hint=1` non-secret cookie for Next.js middleware routing; access tokens held in memory.
- Every endpoint gets a typed Pydantic request/response model — no raw `dict` handling.
- Secrets via `.env`, never hardcoded, never committed. `.env.example` documents every required variable with a placeholder value.

## Reference docs (read on demand, not preloaded)

| Doc | Contains |
|---|---|
| `/docs/ARCHITECTURE.md` | Full module map (all 13 areas from the original brief), milestone breakdown, directory tree, tech stack + rationale, full explanation of the Laws above |
| `/docs/SCHEMA.md` | Complete data model across all 4 milestones — DDL, with clear current-vs-designed status per table |
| `/docs/API_CONVENTIONS.md` | Request/response envelope, error shape, naming, versioning, pagination |
| `/docs/SCIENCE_CONSTRAINTS.md` | What's scientifically valid to claim about video-based biomechanics, with numbers and sources |
| `/docs/DECISIONS.md` | Append-only log of why things are the way they are, plus open questions |
| `/docs/STATE.md` | What's actually built right now, and the reusable Definition-of-Done checklist |
| `/docs/REAL_DATA_VALIDATION.md` | Evaluation results of the pipeline across 24 real-world exercise clips |
| `/docs/FRONTEND_AUDIT.md` | Comprehensive UX, design, and accessibility audit of the Next.js frontend |
