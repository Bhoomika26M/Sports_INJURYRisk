"""Pose estimation pipeline using MediaPipe and YOLOv8-pose."""

import cv2
import numpy as np
import mediapipe as mp
from ultralytics import YOLO

mp_pose = mp.solutions.pose
mp_drawing = mp.solutions.drawing_utils


def extract_world_landmarks(pose_world_landmarks) -> dict:
    """Extract standard MediaPipe world landmarks into a dictionary."""
    out = {}
    for i, lm in enumerate(pose_world_landmarks.landmark):
        # We store them by string index matching MediaPipe mapping for ease, or just the index
        # For our system, the calculations.py expects the raw integer keys or an array indexed by integer.
        # Let's map integer index to a tuple/list of [x, y, z] for smaller JSON size.
        out[str(i)] = [lm.x, lm.y, lm.z]
    return out


def run_yolo_person_check(video_path: str, model, sample_frames: int = 10) -> list[int]:
    """
    Run YOLOv8-pose on a few sampled frames to check person count.
    Returns a list of person counts for each sampled frame.
    """
    if model is None:
        model = YOLO("yolov8n-pose.pt")
    
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    if total_frames == 0:
        return []

    # Calculate frame indices to sample evenly
    step = max(1, total_frames // sample_frames)
    indices = [i * step for i in range(sample_frames) if i * step < total_frames]
    
    person_counts = []
    
    for idx in indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            continue
            
        # Run inference
        results = model(frame, verbose=False)
        
        # Count persons (YOLOv8 returns a list of Results objects)
        count = 0
        if len(results) > 0 and results[0].boxes is not None:
            count = len(results[0].boxes)
            
        person_counts.append(count)
        
    cap.release()
    return person_counts


def extract_thumbnail(video_path: str, output_path: str) -> None:
    """Extract a frame from the middle of the video to use as a thumbnail."""
    cap = cv2.VideoCapture(video_path)
    midpoint = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) // 2
    cap.set(cv2.CAP_PROP_POS_FRAMES, midpoint)
    ok, frame = cap.read()
    if ok:
        cv2.imwrite(output_path, frame)
    cap.release()


def run_mediapipe_full_pass(video_path: str, annotate_output_path: str | None = None, progress_callback=None):
    """
    Run MediaPipe pose over all frames.
    Extract world landmarks, and optionally burn the skeleton into an output video.
    Calls progress_callback(pct) periodically if provided.
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width, height = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    writer = None
    if annotate_output_path:
        writer = cv2.VideoWriter(annotate_output_path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (width, height))

    frame_results = []
    
    with mp_pose.Pose(static_image_mode=False, model_complexity=1) as pose:
        frame_idx = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
                
            timestamp_ms = int(cap.get(cv2.CAP_PROP_POS_MSEC))
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = pose.process(rgb)
            
            if result.pose_world_landmarks:
                frame_results.append({
                    "frame_number": frame_idx,
                    "timestamp_ms": timestamp_ms,
                    "world_landmarks": extract_world_landmarks(result.pose_world_landmarks),
                })
                
                if writer and result.pose_landmarks:
                    mp_drawing.draw_landmarks(
                        frame, result.pose_landmarks, mp_pose.POSE_CONNECTIONS,
                        mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    )
                    
            if writer:
                writer.write(frame)
                
            if progress_callback and total_frames > 0:
                if frame_idx % max(1, total_frames // 10) == 0:
                    progress_callback(int(100 * frame_idx / total_frames))
                    
            frame_idx += 1

    cap.release()
    if writer:
        writer.release()
        
    detection_rate = len(frame_results) / frame_idx if frame_idx > 0 else 0.0
    return frame_results, detection_rate
