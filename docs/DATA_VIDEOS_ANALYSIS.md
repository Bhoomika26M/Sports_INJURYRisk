# Video Dataset Analysis & Agent Verification Guide

This document provides a comprehensive breakdown of all 9 video clips located in [`data/`](file:///c:/Users/USER/Desktop/injury%20detection/data), their physical movements, camera perspectives, detection gate behaviors, and biomechanical expectations under our **Pose & Risk Engine (v2.2)**.

It also provides turnkey instructions and CLI tools for automated agents to run any video against the model, verify outputs, and handle edge cases.

---

## 1. Summary Catalog

| Video Filename | Movement | View | Resolution | FPS | Sec | People Seen | Expected Pipeline Outcome | Quality / Gate Notes |
|---|---|---|---|---|---|---|---|---|
| `squatting_barbell_back_squat_side_view.mp4` | `squatting` | `sagittal` | 1920x1080 | 25.0 | 31.5s | 1 | **PASSED** (94.4% coverage) | Validated sagittal angles (hip, knee, trunk lean) |
| `landing_single_leg_drop_soft_landing.mp4` | `landing` | `sagittal` | 1920x1080 | 29.2 | 9.6s | 1 | **PASSED** (97.5% coverage) | Validated unilateral drop landing kinematics |
| `landing_one_foot_landing_pivot.mp4` | `landing` | `sagittal` | 1280x720 | 30.0 | 12.5s | 1 | **PASSED** (93.0% coverage) | Validated landing & pivot mechanics |
| `jumping_box_jump_demo.mp4` | `jumping` | `sagittal` | 3840x2026 | 24.0 | 9.8s | 1 | **PASSED** (100% coverage) | 4K AV1 container; takeoff & landing knee flexion |
| `throwing_shot_put_slow_motion.mp4` | `throwing` | `sagittal` | 1280x720 | 30.0 | 25.6s | 1 | **PASSED** (100% coverage) | Slow-motion rotational glide and release |
| `cutting_aquabag_punch_cod.mp4` | `cutting` | `frontal` | 1920x1080 | 60.0 | 11.4s | 1 | **PASSED** (84.4% coverage) | Frontal camera: qualitative knee valgus flag only |
| `cutting_180_cut_mechanics.mp4` | `cutting` | `sagittal` | 1920x1080 | 60.0 | 27.8s | 3 | **REJECTED** (41.9% coverage) | Gate: `multiple_people_subject_unstable` |
| `running_form_side_view.mp4` | `running` | `sagittal` | 1280x720 | 30.0 | 16.2s | 3 | **REJECTED** (28.0% coverage) | Gate: `multiple_people_subject_unstable` |
| `sprinting_sprint_speed_drills.mp4` | `sprinting` | `sagittal` | 1280x720 | 30.0 | 46.6s | 6 | **REJECTED** (14.9% coverage) | Gate: `multiple_people_subject_unstable` |

---

## 2. Detailed Breakdown Per Video

### 1. `squatting_barbell_back_squat_side_view.mp4`
- **Movement Type**: `squatting`
- **Camera View**: `sagittal` (lateral/side-on)
- **Description**: A solo lifter in a training rack performing multiple repetitions of barbell back squats. The camera is stationary and orthogonal to the lifter's sagittal plane.
- **Model Expectations**:
  - Person Detection: 1 athlete locked with 100% ID stability.
  - MediaPipe Pose: Landmark visibility > 0.90 across both hips, knees, and ankles.
  - Biomechanical Metrics: Peak knee flexion, hip flexion angle, forward trunk lean, and knee-to-ankle alignment.
  - Risk Scoring: Scored against sagittal squatting baselines. If baseline has < 10 videos or < 3 distinct athletes, returns HTTP 202 ("insufficient_baseline_data") rather than fabricating a score.

### 2. `landing_single_leg_drop_soft_landing.mp4`
- **Movement Type**: `landing`
- **Camera View**: `sagittal`
- **Description**: Single female athlete performing an elevated box step-down into a single-leg landing, absorbing shock through controlled knee flexion.
- **Model Expectations**:
  - Person Detection: Single track ID, no occlusions.
  - MediaPipe Pose: 97.5% coverage.
  - Biomechanical Metrics: Peak landing knee flexion (assessing stiff vs soft landing), knee flexion angular velocity, and trunk stability.
  - Outcome: **PASSED** (produces ~388 metric observations across frames).

### 3. `landing_one_foot_landing_pivot.mp4`
- **Movement Type**: `landing`
- **Camera View**: `sagittal`
- **Description**: Single athlete executing a unilateral landing followed immediately by a rapid pivot turn on indoor court flooring.
- **Model Expectations**:
  - Person Detection: 1 track ID, 93.0% coverage.
  - Biomechanical Metrics: Ground contact deceleration, initial contact knee flexion angle, and trunk rotation.
  - Outcome: **PASSED**.

### 4. `jumping_box_jump_demo.mp4`
- **Movement Type**: `jumping`
- **Camera View**: `sagittal`
- **Description**: Single male athlete performing plyometric box jumps in a gym. Captured in ultra-high resolution (4K: 3840x2026) encoded with AV1 (`AV01`).
- **Model Expectations**:
  - Video Decoder: OpenCV opens AV1 container seamlessly.
  - Coverage Gate: 100% detection coverage.
  - Biomechanical Metrics: Countermovement squat depth, take-off hip extension, peak flight phase, and landing knee flexion.
  - Outcome: **PASSED**.

### 5. `throwing_shot_put_slow_motion.mp4`
- **Movement Type**: `throwing`
- **Camera View**: `sagittal`
- **Description**: Solo track & field athlete executing a full rotational shot-put sequence in high frame rate / slow motion.
- **Model Expectations**:
  - Video Stride: Captured in slow motion; pipeline uses stride computation to sample within worker budget.
  - Coverage Gate: 100% detection coverage.
  - Biomechanical Metrics: Shoulder abduction, elbow angle, trunk rotation angle during glide and release.
  - Outcome: **PASSED**.

### 6. `cutting_aquabag_punch_cod.mp4`
- **Movement Type**: `cutting`
- **Camera View**: `frontal`
- **Description**: Agility / combat conditioning drill where athlete strikes an aqua bag and performs a rapid change-of-direction lateral cut.
- **Model Expectations**:
  - Camera View Constraint: Frontal camera view. Per `/docs/SCIENCE_CONSTRAINTS.md`, frontal plane measurements can **never** claim exact knee valgus angles. All knee valgus metrics are labeled with `'qualitative'` confidence.
  - Coverage Gate: 84.4% detection coverage -> **PASSED**.

### 7. `cutting_180_cut_mechanics.mp4`
- **Movement Type**: `cutting`
- **Camera View**: `sagittal`
- **Description**: Turf drill demonstrating 180-degree change of direction. Three individuals are visible in the background and foreground, moving dynamically.
- **Model Expectations**:
  - YOLO Tracking: Detects 3 separate track IDs. The primary athlete drops below 70% continuity (41.9% coverage).
  - Gate Decision: **REJECTED** with error code `multiple_people_subject_unstable`.
  - Scientific Rationale: The pipeline explicitly refuses to guess or inadvertently blend joints from adjacent athletes.

### 8. `running_form_side_view.mp4`
- **Movement Type**: `running`
- **Camera View**: `sagittal`
- **Description**: 3 runners running side-by-side along an outdoor path.
- **Model Expectations**:
  - YOLO Tracking: 3 track IDs detected. Overlapping silhouettes cause frequent track swaps, resulting in 28.0% main subject coverage.
  - Gate Decision: **REJECTED** with code `multiple_people_subject_unstable`.
  - Pipeline behavior: Safe rejection without crashing.

### 9. `sprinting_sprint_speed_drills.mp4`
- **Movement Type**: `sprinting`
- **Camera View**: `sagittal`
- **Description**: Group track training with multiple athletes executing sequential sprint acceleration runs.
- **Model Expectations**:
  - YOLO Tracking: 6 different track IDs detected across 46.6 seconds.
  - Gate Decision: **REJECTED** (14.9% coverage) with code `multiple_people_subject_unstable`.

---

## 3. How An Agent Can Run & Verify These Videos

We provide a dedicated validation tool: [`backend/scripts/verify_data_videos.py`](file:///c:/Users/USER/Desktop/injury%20detection/backend/scripts/verify_data_videos.py).

### Commands

1. **List the catalog and expected outcomes**:
   ```bash
   python backend/scripts/verify_data_videos.py --list
   ```

2. **Verify a single video (full resolution)**:
   ```bash
   python backend/scripts/verify_data_videos.py --video landing_single_leg_drop_soft_landing.mp4
   ```

3. **Fast Verification for CI / Quick Agent Checks (skips frames via stride)**:
   ```bash
   python backend/scripts/verify_data_videos.py --video jumping_box_jump_demo.mp4 --fast
   ```

4. **Verify all 9 videos and output machine-readable JSON**:
   ```bash
   python backend/scripts/verify_data_videos.py --all --fast --json
   ```

---

## 4. Code Modifications Made

1. **Windows & Host Path Compatibility Fix**:
   - In [`backend/scripts/e2e_video_check.py`](file:///c:/Users/USER/Desktop/injury%20detection/backend/scripts/e2e_video_check.py) and [`backend/scripts/real_clip_validation.py`](file:///c:/Users/USER/Desktop/injury%20detection/backend/scripts/real_clip_validation.py), hardcoded `"/uploads"` paths were updated to `settings.upload_dir` (`os.path.join(settings.upload_dir, storage_key)`).
   - This ensures scripts run cleanly on both native host Windows environments and Docker containers.
2. **Added Direct Verification CLI**:
   - Added [`backend/scripts/verify_data_videos.py`](file:///c:/Users/USER/Desktop/injury%20detection/backend/scripts/verify_data_videos.py) with automated pass/reject expectation assertions.
