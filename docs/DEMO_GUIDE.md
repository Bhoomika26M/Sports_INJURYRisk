# Demo Guide

This guide explains how to run the Milestone 2 demo using the provided script.

## Prerequisites

- Python 3.12+
- Required dependencies (see `backend/requirements.txt`)
- A sample sports video file

## Running the Demo

### Command

```bash
python scripts/run_demo.py --input sample_video.mp4 --activity squat --output outputs/demo
```

### Arguments

- `--input`: Path to input video (required)
- `--activity`: Activity type - choices: `squat`, `jump`, `running` (required)
- `--output`: Output directory (default: `outputs/demo`)

### Example

```bash
python scripts/run_demo.py \
    --input data/sample_squat.mp4 \
    --activity squat \
    --output outputs/demo
```

## Output

The demo generates the following files in the output directory:

```
outputs/demo/
├── annotated_video.mp4          # Video with skeleton overlay
├── analysis.json                # Full analysis data
├── biomechanics.json            # Biomechanical features
├── movement_windows.json        # Movement window data
├── performance.json             # Processing performance metrics
├── report.html                  # HTML report
└── frames/                      # Sample annotated frames
    ├── frame_0000.jpg
    ├── frame_0010.jpg
    └── ...
```

## Output Files

### annotated_video.mp4
- Original video with skeleton visualization
- Bounding boxes and tracker IDs
- Pose landmarks and connections
- Biomechanical measurements overlay

### analysis.json
Complete analysis data including:
- Video metadata
- Pose analysis results
- Tracking data
- ROI data
- Movement-change analysis

### biomechanics.json
Biomechanical features:
- Joint angles (ROM)
- Symmetry metrics
- Trunk lean
- Velocity and acceleration
- Movement quality score

### movement_windows.json
Detected movement windows:
- Repetition/phase information
- Start/end times
- Duration
- Phase-specific metrics

### performance.json
Processing performance:
- Processing time
- FPS (video and processed)
- Detector calls
- Tracking IDs
- Pose confidence

### report.html
Comprehensive HTML report with:
- Video information
- Processing details
- Pose quality
- Movement windows
- Biomechanics
- Movement quality
- Movement-change analysis
- Warnings and limitations

### frames/
Sample annotated frames as images (10 samples by default)

## What the Demo Does

1. **Opens video** with OpenCV
2. **Detects athletes** using YOLO11n
3. **Tracks athletes** using ByteTrack
4. **Crops ROI** with 15% padding
5. **Estimates pose** using MediaPipe BlazePose (33 landmarks)
6. **Maps coordinates** from ROI to original frame
7. **Applies smoothing** (Savitzky-Golay filter)
8. **Normalizes skeleton**
9. **Segments movements** (squat/jump/running)
10. **Calculates biomechanics** (angles, ROM, symmetry, etc.)
11. **Scores movement quality** (weighted components)
12. **Analyzes movement changes** (early vs late)
13. **Generates annotated video**
14. **Extracts sample frames**
15. **Generates HTML report**

## Troubleshooting

### Video not found
Ensure the input video path is correct and the file exists.

### Model loading errors
The demo will download YOLO11n automatically on first run. Ensure internet connection is available.

### Memory errors
For large videos, the demo may consume significant memory. Consider using shorter videos for testing.

### Slow processing
Processing speed depends on:
- Video length and resolution
- CPU/GPU performance
- Number of people in video

## Integration with Backend

The demo script uses the same pipeline as the backend's `VideoProcessingService`. The results are compatible with the database schema and API responses.

## Next Steps

After running the demo:
1. Open `report.html` in a browser to view the full analysis
2. Play `annotated_video.mp4` to see the skeleton visualization
3. Review `analysis.json` for raw data
4. Use the dataset evaluation script to benchmark the pose pipeline:

```bash
python scripts/evaluate_pose_pipeline.py --dataset coco --data-dir /path/to/coco
```
