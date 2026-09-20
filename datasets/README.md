# Datasets for Sports Injury Risk Detection

This directory contains datasets and dataset integration for the Sports Injury Risk Detection system.

## Dataset Registry

The dataset registry is maintained in `datasets/registry/datasets.json` and contains metadata about all datasets used in the system.

## Registered Datasets

### 1. Human3.6M
- **Purpose**: Human pose estimation, joint tracking, movement analysis
- **Modality**: Video + Motion Capture
- **Annotation Format**: 3D joint coordinates
- **Expected Keypoints**: 17 joints (head, neck, shoulders, elbows, wrists, hips, knees, ankles)
- **Source**: http://vision.imar.ro/human3.6m/
- **Status**: Not downloaded
- **License**: Research use only, requires license agreement
- **Setup**: Requires manual download and license request from the official website

### 2. MPII Human Pose
- **Purpose**: Body keypoint detection, activity recognition
- **Modality**: Images
- **Annotation Format**: 2D joint coordinates
- **Expected Keypoints**: 16 joints (head, neck, shoulders, elbows, wrists, hips, knees, ankles)
- **Source**: http://human-pose.mpi-inf.mpg.de/
- **Status**: Not downloaded
- **License**: Research use only
- **Setup**: Download from official website, requires registration

### 3. COCO Keypoints
- **Purpose**: Pose estimation training, human motion analysis
- **Modality**: Images
- **Annotation Format**: 2D joint coordinates with visibility
- **Expected Keypoints**: 17 keypoints (nose, eyes, ears, shoulders, elbows, wrists, hips, knees, ankles)
- **Source**: https://cocodataset.org/
- **Status**: Not downloaded
- **License**: Creative Commons, research and commercial use allowed
- **Setup**: Can be downloaded automatically using COCO API or manually from website

### 4. SportsPose
- **Purpose**: Sports-specific movement analysis, athlete posture assessment
- **Modality**: Video
- **Annotation Format**: 2D/3D joint coordinates
- **Expected Keypoints**: Variable, sport-specific
- **Source**: https://github.com/opencv/cvat
- **Status**: Not downloaded
- **License**: Requires manual collection or annotation
- **Setup**: This dataset typically requires custom annotation using tools like CVAT

### 5. FIFA Injury Dataset
- **Purpose**: Injury trend analysis, risk factor modeling
- **Modality**: Tabular data
- **Annotation Format**: Injury records, player statistics
- **Expected Keypoints**: N/A (tabular data)
- **Source**: https://www.fifainjury.com/
- **Status**: Not downloaded
- **License**: Research use only, may require access request
- **Setup**: Requires access request from FIFA or research institutions

### 6. Sample Pose Dataset
- **Purpose**: Dataset integration testing, pose data structure validation
- **Modality**: JSON annotations
- **Annotation Format**: 2D joint coordinates
- **Expected Keypoints**: 17 keypoints (nose, eyes, ears, shoulders, elbows, wrists, hips, knees, ankles)
- **Source**: Internal sample
- **Status**: Sample integrated
- **License**: Sample data for testing purposes
- **Setup**: Included in repository at `datasets/sample/sample_pose.json`

## Directory Structure

```
datasets/
├── README.md                 # This file
├── registry/
│   └── datasets.json        # Dataset registry metadata
├── raw/                      # Raw downloaded datasets (not in git)
├── processed/                # Processed datasets (not in git)
└── sample/
    └── sample_pose.json     # Sample dataset for testing
```

## Dataset Integration Status

- **Sample Integrated**: 1 dataset (Sample Pose Dataset)
- **Not Downloaded**: 5 datasets (Human3.6M, MPII Human Pose, COCO Keypoints, SportsPose, FIFA Injury Dataset)
- **Available**: 0 datasets
- **Requires Manual Download**: 5 datasets

## Dataset Validation

Run the dataset validation script to check dataset integration status:

```bash
python scripts/dataset/validate_datasets.py
```

This script will:
- Inspect registered datasets
- Check expected files
- Validate sample annotations
- Report missing datasets
- Report valid datasets

## Adding New Datasets

To add a new dataset to the registry:

1. Download or obtain the dataset
2. Place raw files in `datasets/raw/`
3. Process the dataset to match the common pose representation
4. Place processed files in `datasets/processed/`
5. Add metadata to `datasets/registry/datasets.json`
6. Update the validation script if needed
7. Run validation to confirm integration

## Common Pose Representation

The system uses a common pose representation for all datasets:

```json
{
  "person_id": 1,
  "keypoints": [
    {
      "name": "nose",
      "x": 0.0,
      "y": 0.0,
      "confidence": 0.0
    }
  ]
}
```

This standardized format allows Milestone 2 to plug in multiple datasets seamlessly.

## Milestone 1 Scope

In Milestone 1, the focus is on:
- Creating the dataset registry structure
- Implementing a sample dataset for testing
- Creating validation infrastructure
- Setting up the dataset API endpoint

Actual integration of large datasets (Human3.6M, COCO, etc.) is deferred to Milestone 2 when pose estimation models are implemented.

## Future Milestones

- **Milestone 2**: Integrate pose estimation datasets for model training
- **Milestone 3**: Use historical injury datasets for risk prediction models
- **Milestone 4**: Expand dataset collection for improved model accuracy

## Notes

- Large datasets are not included in the git repository
- Use `.gitignore` to exclude `datasets/raw/` and `datasets/processed/`
- Always respect dataset licenses and usage restrictions
- Some datasets require formal license agreements or access requests
