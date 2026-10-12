# SYSTEM_WORKFLOW.md — End-to-End Operational Pipeline & Technical Architecture

This document describes the complete operational workflow of the Sports Injury Risk Detection Platform, tracing a video clip from upload to final multi-role reporting.

---

## 1. High-Level Pipeline Architecture

```
[Athlete / Coach Video Upload]
              │
              ▼
    1. Validation & Storage (FFprobe, local disk / uploads volume)
              │
              ▼
    2. Computer Vision Pipeline (YOLOv8n-pose + BoT-SORT + MediaPipe)
              │
              ├── Main-Subject Lock (resolves multi-person gym clips)
              └── Landmark Visibility Filter (< 0.5 discarded)
              │
              ▼
    3. Coverage & Quality Gating
              ├── < 40% Coverage ──► REJECTED (HTTP 422: clear coaching feedback)
              ├── 40-70% Coverage ─► PROVISIONAL (Carries coverage_caveat; excluded from baselines)
              └── >= 70% Coverage ─► GOLD STANDARD (Eligible for population reference baselines)
              │
              ▼
    4. Biomechanical Kinematics Engine
              ├── Movement-Specific Calculators (7 types in registry)
              ├── Sagittal Plane ────► Validated Joint Angles (Knee/Hip flexion, Trunk lean)
              └── Frontal Plane ─────► Qualitative Alignment Flags (Knee valgus, Hip adduction)
              │
              ▼
    5. Population Baseline & Risk Assessment
              ├── Baseline Sufficiency Gate (Floor check: returns HTTP 202 if building)
              ├── 35% Biomechanical Deviation (Isolation Forest + Robust-Z)
              ├── 20% Historical Injury Factors (Relevance x Recency)
              ├── 20% Bilateral Asymmetry (Limb Symmetry Index)
              ├── 15% Training Load (ACWR: Acute:Chronic Workload Ratio)
              └── 10% Fatigue & Drift (RPE trend + kinematic variance)
              │
              ▼
    6. Multi-Tenant Presentation & Exports
              ├── Role Dashboards (Athlete / Coach / Physio / Scientist / Admin)
              ├── Interactive Overlay Player & Recharts Angle Waveforms
              └── Export Service (PDF Clinical Report, Multi-sheet Excel, Frame-by-frame CSV)
```

---

## 2. Step-by-Step Workflow

### Step 1: Video Ingestion & Container Validation
1. **Upload Request**: The client requests an upload token via `POST /api/v1/videos/upload-url` providing athlete ID, movement type, and camera view (or `"auto"`).
2. **Access Verification**: Backend checks user role and athlete ownership (`_can_access_athlete`).
3. **Payload Ingestion**: File is uploaded directly to storage (`/uploads` in Docker or local disk).
4. **Integrity Check**: Backend runs FFprobe to extract duration, dimensions, framerate (FPS), and container validity. Videos exceeding limits or corrupted files are caught immediately.

### Step 2: Computer Vision & Pose Tracking
Processing runs in-process via `app/modules/pose/jobs.py` (no Redis or separate worker required):
1. **Person Detection & Tracking**: YOLOv8n-pose detects persons in each frame. BoT-SORT tracks identities across frames.
2. **Main-Subject Lock**: The person with the greatest presence and temporal continuity is locked as the primary athlete. This prevents tracking jumps when bystanders walk past the camera.
3. **Landmark Extraction**: MediaPipe extracts 33 3D body landmarks for the tracked subject.
4. **Visibility Gating**: Keypoints with visibility `< 0.5` are marked invalid to prevent noisy extrapolation.

### Step 3: Quality Gating & Coverage Filter
- **Coverage Floor**: Percentage of frames with the primary athlete tracked is computed:
  - `< 40%`: Automatically failed with informative guidance (e.g. "Athlete tracked in only 22% of frames; ensure athlete remains in frame").
  - `40% – 70%`: Processed with a `coverage_caveat`. Scored provisionally, but **strictly excluded** from population reference baselines to prevent polluting the normal envelope.
  - `> 70%`: Marked high/fair quality and eligible for population baselines.

