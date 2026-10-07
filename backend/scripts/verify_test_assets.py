"""Verify test-asset clips against the Sports Injury Risk Detection model pipeline.

Regression check over the 5 clips in ``test-assets/`` (sample-clips + internet-clips).
Drives tracking (YOLO BoT-SORT) + MediaPipe full pass + coverage gate + ``analyze_frames``
directly — no DB, no server needed.

Usage:
    python backend/scripts/verify_test_assets.py --list
    python backend/scripts/verify_test_assets.py --video squat_sample.mp4
    python backend/scripts/verify_test_assets.py --all [--fast]
    python backend/scripts/verify_test_assets.py --all --json

Expected outcomes (verified on CPU, October 2026 — see evidence in git history notes):
  - squat_sample.mp4 / squat_demo.webm : PASS — solo barbell back-squat demo (rear view),
    single track at 100% coverage, detection 100%, (squatting, sagittal) fully validated.
    NOTE: squat_demo.webm is a VP9 transcode of the same 213-frame content; the PIPELINE
    handles .webm fine even though the upload API currently rejects that extension.
  - test_figure.mp4 : REJECT low_detection_quality — synthetic white stick figure on black;
    YOLO holds no substantive track (5/90 frames), MediaPipe measures 0 poses.
  - 7a6W56OeU8w.mp4 (HIIT group class) / Px4cyTAHrWc.mp4 (group fitness class) : REJECT
    multiple_people_subject_unstable — 4-6 substantive tracks, main-subject coverage
    49-64%, detection 48-52%, all below the 70% full-confidence floor.
"""

import argparse
import json
import os
import sys
import time

# Ensure backend root is on sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
REPO_ROOT = os.path.dirname(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)

ASSETS_DIR = os.path.join(REPO_ROOT, "test-assets")

TEST_ASSETS = [
    {
        "file": os.path.join("sample-clips", "squat_sample.mp4"),
        "movement": "squatting",
        "view": "sagittal",
        "expected_gate": "pass",
        "expected_coverage": ">= 95%",
        "expected_persons": 1,
        "expected_grade": "fair",
        "min_validated_metrics": 500,
        "description": "Solo barbell back-squat demo filmed from behind (rear view). "
        "Single athlete, 213 frames at 720p30. Best label is (squatting, sagittal).",
    },
    {
        "file": os.path.join("sample-clips", "squat_demo.webm"),
        "movement": "squatting",
        "view": "sagittal",
        "expected_gate": "pass",
        "expected_coverage": ">= 95%",
        "expected_persons": 1,
        "expected_grade": "fair",
        "min_validated_metrics": 500,
        "description": "VP9 transcode of the same 213-frame solo squat demo as squat_sample.mp4. "
        "Pipeline handles .webm (OpenCV decodes VP9); the upload API rejects .webm separately.",
    },
    {
        "file": os.path.join("sample-clips", "test_figure.mp4"),
        "movement": "squatting",
        "view": "frontal",
        "expected_gate": "reject",
        "reject_code": "low_detection_quality",
        "expected_coverage": "0%",
        "expected_persons": 0,
        "description": "Synthetic white stick figure on a black background (640x480 mpeg4, 90 frames). "
        "No real person: no substantive YOLO track, 0 MediaPipe poses.",
    },
    {
        "file": os.path.join("internet-clips", "7a6W56OeU8w.mp4"),
        "movement": "jumping",
        "view": "frontal",
        "expected_gate": "reject",
        "reject_code": "multiple_people_subject_unstable",
        "expected_coverage": "< 70%",
        "expected_persons": 6,
        "description": "'Extreme HIIT Group Fitness Class at Crunch Fitness' (1080p24, 30s). "
        "Medicine-ball slams, hurdle hops, leg close-ups; 6 substantive tracks, camera cuts.",
    },
    {
        "file": os.path.join("internet-clips", "Px4cyTAHrWc.mp4"),
        "movement": "squatting",
        "view": "frontal",
        "expected_gate": "reject",
        "reject_code": "multiple_people_subject_unstable",
        "expected_coverage": "< 70%",
        "expected_persons": 4,
        "description": "'Total Body Group Fitness Class' (1080p30, 46.9s). Resistance-band leg work "
        "close-ups plus wide multi-person class shots; 4 substantive tracks.",
    },
]


def _find_weights() -> str:
    for p in [
        os.path.join(BACKEND_DIR, "yolov8n-pose.pt"),
        os.path.join(REPO_ROOT, "yolov8n-pose.pt"),
    ]:
        if os.path.exists(p):
            return p
    raise FileNotFoundError("yolov8n-pose.pt not found in backend/ or repository root")


