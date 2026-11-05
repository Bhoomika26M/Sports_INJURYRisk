# AthletiQ — AI Sports Movement Screening & Injury Risk Detection Platform

AthletiQ is an enterprise full-stack AI platform that analyzes athletic movement videos, extracts 33-point 3D anatomical pose landmarks using Google MediaPipe BlazePose, computes clinical biomechanical kinematics, detects movement anomalies, and predicts non-contact injury risks (e.g., ACL tears, hamstring strains, patellar tendinopathy).

---

## 🚀 Live Deployments

| Component | Provider | Live URL | Status |
|---|---|---|---|
| **Frontend Web App** | **Vercel** | [sports-injury-detection.vercel.app](https://sports-injury-detection.vercel.app) | 🟢 Live |
| **Backend API** | **Render (Free Web Service)** | [athletiq-backend-69wv.onrender.com](https://athletiq-backend-69wv.onrender.com) | 🟢 Live |
| **API Documentation** | **Swagger UI** | [athletiq-backend-69wv.onrender.com/docs](https://athletiq-backend-69wv.onrender.com/docs) | 🟢 Live |
| **Backend Health** | **REST Check** | [athletiq-backend-69wv.onrender.com/api/v1/health](https://athletiq-backend-69wv.onrender.com/api/v1/health) | 🟢 Live |

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────┐
│               Frontend: React 19 + Vite                │
│       TailwindCSS • Lucide Icons • Recharts Charts     │
│       Deployed on: Vercel / Render Static Site (Free)  │
└───────────────────────────┬────────────────────────────┘
                            │ REST API / JWT
                            ▼
┌────────────────────────────────────────────────────────┐
│                Backend: FastAPI (Python)               │
│     Pydantic v2 • SQLAlchemy 2.0 • Alembic • JWT Auth  │
│        Deployed on: Render Web Service (Docker / Free) │
└─────────────┬────────────────────────────┬─────────────┘
              │                            │
              ▼                            ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│   AI & Kinematics Engine │  │      Database Engine     │
│   • MediaPipe Pose (CPU) │  │   • PostgreSQL 17 or     │
│   • OpenCV & FFmpeg      │  │   • SQLite (Zero-Config) │
│   • Joint Angle Analysis │  │   • Auto-Schema Sync     │
└──────────────────────────┘  └──────────────────────────┘
```

---

## Free Cloud Deployment (Zero-Cost Hosting)

The platform is optimized to deploy completely free without requiring expensive GPU instances or paid database tiers.

### Option 1: 1-Click Render Blueprint (Recommended)

Render provides free hosting for both the Docker backend and the static frontend with automatic inter-service linking via the included [`render.yaml`](render.yaml):

1. **Push your code** to GitHub.
2. Sign in to [Render](https://dashboard.render.com/) and navigate to **Blueprints**.
3. Click **New Blueprint Instance** and connect your repository (`Bhoomika26M/Sports_INJURYRisk`, branch `Aparna-Sasikumar`).
4. Render detects [`render.yaml`](render.yaml) and provisions:
   - **`athletiq-backend`**: Docker Web Service running FastAPI, MediaPipe, OpenCV, and SQLite on persistent `/tmp` storage.
   - **`athletiq-frontend`**: High-performance Static Site built from Vite, automatically linked to the backend's external URL via `VITE_API_URL`.
5. Click **Apply**. Once built, both services will be live with free HTTPS URLs.

---

### Option 2: Vercel (Frontend) + Render (Backend)

For ultra-fast global edge delivery on the frontend:

#### Step 1: Deploy Backend on Render
1. Go to [Render Dashboard](https://dashboard.render.com/) > **New +** > **Web Service**.
2. Connect your GitHub repository.
3. Configure the service:
   - **Environment**: Docker
   - **Docker Context**: `backend`
   - **Dockerfile Path**: `backend/Dockerfile`
   - **Instance Type**: Free (512 MB RAM / 0.5 CPU)
4. Under **Environment Variables**, add:
   | Variable | Value | Description |
   |---|---|---|
   | `PORT` | `8000` | Application HTTP port |
   | `SECRET_KEY` | *(generate a random 32-char string)* | JWT signature key |
   | `DATABASE_URL_OVERRIDE` | `sqlite:////tmp/sports_injury.db` | Embedded zero-cost SQLite database |
   | `UPLOAD_DIR` | `/tmp/uploads` | Upload storage directory |
   | `UVICORN_WORKERS` | `1` | Optimized for free tier memory limits |
   | `BACKEND_CORS_ORIGINS` | `*` | Allows cross-origin API access |
5. Click **Deploy Web Service** and copy your backend URL (e.g. `https://athletiq-backend.onrender.com`).

#### Step 2: Deploy Frontend on Vercel
1. Go to [Vercel Dashboard](https://vercel.com/) > **Add New...** > **Project**.
2. Import your GitHub repository.
3. Configure the project:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Vite
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Under **Environment Variables**, add:
   | Variable | Value |
   |---|---|
   | `VITE_API_URL` | `https://athletiq-backend.onrender.com/api/v1` |
5. Click **Deploy**. SPA client-side routing is automatically handled by the included [`frontend/vercel.json`](frontend/vercel.json).

---

## Local Development Setup

### Prerequisites
- Node.js (v20+) & npm
- Python 3.11 – 3.14
- Git

### 1. Backend Setup
```bash
cd backend
python -m venv .venv

# Activate virtual environment:
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```
Backend API will be accessible at:
- Root & Health: [http://localhost:8000](http://localhost:8000)
- Interactive API Docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)

### 2. Frontend Setup
In a separate terminal:
```bash
cd frontend
npm install
npm run dev
```
Frontend application will be accessible at [http://localhost:5173](http://localhost:5173).

---

## Quick Start with Docker Compose

To launch the complete containerized stack locally (PostgreSQL 17, FastAPI backend, and Nginx reverse proxy frontend):

```bash
# Start all containers in the background
docker compose up --build -d

# Verify services
docker compose ps

# Access the application
# Frontend UI: http://localhost:3000
# Backend API: http://localhost:8000
```

---

## AI & Computer Vision Kinematics Engine

The video processing pipeline uses Google MediaPipe BlazePose (`pose_landmarker_full.task` and `pose_landmarker_lite.task`) running natively on CPU delegates:

1. **Resolution & Contrast Normalization**: Dynamically scales high-res videos to 1280px standard format with contrast auto-enhancement for dimly lit indoor training gyms.
2. **33-Point 3D Landmark Tracking**: Extracts coordinates for head, shoulders, elbows, wrists, hips, knees, ankles, and feet at video frame rates.
3. **Primary Athlete Focus**: In multi-person environments, automatically locks onto the focal subject based on bounding box proximity.
4. **Dynamic Joint Angle Telemetry**:
   - Bilateral knee flexion angles
   - Torso/trunk lateral lean relative to vertical
   - Hip flexion and ankle dorsiflexion
5. **Annotated Skeleton Export**: Uses `imageio` and FFmpeg to generate browser-compatible MP4 video (`yuv420p` / `libx264`) featuring neon dual-layer skeleton overlays, movement trajectories, and real-time HUD metrics.
6. **Automated Risk Scoring**: Compares movement patterns against clinical norms to compute risk scores (0–100%) and trigger automated alerts.

---

## Role-Based Access Control (RBAC)

The system supports 5 specialized roles:

| Role | Permissions & Dashboards |
|---|---|
| **Athlete** | View personal movement assessments, injury risk scores, corrective exercise plans, and upload movement trials. |
| **Coach** | Track assigned athlete rosters, review movement compliance, and monitor team workload trends. |
| **Physiotherapist** | Access full joint kinematics, symmetry scores, clinical risk evaluations, and prescribe targeted neuromuscular drills. |
| **Sports Scientist** | Cross-athlete dataset exploration, kinematic anomaly detection, population benchmarking, and movement simulation. |
| **Administrator** | Manage user accounts, role delegations, athlete-staff assignments, and system audit logs. |

---

## Automated Test Suite (103 Tests)

The backend includes a comprehensive pytest suite covering unit, integration, validation, security, and end-to-end workflows:

```bash
cd backend
pytest -v
```

All 103 tests pass with 100% success rate:
- ✅ **`test_e2e_lifecycle.py`**: Multi-role journey from registration to video upload, kinematic analysis, alert dispatch, and PDF/Excel export.
- ✅ **`test_videos.py` & `test_processing.py`**: Multipart video upload validation, MediaPipe pose extraction, skeleton rendering, and artifact storage.
- ✅ **`test_security.py`**: JWT validation, password hashing, role enforcement, and path traversal defense.
- ✅ **`test_anomaly.py` & `test_risk_scoring.py`**: Clinical anomaly algorithms and injury risk calculations.
- ✅ **`test_monitoring.py`**: System health endpoints (`/health/live`, `/health/ready`, `/health/metrics`).

---

## Environment Variables Reference

### Backend (`backend/.env` or Cloud Dashboard)
| Variable | Default | Purpose |
|---|---|---|
| `SECRET_KEY` | *(auto-generated)* | Key for signing JWT authentication tokens |
| `DATABASE_URL_OVERRIDE` | `sqlite:///./sports_injury.db` | Direct database connection string (SQLite or PostgreSQL) |
| `BACKEND_CORS_ORIGINS` | `["*"]` | Allowed CORS origins for frontend requests |
| `UPLOAD_DIR` | `../uploads` | Storage path for uploaded videos and JSON landmarks |
| `UVICORN_WORKERS` | `1` | Number of Uvicorn workers (keep at 1 for free cloud tiers) |
| `ADMIN_REGISTRATION_CODE` | `admin-secret-dev-code` | Secret code required for registering administrator accounts |

### Frontend (`frontend/.env` or Cloud Dashboard)
| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_URL` | `http://localhost:8000/api/v1` | URL of the deployed FastAPI backend API |
| `VITE_GOOGLE_CLIENT_ID` | `...` | Optional Google OAuth 2.0 Web Client ID |
