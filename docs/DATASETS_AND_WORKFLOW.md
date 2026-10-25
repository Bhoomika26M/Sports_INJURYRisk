# Datasets and Movement Analysis Workflow

This document outlines the architecture, integration adapters, and clinical biomechanical workflows for the Sports Injury Risk Detection platform.

---

## 1. Integrated Datasets & Benchmarks

The platform integrates 5 core computer vision and clinical datasets to power pose standardization, movement analysis, and risk factor evaluation:

| Dataset | Primary Purpose | Keypoint Topology | Role in Platform |
| :--- | :--- | :--- | :--- |
| **Human3.6M** | 3D Human Pose & Depth Estimation | 17 / 32 3D skeleton joints | Benchmark for 3D depth inference, joint velocities, and Range of Motion (ROM). |
| **MPII Human Pose** | 2D Keypoint Detection & Activity Recognition | 16 body joints (410 activity classes) | Baseline 2D topology and standard activity classification mapping. |
| **COCO Keypoints** | General In-the-Wild Pose Standard | 17 keypoints `(x, y, v)` | Standard backbone pretraining topology (MediaPipe / YOLO-pose input adapter). |
| **SportsPose** | Dynamic Sports Biomechanics | 24 high-velocity 3D athletic markers | High-speed athletic kinematics calibration (sprint acceleration, drop jumps, cutting). |
| **FIFA Injury Reference** | Clinical Injury Prevention & Risk Modeling | Evidence-based clinical rules (FIFA 11+ / F-MARC) | Mathematical risk thresholds for dynamic knee valgus, stiff landing, trunk lean, and asymmetry. |

---

## 2. Pose Estimation vs. Clinical Injury-Risk Modeling

* **Pose Estimation Datasets** (Human3.6M, MPII, COCO, SportsPose) teach computer vision models to locate $(x, y, z)$ joint coordinates. A skeleton map by itself cannot diagnose injury.
* **Injury-Risk Modeling** (FIFA 11+ / F-MARC Reference) provides the clinical translation layer. Joint angles, angular velocities, and bilateral asymmetries computed from pose data are compared against established medical thresholds to flag high-risk motion patterns.

---

## 3. FIFA 11+ Evidence-Based Risk Factor Thresholds

The platform actively benchmarks calculated kinematic values against the following clinical rules:

1. **Dynamic Knee Valgus (Inward Knee Collapse):**
   * *Target Normative Value:* $\le 10^\circ$
   * *Moderate Risk:* $10^\circ - 18^\circ$
   * *High Risk (ACL Indicator):* $> 18^\circ$
   * *Clinical Implication:* Primary non-contact mechanism for Anterior Cruciate Ligament (ACL) rupture and patellofemoral syndrome.
   * *Intervention:* FIFA 11+ Part 2 jump landing alignment, single-leg squats, and gluteus medius strengthening.

2. **Landing Knee Flexion (Stiff Landing):**
   * *Target Normative Value:* $\ge 45^\circ$ flexion
   * *Moderate Risk:* $30^\circ - 45^\circ$
   * *High Risk:* $< 30^\circ$ (stiff landing)
   * *Clinical Implication:* Multiplies ground reaction impact transmitted directly into knee ligaments and tendons.
   * *Intervention:* Box drop landing cueing: *"land softly on the balls of your feet and bend your knees"*.

3. **Forward & Lateral Trunk Lean:**
   * *Target Normative Value:* $\le 15^\circ$
   * *Moderate Risk:* $15^\circ - 25^\circ$
   * *High Risk:* $> 25^\circ$
   * *Clinical Implication:* Shifts body center of mass outside base of support, exponentially increasing knee abduction moment.
   * *Intervention:* Core stabilization: front/side planks, single-leg bird-dogs.

4. **Limb Symmetry Index (LSI):**
   * *Target Normative Value:* $\le 10\%$ (or $\le 10^\circ$ angle delta)
   * *Borderline Risk:* $10\% - 15\%$
   * *High Risk:* $> 15\%$
   * *Clinical Implication:* Indicates chronic overcompensation, limb unloading, or incomplete rehabilitation.
   * *Intervention:* Unilateral balance drills, single-leg hop stabilization, controlled eccentric loading.

---

## 4. Multi-Dataset Adapters & API Endpoints

The system includes native adapters (`backend/app/utils/dataset_adapters.py`) to convert external pose formats into the platform's standardized 33-landmark schema:

* `convert_coco_keypoints(keypoints, width, height)`
* `convert_mpii_joints(joints, width, height)`
* `convert_human36m_joints(joints_3d, is_normalized)`
* `convert_sportspose_frame(sports_dict)`
* `evaluate_fifa_risk_compliance(observed_metrics)`

### REST Endpoints (`/api/v1/datasets`)

* `GET /api/v1/datasets`: Lists all integrated datasets with full specifications.
* `GET /api/v1/datasets/{dataset_id}`: Fetches individual dataset topology and clinical role.
* `GET /api/v1/datasets/fifa/risk-factors`: Returns clinical thresholds and intervention protocols.
* `GET /api/v1/datasets/{dataset_id}/sample`: Generates realistic sample benchmark payloads.
* `POST /api/v1/datasets/convert`: Normalizes external keypoints into platform format, calculates biomechanics, and produces a FIFA clinical compliance assessment.

---

## 5. Frontend Integration

Athletes, coaches, and sports scientists can access the **Datasets & Standards** dashboard at `/datasets`:
* **Dataset Catalog Tab:** Interactive overview of all 5 datasets.
* **FIFA 11+ Reference Tab:** In-depth guide to clinical risk thresholds and prevention exercise drills.
* **Pipeline Simulator Tab:** Live converter where users can load COCO, MPII, Human3.6M, or SportsPose frames and inspect computed angles and FIFA compliance in real-time.
