# AthletiQ — AI Sports Movement Screening & Injury Risk Detection Platform

AthletiQ is an enterprise AI platform that analyzes athlete movement videos, extracts 33-point 3D pose landmarks via MediaPipe, computes clinical biomechanical kinematics, detects movement anomalies, and predicts non-contact injury risks.

---

## Key Features

- **Computer Vision Pose Estimation**: High-accuracy landmark extraction using Google MediaPipe BlazePose.
- **Biomechanical Kinematics Engine**: Calculates dynamic frontal knee valgus, trunk lateral lean, forward flexion, and bilateral limb loading symmetry.
- **Dynamic Anomaly Detection**: Benchmarks movements against normative athletic clinical ranges (e.g., FIFA Medical Network, ACSM).
- **Injury Risk Scoring & Corrective Drills**: Computes weighted vulnerability scores (0–100%) and automatically synthesizes personalized corrective neuromuscular protocols.
- **Clinical Reporting & Multi-Format Exports**: Exports print-ready clinical PDF assessments and multi-tab Excel workbooks.
- **In-App Notification & Alert System**: Dispatches instant severity-coded alerts (`critical`, `warning`, `info`) for high-risk movement patterns.
- **Role-Based Access Control (RBAC)**: Fine-grained access policies for Athletes, Coaches, Physiotherapists, Sports Scientists, and Administrators.
- **Production-Ready Docker Architecture**: Multi-stage container builds with Nginx reverse proxy, PostgreSQL 17, and FastAPI.

---

## Quick Start (Docker Compose)

The fastest way to run the entire full-stack system (Database, Backend, and Frontend):

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd sports-injury-risk
   ```

2. **Launch all containers**:
   ```bash
   docker compose up --build -d
   ```

3. **Access Services**:
   - Web Application: [http://localhost:3000](http://localhost:3000)
   - Backend API: [http://localhost:8000](http://localhost:8000)
   - Interactive Swagger API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
   - System Health: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

4. **Seed Rich Demo Data (Optional)**:
   ```bash
   docker compose exec -e SEED_DEMO_DATA=true backend python seed_demo.py
   ```

---

## Local Development Setup

### Prerequisites
- Node.js (v22+)
- Python 3.11 - 3.14
- PostgreSQL 17

### 1. Environment Variables
Copy `.env.example` to `.env` in the root, `backend/.env`, and `frontend/.env`:
```bash
cp .env.example .env
cp .env.example backend/.env
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 3. Backend Setup
```bash
cd backend
python -m venv .venv

# Windows:
.\.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

---

## Automated Test Suite (103 Tests)

To run the complete automated test suite (Unit, Integration, API Validation, Security, Monitoring, and E2E):
```bash
cd backend
.\.venv\Scripts\activate
pytest -v
```

### Test Coverage Highlights
- `test_e2e_lifecycle.py`: Multi-role end-to-end journey from registration to video upload, kinematic analysis, notification alerts, and PDF/Excel exports.
- `test_security.py`: Verifies token tampering rejection, authentication bypass prevention, RBAC boundary enforcement, path traversal defense, and SQL injection resilience.
- `test_api_validation.py`: Verifies boundary conditions, invalid file types, empty files, and malformed request schemas.
- `test_monitoring.py`: Verifies liveness (`/health/live`), readiness (`/health/ready`), runtime metrics (`/health/metrics`), and HTTP security headers.
- `test_processing.py`: Real-world video processing with MediaPipe landmark generation.

---

## Documentation

Detailed technical documentation and user guides are available in the [`docs/`](docs/) directory:

- [System Architecture & Integration Blueprint](docs/ARCHITECTURE_AND_INTEGRATION.md): Component topology, video pipeline lifecycle, and database schemas.
- [REST API Reference Guide](docs/API_DOCUMENTATION.md): Comprehensive endpoint parameters, payloads, responses, and error codes.
- [Production Deployment Guide](docs/DEPLOYMENT_GUIDE.md): Local Docker Compose, cloud VPS deployment, Nginx SSL/TLS, and database backup/restore.
- [User & Clinical Workflow Guide](docs/USER_GUIDE.md): Visual walkthroughs for Athletes, Coaches, Physiotherapists, Sports Scientists, and Administrators.
- [Security & Compliance Architecture](docs/SECURITY_AND_COMPLIANCE.md): HIPAA & GDPR considerations, biometric data privacy, and RBAC matrix.
- [Google OAuth 2.0 Setup Guide](docs/GOOGLE_AUTH_SETUP.md): Step-by-step Google Cloud Console configuration and authentication testing.
- [Datasets and Movement Analysis Workflow](docs/DATASETS_AND_WORKFLOW.md): Computer vision datasets (Human3.6M, COCO, etc.) and biomechanical models.
