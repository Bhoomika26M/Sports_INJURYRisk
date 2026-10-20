# Kinematix: Sports Biomechanics & Injury Risk Intelligence Platform

A high-performance sports movement biomechanics and injury risk intelligence platform that analyzes athletic movement videos to identify biomechanical deviations, detect abnormal kinematic patterns, calculate transparent multi-factor injury risk scores, and prescribe targeted corrective interventions.

Built with **FastAPI**, **Google MediaPipe Pose**, **OpenCV**, **SQLAlchemy**, **ReportLab**, **openpyxl**, and **React 19 + Tailwind CSS + Recharts**.

---

## Technical & Scientific Governance Notice

> [!NOTE]
> **Deterministic Rule-Based Screening Methodology**:
> Kinematix evaluates injury risk using deterministic mathematical formulas and kinematic safety thresholds calibrated against peer-reviewed sports medicine and biomechanics literature (e.g., Hewett et al. dynamic knee valgus thresholds, McLean et al. ACL landing mechanics, Gabbett Acute-to-Chronic Workload Ratios).
>
> Kinematix is designed for athletic screening, movement monitoring, and workload management. It does **not** make unverified clinical diagnostic claims, nor does it claim deep learning model training on proprietary clinical datasets. Occluded or undetected video frames are marked unavailable; no simulated or fabricated measurements are displayed.

---

## Milestone Architecture Overview

### Milestone 1: Authentication, Roles & Athlete Profiles
- **Role-Based Access Control (RBAC)**:
  - 5 authenticated platform roles: **Athlete**, **Coach**, **Physiotherapist**, **Sports Scientist**, and **Administrator**.
  - Secure bcrypt password hashing and JWT bearer session tokens.
  - Interactive login modal with one-click quick switch demo accounts for all five roles.
- **Secure Password Reset Flow**:
  - `POST /api/auth/forgot-password`: Generates secure, single-use SHA-256 hashed reset tokens with a strict 15-minute expiration.
  - `POST /api/auth/reset-password`: Atomically verifies token validity, checks expiration, updates password hash, and marks token as used.
  - Reset tokens are **never** exposed in API responses or console logs.
  - Configurable SMTP integration for production email delivery.
- **Athlete Profiles & Workload Management**:
  - Athlete identification, sport category, primary position, physical baselines (height, weight, age).
  - Longitudinal injury history tracking (injury type, severity, clinical status).
  - Acute-to-Chronic Workload Ratio (ACWR) and weekly training load monitoring.
- **Normative Dataset Benchmarks**:
  - Literature-backed normative references: **Human3.6M**, **SportsPose**, **MPII**, **COCO Keypoints**, and **FIFA Injury Surveillance Dataset**.
  - Reference benchmarks for dynamic valgus, trunk lateral lean, limb symmetry indices, and ACWR safety zones.

### Milestone 2: Markerless Pose Estimation & Biomechanical Analysis
- **33-Landmark Pose Estimation**:
  - Real-time 33-point markerless skeleton extraction powered by Google MediaPipe Pose.
  - Overlay HUD telemetry displaying joint connections, tracked limb angles, and real-time tracking metrics.
- **Missed Detection & Occlusion Safety**:
  - Occluded or out-of-frame limbs are safely marked `None` / unavailable.
  - Never fabricates or interpolates fake joint measurements when athletes exit frame.
  - Biomechanical analysis engine filters strictly for valid frames, calculating true detection rates and reporting tracking status.
- **10 Core Biomechanical Parameters**:
  1. **Dynamic Knee Valgus Angle** (Frontal Plane Projection Angle / FPPA).
  2. **Hip Stability & Pelvic Drop** (Trendelenburg sign indicator).
  3. **Peak Lateral Trunk Lean & Sagittal Flexion**.
  4. **Landing Mechanics & Contact Cushion Score** (Knee flexion angle at impact).
  5. **Bilateral Movement Symmetry Index** ($BAI = \frac{|L - R|}{\max(L, R)} \times 100\%$).
  6. **Range of Motion (ROM) Score**.
  7. **Joint Collinear Tracking Alignment**.
  8. **Balance & Stability Index**.
  9. **Estimated Kinetic Ground Impact Force (G-force)**.
  10. **Estimated Kinetic Stride / Jump Reach**.
- **Movement Validation**:
  - Rigorous video file validation: MIME type check, file size limit (250MB), 0-byte rejection, and OpenCV decode verification.

