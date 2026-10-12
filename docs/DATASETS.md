# Datasets Documentation

This document describes the datasets supported by the Sports Injury Risk Detection system for pose estimation validation and injury-risk reference data.

## Overview

The system supports the following datasets:

1. **Human3.6M** - 3D human pose estimation dataset
2. **MPII Human Pose** - 2D human pose estimation dataset
3. **COCO Keypoints** - Person detection and pose estimation dataset
4. **SportsPose** - Sports-specific pose dataset
5. **FIFA Injury Dataset** - Injury label and risk factor reference data

## Dataset Adapters

Each dataset has an adapter in `backend/app/datasets/adapters.py` that handles:

- Data loading
- Annotation format conversion
- Keypoint mapping to BlazePose (33 landmarks)
- Preprocessing

### Using Adapters

```python
from app.datasets import get_adapter

# Get adapter for a dataset
adapter = get_adapter("coco", "/path/to/coco")

# Load annotations
annotations = adapter.load_annotations()

# Map keypoints to BlazePose format
blazepose_keypoints = adapter.map_keypoints_to_blazepose(dataset_keypoints)

# Get keypoint mapping
mapping = adapter.get_keypoint_mapping()
```

## Human3.6M

### Description
- **Size**: 3.6 million human poses
- **Keypoints**: 17 keypoints
- **Format**: 3D poses (x, y, z)
- **Use Case**: 3D human pose estimation validation

### Acquisition
- **URL**: http://vision.imar.ro/human3.6m/
- **License**: Requires license application
- **Access**: Must request access from the Human3.6M team

### Directory Structure
```
data/datasets/human36m/
├── h36m/
│   ├── S1/
│   ├── S5/
│   ├── S6/
│   ├── S7/
│   ├── S8/
│   ├── S9/
│   └── S11/
└── metadata/
```

### Key Point Mapping
Human3.6M has 17 keypoints. Compatible keypoints map to BlazePose:

| Human3.6M Index | Human3.6M Name | BlazePose Name |
|-----------------|----------------|----------------|
| 0 | hip | left_hip |
| 1 | right_hip | right_hip |
| 2 | right_knee | right_knee |
| 3 | right_foot | right_ankle |
| 4 | left_hip | left_hip |
| 5 | left_knee | left_knee |
| 6 | left_foot | left_ankle |
| 11 | right_shoulder | right_shoulder |
| 12 | right_elbow | right_elbow |
| 13 | right_wrist | right_wrist |
| 14 | left_shoulder | left_shoulder |
| 15 | left_elbow | left_elbow |
| 16 | left_wrist | left_wrist |

### Preprocessing
- Convert 3D coordinates to 2D (x, y) for validation
- Normalize coordinates to image dimensions
- Handle missing keypoints

### Intended Use
- 3D pose estimation benchmarking
- Biomechanical pipeline validation
- Keypoint mapping validation

### License/Access Constraints
- Requires license application
- Academic use only
- Cannot redistribute data

## MPII Human Pose

### Description
- **Size**: ~40k people
- **Keypoints**: 16 keypoints
- **Format**: 2D poses (x, y)
- **Use Case**: 2D human pose estimation validation

### Acquisition
- **URL**: http://human-pose.mpi-inf.mpg.de/
- **License**: Research use only
- **Access**: Download from official website

### Directory Structure
```
data/datasets/mpii/
├── images/
├── annotations/
│   └── train.json
└── test.json
```

### Key Point Mapping
MPII has 16 keypoints. Compatible keypoints map to BlazePose:

| MPII Index | MPII Name | BlazePose Name |
|------------|-----------|----------------|
| 0 | right_ankle | right_ankle |
| 1 | right_knee | right_knee |
| 2 | right_hip | right_hip |
| 3 | left_hip | left_hip |
| 4 | left_knee | left_knee |
| 5 | left_ankle | left_ankle |
| 10 | right_wrist | right_wrist |
| 11 | right_elbow | right_elbow |
| 12 | right_shoulder | right_shoulder |
| 13 | left_shoulder | left_shoulder |
| 14 | left_elbow | left_elbow |
| 15 | left_wrist | left_wrist |

### Preprocessing
- Parse JSON annotation format
- Scale coordinates to image dimensions
- Handle occluded keypoints

### Intended Use
- 2D pose estimation benchmarking
- Keypoint mapping validation
- Comparison with BlazePose accuracy

### License/Access Constraints
- Research use only
- Citation required

## COCO Keypoints

### Description
- **Size**: 200k images with keypoints
- **Keypoints**: 17 keypoints
- **Format**: 2D poses (x, y, visibility)
- **Use Case**: Person detection and pose estimation

### Acquisition
- **URL**: https://cocodataset.org/#keypoints-2020
- **License**: Creative Commons
- **Access**: Free download

