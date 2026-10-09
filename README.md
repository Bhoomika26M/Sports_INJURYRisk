# Sports Injury Risk Detection from Video

An AI-powered Sports Biomechanics and Injury Risk Intelligence Platform that analyzes athlete movement videos to identify biomechanical issues, detect abnormal movement patterns, assess injury risk factors, and predict potential injuries before they occur.

Built with **FastAPI**, **Google MediaPipe Pose**, **OpenCV**, **SQLAlchemy**, and **React 19 + Tailwind CSS + Recharts**.

---

## 🏆 Completed Milestones Overview

### Milestone 1: Project Initialization, Architecture & Core Setup
- **System Architecture & Data Modeling**: Fully relational SQLite / PostgreSQL schema via SQLAlchemy ORM models (`User`, `Athlete`, `VideoRecord`, `BiomechanicalAnalysis`, `InjuryRiskAssessment`).
- **User Authentication & Role-Based Access Control (RBAC)**:
  - 5 Roles: **Athlete**, **Coach**, **Physiotherapist**, **Sports Scientist**, **Administrator**.
  - Secure bcrypt password hashing and JWT token authorization.
  - Pre-seeded demo credentials for instant 1-click role simulation.
- **Athlete Profile Management**:
  - Athlete ID, sport type, position, age, height, weight.
  - Longitudinal injury history tracking (injury type, severity, clinical status).
  - Training load metrics: Weekly hours and **Acute-to-Chronic Workload Ratio (ACWR)**.
  - Physical baseline assessment metrics.
- **Sports Biomechanics Datasets Module**:
  - Standard reference benchmarks integrated: **Human3.6M**, **SportsPose**, **MPII**, **COCO Keypoints**, and **FIFA Injury Surveillance Dataset**.
  - Clinical normative baseline thresholds for knee valgus, trunk lean, bilateral asymmetry, and ACWR.

### Milestone 2: Pose Estimation & Biomechanical Analysis
- **Pose Estimation Engine**:
  - **MediaPipe Pose 33-point markerless skeleton extraction** on CPU with TensorFlow Lite XNNPACK delegate.
  - Real-time video frame processor rendering skeleton bones, color-coded joints, and on-screen HUD telemetry.
  - Frame-by-frame joint angle calculation for knees, hips, elbows, trunk lean, and pelvic obliquity.
- **Biomechanical Analysis Engine**:
  - **Dynamic Knee Valgus Angle** (Frontal Plane Projection Angle / FPPA) calculation — critical biomarker for ACL tear prediction.
  - **Hip Stability & Pelvic Drop** (Trendelenburg sign indicator).
  - **Trunk Lean Analysis** (lateral lean and forward flexion angles).
  - **Landing Mechanics Evaluation** (knee flexion angle at ground contact & landing stiffness index).
  - **Bilateral Movement Symmetry Index** ($BAI = \frac{|L - R|}{\max(L, R)} \times 100\%$).
  - **Range of Motion (ROM)** and **Joint Collinear Alignment**.
  - **Force Impact / Ground Reaction Force Estimation** (kinetic G-force approximation).
- **Synthetic Athletic Movement Capture Generator**:
  - One-click generator creating realistic biomechanical movements (Drop Jump Landing with dynamic valgus, Side Cutting, Deep Squat) so testing works out-of-the-box without manual file searches.

### Milestone 3: Injury Prediction & Corrective Recommendations
- **Weighted Scoring Engine** (Implements exact formula from Page 6 of specification):
  $$\text{Injury Risk Score} = 0.35 \times \text{Biomechanical Deviations} + 0.20 \times \text{Historical Injury Factors} + 0.20 \times \text{Movement Asymmetry} + 0.15 \times \text{Training Load Indicators} + 0.10 \times \text{Fatigue Indicators}$$
  - Categorical Risk Bands:
    - **Low Risk** (0 - 30)
    - **Moderate Risk** (31 - 60)
    - **High Risk** (61 - 85)
    - **Critical Risk** (86 - 100)
  - Core performance scores: **Movement Quality Score**, **Biomechanical Efficiency Score**, **Fatigue Risk Score**, **Overall Athlete Health Score**.
