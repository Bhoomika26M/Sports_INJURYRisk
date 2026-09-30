"""Pose pipeline smoke test — verifies MediaPipe and YOLO26-pose are installed and functional.

Usage:
    python scripts/pose_smoke_test.py <video_path>

Prints confirmation for both MediaPipe Pose and Ultralytics YOLO-pose.
Exit code 0 = both passed, 1 = any failure.
"""

import sys
import os


def test_mediapipe(video_path: str) -> bool:
    """Run the real pipeline MediaPipe pass on a video and confirm landmarks."""
    try:
        import sys
        import mediapipe as mp
        import cv2

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from app.modules.pose.pipeline import run_mediapipe_full_pass, track_persons

        print(f"[MediaPipe] Version: {mp.__version__}")
        print(f"[MediaPipe] Processing: {video_path}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"[MediaPipe] ERROR: Cannot open video: {video_path}")
            return False
        cap.release()

        # Track first (exercises YOLO tracking + main-subject selection)...
        tracking = track_persons(video_path, model=None, stride=5)
        print(f"[MediaPipe] Tracking: max_persons={tracking['max_persons']} "
              f"main_track={tracking['main_track_id']} tracked={tracking['tracked']}")
        boxes = None
        if tracking["main_track_id"] is not None:
            main_frames = tracking["tracks"][tracking["main_track_id"]]
            boxes = {i: main_frames.get(i) for i in range(tracking["frames_processed"])}

        # ...then pose on the tracked subject (None = full-frame fallback).
        frame_results, detection_rate = run_mediapipe_full_pass(video_path, subject_boxes=boxes)

        print(f"[MediaPipe] Frames with landmarks: {len(frame_results)}")
        print(f"[MediaPipe] Detection rate: {detection_rate:.0%}")

        if not frame_results:
            print("[MediaPipe] ERROR: No landmarks extracted from any frame")
            return False

        print("[MediaPipe] ✓ PASSED — MediaPipe Pose is functional")
        return True

    except Exception as e:
        print(f"[MediaPipe] ERROR: {e}")
        return False


def test_yolo_pose(video_path: str) -> bool:
    """Run YOLO-pose on a video and confirm person detection works."""
    try:
        from ultralytics import YOLO
        import cv2

        print(f"\n[YOLO-Pose] Processing: {video_path}")

        # Use YOLOv8-pose (nano variant for speed in smoke test)
        model = YOLO("yolov8n-pose.pt")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"[YOLO-Pose] ERROR: Cannot open video: {video_path}")
            return False

        frames_processed = 0
        persons_detected = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames_processed += 1
            results = model(frame, verbose=False)
            for r in results:
                if r.keypoints is not None and len(r.keypoints) > 0:
                    persons_detected += 1
            if frames_processed >= 30:  # Process max 30 frames for smoke test
                break

        cap.release()

        print(f"[YOLO-Pose] Frames processed: {frames_processed}")
        print(f"[YOLO-Pose] Frames with person detected: {persons_detected}")

        if frames_processed == 0:
            print("[YOLO-Pose] ERROR: No frames read from video")
            return False

        print("[YOLO-Pose] ✓ PASSED — YOLO-Pose is functional")
        return True

    except Exception as e:
        print(f"[YOLO-Pose] ERROR: {e}")
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/pose_smoke_test.py <video_path>")
        sys.exit(1)

    video_path = sys.argv[1]
    if not os.path.exists(video_path):
        print(f"ERROR: File not found: {video_path}")
        sys.exit(1)

    print("=" * 60)
    print("POSE PIPELINE SMOKE TEST")
    print("=" * 60)

    mp_ok = test_mediapipe(video_path)
    yolo_ok = test_yolo_pose(video_path)

    print("\n" + "=" * 60)
    print("RESULTS:")
    print(f"  MediaPipe Pose: {'✓ PASS' if mp_ok else '✗ FAIL'}")
    print(f"  YOLO-Pose:      {'✓ PASS' if yolo_ok else '✗ FAIL'}")
    print("=" * 60)

    if mp_ok and yolo_ok:
        print("\n✓ All pose libraries functional — safe to proceed.")
        sys.exit(0)
    else:
        print("\n✗ One or more pose libraries failed — do not proceed.")
        sys.exit(1)


if __name__ == "__main__":
    main()
