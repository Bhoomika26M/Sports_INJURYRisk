# ML Experimental Notebooks

This directory contains Jupyter notebooks used for research, exploratory data analysis (EDA), model benchmarking, and biomechanical validation.

## Research Workflows & Planned Notebooks

1. **`01_exploratory_pose_estimation.ipynb`**
   - Benchmark 2D/3D markerless pose estimation models: MediaPipe Pose vs. YOLOv8-Pose vs. RTMPose.
   - Analyze inference speed (FPS) and anatomical keypoint stability across rapid movements.

2. **`02_joint_angle_kinematics.ipynb`**
   - Vector geometry implementations to calculate:
     - 3D Knee Valgus / Varus angle.
     - Sagittal Knee Flexion angle over time.
     - Ankle Inversion / Eversion and dorsiflexion angles.
   - Digital filtering tests: Butterworth low-pass filter vs. Savitzky-Golay smoothing.

3. **`03_injury_risk_scoring_validation.ipynb`**
   - Correlation analysis comparing calculated video metrics against clinical screening baselines.
   - Threshold tuning for ACL, ankle sprain, and hamstring strain risk tiers (Low, Moderate, High).
