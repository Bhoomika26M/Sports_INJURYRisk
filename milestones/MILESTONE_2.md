# Milestone 2: 33-Point MediaPipe Pose Estimation & Kinematics Engine

## 🎯 Objective
Extract 33 3D anatomical body landmarks from athletic movement footage in real-time, compute clinical biomechanical joint angles, evaluate dynamic knee valgus and bilateral asymmetry, and generate movement quality scores.

---

## 🛠 Implemented Components

### 1. Computer Vision Pose Landmarker
- **MediaPipe Tasks API**: Utilizes `mediapipe.tasks.python.vision.PoseLandmarker` for sub-pixel 3D joint localization.
- **Calibrated Detection Confidence**: Tuned detection, presence, and tracking thresholds to `0.25` for zero-frame drop across full-court and wide-angle sports match footage.
- **33 Keypoints Tracked**: Shoulders, elbows, wrists, hips, knees, ankles, heels, and toe indices across sagittal and frontal planes.

### 2. Biomechanical Movement Quality Engine
- **Dynamic Knee Valgus Calculation**:
  Medial deviation of the knee joint relative to the hip-ankle mechanical vector:
  $$\text{Valgus Angle} = |\theta_{\text{knee}} - 180^\circ| \quad (\text{Clinical threshold: } > 8.0^\circ \text{ elevated, } > 14.0^\circ \text{ critical collapse})$$
- **Bilateral Limb Asymmetry Index**:
  Quantitative bilateral limb loading differential:
  $$\text{Asymmetry Index} = \frac{|\text{Left} - \text{Right}|}{\max(\text{Left}, \text{Right})} \times 100\% \quad (\text{Threshold: } > 10\% \text{ warning, } > 20\% \text{ severe})$$
- **Knee Flexion Range of Motion (ROM)**:
  Measures sagittal squat/landing depth to flag stiff deceleration impacts (< 60° landing depth).
- **Trunk Lean & Postural Stability**:
  Calculates sagittal and lateral torso displacement relative to the vertical gravity vector.
- **Movement Quality Index**:
  Weighted composite score (0–100) combining Valgus Stability (35%), Symmetry (25%), ROM (25%), and Posture (15%).

---

## 📁 Source Code Mapping

| File Path | Description |
| :--- | :--- |
| [`backend/app/services/pose_estimator.py`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/backend/app/services/pose_estimator.py) | MediaPipe 33-keypoint inference engine on images and video files |
| [`backend/app/services/biomechanics.py`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/backend/app/services/biomechanics.py) | Trigonometric kinematic math, valgus, asymmetry, and quality scoring |
| [`backend/app/models/analysis.py`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/backend/app/models/analysis.py) | Database table storing time-series kinematics and detected anomalies |
| [`backend/app/routes/analysis.py`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/backend/app/routes/analysis.py) | Endpoints `/analysis/process-video` and `/analysis/analyze-video-file` |
| [`backend/app/schemas/analysis.py`](file:///C:/Users/MARIYA%20JOHN/sports-injury-ai/backend/app/schemas/analysis.py) | Pydantic response contracts for quality reports and sampled frames |

---

## 🧪 Verification & Tests

Run Milestone 2 automated tests:
```bash
cd backend
pytest tests/test_milestone2.py -v
```

### Test Cases Verified:
- `test_calculate_angle_2d_right_angle`: Verifies 90.0° trigonometric accuracy.
- `test_calculate_angle_2d_straight_line`: Verifies 180.0° collinear calculation.
- `test_knee_valgus_calculation`: Zero valgus on straight limb, positive valgus on medial knee collapse.
- `test_bilateral_asymmetry_index`: Identifies bilateral load imbalances.
- `test_movement_quality_assessment`: Composite scoring and grade assignment (`EXCELLENT`, `GOOD`, `NEEDS_IMPROVEMENT`).
- `test_pose_estimator_init_and_frame_inference`: MediaPipe model asset loading and landmark extraction.
- `test_synthetic_demo_database_storage`: Kinematic persistence in database records.
