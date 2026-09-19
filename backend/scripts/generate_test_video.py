"""Generate a synthetic test video with a simple stick figure for pose smoke testing.

Creates a 3-second, 30fps, 640x480 MP4 with a moving stick figure.
"""

import numpy as np

try:
    import cv2
except ImportError:
    print("OpenCV not installed locally — this script runs inside the Docker container.")
    print("Run: docker compose exec backend python scripts/generate_test_video.py")
    exit(1)


def generate_test_video(output_path: str, duration_s: float = 3.0, fps: int = 30):
    width, height = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    total_frames = int(duration_s * fps)

    for i in range(total_frames):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:] = (40, 40, 40)  # dark gray background

        # Simple animated stick figure
        t = i / total_frames
        cx = int(width / 2 + 50 * np.sin(2 * np.pi * t))
        cy = int(height / 2)

        # Head
        cv2.circle(frame, (cx, cy - 80), 20, (200, 200, 200), -1)
        # Body
        cv2.line(frame, (cx, cy - 60), (cx, cy + 20), (200, 200, 200), 3)
        # Arms
        arm_angle = 30 * np.sin(4 * np.pi * t)
        lax = int(cx - 50 * np.cos(np.radians(arm_angle)))
        lay = int(cy - 30 + 50 * np.sin(np.radians(arm_angle)))
        rax = int(cx + 50 * np.cos(np.radians(arm_angle)))
        ray = int(cy - 30 - 50 * np.sin(np.radians(arm_angle)))
        cv2.line(frame, (cx, cy - 30), (lax, lay), (200, 200, 200), 3)
        cv2.line(frame, (cx, cy - 30), (rax, ray), (200, 200, 200), 3)
        # Legs
        leg_angle = 20 * np.sin(4 * np.pi * t)
        llx = int(cx - 40 * np.sin(np.radians(leg_angle)))
        lly = cy + 80
        rlx = int(cx + 40 * np.sin(np.radians(leg_angle)))
        rly = cy + 80
        cv2.line(frame, (cx, cy + 20), (llx, lly), (200, 200, 200), 3)
        cv2.line(frame, (cx, cy + 20), (rlx, rly), (200, 200, 200), 3)

        writer.write(frame)

    writer.release()
    print(f"Generated test video: {output_path} ({total_frames} frames, {fps}fps, {duration_s}s)")


if __name__ == "__main__":
    generate_test_video("/test-assets/sample-clips/test_figure.mp4")
