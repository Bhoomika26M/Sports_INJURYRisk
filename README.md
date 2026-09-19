# Sports Injury Risk Detection Platform

A modular platform for coaches, physiotherapists, and sports scientists to upload athlete movement videos and receive pose-derived movement-quality metrics and heuristic risk flags.

Built for an 8-week internship program across 4 milestones. Five roles: `athlete`, `coach`, `physiotherapist`, `sports_scientist`, `admin`.

## Project status

Live status and the reusable Definition-of-Done checklist live in [`/docs/STATE.md`](/docs/STATE.md) — this table reflects it:

| Milestone | Scope | Status |
|---|---|---|
| M1 — auth, athletes, env setup | Auth module, Athlete module, RBAC, argon2 + httpOnly cookies | Complete |
| M2 — video, pose, biomechanics | Video upload, MediaPipe Pose, YOLO26-pose, biomechanics math | Complete |
| M3 — risk scoring, recommendations | Heuristic risk scoring, unsupervised anomaly detection, corrective recommendations | Complete |
| M4 — dashboards, notifications, reports, deploy | Analytics, notifications, PDF/Excel reports, deployment | Not started |

## Highlights

- **Backend**: FastAPI modular monolith, PostgreSQL 16 (SQLAlchemy 2.0 async + Alembic), Redis 7.
- **Frontend**: Next.js 16 (App Router), TypeScript, Tailwind CSS, TanStack Query, evolved neumorphic UI.
- **Auth**: Argon2 password hashing, JWT access tokens with httpOnly refresh-token rotation.
- **Athlete Management**: Full CRUD for athletes, injury history, and training loads.
- **Video → Pose → Biomechanics**: Mock S3 upload, MediaPipe Pose + YOLO26-pose (pretrained only), sagittal metrics validated / frontal-plane metrics qualitative.
- **Risk Scoring**: Literature-cited heuristic scores, Isolation-Forest anomaly detection against movement baselines, rule-based corrective recommendations. No supervised injury prediction.
- **Testing**: pytest + httpx (backend), zero-stub hygiene enforced per [`/docs/STATE.md`](/docs/STATE.md).

## Quickstart

1. **Clone and Configure:**
   ```bash
   cp .env.example .env
   # Update passwords/secrets in .env if desired
   ```

2. **Run the stack:**
   ```bash
   docker compose up --build
   ```
   Brings up Postgres, Redis, backend, and frontend together.

3. **Initialize Database:**
   Wait for Postgres to be healthy, then run:
   ```bash
   docker compose exec backend alembic upgrade head
   docker compose exec backend python -m app.seed
   ```

4. **Access the Application:**
   - **Frontend:** http://localhost:3000
   - **Backend API Docs:** http://localhost:8000/docs

   **Demo accounts:**

   | Role | Email | Password |
   |---|---|---|
   | Admin | `admin@demo.com` | `demo123` |
   | Coach | `coach@demo.com` | `demo123` |
   | Physiotherapist | `physio@demo.com` | `demo123` |
   | Sports Scientist | `scientist@demo.com` | `demo123` |
   | Athlete | `athlete@demo.com` | `demo123` |
   | Athlete (soccer) | `soccer.athlete@demo.com` | `demo123` |
   | Athlete (track) | `track.athlete@demo.com` | `demo123` |

## Documentation Reference

See the `/docs/` folder for architectural rules, schemas, and state tracking:

- `/docs/ARCHITECTURE.md` - Full module map and tech stack rationale
- `/docs/STATE.md` - Definition of Done and current progress
- `/docs/SCHEMA.md` - Database schema definitions
- `/docs/API_CONVENTIONS.md` - API design rules
- `/docs/SCIENCE_CONSTRAINTS.md` - Rules around biomechanical claims
- `/docs/DECISIONS.md` - Architectural decisions log