# Sports Injury Risk Detection
## Dataset Collection – Milestone 1

### 1. Purpose

Datasets are required to train, evaluate, and validate the computer
vision, pose estimation, biomechanical analysis, and injury risk
prediction components of the Sports Injury Risk Detection system.

The datasets selected for initial research cover human pose estimation,
sports movement analysis, and injury-related information.

---

## 2. Human3.6M

### Purpose

Human3.6M is a large-scale human motion dataset containing videos and
3D human body pose information.

### Planned Use

- Human pose estimation research
- Human movement analysis
- 3D body keypoint research
- Testing pose estimation approaches

### Project Relevance

The dataset can help understand how human body joints and movement
patterns can be represented computationally.

---

## 3. MPII Human Pose Dataset

### Purpose

MPII Human Pose is a human pose estimation dataset containing
annotated human poses in real-world activities.

### Planned Use

- 2D human pose estimation
- Body keypoint detection
- Movement pose analysis
- Evaluation of pose estimation techniques

### Project Relevance

The dataset can help in understanding body joint detection before
applying pose estimation to sports videos.

---

## 4. COCO Keypoints

### Purpose

The COCO dataset contains images with human keypoint annotations
used for human pose estimation.

### Planned Use

- Human keypoint detection
- Pose estimation
- Testing computer vision models
- Initial model development

### Project Relevance

COCO Keypoints can be used as a general-purpose human pose dataset
before adapting the system to sports-specific movements.

---

## 5. SportsPose

### Purpose

SportsPose is considered for sports-specific human pose and movement
analysis.

### Planned Use

- Sports movement analysis
- Athlete pose estimation
- Sports-specific movement patterns
- Biomechanical feature extraction

### Project Relevance

Sports-specific pose information is important because athlete
movements differ significantly from general human activities.

---

## 6. FIFA Injury Dataset

### Purpose

The FIFA injury dataset is considered as a reference for sports
injury-related information.

### Planned Use

- Injury pattern research
- Injury risk factor analysis
- Understanding sports injury data
- Supporting future injury prediction models

### Project Relevance

Injury-related data can help connect movement and biomechanical
features with potential injury risk.

---

## 7. Dataset Strategy

The project will use a combination of general human pose datasets
and sports-specific/injury-related datasets.

The initial approach is:

```text
General Pose Datasets
        │
        ├── Human3.6M
        ├── MPII
        └── COCO Keypoints
                │
                ▼
       Pose Estimation Research
                │
                ▼
Sports-Specific Data
        │
        └── SportsPose
                │
                ▼
     Sports Movement Analysis
                │
                ▼
Injury-Related Information
        │
        └── FIFA Injury Dataset
                │
                ▼
    Future Injury Risk Model
8. Initial Dataset Selection

For the initial development stage, the project will focus on:

COCO Keypoints – general human pose estimation
Human3.6M – human movement and pose research
SportsPose – sports movement analysis
FIFA Injury Dataset – injury-related research

MPII will also be studied as an additional pose estimation dataset.

9. Dataset Considerations

Before using any dataset for model training, the following will be
checked:

Dataset license
Usage restrictions
Data format
Available annotations
Pose/keypoint format
Number of samples
Sports coverage
Injury-related information
Suitability for the project
10. Future Dataset Processing

After dataset selection, the data processing pipeline will include:

Dataset
   ↓
Data Collection
   ↓
Data Cleaning
   ↓
Annotation Verification
   ↓
Pose / Keypoint Extraction
   ↓
Feature Extraction
   ↓
Dataset Preparation
   ↓
Model Training
   ↓
Model Evaluation

Dataset preprocessing and model training will be implemented in later
milestones.


### Step 11 — Create a dataset folder

Inside `backend`, create:

```text
backend/
└── datasets/