### Milestone 3: Transparent Risk Scoring, Anomalies & Role Dashboards
- **Transparent Weighted Scoring Formula**:
  $$\text{Injury Risk Score} = 0.35 \times \text{Biomech Deviations} + 0.20 \times \text{Injury History} + 0.20 \times \text{Asymmetry} + 0.15 \times \text{Training Load (ACWR)} + 0.10 \times \text{Fatigue}$$
  - Risk Categorization:
    - **Low Risk** (0 - 30)
    - **Moderate Risk** (31 - 60)
    - **High Risk** (61 - 85)
    - **Critical Risk** (86 - 100)
- **6 Core Injury Categories Prediction**:
  - **ACL Injury Risk** (Dynamic valgus > 15°, landing stiffness, asymmetry).
  - **Hamstring Strain Risk** (Pelvic obliquity, rapid deceleration strain).
  - **Ankle Sprain Risk** (Excessive ground reaction force, center-of-mass sway).
  - **Shoulder Injury Risk** (Overhead sport profile, scapular dyskinesis).
  - **Lower Back Injury Risk** (Excessive lateral trunk lean > 10°, pelvic unleveling).
  - **Overuse Injury Risk** (ACWR > 1.45 danger threshold, training volume spikes).
- **Movement Anomaly Detection**:
  - High-frequency kinematic threshold breach detection.
  - Fatigue drift analysis measuring progressive technique decay over repetitions.
- **Longitudinal Risk Score Trends**:
  - Historical session-over-session risk score and movement symmetry trajectory charts.
- **Targeted Corrective Interventions**:
  - Prescribed corrective exercises with sets, reps, frequency, and clinical coaching cues.
  - Mobility improvement protocols, strengthening plans, recovery strategies, and workload modifications.
- **5 Dedicated Role Dashboards**:
  - **Coach Dashboard**: Squad availability %, high-risk athlete alerts, full readiness roster table, workload modifications.
  - **Physiotherapist Dashboard**: Clinical rehabilitation registry, flagged valgus cases, asymmetry tracking.
  - **Sports Scientist Dashboard**: Cohort population means vs SportsPose gold standard, research insights.
  - **Administrator Dashboard**: System infrastructure metrics (users, videos, storage, DB engine), user directory with role filter, and audit logs.
  - **Athlete Dashboard**: Personal injury risk score, daily exercise checklist, active recovery guidelines.

### Milestone 4: Reports, Integration, Testing & Deployment
- **Multi-Format Analytical Report Exports**:
  - **PDF Executive Report** (`/api/reports/{id}/pdf`): Formatted clinical assessment report via ReportLab including athlete metadata, weighted score component breakdown, 10 biomechanical metrics table, 6 injury risk categories, corrective prescriptions, and methodology disclosures.
  - **Excel Workbook Export** (`/api/reports/{id}/excel`): Structured 3-sheet spreadsheet via openpyxl containing Summary & Risk, Biomechanical Metrics, and Frame-by-Frame Kinematics time-series data.
- **PostgreSQL Database Support**:
  - Configurable primary database connection via SQLAlchemy (`DATABASE_URL=postgresql://user:pass@host:5432/kinematix`).
  - Seamless fallback to SQLite for zero-config local development.
- **Docker Containerization**:
  - `docker-compose.yml` with PostgreSQL 16 healthcheck, FastAPI backend, and Nginx frontend.
- **Automated Test Suite**:
  - 15 comprehensive unit and integration tests covering authentication, RBAC, password reset, scoring formulas, video upload validation, occlusion handling, admin dashboards, and PDF/Excel report generation.

---

## 🚀 Quick Start Guide

### Option 1: Docker Deployment (Recommended for Production)

