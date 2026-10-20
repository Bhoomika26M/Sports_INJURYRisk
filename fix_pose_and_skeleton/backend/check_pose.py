"""Check pose detection on a video, without the website or the database.

    python check_pose.py my_video.mp4
    python check_pose.py my_video.mp4 --save tracked.mp4    # also writes a copy with joints drawn

Prints how often each body point was found and whether the analysis can run.
"""
import argparse
import sys

import numpy as np


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("--save", help="write a copy of the video with the skeleton drawn on it")
    ap.add_argument("--activity", default="squatting")
    args = ap.parse_args()

    from app.services.analysis_pipeline import analyze_pose
    from app.services.pose_estimation import JOINT_NAMES, SKELETON_EDGES, PoseEstimator

    print("Loading pose model (the first run downloads about 9 MB)...")
    try:
        seq = PoseEstimator().process_video(args.video)
    except Exception as exc:  # noqa: BLE001
        print(f"\nPose estimation failed: {exc}")
        return 1

    print(f"\nFrames read: {len(seq.positions)}   Person found in {seq.detection_rate:.0%} of frames\n")
    found = (~np.isnan(seq.positions[:, :, 0])).mean(axis=0)
    for name, share in zip(JOINT_NAMES, found):
        bar = "#" * int(share * 20)
        print(f"  {name.replace('_', ' '):<15} {share:5.0%}  {bar}")

    missing = [n.replace("_", " ") for n, s in zip(JOINT_NAMES, found) if s < 0.5]
    if missing:
        print("\nProblem: these points are rarely visible: " + ", ".join(missing))
        print("Film the whole body, head to feet, in good light, with one person in frame.")
    else:
        try:
            r = analyze_pose(seq.positions, seq.fps, args.activity)
            print(f"\nAnalysis works. Risk score {r['risk_score']} ({r['risk_category']}), "
                  f"movement quality {r['movement_quality']}.")
        except Exception as exc:  # noqa: BLE001
            print(f"\nJoints were found but the analysis failed: {exc}")

    if args.save:
        import cv2

        cap = cv2.VideoCapture(args.video)
        w, h = int(cap.get(3)), int(cap.get(4))
        out = cv2.VideoWriter(args.save, cv2.VideoWriter_fourcc(*"mp4v"), seq.fps, (w, h))
        idx = {n: i for i, n in enumerate(JOINT_NAMES)}
        t = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if t < len(seq.positions):
                P = seq.positions[t]
                for a, b in SKELETON_EDGES:
                    pa, pb = P[idx[a]], P[idx[b]]
                    if not (np.isnan(pa).any() or np.isnan(pb).any()):
                        cv2.line(frame, (int(pa[0] * w), int(pa[1] * h)), (int(pb[0] * w), int(pb[1] * h)), (255, 200, 0), 3)
                for p in P:
                    if not np.isnan(p).any():
                        cv2.circle(frame, (int(p[0] * w), int(p[1] * h)), 6, (255, 255, 255), -1)
                        cv2.circle(frame, (int(p[0] * w), int(p[1] * h)), 6, (235, 99, 37), 2)
            out.write(frame)
            t += 1
        cap.release()
        out.release()
        print(f"\nSaved video with joints drawn: {args.save}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