- **Injury Risk Prediction Engine (6 Core Categories)**:
  1. **ACL Injury Risk**: Dynamic knee valgus (> 15° threshold), stiff landing, bilateral landing asymmetry, ligament history.
  2. **Hamstring Injury Risk**: Pelvic obliquity drift, overstriding deceleration, eccentric deceleration deficit.
  3. **Ankle Sprain Risk**: Elevated ground reaction force (> 3.0G), lateral center-of-mass sway, prior ligament laxity.
  4. **Shoulder Injury Risk**: Overhead sport profile, scapular dyskinesis, kinetic chain torque leakage.
  5. **Lower Back Injury Risk**: Excessive lateral trunk lean (> 10°), asymmetric pelvic unleveling, lumbar shear.
  6. **Overuse Injury Risk**: Acute:Chronic Workload Ratio in danger zone (> 1.45), high weekly volume, kinematic fatigue drift.
- **Movement Anomaly Detection Engine**:
  - Temporal frame-by-frame threshold anomaly detection.
  - Fatigue-related movement monitoring measuring kinematic decay across repetitions.
  - Timestamped anomaly events feed.
- **Corrective Recommendation Engine**:
  - Targeted clinical exercise prescriptions with sets, reps, frequency, and coaching cues (e.g. Banded Monster Walks for valgus, Nordic curls for hamstrings, Pallof press for trunk lean).
  - Mobility improvement protocols, strengthening plans, recovery plans, and workload modifications.
- **Role-Specific Intelligence Dashboards**:
  - **Coach Dashboard**: Squad availability %, high-risk athlete alerts, full readiness roster table, workload modifications.
  - **Physiotherapist Dashboard**: Clinical rehabilitation registry, flagged valgus cases, asymmetry tracking.
  - **Sports Scientist Dashboard**: Cohort population means vs SportsPose gold standard, research insights.
  - **Athlete Dashboard**: Personal injury risk score, daily exercise checklist, active recovery guidelines.

---

## 🚀 Quick Start Guide

### 1. Launch with One Click
In the project directory, run:
```bat
.\run_app.bat
```
*(Or run `.\run_app.ps1` in PowerShell)*

### 2. Manual Startup

**Backend:**
```bash
cd backend
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```
- API Documentation (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/api/health](http://localhost:8000/api/health)

**Frontend:**
```bash
cd frontend
npm run dev -- --host 127.0.0.1 --port 3000
```
- Web Application: [http://localhost:3000](http://localhost:3000)

---

## 👥 Seed User Accounts

All demo accounts use password: `password123`

| Role | Email | Name | Focus |
|---|---|---|---|
| **Athlete** | `athlete@sportsai.com` | Marcus Vance | Personal Risk, Daily Exercises |
| **Coach** | `coach@sportsai.com` | Coach Roberto Martinez | Squad Availability, Workload |
| **Physiotherapist** | `physio@sportsai.com` | Dr. Sarah Jenkins | Rehab Registry, Joint ROM |
| **Sports Scientist** | `scientist@sportsai.com` | Dr. Alexei Volkov | Kinematics Distributions, Datasets |
| **Administrator** | `admin@sportsai.com` | Sys Admin | Full Platform Governance |

*(You can also use the role switcher in the top navigation bar to switch perspectives instantly).*

---

## 🧪 Automated Test Suite

Run the backend test suite:
```bash
cd backend
python -m pytest tests/test_api.py -v
```

Tests validate:
- System Health Check
- Reference Datasets Metadata
- JWT Authentication & Role Checking
- Athlete Profile Creation & Querying
- Exact Mathematical Implementation of Weighted Scoring Model (Page 6)
- Coach, Physio, and Sports Scientist Dashboard Endpoints
