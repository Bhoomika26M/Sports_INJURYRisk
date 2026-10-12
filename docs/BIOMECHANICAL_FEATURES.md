# Biomechanical Features Documentation

This document describes the biomechanical features calculated by the Milestone 2 system.

## Important Disclaimer

**All biomechanical features are video-derived proxies based on monocular RGB video analysis.**

These features are:
- NOT clinically validated
- NOT medical diagnoses
- NOT suitable for clinical decision-making without validation
- Sensitive to camera positioning, lighting, and athlete visibility

## Feature Categories

### 1. Joint Angles

#### Knee Angle

**Description:** Angle at the knee joint formed by hip-knee-ankle.

**Input Landmarks:**
- Hip (left or right)
- Knee (left or right)
- Ankle (left or right)

**Formula:**
```
vector1 = hip - knee
vector2 = ankle - knee
angle = acos(dot(vector1, vector2) / (|vector1| * |vector2|))
```

**Units:** Degrees (0-180)

**Coordinate Assumptions:**
- 2D coordinates from monocular camera
- Angle calculated in image plane
- Perspective distortion affects accuracy

**Confidence Requirements:**
- All three keypoints must have confidence ≥ 0.3
- If any keypoint below threshold, returns None

**Limitations:**
- Frontal view may not accurately represent knee flexion
- Side view recommended for sagittal plane movements
- No depth information

**Interpretation:**
- 180°: Fully extended
- 90°: Right angle
- <90°: Deep flexion (squat depth)

---

#### Hip Angle

**Description:** Angle at the hip joint formed by shoulder-hip-knee.

**Input Landmarks:**
- Shoulder (left or right)
- Hip (left or right)
- Knee (left or right)

**Formula:** Same as knee angle

**Units:** Degrees (0-180)

**Coordinate Assumptions:**
- 2D coordinates from monocular camera
- Side view recommended for accuracy

**Confidence Requirements:**
- All three keypoints must have confidence ≥ 0.3

**Limitations:**
- Frontal view may not accurately represent hip flexion
- Perspective distortion affects accuracy

**Interpretation:**
- Larger angles indicate greater hip flexion

---

#### Elbow Angle

**Description:** Angle at the elbow joint formed by shoulder-elbow-wrist.

**Input Landmarks:**
- Shoulder (left or right)
- Elbow (left or right)
- Wrist (left or right)

**Formula:** Same as knee angle

**Units:** Degrees (0-180)

**Limitations:**
- May not be relevant for lower-body sports
- Requires upper-body visibility

---

#### Shoulder Angle

**Description:** Angle at the shoulder joint formed by elbow-shoulder-hip.

**Input Landmarks:**
- Elbow (left or right)
- Shoulder (left or right)
- Hip (left or right)

**Formula:** Same as knee angle

**Units:** Degrees (0-180)

**Limitations:**
- May not be relevant for lower-body sports
- Complex 3D motion may not be captured in 2D

---

### 2. Range of Motion (ROM)

#### Description

For each joint, calculate the range of motion across the entire movement.

**Formula:**
```
ROM = max_angle - min_angle
```

**Input:** Sequence of joint angles across frames

**Output:**
- `min_angle`: Minimum angle observed
- `max_angle`: Maximum angle observed
- `rom`: Range of motion (max - min)

**Units:** Degrees

**Confidence Requirements:**
- Filters out None values from low-confidence frames
- Requires at least one valid angle

**Limitations:**
- Dependent on accurate angle calculation
- Sensitive to outliers
- No comparison to reference ranges

**Interpretation:**
- Larger ROM indicates greater joint movement
- Should be interpreted in context of activity

---

### 3. Left-Right Symmetry

#### Description

Calculate asymmetry between left and right side measurements.

**Formula:**
```
asymmetry = |left_value - right_value|
```

**Metrics:**
- `mean_asymmetry`: Average asymmetry across frames
- `max_asymmetry`: Maximum asymmetry observed
- `std_asymmetry`: Standard deviation of asymmetry

**Input:** Paired left and right measurements (e.g., knee angles)

**Units:** Same as input (degrees for angles)

**Confidence Requirements:**
- Filters out None values
- Aligns left and right by frame index

**Limitations:**
- Assumes frontal or symmetrical camera view
- Asymmetry may be legitimate (e.g., handedness)
- No reference "normal" asymmetry value

**Interpretation:**
- Higher asymmetry may indicate imbalance
- Context-dependent (some asymmetry is normal)

---

### 4. Knee Alignment / Valgus Proxy

#### Description

Video-derived proxy for knee alignment in the frontal plane.

**Input Landmarks:**
- Hip (left or right)
- Knee (left or right)
- Ankle (left or right)

**Formula:**
```
expected_knee_x = (hip_x + ankle_x) / 2
deviation = knee_x - expected_knee_x
```

**Units:** Pixels (relative to torso normalization)

**Coordinate Assumptions:**
- Frontal view required
- Monocular camera
- No camera calibration

**Confidence Requirements:**
- All three keypoints must have confidence ≥ 0.3

**Limitations:**
- **NOT a clinically validated valgus measurement**
- 2D projection of 3D alignment
- Perspective distortion affects accuracy
- Does not account for hip abduction/adduction
- Cannot distinguish between true valgus and camera angle

**Interpretation:**
- Positive deviation: knee outward (valgus-like)
- Negative deviation: knee inward (varus-like)
- Magnitude indicates degree of deviation

**Warning:** Do not use for clinical diagnosis without validation.

---

### 5. Trunk Lean

#### Description

Angle of trunk relative to vertical.

**Input Landmarks:**
- Left shoulder
- Right shoulder
- Left hip
- Right hip

