# Sports Injury Risk Detection from Video

AI-powered sports injury intelligence and prevention platform that analyzes athlete movement videos to identify biomechanical abnormalities, assess injury risks (ACL, hamstring, ankle, patellar), and generate personalized corrective exercise prescriptions.

---

## 🌟 Key Features & Implemented Modules

### 1. User Authentication & Role-Based Access Control (RBAC)
- Secure JWT bearer token authentication and salted password hashing (bcrypt).
- Full 5-role governance:
  - **Athlete**: Movement scanning, personal injury scores, corrective exercise guidance.
  - **Coach**: Squad risk overview, team readiness index, load deloading alerts.
  - **Physiotherapist**: Clinical rehabilitation tracking, joint vulnerability matrix, corrective protocol adherence.
  - **Sports Scientist**: Biomechanical deep-dive analytics, joint angle distributions, risk correlations.
  - **Administrator**: User permissions management, system health metrics, audit telemetry.

### 2. Athlete Profile & Training Load Management
- Biometric records: Age, height, weight, sport type, and positional tracking.
- Training load monitoring (0–100%) with acute load threshold warnings (>80%).
- Historical injury records integrated into machine learning risk inference.

### 3. Video Processing & Pose Estimation Engine
- Video upload (MP4, MOV, WEBM) and synthetic movement generation for rapid assessment.
- 33 3D body landmark extraction using **MediaPipe Pose**.
- Sub-pixel joint tracking across sagittal and frontal anatomical planes.

### 4. Biomechanical Movement Quality Analysis
- **Dynamic Knee Valgus**: Medial knee displacement calculation against the 8.0° clinical safety threshold.
- **Bilateral Limb Asymmetry**: Bilateral symmetry discrepancy evaluation across movement phases.
- **Range of Motion (ROM)**: Sagittal knee and hip flexion depth measurement.
- **Postural Alignment**: Sagittal and lateral trunk lean tracking.
- Interactive frame-by-frame kinematics timeline scrubber.

### 5. Multi-Factor AI Injury Risk Prediction
- **Calibrated Multi-Output Random Forest Model**:
  - **ACL Ligament Strain Risk** (correlated with knee valgus and stiff landing).
  - **Hamstring Strain Risk** (correlated with bilateral asymmetry and sprint fatigue).
  - **Ankle Inversion / Sprain Risk** (correlated with lateral sway and postural instability).
  - **Patellar Tendonitis Risk** (correlated with training load overload).
- **Early Warning System**: Automated alerts for severe biomechanical anomalies.
- **Prescriptive Corrective Protocols**: Targeted exercise recommendations with dose and frequency.

### 6. Executive Dashboards & Analytics
- **Coach Squad Hub**: Squad health index, high-risk athlete count, team roster with live status badges.
- **Physiotherapy Rehab Center**: Rehabilitation stage progression (Phase 1 to Phase 4), joint vulnerability radar, adherence tracking.
- **Sports Science Lab**: Movement comparisons (Squat vs Jump-Landing vs Sprint Gait), research correlation matrices, ML validation metrics.
- **Admin Control Center**: User role management, API latency telemetry, server vitals.

### 7. Notification, Alerts & Reporting System
- Real-time early warning notifications bell with unread counters and severity indicators.
- **Printable Medical & Biomechanical Assessment Report**: Pre-formatted for PDF export / printing.
- **CSV Data Export**: One-click download of athletic and kinematic data for external analysis.

### 8. Containerization & Deployment
- Docker containerization for frontend and backend (`docker-compose.yml`, `Dockerfile.backend`, `Dockerfile.frontend`, `nginx.conf`).
- Complete automated unit and integration tests (`pytest`).

---

## 🏗 System Architecture

```
┌────────────────────────────────────────────────────────┐
│                   React 19 Frontend                    │
│   (Studio • Coach • Physio • Sports Science • Admin)   │
└───────────────────────────▲────────────────────────────┘
                            │ REST / JSON (JWT Auth)
┌───────────────────────────▼────────────────────────────┐
│                  FastAPI API Gateway                   │
│   (/auth, /athletes, /analysis, /prediction,           │
│    /dashboard, /notifications, /reports, /users)       │
└──────┬────────────────────┬────────────────────┬───────┘
       │                    │                    │
┌──────▼───────┐     ┌──────▼───────┐     ┌──────▼───────┐
│ MediaPipe CV │     │ Scikit-Learn │     │  SQLite / PG │
│ 33 Keypoints │     │ Risk Models  │     │ Relational DB│
└──────────────┘     └──────────────┘     └──────────────┘
```

---

## 🔑 Demo Presentation Credentials

For immediate one-click evaluation during final presentations, pre-seeded role accounts are available (or use the one-click quick-fill buttons on the login screen):

| Role | Email | Password | Primary Dashboard |
| :--- | :--- | :--- | :--- |
| **🏀 Coach** | `coach@sportguard.ai` | `coach123` | Squad Readiness, Deload Triggers, Roster Status |
| **🩺 Physiotherapist** | `physio@sportguard.ai` | `physio123` | Rehab Progression (Phases 1-4), Joint Vulnerability, Adherence |
| **🔬 Sports Scientist** | `science@sportguard.ai` | `science123` | Biomechanical Kinematics Lab, Valgus/Asymmetry Benchmarks |
| **🏃 Athlete** | `athlete@sportguard.ai` | `athlete123` | Movement Studio, Personal Risk, Tailored Prescriptions |
| **⚙️ Administrator** | `admin@sportguard.ai` | `admin123` | RBAC Management, System Health, API Telemetry |

---

## 🚀 Quick Start Guide

### Option 1: One-Click Launch (Windows)
Double-click `run_dev.bat` from the project root:
```bat
run_dev.bat
```
This automatically boots both backend and frontend servers:
- **Frontend App**: [http://localhost:5173](http://localhost:5173)
- **FastAPI Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### Option 2: Manual Development Setup

#### Backend Setup
```bash
cd backend
python -m venv venv
venv\Scripts\activate   # On Windows (or source venv/bin/activate on Linux/Mac)
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

---

### Option 3: Docker Deployment

To launch the complete containerized stack:
```bash
cd docker
docker-compose up --build
```
- Frontend will be served at `http://localhost:80` (or `http://localhost:5173`)
- Backend will be accessible at `http://localhost:8000`

---

## 🧪 Running Automated Tests

Run the backend test suite:
```bash
cd backend
pytest
```
Tests cover:
- Authentication, Registration, and JWT token issuance
- Athlete CRUD and Roster operations
- Pose kinematics & Biomechanical assessment logic
- AI Injury prediction model inference and recommendation engine
- Coach, Physio, Sports Science, and Admin dashboard endpoints
- Notifications and CSV report generation