### Step 4: Biomechanical Kinematic Calculations
The calculator registry (`app/modules/biomechanics/registry.py`) routes the landmarks to the appropriate movement calculator:

| Movement Type | Primary Validated Angles (Sagittal) | Qualitative Indicators (Frontal) | Dynamic Signals |
|---|---|---|---|
| **Squatting** | Knee flexion (L/R), Hip flexion (L/R), Trunk lean | Knee valgus deviation %, Hip adduction | Repetition depth, descent/ascent tempo |
| **Jumping** | Countermovement knee flexion, Hip flexion, Trunk lean | Takeoff knee valgus % | Flight time, takeoff/landing symmetry |
| **Landing** | Initial contact knee & hip flexion, Trunk lean | Impact knee valgus / varus % | Energy absorption symmetry, LESS criteria |
| **Running** | Stance knee flexion, Hip extension, Trunk lean | Contralateral pelvic drop % | Cadence (steps/min), step-time asymmetry |
| **Sprinting** | Stance knee flexion, Hip extension, Trunk lean | Contralateral pelvic drop % | High cadence (200+ spm), ground contact ratio |
| **Throwing** | Transverse trunk rotation swing, Trunk lean | Arm cocking alignment | Peak rotation velocity, rotational symmetry |
| **Cutting** | Plant-foot knee flexion, Lateral trunk lean | Plant-knee valgus flag % | Pelvis heading turn (deg), change-of-direction time |

#### Scientific Plane Constraints
- **Sagittal View (Side-on)**: True 2D joint angles are valid with ~5.9–6.8° RMSE. Used for numeric graphs, peaks, and range of motion.
- **Frontal View (Head-on)**: Parallax and depth foreshortening make 2D sagittal angles unmeasurable. The system reports **qualitative flags** (e.g. knee valgus deviation %, hip adduction) and directs the user to skeletal overlay inspection without rendering misleading angle numbers.

### Step 5: Population Baselines & Multi-Factor Risk Assessment
1. **Baseline Sufficiency Gate**:
   - Requires completed, clean videos across distinct athletes before computing relative anomaly scores.
   - If below threshold, returns `HTTP 202 Accepted` ("Baseline building"). Biomechanical numbers and charts are fully available, but no fabricated risk score is emitted.
2. **5-Component Transparent Composite**:
   $$\text{Overall Score} = \sum_{i} \left( \frac{w_i}{\sum_{\text{avail}} w_j} \times s_i \right)$$
   - **35% Biomechanical Deviation**: Unsupervised Isolation Forest on video-level extremes (p05, p95) + robust-z tail scoring against other videos of the same movement.
   - **20% Prior Injury History**: Evaluates recorded injuries by movement relevance and recency (unresolved, recent <24mo, remote).
   - **20% Bilateral Asymmetry**: Limb Symmetry Index ($\text{LSI} = \frac{\text{weaker}}{\text{stronger}} \times 100\%$) across peak joint angles.
   - **15% Training Load (ACWR)**: 7-day acute to 28-day chronic load ratio from daily training logs.
   - **10% Fatigue & Drift**: RPE trend across prior 4 weeks + within-session kinematic drift across repetitions.
3. **6 Specific Injury Categories**:
   - ACL, Hamstring strain, Ankle sprain, Shoulder, Lower back, Overuse.
   - Output as risk *levels* (`low`, `moderate`, `high`, `critical`) with named drivers, never ML percentages.

### Step 6: Multi-Tenant Dashboards & Reporting
- **Alerting**: If overall score or any injury category reaches `high` or `critical`, in-app notifications are automatically dispatched to the athlete's coach and assigned medical staff.
- **Role Dashboards**:
  - Athletes view personal readiness and actionable recommendations.
  - Coaches view team readiness roster and squad load trends.
  - Physios and Scientists inspect clinical flags, LSI balance, and population distributions.
- **Exports**:
  - **PDF Report**: Clinical-grade summary for doctor or coaching consultations.
  - **Excel Workbook**: Multi-tab analytical sheet containing per-frame data, summaries, and baseline statistics.
  - **CSV**: Raw frame-by-frame joint angles with timestamps.
