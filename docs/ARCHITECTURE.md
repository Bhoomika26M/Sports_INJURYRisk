# ARCHITECTURE.md

This is reference material — read on demand, not preloaded into every task. `/AGENTS.md` has the compressed, always-relevant version of the rules here.

## §1. The Laws, in full, with rationale

**No microservices.** The original brief specifies 12 separately-boxed "microservices" plus 7 data stores, full observability, and multi-region DR. That's a 6–12 month platform for a small team, not an 8-week internship deliverable. A **modular monolith** — one deployable backend, folders that mirror the diagram's service boundaries — preserves every logical boundary the diagram cares about (you can point at any box in the original diagram and show the matching folder in this repo) without the operational tax of service discovery, inter-service auth, and 12x the health checks that would consume the timeline before a single feature works.

**PostgreSQL only.** The brief lists Postgres, MongoDB, Redis, a time-series DB, a data warehouse, and a vector DB. In practice: Postgres JSONB handles flexible/nested data as well as MongoDB would at this scale; TimescaleDB and pgvector are Postgres *extensions*, not new services, so "time-series" and "vector" capability can be added to the same instance if actually needed; a data warehouse is infrastructure for querying terabytes across an org, and this pilot's entire dataset fits in Postgres with room to spare. Redis is kept — it earns its place as both the Celery/arq task broker and the cache layer.

**No supervised injury prediction.** There is no public dataset linking video-derived biomechanics to confirmed injury outcomes at any usable scale. Real research in this space (see `/docs/SCIENCE_CONSTRAINTS.md` for citations) that achieves genuine predictive accuracy does so with thousands of labeled real injury outcomes tied to professional athletes — a resource that does not exist for a student project. Claiming a trained "injury probability" model without that data is not a simplification, it's a fabrication. The system instead ships two honest alternatives: a heuristic score built from literature-cited biomechanical thresholds, and unsupervised anomaly detection (autoencoder or isolation forest) against a normal-movement baseline — the latter needs zero injury labels because it compares movement to itself, not to injury outcomes.

**No training a pose model from scratch.** Pretrained MediaPipe Pose and Ultralytics YOLO26-pose cover this project's needs completely. Datasets like Human3.6M exist to train pose estimation networks in the first place — that work is already done and shipped inside these pretrained models; re-deriving it is out of scope and unnecessary.

**Frontal-plane measurements are qualitative only.** Tested directly against Vicon 3D motion capture, monocular pose estimation's knee valgus angle showed 18–20° of error and correlation as low as r=0.008 in places. Sagittal-plane angles (knee/hip flexion, trunk lean) tested far better — ~6° RMSE, 0.83–0.93 correlation. Full numbers and sources: `/docs/SCIENCE_CONSTRAINTS.md`. This asymmetry is encoded directly into the schema (`biomechanical_metrics.confidence` in `/docs/SCHEMA.md`) so it's structurally impossible to silently present a frontal-plane guess as a validated measurement.

## §2. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Backend | Python 3.12+, FastAPI | Matches original brief; async-native; auto-generated OpenAPI docs double as the live API contract |
| ORM / migrations | SQLAlchemy 2.0 (async) + Alembic | Standard, well-documented pairing |
| Database | PostgreSQL 16 | Sole engine — see §1 |
| Cache / queue broker | Redis 7 | Celery/arq broker from M2 onward, plus general caching |
| Auth | JWT (access + refresh) via `python-jose`/`pyjwt`, `argon2-cffi` hashing | Standard, no OAuth2 complexity needed for v1 |
| Frontend | Next.js 16 (App Router), TypeScript, Tailwind CSS | Matches original brief; App Router is current Next.js practice |
| Frontend data layer | TanStack Query | Standard caching/fetching layer, avoids hand-rolled fetch logic |
| Pose libraries | `mediapipe`, `ultralytics` (YOLO26-pose) | See §1 — pretrained only |
| Containerization | Docker + docker-compose (local), same Dockerfiles reused for deploy | One config for dev and prod parity |
| Deployment target | Render or Railway (app), Cloudflare R2 or S3 (video storage) | Cheaper and faster to stand up than raw AWS/Azure for a student budget; swap freely — nothing in the evaluation criteria requires a specific cloud vendor, only that it's "deployed" |
| Testing | pytest + httpx (backend) | Standard FastAPI testing stack |

## §3. Complete module map — all 13 areas from the original brief

