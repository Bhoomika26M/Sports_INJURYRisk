# Sports Injury Risk Detection Platform

A modular platform for coaches, physiotherapists, and sports scientists to upload athlete movement videos and receive pose-derived movement-quality metrics and heuristic risk flags. 

Built for an 8-week internship program across 4 milestones.

## Milestone 1 Status: **Complete**

Milestone 1 implements the foundational architecture, including:
- **Backend**: FastAPI modular monolith with PostgreSQL (SQLAlchemy + asyncpg) and Redis.
- **Frontend**: Next.js 14 (App Router) with Tailwind CSS.
- **Auth**: Argon2 password hashing, secure HttpOnly refresh token rotation, and JWT access tokens.
- **Athlete Management**: Full CRUD for athletes, injury history, and training loads.
- **RBAC**: Strict role-based access control (Admin, Coach, Physiotherapist, Sports Scientist, Athlete).
- **Pose De-risking**: Containerized dependencies for MediaPipe Pose and Ultralytics YOLOv8-pose.

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
   | Coach | `coach@demo.com` | `demo123` |
   | Physiotherapist | `physio@demo.com` | `demo123` |
   | Sports Scientist | `scientist@demo.com` | `demo123` |
   | Athlete | `athlete@demo.com` | `demo123` |
   | Admin | `admin@demo.com` | `demo123` |

## Documentation Reference
See the `/docs/` folder for architectural decisions, schemas, and state tracking.
- `/docs/ARCHITECTURE.md` - Full system overview
- `/docs/STATE.md` - Definition of Done and current progress
- `/docs/SCHEMA.md` - Database schema definitions
- `/docs/API_CONVENTIONS.md` - API design rules
- `/docs/SCIENCE_CONSTRAINTS.md` - Rules around biomechanical claims
