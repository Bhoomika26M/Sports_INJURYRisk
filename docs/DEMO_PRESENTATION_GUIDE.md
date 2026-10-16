# Verification Report & Demo Presentation Guide

## 1. Executive Summary & Verification Results

All changes from `injury_risk_fast_run_changed_files.zip` have been applied, integrated, and verified end-to-end on Windows with native PostgreSQL, Docker Desktop, and Chrome. All video files from `data/` and `test-assets/` were uploaded and processed through the live pipeline.

### Key Verification Metrics
- **Processing Speed**: Real clip analysis dropped from multiple minutes to **~15–24 seconds** on this laptop (YOLO running at 15 FPS with bounding-box interpolation and resized frame; MediaPipe pose running full-pass).
- **In-Process Job Queue**: Redis and arq were removed. The backend processes uploads sequentially in-process with automatic recovery on startup.
- **H.264 Playback in Chrome**: Generated tracked videos use `libx264` with `yuv420p` and `+faststart`. **Verified in Chrome**: the "With tracking" tab displays the athlete's bounding box, pose skeleton, and angles seamlessly.
- **Corpus Processing Across Movements**: 18 total videos processed across all 7 movements from `data/` and `test-assets/`:
  - **12 Completed Videos**: Squatting (6 clips across 6 distinct athletes), Landing (2 clips), Jumping (1 4K AV1 clip), Throwing (1 slow-mo clip), Cutting (1 frontal clip).
  - **6 Refused / Guardrail Videos**: Multi-runner and crowded clips (`running_form_side_view`, `sprinting_sprint_speed_drills`, `cutting_180_cut_mechanics`, `7a6W56OeU8w`, `Px4cyTAHrWc`) were safely rejected with `multiple_people_subject_unstable`. Synthetic stick figure (`test_figure.mp4`) rejected with `no_person_detected`.
- **AI Baselines & Risk Scores Active**:
  - `squatting_barbell_back_squat_side_view.mp4`: **Score 54.8 / 100** (High Risk), 5 recommendations.
  - `squat_sample.mp4`: **Score 26.7 / 100** (Moderate Risk), 2 recommendations.
  - `clip.mp4` (squat 1, 2, 3): **Score 37.2 / 100** (Moderate Risk), 2 recommendations.
- **Test Suite**:
  - `tests/test_speed_and_jobs.py`: 14 passed, 1 skipped.
  - `tests/test_upload_formats.py`: 6/6 passed (MP4, MOV, WebM, AVI, MKV, M4V).
  - `tests/test_pose_tasks.py`: 7/7 passed.
  - `tests/test_worker_task.py`, `test_compose_env.py`, `test_health.py`: 14/14 passed.
- **Frontend**: Next.js 16 production build (`npm run build`) succeeded across all 21 App Router pages and is served via `npm run start` on port 3000.

---

## 2. Launch Commands for Demo Day

### Option A: Native Host (Fastest & Recommended)
1. **PostgreSQL**: Native Postgres is already listening on port 5432.
2. **Terminal 1 — Backend API**:
   ```powershell
   cd "c:\Users\USER\Desktop\injury detection\backend"
   python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```
   *Health check: `http://localhost:8000/health` → `{"status":"healthy"}`.*
3. **Terminal 2 — Frontend App**:
   ```powershell
   cd "c:\Users\USER\Desktop\injury detection\frontend"
   npm run start
   ```
   *App URL: **`http://localhost:3000`** (use `localhost`, not `127.0.0.1`).*

### Option B: With Docker Desktop
- If starting Postgres via Docker Compose: `docker compose up -d` starts the Postgres 15 container.
- To run the full containerized stack: `docker compose --profile app up --build`.

---

## 3. Demo Presentation Workflow (What to Show & Say)

### Phase 1: Context & Login (1 minute)
- **Open**: `http://localhost:3000/login`
- **What to say**:
  > *"Our platform analyzes athlete movement biomechanics from single-camera video to identify injury risk indicators without relying on false 'ML predictions'. We support five specialized roles: Coach, Physiotherapist, Sports Scientist, Athlete, and Admin. Today I am logging in as Coach."*
- **Action**: Enter `coach@demo.com` / `demo123` (or `admin@demo.com` / `demo123` to view all uploads) and click **Sign in**.

### Phase 2: Coach Dashboard & Athletes (1–2 minutes)
- **URL**: `http://localhost:3000/dashboard/coach`
- **What to highlight**:
  - Show the squad overview, active athletes, and risk distribution.
  - Click **Athletes** (`/athletes`): show the athlete profile cards, sports (basketball, soccer, track), and prior injury records (prior ACL sprain or hamstring strain).
- **What to say**:
  > *"Risk scoring does not examine video in isolation; it integrates an athlete's prior injury history and acute-to-chronic training load into the overall evaluation."*

