"""Pose pipeline smoke test — verifies MediaPipe and YOLO26-pose are installed and functional.

Usage:
    python scripts/pose_smoke_test.py <video_path>

Prints confirmation for both MediaPipe Pose and Ultralytics YOLO-pose.
Exit code 0 = both passed, 1 = any failure.
"""

import sys
import os


def test_mediapipe(video_path: str) -> bool:
    """Run MediaPipe Pose on a video and confirm landmarks are extracted."""
    try:
        import mediapipe as mp
        import cv2

        print(f"[MediaPipe] Version: {mp.__version__}")
        print(f"[MediaPipe] Processing: {video_path}")

        mp_pose = mp.solutions.pose
        pose = mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            print(f"[MediaPipe] ERROR: Cannot open video: {video_path}")
            return False

        frames_processed = 0
        frames_with_landmarks = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frames_processed += 1
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = pose.process(rgb)
            if results.pose_landmarks:
                frames_with_landmarks += 1
            if frames_processed >= 30:  # Process max 30 frames for smoke test
                break

        cap.release()
        pose.close()

        print(f"[MediaPipe] Frames processed: {frames_processed}")
        print(f"[MediaPipe] Frames with landmarks: {frames_with_landmarks}")

        if frames_processed == 0:
            print("[MediaPipe] ERROR: No frames read from video")
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
