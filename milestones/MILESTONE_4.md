# Milestone 4: Role Dashboards, Real Broadcast Video Analysis, Export System & Docker

## 🎯 Objective
Complete the production ecosystem: implement 5 role-specific executive dashboards, deploy real broadcast sports match footage with purposeful AI bounding boxes, provide printable clinical PDF reports and CSV datasets, and containerize the frontend and backend with Docker.

---

## 🛠 Implemented Components

### 1. Five Role-Specific Executive Dashboards
- **Coach Squad Hub (`/dashboard/coach`)**:
  - Squad Health Index, High-Risk Athlete Count, Active Roster table with live injury probability tags.
  - Squad-level load deloading alerts to protect players from overtraining.
- **Physiotherapy Rehab Center (`/dashboard/physio`)**:
  - 4-Phase Rehabilitation Stage Progression (Acute -> Load Introduction -> Sport-Specific -> Return to Play).
  - Joint Vulnerability Matrix (Knee Valgus, Hamstring Strain, Ankle Instability).
  - Corrective exercise protocol adherence tracking (avg 82%).
- **Sports Science Biomechanics Lab (`/dashboard/sports-scientist`)**:
  - Kinematic benchmarks across activities (Squat vs Jump-Landing vs Sprint Gait).
  - Research correlation matrices (Pearson's $r$ between valgus and ACL strain).
  - ML model validation metrics ($R^2$, MAE, Keypoint PCK@0.2).
- **Admin Control Center (`/dashboard/admin`)**:
  - User permissions governance (list users, update role, delete).
  - System health metrics: FastAPI gateway uptime, API response latency (ms), Computer Vision inference engine status.
- **Athlete Studio View**:
  - Biometric profile overview, live movement studio with pose playback, individual risk scores, and tailored exercise doses.

### 2. Video Studio: Uploaded Athlete Video & Broadcast Match Analysis
- **Dedicated Uploaded Video Player**:
  - When the user clicks **"UPLOAD ATHLETE VIDEO"**, the interface automatically expands to full width and focuses exclusively on **THAT uploaded video**.
  - Displays file name, file size in MB, movement pattern, and live pose landmarking status.
  - Completely hides sample videos to eliminate website clutter.
- **Real Broadcast Sports Match Footage**:
  - **Basketball Court** (`broadcast_basketball.mp4`): Jump shot & court landing with dynamic valgus collapse.
  - **Volleyball Arena** (`broadcast_volleyball.mp4`): Spike jump takeoff & stiff block landing impact (> 5.2G).
  - **100m Track Sprint** (`sprint_track_clean.mp4`): Real stadium 100m race with stride cadence and hamstring tension.
  - **Soccer Pitch** (`detected_soccer_match.mp4`): Turf plant-and-cut deceleration and rotational shear.
- **Purposeful AI Bounding Boxes**:
  - **Athlete ROI Isolation**: Crops the target athlete from teammates, opponents, and stadium background.
  - **Feature Extraction**: 33 keypoints inside the box feed directly into the Random Forest model.
  - **Risk-Adaptive Colors**: 🟢 **Green** (Safe) -> 🟡 **Amber** (Asymmetry Warning) -> 🔴 **Red** (Valgus Collapse).

### 3. Reporting, Notifications & Data Export
- **Printable Clinical PDF Report**: Pre-styled for browser print and PDF export with report ID, metadata, kinematic charts, anomaly flags, and medical sign-off.
- **CSV Data Export (`/reports/export/csv`)**: One-click download of athletic and kinematic data for external research.
- **Live Notifications Bell (`/notifications`)**: Real-time alerts for acute training load spikes and high-risk movements.

### 4. Containerization & Production Deployment
- **Docker Compose (`docker-compose.yml`)**: Multi-container stack orchestration with automatic healthchecks.
- **Backend Dockerfile (`docker/Dockerfile.backend`)**: Python 3.13 image with OpenCV, MediaPipe, and Scikit-Learn.
- **Frontend Dockerfile (`docker/Dockerfile.frontend`)**: Multi-stage Node.js build with Nginx reverse proxy serving static assets.
- **One-Click Launch**: Windows `run_dev.bat` boots backend and frontend concurrently in separate terminal windows.

---

## 📁 Source Code Mapping

| File Path | Description |
| :--- | :--- |
| [`backend/app/routes/dashboard.py`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/backend/app/routes/dashboard.py) | Endpoints for Coach, Physio, Sports Scientist, Admin, and Athlete dashboards |
| [`backend/app/routes/notifications.py`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/backend/app/routes/notifications.py) | Live alert bell, mark-as-read, and severity filter endpoints |
| [`backend/app/routes/reports.py`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/backend/app/routes/reports.py) | Report generation and `/reports/export/csv` dataset download |
| [`backend/app/routes/users.py`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/backend/app/routes/users.py) | RBAC user management (list, update role, delete) |
| [`frontend/public/videos/`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/frontend/public/videos/) | Real H.264 sports match footage (Basketball, Volleyball, Track, Soccer) |
| [`frontend/src/App.tsx`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/frontend/src/App.tsx) | Complete React 19 UI with role-based navigation, focused upload player, and report printing |
| [`frontend/src/App.css`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/frontend/src/App.css) | Cyberpunk athletic UI styling and responsive layouts |
| [`docker-compose.yml`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/docker-compose.yml) | Root Docker Compose orchestration file |
| [`docker/`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/docker/) | Dockerfiles for frontend, backend, and Nginx configuration |

---

## 🧪 Verification & Tests

Run Milestone 4 automated tests:
```bash
cd backend
pytest tests/test_dashboards.py -v
```

### Test Cases Verified:
- `test_coach_dashboard`: Verifies squad health index and athlete risk roster.
- `test_physio_dashboard`: Verifies 4-phase rehab progression and joint vulnerability matrix.
- `test_sports_scientist_dashboard`: Verifies kinematic benchmarks and Pearson correlation matrices.
- `test_admin_dashboard`: Verifies user counts and system health metrics.
- `test_notifications_endpoints`: Verifies notification fetching, creation, and mark-as-read.
- `test_reports_endpoints`: Verifies report generation and CSV download integrity.

---

## 🏆 Full Suite Summary

Run the entire 24-test suite across all 4 milestones:
```bash
cd backend
pytest -v
```
**Result**: **24 passed, 0 failed in 4.86s**.