### Directory Structure
```
data/datasets/coco/
├── images/
│   ├── train2017/
│   └── val2017/
└── annotations/
    ├── person_keypoints_train2017.json
    └── person_keypoints_val2017.json
```

### Key Point Mapping
COCO has 17 keypoints that are largely compatible with BlazePose:

| COCO Index | COCO Name | BlazePose Name |
|------------|------------|----------------|
| 0 | nose | nose |
| 1 | left_eye | left_eye |
| 2 | right_eye | right_eye |
| 3 | left_ear | left_ear |
| 4 | right_ear | right_ear |
| 5 | left_shoulder | left_shoulder |
| 6 | right_shoulder | right_shoulder |
| 7 | left_elbow | left_elbow |
| 8 | right_elbow | right_elbow |
| 9 | left_wrist | left_wrist |
| 10 | right_wrist | right_wrist |
| 11 | left_hip | left_hip |
| 12 | right_hip | right_hip |
| 13 | left_knee | left_knee |
| 14 | right_knee | right_knee |
| 15 | left_ankle | left_ankle |
| 16 | right_ankle | right_ankle |

### Preprocessing
- Parse COCO JSON format
- Handle visibility flags (0=not labeled, 1=labeled but not visible, 2=visible)
- Scale coordinates to image dimensions

### Intended Use
- Pose estimation benchmarking
- Keypoint mapping validation
- PCK (Percentage of Correct Keypoints) evaluation

### License/Access Constraints
- Creative Commons Attribution 4.0 License
- Free to use and modify
- Citation required

## SportsPose

### Description
- **Size**: Sports-specific poses
- **Keypoints**: 17 keypoints (COCO-style)
- **Format**: 2D poses
- **Use Case**: Sports-specific pose estimation

### Acquisition
- **URL**: https://github.com/microsoft/SportsPose
- **License**: MIT License
- **Access**: GitHub repository

### Directory Structure
```
data/datasets/sportspose/
├── images/
├── annotations/
└── metadata/
```

### Key Point Mapping
SportsPose uses COCO-style keypoints. See COCO section for mapping.

### Preprocessing
- Uses COCO preprocessing pipeline
- Handles sports-specific annotations

### Intended Use
- Sports pose estimation validation
- Biomechanical pipeline validation
- Sports-specific movement analysis

### License/Access Constraints
- MIT License
- Free to use and modify

## FIFA Injury Dataset

### Description
- **Size**: Injury records
- **Format**: Injury labels and risk factors
- **Use Case**: Injury-risk reference data for Milestone 3

### Important Note
FIFA dataset is **NOT a pose dataset**. It provides injury labels and risk factors that will be used in Milestone 3 for injury classification.

### Acquisition
- **URL**: https://www.fifamedicalnetwork.com/
- **License**: Requires licensing
- **Access**: Must request access from FIFA

### Directory Structure
```
data/datasets/fifa/
├── injury_records/
├── risk_factors/
└── metadata/
```

### Intended Use
- Injury label data for Milestone 3
- Risk factor analysis
- Injury classifier training (future)

### License/Access Constraints
- Requires licensing from FIFA
- Strict usage restrictions
- Cannot redistribute data

## Dataset Evaluation

See `scripts/evaluate_pose_pipeline.py` for evaluation scripts.

### Supported Metrics

#### COCO
- PCK (Percentage of Correct Keypoints)
- PCKh (PCK normalized by head size)
- AP (Average Precision)

#### MPII
- PCKh
- mAP (mean Average Precision)

#### Human3.6M
- 3D PCK
- MPJPE (Mean Per Joint Position Error)

### Limitations

Some datasets cannot be evaluated due to:
- **Access/Licensing**: Human3.6M, FIFA require licenses
- **Format**: Different annotation formats require custom parsers
- **Keypoint Mismatch**: Some datasets have incompatible keypoints

If a dataset cannot be evaluated, the evaluation script will explicitly state the limitation.

## Current Status

- ✅ Adapters implemented for all datasets
- ⚠️  Actual dataset downloading requires user action
- ⚠️  Evaluation scripts require dataset access
- ✅ Keypoint mappings defined
- ✅ Documentation complete

## Next Steps

1. Download desired datasets to `data/datasets/`
2. Run evaluation script: `python scripts/evaluate_pose_pipeline.py --dataset coco`
3. Review benchmark results
4. Use FIFA data in Milestone 3 for injury classification

## References

- Human3.6M: http://vision.imar.ro/human3.6m/
- MPII: http://human-pose.mpi-inf.mpg.de/
- COCO: https://cocodataset.org/#keypoints-2020
- SportsPose: https://github.com/microsoft/SportsPose
- FIFA: https://www.fifamedicalnetwork.com/