**Formula:**
```
shoulder_center = (left_shoulder + right_shoulder) / 2
hip_center = (left_hip + right_hip) / 2
dx = shoulder_center.x - hip_center.x
dy = shoulder_center.y - hip_center.y
angle = atan2(dx, -dy)
```

**Units:** Degrees

**Coordinate Assumptions:**
- Vertical is negative y direction
- Monocular camera
- Frontal or side view

**Confidence Requirements:**
- All four keypoints must have confidence ≥ 0.3

**Metrics:**
- `mean`: Average trunk lean
- `max`: Maximum trunk lean
- `min`: Minimum trunk lean
- `std`: Standard deviation

**Limitations:**
- 2D projection of 3D orientation
- Camera angle affects measurement
- No compensation for tilt

**Interpretation:**
- 0°: Vertical trunk
- Positive: Leaning right
- Negative: Leaning left

---

### 6. Velocity

#### Description

First derivative of measurements over time.

**Formula:**
```
velocity[t] = (value[t] - value[t-1]) / (timestamp[t] - timestamp[t-1])
```

**Input:** Sequence of measurements with timestamps

**Units:** Degrees per second (for angles)

**Confidence Requirements:**
- Filters out None values
- Requires valid previous frame

**Metrics:**
- `knee_mean`: Average knee velocity
- `knee_max`: Maximum knee velocity

**Limitations:**
- Sensitive to noise (differentiation amplifies noise)
- Requires temporal smoothing
- Actual frame rate may vary

**Interpretation:**
- Higher velocity indicates faster movement
- May correlate with power/explosiveness

---

### 7. Acceleration

#### Description

Second derivative of measurements over time.

**Formula:**
```
acceleration[t] = (velocity[t] - velocity[t-1]) / (timestamp[t] - timestamp[t-1])
```

**Input:** Velocity sequence with timestamps

**Units:** Degrees per second² (for angles)

**Confidence Requirements:**
- Requires two valid previous velocity values

**Metrics:**
- `knee_mean`: Average knee acceleration
- `knee_max`: Maximum knee acceleration

**Limitations:**
- Very sensitive to noise
- Requires smoothing
- May not be reliable without filtering

**Interpretation:**
- Higher acceleration indicates more explosive movement
- May correlate with impact forces

---

### 8. Movement Quality

#### Description

Overall assessment of movement quality.

**Current Implementation:**
- Placeholder score (75/100)
- Components:
  - Symmetry: 80/100
  - Stability: 75/100
  - Smoothness: 70/100

**Note:** This is a placeholder. Future versions will implement:

**Proposed Components:**
- Pose quality (confidence-based)
- Symmetry (left-right balance)
- Stability (trunk control)
- Smoothness (movement fluidity)
- ROM appropriateness (activity-specific)

**Limitations:**
- Current implementation is placeholder
- No activity-specific criteria
- No validated scoring system

**Future Work:**
- Activity-specific quality criteria
- Machine learning-based quality assessment
- Comparison to expert-labeled data

---

## Data Structure

All features are stored as JSON in the `biomechanical_analyses` table:

```json
{
  "joint_angles": {
    "knee_left": {"min_angle": 90, "max_angle": 150, "rom": 60},
    "knee_right": {"min_angle": 92, "max_angle": 148, "rom": 56},
    "hip_left": {"min_angle": 70, "max_angle": 120, "rom": 50},
    "hip_right": {"min_angle": 72, "max_angle": 118, "rom": 46}
  },
  "rom": {
    "knee_left": {"min_angle": 90, "max_angle": 150, "rom": 60},
    ...
  },
  "symmetry": {
    "knee_asymmetry": {"mean_asymmetry": 5.2, "max_asymmetry": 12.0, "std_asymmetry": 3.1},
    "hip_asymmetry": {"mean_asymmetry": 4.8, "max_asymmetry": 10.0, "std_asymmetry": 2.9}
  },
  "knee_alignment": {
    "left_deviation": [...],
    "right_deviation": [...]
  },
  "trunk_lean": {
    "mean": 2.5,
    "max": 8.0,
    "min": -3.0,
    "std": 2.1
  },
  "velocity": {
    "knee_mean": 45.2,
    "knee_max": 120.5
  },
  "acceleration": {
    "knee_mean": 250.3,
    "knee_max": 800.7
  },
  "movement_quality": {
    "score": 75.0,
    "components": {
      "symmetry": 80.0,
      "stability": 75.0,
      "smoothness": 70.0
    }
  }
}
```

## Future Milestone 3 Integration

These biomechanical features are designed to be input features for the Milestone 3 injury-risk prediction model:

**Proposed ML Input Features:**
- Joint angle statistics (mean, min, max, std)
- ROM for each joint
- Symmetry metrics
- Trunk lean statistics
- Velocity and acceleration statistics
- Movement quality components
- Pose confidence statistics
- Fatigue-related changes (early vs late reps)
- Activity type (categorical)
- Athlete demographics (age, height, weight)

**The ML model will:**
- Learn feature importance
- Combine features non-linearly
- Predict injury risk probability
- Provide interpretable results

## Validation Requirements

Before clinical use, these features require:

1. **Clinical Validation:** Compare to gold-standard measurements
2. **Reliability Testing:** Test-retest reliability
3. **Accuracy Assessment:** Against motion capture systems
4. **Camera Calibration:** Known camera parameters
5. **Reference Ranges:** Population-specific norms
6. **Expert Review:** Sports scientist/physiotherapist validation

## Citations

Biomechanical principles based on:
- Standard kinesiology textbooks
- Sports biomechanics literature
- Movement analysis research

(References to be added in future iterations)