### Phase 3: Movement Diversity in Video Library (2 minutes)
- **URL**: `http://localhost:3000/videos`
- **What to highlight**:
  - Show the rich variety of sports movements processed:
    - **Squatting**: Barbell squat and bodyweight squats.
    - **Landing**: Unilateral drop-landing and pivot landing.
    - **Jumping**: Box jump test (processed from high-res 4K footage).
    - **Throwing**: Shot put technique analysis.
    - **Cutting**: Change-of-direction mechanics.
  - Show the **Guardrail Refusals**: click on `running_form_side_view.mp4` or `sprinting_sprint_speed_drills.mp4` to show the `multiple_people_subject_unstable` badge.
- **What to say**:
  > *"Notice how the system enforces strict sports-science quality gates. When footage contains 3 runners side-by-side or unstable subject occlusion, it explicitly refuses to guess rather than attributing the wrong runner's mechanics to an athlete."*

### Phase 4: Video Player & Biomechanics Deep-Dive (3 minutes)
- **Action**: Click on **`squatting_barbell_back_squat_side_view.mp4`** or `squat_sample.mp4`.
- **What to highlight**:
  1. Toggle between **"With tracking"** and **"Original"**.
  2. Hit **Play** on the tracked video:
     - Show the smooth browser H.264 playback.
     - Show the green YOLO bounding box and full skeletal pose skeleton overlay.
  3. **Biomechanics Grid & Reps**:
     - Completed repetitions counter and rep duration.
     - Knee flexion, hip flexion, and trunk lean angles.
     - Bilateral asymmetry balance between left and right legs.
  4. **Angle Curves Over Time**: Point out the flexion cycles across each repetition.
- **What to say**:
  > *"The dual-stage pipeline uses YOLOv8 for athlete locking and MediaPipe Pose for 3D anatomical landmarks, rendering directly to browser-playable H.264."*

### Phase 5: Injury Category Risk Assessment & Recommendations (2 minutes)
- **URL**: `.../results` tab on the video page.
- **What to highlight**:
  - **Overall Movement Score**: (e.g. `54.8 / 100` High Risk on barbell squat, `26.7` on bodyweight squat).
  - **6 Injury Categories**:
    - **Hamstring Strain** & **Lower Back**: Flagged according to bilateral load asymmetry and trunk lean.
    - **ACL, Ankle Sprain, Shoulder, Overuse**: Flagged according to movement-specific deviations.
  - **Actionable Recommendations**:
    - Highlight specific drills generated (e.g., *Address left/right asymmetry*, *Nordic hamstring exercise*).
  - **Export Buttons**: Click **Download CSV** or **Export PDF** to show the professional report generation.

### Phase 6: Live Upload Demo (Optional, ~20s)
- **URL**: `http://localhost:3000/videos/upload`
- **Action**:
  - Upload `test-assets\sample-clips\squat_sample.mp4`.
  - Movement: `squatting`, View: `sagittal`.
  - Click **Upload & Process**.
  - Show the progress bar advancing steadily through tracking and pose phases, finishing in under 20 seconds!

---

## 4. Key Talking Points & Scientific Constraints

| Question / Topic | What to Say |
|---|---|
| **"Is this predicting an injury?"** | *"No. We deliberately do not claim ML injury prediction. No accessible dataset reliably links video pose to clinical injury incidence. Instead, we perform unsupervised anomaly detection against empirical movement baselines and literature-cited biomechanical thresholds."* |
| **"What if only 1 video has been uploaded?"** | *"The platform features a Baseline Sufficiency Gate. It returns 'Baseline Building' (HTTP 202) until at least 3 completed videos across 2 distinct athletes exist for that exercise type. We never fabricate scores."* |
| **"What models are used?"** | *"Pretrained Ultralytics YOLOv8 for athlete detection and subject lock, and MediaPipe Pose Landmarker for 3D landmark extraction."* |
| **"How are knee valgus and frontal plane angles handled?"** | *"Frontal-plane knee valgus from 2D monocular video cannot reliably yield sub-degree precision due to perspective foreshortening. We report frontal-plane metrics as qualitative risk flags, in accordance with sports science literature."* |

---

## 5. Troubleshooting & Safety Tips

- **Access URL**: Always use `http://localhost:3000`, NOT `http://127.0.0.1:3000` (cookies are bound to localhost).
- **Accounts**:
  - Coach: `coach@demo.com` / `demo123`
  - Admin (sees all uploads): `admin@demo.com` / `demo123`
  - Athlete: `athlete@demo.com` / `demo123`
  - Physio: `physio@demo.com` / `demo123`
- **Pre-warmed Pipeline**: The backend loads YOLO and MediaPipe on startup, so the very first upload will not stall on model loading.
