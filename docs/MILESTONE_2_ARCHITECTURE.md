# Milestone 2 Architecture

## Overview

Milestone 2 implements a complete biomechanical movement analysis pipeline that processes sports videos to extract pose, movement, and biomechanical features.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                          │
│  - Video Upload                                                │
│  - Activity Selection                                          │
│  - Analysis Dashboard                                          │
│  - Skeleton Visualization                                      │
│  - Charts & Metrics                                            │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/REST API
┌────────────────────────▼────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│  - Authentication & Authorization                              │
│  - Video Upload & Storage                                     │
│  - Video Processing Service                                    │
│  - Analysis Results API                                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│                   Processing Pipeline                             │
│                                                                  │
│  Video                                                           │
│    ↓                                                             │
│  OpenCV Preprocessing                                           │
│    ↓                                                             │
│  YOLO11n Person Detection                                      │
│    ↓                                                             │
│  ByteTrack Multi-Object Tracking                               │
│    ↓                                                             │
│  ROI Cropping (with padding)                                    │
│    ↓                                                             │
│  MediaPipe BlazePose (33 landmarks)                            │
│    ↓                                                             │
│  Coordinate Mapping (ROI → Original Frame)                      │
│    ↓                                                             │
│  Temporal Smoothing (Savitzky-Golay)                           │
│    ↓                                                             │
│  Skeleton Normalization                                        │
│    ↓                                                             │
│  Movement Segmentation (Squat/Jump/Running)                   │
│    ↓                                                             │
│  Biomechanical Calculations                                     │
│    ↓                                                             │
│  Movement Quality Scoring                                      │
│    ↓                                                             │
│  Movement-Change Analysis (Early vs Late)                       │
│    ↓                                                             │
│  Report Generation                                            │
└──────────────────────────────────────────────────────────────────┘
```

## Components

### Frontend

**Location**: `frontend/`

**Technologies**: React, React Router, Axios, Tailwind CSS, Recharts

**Key Components**:
- `VideoUpload.jsx` - Video upload with activity selection
- `VideoAnalysis.jsx` - Analysis dashboard with:
  - Video player (annotated)
  - Skeleton view
  - Pose quality metrics
  - Movement windows table
  - Biomechanical measurements
  - Time-series charts
  - Movement quality scores
  - Movement-change analysis

### Backend

**Location**: `backend/`

**Technologies**: FastAPI, SQLAlchemy, SQLite, Pydantic

**Key Modules**:

#### API Routes (`app/api/routes/`)
- `auth.py` - Authentication endpoints
- `videos.py` - Video upload, processing, analysis endpoints
- `athletes.py` - Athlete management
- `datasets.py` - Dataset information

#### Services (`app/services/`)
- `processing_service.py` - Main pipeline orchestrator
- `video_service.py` - Video management
- `video_annotation_service.py` - Annotated video generation
- `auth_service.py` - Authentication logic

#### Processing (`app/processing/`)
- `video_processor.py` - OpenCV video handling
- `roi.py` - ROI cropping and coordinate mapping
- `smoothing.py` - Temporal smoothing
- `normalization.py` - Skeleton normalization

#### Detection & Tracking (`app/detection/`, `app/tracking/`)
- `yolo11.py` - YOLO11n person detector
- `yolo_tracker.py` - ByteTrack multi-object tracker

#### Pose Estimation (`app/pose/`)
- `mediapipe_pose.py` - MediaPipe BlazePose (33 landmarks)
- `estimator.py` - Base pose estimator interface
- `blazepose_mapping.py` - Canonical 33-point mapping

#### Biomechanics (`app/biomechanics/`)
- `calculator.py` - Joint angles, ROM, symmetry, velocity, acceleration

#### Movement Analysis (`app/movement/`)
- `segmentation.py` - Movement window detection (squat, jump, running)
- `change_analysis.py` - Early vs late movement variation

#### Visualization (`app/visualization/`)
- `skeleton_renderer.py` - Skeleton visualization with BlazePose 33 landmarks

#### Reports (`app/reports/`)
- `html_generator.py` - HTML report generation

#### Datasets (`app/datasets/`)
- `adapters.py` - Dataset adapters (Human3.6M, MPII, COCO, SportsPose, FIFA)

## Database Schema

### Videos Table
- id, athlete_id, uploaded_by, filename, storage_path
- activity_type, file_size, duration, fps, width, height
- processing_status, processing_error
- timestamps

### Pose Analysis Table
- id, video_id, pose_model, pose_model_version
- total_frames, processed_frames, frame_sample_rate
- pose_quality (JSON)
- keypoints_data (JSON)
- tracking_data (JSON)
- roi_data (JSON)
- movement_change_analysis (JSON)
- normalized_skeleton (JSON)

### Biomechanical Analysis Table
- id, pose_analysis_id
- joint_angles (JSON)
- symmetry (JSON)
- trunk_lean (JSON)
- velocity (JSON)
- acceleration (JSON)
- movement_quality (JSON)

### Movement Windows Table
- id, pose_analysis_id
- start_frame, end_frame, start_time, end_time
- phase, repetition_number, jump_number, stride_number
- metrics (JSON)
- quality_score, quality_notes

## Pipeline Flow

### 1. Video Upload
- User uploads video via frontend
- Video stored in secure server directory
- Activity type selected (squat, jump, running)
- Database record created

### 2. Video Processing
```
Video → OpenCV → YOLO11n → ByteTrack → ROI → BlazePose → 
Coordinate Mapping → Smoothing → Normalization → 
Movement Segmentation → Biomechanics → Movement Quality → 
Movement-Change Analysis
```

### 3. Analysis Results
- Pose quality metrics
- Biomechanical features
- Movement windows
- Movement quality score
- Early vs late comparison

### 4. Visualization
- Annotated video generation
- Skeleton overlay
- Charts and metrics
- HTML report

## Key Features

### Person Detection & Tracking
- **Detector**: YOLO11n (Ultralytics)
- **Tracker**: ByteTrack (built into YOLO)
- **Output**: Stable track IDs across frames

### Pose Estimation
- **Model**: MediaPipe BlazePose
- **Landmarks**: 33 keypoints
- **Format**: Pixel coordinates in original frame
- **Mapping**: Canonical BlazePose 33-point mapping

### Biomechanical Features
- Joint angles (knee, hip, elbow, shoulder, ankle)
- Range of motion (ROM)
- Left-right symmetry
- Trunk lean
- Velocity and acceleration
- Smoothness and stability

### Movement Segmentation
- **Squat**: Descent-bottom-ascent cycles
- **Jump/Landing**: Takeoff-flight-landing
- **Running**: Stride cycles

### Movement Quality
- **Components**: confidence, symmetry, alignment, stability, ROM, smoothness
- **Weights**: Configurable (default: 15%, 20%, 20%, 15%, 15%, 15%)
- **Score**: Weighted average (0-100)

### Movement-Change Analysis
- Splits repetitions into EARLY, MIDDLE, LATE
- Compares ROM, symmetry, trunk lean, velocity, etc.
- Reports early vs late changes (not medical fatigue diagnosis)

## Dependencies

### Backend
- FastAPI
- SQLAlchemy
- Pydantic
- OpenCV (cv2)
- MediaPipe
- Ultralytics (YOLO)
- NumPy
- SciPy

### Frontend
- React
- React Router
- Axios
- Tailwind CSS
- Recharts

## Security

- JWT-based authentication
- Role-based access control (RBAC)
- IDOR protection
- Secure file upload (validation, safe filenames)
- Path traversal prevention
- Oversized file prevention

## Performance

- Video FPS tracking
- Processing FPS measurement
- Detector call counting
- Pose frame counting
- Mean confidence tracking

## Limitations

- 2D video without camera calibration
- No 3D depth information
- No ground reaction force
- No EMG data
- Camera angle affects measurements
- Individual anatomical differences not accounted for

## Next Steps (Milestone 3)

- Injury-risk classification model
- FIFA injury data integration
- Machine learning pipeline
- Risk prediction API