def verify_clip(item: dict, fast: bool = False) -> dict:
    from ultralytics import YOLO
    from app.modules.pose.coverage import assess_coverage, summarize_tracking
    from app.modules.pose.pipeline import (
        compute_stride,
        probe_video,
        run_mediapipe_full_pass,
        track_persons,
    )
    from app.modules.pose.processing import analyze_frames

    video_path = os.path.join(ASSETS_DIR, item["file"])
    if not os.path.exists(video_path):
        return {"file": item["file"], "status": "error", "message": f"File not found: {video_path}"}

    t0 = time.time()
    probe = probe_video(video_path)
    fps = probe["fps"]
    stride = compute_stride(fps)
    if fast:
        stride = max(stride, 3)

    yolo = YOLO(_find_weights())

    # 1. Track persons with YOLO
    tracking = track_persons(video_path, model=yolo, stride=stride, fps=fps)
    summary = summarize_tracking(tracking)
    main_track_id = tracking["main_track_id"]

    subject_boxes = None
    if main_track_id is not None:
        main_frames = tracking["tracks"][main_track_id]
        subject_boxes = {i: main_frames.get(i) for i in range(tracking["frames_processed"])}

    # 2. MediaPipe pass
    diagnostics: dict = {}
    frame_results, detection_rate = run_mediapipe_full_pass(
        video_path,
        subject_boxes=subject_boxes,
        diagnostics=diagnostics,
        stride=stride,
        full_frame_fallback=not summary.multi_person,
    )

    assessment = assess_coverage(summary, detection_rate)
    gate_outcome = assessment.outcome  # "reject", "partial", "ok"

    result = {
        "file": item["file"],
        "movement": item["movement"],
        "view": item["view"],
        "duration_s": round(probe["frames"] / fps, 1) if fps > 0 else 0,
        "resolution": f"{probe['width']}x{probe['height']}",
        "fps": round(fps, 2),
        "stride_used": stride,
        "tracks_seen": summary.tracks_seen,
        "substantive_tracks": summary.substantive_tracks,
        "multi_person": summary.multi_person,
        "max_persons": summary.max_persons,
        "main_track_coverage": round(summary.main_track_coverage, 3),
        "subject_height_px": round(summary.subject_height_px, 1)
        if summary.subject_height_px is not None
        else None,
        "detection_rate": round(detection_rate, 3),
        "gate_outcome": gate_outcome,
        "gate_code": assessment.code if gate_outcome == "reject" else None,
        "gate_message": assessment.message if gate_outcome == "reject" else None,
        "time_s": round(time.time() - t0, 2),
    }

    if gate_outcome == "reject":
        result["pipeline_status"] = "REJECTED_BY_GATE"
        result["matches_expectation"] = (
            item["expected_gate"] == "reject"
            and (not item.get("reject_code") or item["reject_code"] == assessment.code)
        )
        return result

    # 3. Biomechanical analysis
    metrics, analysis = analyze_frames(
        frame_results, item["movement"], item["view"], fps, diagnostics
    )
    validated_metrics = [m for m in metrics if m.get("confidence") == "validated"]
    quality = analysis.get("quality", {})

    result["pipeline_status"] = "PASSED"
    result["metric_count"] = len(metrics)
    result["validated_metric_count"] = len(validated_metrics)
    result["quality_grade"] = quality.get("grade")
    result["quality_warnings"] = [w.get("code") for w in quality.get("warnings", [])]
    result["matches_expectation"] = (
        item["expected_gate"] == "pass"
        and len(validated_metrics) >= int(item.get("min_validated_metrics", 1))
        and (not item.get("expected_grade") or quality.get("grade") == item["expected_grade"])
    )

    return result


def main():
    parser = argparse.ArgumentParser(description="Verify test-asset clips against model pipeline.")
    parser.add_argument("--list", action="store_true", help="List all clips in catalog")
    parser.add_argument("--video", type=str, help="Verify specific clip filename")
    parser.add_argument("--all", action="store_true", help="Verify all catalog clips")
    parser.add_argument("--fast", action="store_true", help="Speed up by using stride")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    if args.list:
        if args.json:
            print(json.dumps(TEST_ASSETS, indent=2))
        else:
            print("\n=== TEST-ASSET VIDEO CATALOG ===")
            print(f"{'File':<42} | {'Movement':<10} | {'View':<8} | {'Expected':<10}")
            print("-" * 78)
            for c in TEST_ASSETS:
                print(
                    f"{c['file']:<42} | {c['movement']:<10} | {c['view']:<8} | "
                    f"{c['expected_gate'].upper():<10}"
                )
        return

    targets = []
    if args.video:
        matched = [
            c
            for c in TEST_ASSETS
            if c["file"] == args.video or os.path.basename(args.video) == os.path.basename(c["file"])
        ]
        if not matched:
            print(f"Error: video '{args.video}' not found in catalog. Use --list to see options.")
            sys.exit(1)
        targets = matched
    elif args.all:
        targets = TEST_ASSETS
    else:
        parser.print_help()
        sys.exit(0)

    results = []
    for item in targets:
        print(f"\nProcessing {item['file']} ({item['movement']}, {item['view']})...", flush=True)
        res = verify_clip(item, fast=args.fast)
        results.append(res)
        status_str = "MATCH" if res.get("matches_expectation") else "MISMATCH"
        print(f"  Result: {res.get('pipeline_status')} ({status_str}) in {res.get('time_s')}s")
        if res.get("pipeline_status") == "PASSED":
            print(
                f"  Metrics: {res.get('metric_count')} total / "
                f"{res.get('validated_metric_count')} validated, "
                f"Grade: {res.get('quality_grade')} {res.get('quality_warnings')}"
            )
        else:
            print(f"  Gate Code: {res.get('gate_code')} - {res.get('gate_message')}")

    if args.json:
        print("\n" + json.dumps(results, indent=2))

    if not all(r.get("matches_expectation") for r in results):
        sys.exit(2)


if __name__ == "__main__":
    main()
