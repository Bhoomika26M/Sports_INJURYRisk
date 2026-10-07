"""Verify data videos against the Sports Injury Risk Detection model pipeline.

Usage:
    python backend/scripts/verify_data_videos.py --list
    python backend/scripts/verify_data_videos.py --video jumping_box_jump_demo.mp4
    python backend/scripts/verify_data_videos.py --all [--fast]

Flags:
    --video <filename> : Verify a single video by name
    --all              : Run verification across all 9 data clips
    --fast             : Run with frame-skipping/stride for ultra-fast agent smoke checks
    --list             : List all videos and expected outcomes
    --json             : Output results in JSON format
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

DATA_DIR = os.path.join(REPO_ROOT, "data")

EXPECTED_CATALOG = [
    {
        "file": "squatting_barbell_back_squat_side_view.mp4",
        "movement": "squatting",
        "view": "sagittal",
        "expected_gate": "pass",
        "expected_coverage": ">= 80%",
        "expected_persons": 1,
        "description": "Solo male lifter executing barbell back squat repetitions inside a gym rack. Lateral sagittal perspective.",
    },
    {
        "file": "landing_single_leg_drop_soft_landing.mp4",
        "movement": "landing",
        "view": "sagittal",
        "expected_gate": "pass",
        "expected_coverage": ">= 90%",
        "expected_persons": 1,
        "description": "Single female athlete stepping off elevated box into unilateral drop landing with soft knee flexion.",
    },
    {
        "file": "landing_one_foot_landing_pivot.mp4",
        "movement": "landing",
        "view": "sagittal",
        "expected_gate": "pass",
        "expected_coverage": ">= 85%",
        "expected_persons": 1,
        "description": "Single athlete performing unilateral landing and pivoting maneuver on court floor.",
    },
    {
        "file": "running_form_side_view.mp4",
        "movement": "running",
        "view": "sagittal",
        "expected_gate": "reject",
        "reject_code": "multiple_people_subject_unstable",
        "expected_coverage": "< 40%",
        "expected_persons": 3,
        "description": "Three runners jogging side-by-side. Severe occlusion and subject instability across camera view.",
    },
    {
        "file": "sprinting_sprint_speed_drills.mp4",
        "movement": "sprinting",
        "view": "sagittal",
        "expected_gate": "reject",
        "reject_code": "multiple_people_subject_unstable",
        "expected_coverage": "< 25%",
        "expected_persons": 6,
        "description": "Track sprint speed drills featuring multiple athletes entering/exiting frame. Main subject cannot maintain tracking.",
    },
    {
        "file": "jumping_box_jump_demo.mp4",
        "movement": "jumping",
        "view": "sagittal",
        "expected_gate": "pass",
        "expected_coverage": ">= 95%",
        "expected_persons": 1,
        "description": "Single athlete performing plyometric box jump reps. 4K AV1 video decoding cleanly.",
    },
    {
        "file": "throwing_shot_put_slow_motion.mp4",
        "movement": "throwing",
        "view": "sagittal",
        "expected_gate": "pass",
        "expected_coverage": ">= 95%",
        "expected_persons": 1,
        "description": "Solo track athlete performing rotational shot-put glide and release in slow motion.",
    },
    {
        "file": "cutting_180_cut_mechanics.mp4",
        "movement": "cutting",
        "view": "sagittal",
        "expected_gate": "reject",
        "reject_code": "multiple_people_subject_unstable",
        "expected_coverage": "< 50%",
        "expected_persons": 3,
        "description": "Turf agility drill with 180 cut mechanics. 3 people in frame; main subject falls below 70% detection floor.",
    },
    {
        "file": "cutting_aquabag_punch_cod.mp4",
        "movement": "cutting",
        "view": "frontal",
        "expected_gate": "pass",
        "expected_coverage": ">= 75%",
        "expected_persons": 1,
        "description": "High-intensity change of direction (COD) with aqua bag punch. Frontal camera view yielding qualitative valgus metrics.",
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
    import cv2
    from ultralytics import YOLO
    from app.modules.pose.coverage import assess_coverage, summarize_tracking
    from app.modules.pose.pipeline import (
        track_persons,
        run_mediapipe_full_pass,
        compute_stride,
        probe_video,
    )
    from app.modules.pose.processing import analyze_frames

    video_path = os.path.join(DATA_DIR, item["file"])
    if not os.path.exists(video_path):
        return {"file": item["file"], "status": "error", "message": f"File not found: {video_path}"}

    t0 = time.time()
    probe = probe_video(video_path)
    fps = probe["fps"]
    stride = compute_stride(fps)
    if fast:
        stride = max(stride, 3)

    model_path = _find_weights()
    yolo = YOLO(model_path)

    # 1. Track persons with YOLO
    tracking = track_persons(video_path, model=yolo, stride=stride, fps=fps)
    summary = summarize_tracking(tracking)
    main_track_id = tracking["main_track_id"]

    subject_boxes = None
    if main_track_id is not None:
        main_frames = tracking["tracks"][main_track_id]
        subject_boxes = {i: main_frames.get(i) for i in range(tracking["frames_processed"])}

    # 2. MediaPipe pass
    diagnostics = {}
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
        "fps": round(fps, 1),
        "stride_used": stride,
        "max_persons": tracking["max_persons"],
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
    result["matches_expectation"] = (item["expected_gate"] == "pass")

    return result


def main():
    parser = argparse.ArgumentParser(description="Verify data directory clips against model pipeline.")
    parser.add_argument("--list", action="store_true", help="List all videos in catalog")
    parser.add_argument("--video", type=str, help="Verify specific video filename")
    parser.add_argument("--all", action="store_true", help="Verify all catalog videos")
    parser.add_argument("--fast", action="store_true", help="Speed up by using stride")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    if args.list:
        if args.json:
            print(json.dumps(EXPECTED_CATALOG, indent=2))
        else:
            print("\n=== DATA DIRECTORY VIDEO CATALOG ===")
            print(f"{'Filename':<42} | {'Movement':<10} | {'View':<8} | {'Expected':<10}")
            print("-" * 78)
            for c in EXPECTED_CATALOG:
                print(f"{c['file']:<42} | {c['movement']:<10} | {c['view']:<8} | {c['expected_gate'].upper():<10}")
        return

    targets = []
    if args.video:
        matched = [c for c in EXPECTED_CATALOG if c["file"] == args.video or os.path.basename(args.video) == c["file"]]
        if not matched:
            print(f"Error: video '{args.video}' not found in catalog. Use --list to see options.")
            sys.exit(1)
        targets = matched
    elif args.all:
        targets = EXPECTED_CATALOG
    else:
        parser.print_help()
        sys.exit(0)

    results = []
    for item in targets:
        print(f"\nProcessing {item['file']} ({item['movement']}, {item['view']})...", flush=True)
        res = verify_clip(item, fast=args.fast)
        results.append(res)
        status_str = "✓ MATCH" if res.get("matches_expectation") else "✗ MISMATCH"
        print(f"  Result: {res.get('pipeline_status')} ({status_str}) in {res.get('time_s')}s")
        if res.get("pipeline_status") == "PASSED":
            print(f"  Metrics: {res.get('metric_count')} total, Grade: {res.get('quality_grade')}")
        else:
            print(f"  Gate Code: {res.get('gate_code')} - {res.get('gate_message')}")

    if args.json:
        print("\n" + json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
