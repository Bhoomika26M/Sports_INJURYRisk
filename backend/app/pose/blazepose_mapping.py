"""
BlazePose 33-Point Canonical Landmark Mapping

This file provides the explicit canonical mapping for MediaPipe BlazePose 33 landmarks.
Used for skeleton visualization, biomechanical calculations, and coordinate reference.

BlazePose Landmark Index Reference:
===================================

Index | Name                   | Description
------|------------------------|-----------------------------------
0     | nose                   | Nose tip
1     | left_eye_inner         | Left eye inner corner
2     | left_eye               | Left eye center
3     | left_eye_outer         | Left eye outer corner
4     | right_eye_inner        | Right eye inner corner
5     | right_eye              | Right eye center
6     | right_eye_outer        | Right eye outer corner
7     | left_ear               | Left ear
8     | right_ear              | Right ear
9     | mouth_left             | Left mouth corner
10    | mouth_right            | Right mouth corner
11    | left_shoulder          | Left shoulder
12    | right_shoulder         | Right shoulder
13    | left_elbow             | Left elbow
14    | right_elbow            | Right elbow
15    | left_wrist             | Left wrist
16    | right_wrist            | Right wrist
17    | left_pinky             | Left pinky finger tip
18    | right_pinky            | Right pinky finger tip
19    | left_index             | Left index finger tip
20    | right_index            | Right index finger tip
21    | left_thumb             | Left thumb tip
22    | right_thumb            | Right thumb tip
23    | left_hip               | Left hip
24    | right_hip              | Right hip
25    | left_knee              | Left knee
26    | right_knee             | Right knee
27    | left_ankle             | Left ankle
28    | right_ankle            | Right ankle
29    | left_heel              | Left heel
30    | right_heel             | Right heel
31    | left_foot_index        | Left foot index
32    | right_foot_index       | Right foot index


Named Landmarks for Biomechanics:
==================================

These are the primary landmarks used in biomechanical calculations:

Upper Body:
- nose
- left_shoulder
- right_shoulder
- left_elbow
- right_elbow
- left_wrist
- right_wrist

Lower Body:
- left_hip
- right_hip
- left_knee
- right_knee
- left_ankle
- right_ankle

Feet (for running/landing analysis):
- left_heel
- right_heel
- left_foot_index
- right_foot_index


Skeletal Connections (for visualization):
==========================================

Face:
- nose <-> left_eye_inner
- nose <-> right_eye_inner
- left_eye_inner <-> left_eye
- left_eye <-> left_eye_outer
- right_eye_inner <-> right_eye
- right_eye <-> right_eye_outer
- nose <-> left_ear
- nose <-> right_ear
- left_ear <-> mouth_left
- right_ear <-> mouth_right

Upper Body:
- left_shoulder <-> right_shoulder
- left_shoulder <-> left_elbow
- left_elbow <-> left_wrist
- right_shoulder <-> right_elbow
- right_elbow <-> right_wrist
- left_shoulder <-> left_hip
- right_shoulder <-> right_hip

Hands:
- left_wrist <-> left_pinky
- left_wrist <-> left_index
- left_wrist <-> left_thumb
- right_wrist <-> right_pinky
- right_wrist <-> right_index
- right_wrist <-> right_thumb

Lower Body:
- left_hip <-> right_hip
- left_hip <-> left_knee
- left_knee <-> left_ankle
- right_hip <-> right_knee
- right_knee <-> right_ankle

Feet:
- left_ankle <-> left_heel
- left_ankle <-> left_foot_index
- right_ankle <-> right_heel
- right_ankle <-> right_foot_index


Biomechanical Calculation Reference:
=====================================

Knee Angle (left or right):
- Points: hip - knee - ankle
- Uses: left_hip, left_knee, left_ankle (or right equivalents)

Hip Angle (left or right):
- Points: shoulder - hip - knee
- Uses: left_shoulder, left_hip, left_knee (or right equivalents)

Elbow Angle (left or right):
- Points: shoulder - elbow - wrist
- Uses: left_shoulder, left_elbow, left_wrist (or right equivalents)

Trunk Lean:
- Points: shoulder center - hip center
- Uses: left_shoulder, right_shoulder, left_hip, right_hip

Ankle Angle (left or right):
- Points: knee - ankle - foot_index
- Uses: left_knee, left_ankle, left_foot_index (or right equivalents)


Coordinate System:
==================

BlazePose returns normalized coordinates (0.0 to 1.0) where:
- (0, 0) = top-left corner
- (1, 1) = bottom-right corner
- x increases left to right
- y increases top to bottom

For pixel coordinates (used in this system):
- Multiply normalized x by image width
- Multiply normalized y by image height


Important Notes:
=================

1. All landmarks are returned for every frame, but confidence varies
2. Visibility score (confidence) ranges from 0.0 to 1.0
3. Recommended confidence threshold: 0.3 for biomechanics
4. Occluded landmarks may have low confidence
5. This mapping is based on MediaPipe BlazePose model
6. Coordinate mapping from ROI to original frame must account for:
   - ROI bounding box offset
   - ROI cropping dimensions
   - Original frame dimensions
"""

# Canonical mapping dictionary
BLAZEPOSE_LANDMARKS = {
    0: "nose",
    1: "left_eye_inner",
    2: "left_eye",
    3: "left_eye_outer",
    4: "right_eye_inner",
    5: "right_eye",
    6: "right_eye_outer",
    7: "left_ear",
    8: "right_ear",
    9: "mouth_left",
    10: "mouth_right",
    11: "left_shoulder",
    12: "right_shoulder",
    13: "left_elbow",
    14: "right_elbow",
    15: "left_wrist",
    16: "right_wrist",
    17: "left_pinky",
    18: "right_pinky",
    19: "left_index",
    20: "right_index",
    21: "left_thumb",
    22: "right_thumb",
    23: "left_hip",
    24: "right_hip",
    25: "left_knee",
    26: "right_knee",
    27: "left_ankle",
    28: "right_ankle",
    29: "left_heel",
    30: "right_heel",
    31: "left_foot_index",
    32: "right_foot_index"
}

# Reverse mapping
LANDMARK_NAME_TO_INDEX = {v: k for k, v in BLAZEPOSE_LANDMARKS.items()}

# Named landmarks for biomechanics
BIOMECHANICS_LANDMARKS = [
    "nose",
    "left_shoulder",
    "right_shoulder",
    "left_elbow",
    "right_elbow",
    "left_wrist",
    "right_wrist",
    "left_hip",
    "right_hip",
    "left_knee",
    "right_knee",
    "left_ankle",
    "right_ankle"
]

# Skeletal connections for visualization
SKELETON_CONNECTIONS = [
    # Face
    (0, 1), (0, 4), (1, 2), (2, 3), (4, 5), (5, 6),
    (0, 7), (0, 8), (7, 9), (8, 10),
    # Upper body
    (11, 12),  # shoulders
    (11, 13), (13, 15),  # left arm
    (12, 14), (14, 16),  # right arm
    (11, 23), (12, 24),  # shoulders to hips
    # Hands
    (15, 17), (15, 19), (15, 21),  # left hand
    (16, 18), (16, 20), (16, 22),  # right hand
    # Lower body
    (23, 24),  # hips
    (23, 25), (25, 27),  # left leg
    (24, 26), (26, 28),  # right leg
    # Feet
    (27, 29), (27, 31),  # left foot
    (28, 30), (28, 32),  # right foot
]