| # | Module (from brief) | Backend folder | Milestone | Honesty constraint |
|---|---|---|---|---|
| 1 | User Authentication & RBAC | `modules/auth/`, `modules/users/` | M1 | — |
| 2 | Athlete Profile Management | `modules/athletes/` | M1 | — |
| 3 | Video Upload & Processing | `modules/video/` | M2 | Tag `camera_view` (sagittal/frontal) on every video — determines which metrics are even attemptable |
| 4 | Pose Estimation Engine | `modules/pose/` | M2 | Pretrained models only (§1) |
| 5 | Biomechanical Analysis Engine | `modules/biomechanics/` | M2 | Every metric tagged `validated` (sagittal) or `qualitative` (frontal) — see `/docs/SCHEMA.md` |
| 6 | Injury Risk Prediction Engine | `modules/risk_scoring/` | M3 | Renamed in practice to heuristic risk scoring — no supervised prediction (§1) |
| 7 | Movement Anomaly Detection Engine | `modules/risk_scoring/` | M3 | The honest ML component — unsupervised, baseline-relative, no injury labels needed |
| 8 | Risk Scoring Engine | `modules/risk_scoring/` | M3 | Weighted formula must cite its sources; `methodology_note` field is mandatory, not optional |
| 9 | Corrective Recommendation Engine | `modules/recommendations/` | M3 | Recommendations tied to specific flagged metrics, not generic advice |
| 10 | Dashboards (Athlete/Coach/Physio/Sports Scientist/Admin) | frontend `app/dashboard/`, backend `modules/analytics/` | M4 | — |
| 11 | Notification & Alert System | `modules/notifications/` | M4 | — |
| 12 | Reports & Export System (PDF/Excel) | `modules/analytics/` | M4 | Exported reports must carry the same `methodology_note` as the live UI — no laundering the caveat out on export |
| 13 | Final Integration, Testing & Deployment | — (cross-cutting) | M4 | — |

## §4. Complete directory tree

```
project-root/
├── AGENTS.md
├── docker-compose.yml
├── .env.example
├── .gemini/settings.json
├── README.md
├── docs/
│   ├── ARCHITECTURE.md          (this file)
│   ├── SCHEMA.md
│   ├── API_CONVENTIONS.md
│   ├── SCIENCE_CONSTRAINTS.md
│   ├── DECISIONS.md
│   └── STATE.md
├── backend/
│   ├── AGENTS.md
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── alembic/versions/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── core/
│   │   │   ├── security.py       # password hashing, JWT encode/decode
│   │   │   └── deps.py           # get_current_user, require_role()
│   │   ├── modules/
│   │   │   ├── auth/{router,schemas,service}.py
│   │   │   ├── users/{router,models,schemas,service}.py
│   │   │   ├── athletes/{router,models,schemas,service}.py
│   │   │   ├── video/            # M2 — README.md stub only for now
│   │   │   ├── pose/             # M2 — README.md stub only for now
│   │   │   ├── biomechanics/     # M2 — README.md stub only for now
│   │   │   ├── risk_scoring/     # M3 — README.md stub only for now
│   │   │   ├── recommendations/  # M3 — README.md stub only for now
│   │   │   ├── analytics/        # M4 — README.md stub only for now
│   │   │   └── notifications/    # M4 — README.md stub only for now
│   │   └── seed.py
│   ├── scripts/pose_smoke_test.py
│   └── tests/{test_auth.py, test_athletes.py}
├── frontend/
│   ├── AGENTS.md
│   ├── Dockerfile
│   ├── package.json
│   ├── app/
│   │   ├── login/page.tsx
│   │   ├── register/page.tsx
│   │   ├── dashboard/{layout.tsx, page.tsx}
│   │   ├── athletes/{page.tsx, [id]/page.tsx}
│   │   ├── videos/                # M2
│   │   └── reports/                 # M4
│   ├── lib/{api-client.ts, auth-context.tsx}
│   └── components/
└── test-assets/sample-clips/
```

## §5. Milestone-by-milestone scope boundary

- **M1 (Week 1–2):** auth, athlete/injury/training-load CRUD, pose library smoke test. See the Milestone 1 build prompt for full endpoint-level detail.
- **M2 (Week 3–4):** video upload, pose estimation on real video, sagittal-plane biomechanical metrics.
- **M3 (Week 5–6):** movement baselines, anomaly detection, heuristic risk scoring, corrective recommendations.
- **M4 (Week 7–8):** dashboards, notifications, PDF/Excel export, hardening (rate limiting, audit logging — deferred from M1 deliberately, see `/docs/DECISIONS.md`), deployment.

Do not build a milestone's modules early. The empty folders with `README.md` stubs exist specifically so the diagram-to-code mapping is visible from day one without anything being implemented before its time.