Run the entire platform including PostgreSQL, FastAPI backend, and Nginx frontend:
```bash
docker compose up --build
```
- Frontend UI: [http://localhost:3000](http://localhost:3000)
- Backend API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
- PostgreSQL Database: Port 5432 (`kinematix`)

### Option 2: Local Development (Windows / macOS / Linux)

#### 1. Launch with One Click (Windows)
In the project directory, run:
```bat
.\run_app.bat
```
*(Or in PowerShell: `.\run_app.ps1`)*

#### 2. Manual Startup

**Backend:**
```bash
cd backend
# Create virtual environment (optional)
python -m venv venv
# Activate virtual environment:
# Windows: .\venv\Scripts\activate | Unix: source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- API Docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/api/health](http://localhost:8000/api/health)

**Frontend:**
```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 3000
```
- Web Application: [http://localhost:3000](http://localhost:3000)

---

## 🗄️ PostgreSQL Database Setup

To use PostgreSQL instead of SQLite:

1. Create a PostgreSQL database and user:
```sql
CREATE USER kinematix WITH PASSWORD 'your_secret_password';
CREATE DATABASE kinematix OWNER kinematix;
```

2. Copy the environment configuration template:
```bash
cp backend/.env.example backend/.env
```

3. Update `DATABASE_URL` in `backend/.env`:
```env
DATABASE_URL=postgresql://kinematix:your_secret_password@localhost:5432/kinematix
```

The database schema and initial seed data are created automatically on application startup.

---

## 👥 Seed User Accounts

All demo accounts use password: `password123`

| Role | Email | Name | Focus |
|---|---|---|---|
| **Athlete** | `athlete@sportsai.com` | Marcus Vance | Personal Risk, Daily Exercises |
| **Coach** | `coach@sportsai.com` | Coach Roberto Martinez | Squad Availability, Workload |
| **Physiotherapist** | `physio@sportsai.com` | Dr. Sarah Jenkins | Rehab Registry, Joint ROM |
| **Sports Scientist** | `scientist@sportsai.com` | Dr. Alexei Volkov | Kinematics Distributions, Datasets |
| **Administrator** | `admin@sportsai.com` | Sys Admin | Platform Governance, User Accounts, Audits |

*(Use the Quick Demo switcher in the login modal or top navigation to switch perspectives).*

---

## 🧪 Automated Test Suite

Run the backend test suite:
```bash
# Windows PowerShell
$env:PYTHONPATH="backend"; pytest backend/tests

# Unix / macOS
PYTHONPATH=backend pytest backend/tests
```

### Test Coverage Highlights:
- `test_health_check`: Service availability and MediaPipe readiness.
- `test_datasets`: Benchmark metadata and normative references.
- `test_auth_login`: Credential validation and JWT session issuance.
- `test_athletes_list`: Athlete roster querying and baseline physical attributes.
- `test_weighted_scoring_formula`: Verification of the 35/20/20/15/10 weighted formula.
- `test_dashboards`: Role dashboard endpoints (Coach, Physio, Sports Scientist).
- `test_auth_registration_and_rbac`: Registration, role enforcement, and token decoding.
- `test_forgot_and_reset_password_flow`: SHA-256 hashed single-use tokens, expiration, and secure reset.
- `test_admin_user_management`: Administrator-only user listing and role checking.
- `test_video_upload_validation`: Validation for invalid extensions, corrupt files, and 0-byte rejections.
- `test_video_endpoints_and_streaming`: Video retrieval and chunked video streaming.
- `test_missed_detections_safe_handling`: Occlusion safety, zero fabrication on missing frames, valid anomaly filtering.
- `test_admin_dashboard_endpoint`: Infrastructure metrics, role distribution, and activity audit logging.
- `test_reports_pdf_and_excel_export`: ReportLab PDF byte generation and openpyxl XLSX workbook structure.
- `test_athlete_risk_trends_endpoint`: Longitudinal session risk and symmetry tracking.

---

## 📁 Repository Structure

```text
sports-injury-risk-detection/
├── backend/
│   ├── app/
│   │   ├── models/            # SQLAlchemy database models (User, Athlete, Video, Biomechanics, Risk)
│   │   ├── routers/           # FastAPI routers (auth, athletes, videos, biomechanics, injury_risk, dashboards, reports)
│   │   ├── schemas/           # Pydantic validation schemas
│   │   ├── services/          # Engines (pose_engine, biomechanics_engine, risk_scoring, anomaly_detection)
│   │   ├── config.py          # Platform settings and environment loading
│   │   ├── database.py        # SQLAlchemy engine and session factory
│   │   └── main.py            # FastAPI application entrypoint
│   ├── tests/                 # Automated test suite (pytest)
│   ├── .env.example           # Environment configuration template
│   ├── Dockerfile             # Backend container definition
│   └── requirements.txt       # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── api/client.js      # REST API client & auth session manager
│   │   ├── components/        # React UI components (VideoStudio, Biomechanics, InjuryRisk, Dashboards, AuthModal, etc.)
│   │   ├── App.jsx            # Application shell and tab router
│   │   └── main.jsx           # React DOM root
│   ├── Dockerfile             # Frontend container definition
│   ├── nginx.conf             # Production Nginx reverse proxy configuration
│   └── package.json           # Node.js dependencies & scripts
├── docker-compose.yml         # Multi-container orchestration (PostgreSQL + Backend + Frontend)
├── requirements.txt           # Root dependency requirements
├── run_app.bat                # Windows batch launcher
├── run_app.ps1                # PowerShell launcher
└── README.md                  # System documentation & setup guide
```
