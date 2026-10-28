import os
import cv2
import json
import math
import numpy as np
import logging
from collections import deque
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from sqlalchemy.orm import Session
from app.models.video import Video
from app.core.config import settings
from app.utils.video_utils import enhance_frame_contrast, compute_target_dimensions

logger = logging.getLogger(__name__)

# Complete 33 MediaPipe pose landmark names
LANDMARK_NAMES = [
    "nose", "left_eye_inner", "left_eye", "left_eye_outer", "right_eye_inner", "right_eye",
    "right_eye_outer", "left_ear", "right_ear", "mouth_left", "mouth_right", "left_shoulder",
    "right_shoulder", "left_elbow", "right_elbow", "left_wrist", "right_wrist", "left_pinky",
    "right_pinky", "left_index", "right_index", "left_thumb", "right_thumb", "left_hip",
    "right_hip", "left_knee", "right_knee", "left_ankle", "right_ankle", "left_heel",
    "right_heel", "left_foot_index", "right_foot_index"
]

# Anatomical connection pairs
LEFT_ARM = [(11, 13), (13, 15)]
RIGHT_ARM = [(12, 14), (14, 16)]
LEFT_HAND = [(15, 17), (15, 19), (15, 21)]
RIGHT_HAND = [(16, 18), (16, 20), (16, 22)]
TORSO = [(11, 12), (11, 23), (12, 24), (23, 24)]
LEFT_LEG = [(23, 25), (25, 27), (27, 29), (29, 31), (27, 31)]
RIGHT_LEG = [(24, 26), (26, 28), (28, 30), (30, 32), (28, 32)]
HEAD = [(0, 1), (1, 2), (2, 3), (3, 7), (0, 4), (4, 5), (5, 6), (6, 8), (9, 10)]

# Visualizer BGR color scheme
COLOR_LEFT = (235, 120, 37)      # Blue/Cyan for athlete's left side
COLOR_RIGHT = (68, 68, 239)      # Red/Coral for athlete's right side
COLOR_TORSO = (16, 185, 129)     # Emerald Green for trunk
COLOR_SPINE = (245, 158, 11)     # Amber for vertical alignment
COLOR_HEAD = (100, 215, 250)     # Warm Yellow for head
COLOR_TRAJECTORY = (0, 235, 255) # Bright Cyan for trajectory path

def calculate_angle_2d(p1, p2, p3):
    """Calculates 2D planar angle at vertex p2 using vectors (p1-p2) and (p3-p2)."""
    if p1 is None or p2 is None or p3 is None:
        return None
    v1 = (p1[0] - p2[0], p1[1] - p2[1])
    v2 = (p3[0] - p2[0], p3[1] - p2[1])
    mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
    mag2 = math.sqrt(v2[0]**2 + v2[1]**2)
    if mag1 * mag2 == 0:
        return None
    cos_theta = max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (mag1 * mag2)))
    return round(math.degrees(math.acos(cos_theta)), 1)

def calculate_trunk_lean(mid_shoulder, mid_hip):
    """Calculates torso lean in degrees relative to true vertical (0 deg = vertical)."""
    if mid_shoulder is None or mid_hip is None:
        return None
    dx = mid_shoulder[0] - mid_hip[0]
    dy = mid_shoulder[1] - mid_hip[1] # Note: In image coords, up is negative y
    lean = abs(math.degrees(math.atan2(dx, -dy)))
    if lean > 180:
        lean = 360 - lean
    return round(lean, 1)

def get_primary_pose(pose_landmarks_list):
    """
    Selects the focal subject when multiple people are detected.
    Picks the pose with the largest bounding box area (closest to camera).
    """
    if not pose_landmarks_list:
        return None
    if len(pose_landmarks_list) == 1:
        return pose_landmarks_list[0]
        
    best_pose = None
    max_area = -1.0
    for pose in pose_landmarks_list:
        xs = [lm.x for lm in pose]
        ys = [lm.y for lm in pose]
        area = (max(xs) - min(xs)) * (max(ys) - min(ys))
        if area > max_area:
            max_area = area
            best_pose = pose
            
    return best_pose

def draw_custom_skeleton(frame, landmarks, w, h, hip_trajectory=None, frame_angles=None):
    """
    Renders high-visibility, production-grade biomechanical skeleton overlays:
    - Dynamic resolution scaling (joints and bone lines scale proportionally with video resolution).
    - High-contrast dual-layer bones (underlayer dark shadow + bright neon foreground).
    - Prominent triple-layer joint node markers (dark border + bright fill + white core).
    - Floating live joint angle degree callouts right at the knees and trunk.
    - Smooth movement trajectory trail.
    """
    base_scale = max(1.2, min(w, h) / 400.0)

    # Convert normalized landmarks to pixel coords
    pts = {}
    visibilities = {}
    for idx, lm in enumerate(landmarks):
        px = int(np.clip(lm.x * w, 0, w - 1))
        py = int(np.clip(lm.y * h, 0, h - 1))
        pts[idx] = (px, py)
        vis = getattr(lm, "visibility", 0.9)
        if vis is None:
            vis = getattr(lm, "presence", 0.9)
        if vis is None:
            vis = 0.9
        visibilities[idx] = float(vis)

    # 1. Draw Trajectory Trail
    if hip_trajectory and len(hip_trajectory) > 1:
        traj_len = len(hip_trajectory)
        for i in range(1, traj_len):
            alpha = i / float(traj_len)
            thickness = max(2, int(4 * alpha * base_scale))
            color = (int(0 * alpha), int(220 * alpha), int(255 * alpha))
            pt1 = (int(hip_trajectory[i - 1][0] * w), int(hip_trajectory[i - 1][1] * h))
            pt2 = (int(hip_trajectory[i][0] * w), int(hip_trajectory[i][1] * h))
            cv2.line(frame, pt1, pt2, color, thickness, cv2.LINE_AA)

    # 2. Draw Anatomical Segment Connections (Dual-Layer for Maximum Contrast)
    def draw_segment_group(connections, color, thickness):
        shadow_thick = int(thickness * base_scale + 3)
        fg_thick = max(2, int(thickness * base_scale))
        for idx1, idx2 in connections:
            if idx1 in pts and idx2 in pts:
                # Plot as long as both points are within the frame and have minimal presence
                if visibilities.get(idx1, 0) >= 0.05 and visibilities.get(idx2, 0) >= 0.05:
                    # Layer 1: Dark contrast shadow outline
                    cv2.line(frame, pts[idx1], pts[idx2], (15, 23, 42), shadow_thick, cv2.LINE_AA)
                    # Layer 2: Vibrant neon foreground
                    cv2.line(frame, pts[idx1], pts[idx2], color, fg_thick, cv2.LINE_AA)

    draw_segment_group(TORSO, COLOR_TORSO, thickness=3.5)
    draw_segment_group(LEFT_ARM, COLOR_LEFT, thickness=3.0)
    draw_segment_group(LEFT_HAND, COLOR_LEFT, thickness=2.2)
    draw_segment_group(RIGHT_ARM, COLOR_RIGHT, thickness=3.0)
    draw_segment_group(RIGHT_HAND, COLOR_RIGHT, thickness=2.2)
    draw_segment_group(LEFT_LEG, COLOR_LEFT, thickness=4.5)
    draw_segment_group(RIGHT_LEG, COLOR_RIGHT, thickness=4.5)
    draw_segment_group(HEAD, COLOR_HEAD, thickness=2.0)

    # Draw spine line
    if 11 in pts and 12 in pts and 23 in pts and 24 in pts:
        mid_sh = ((pts[11][0] + pts[12][0]) // 2, (pts[11][1] + pts[12][1]) // 2)
        mid_hp = ((pts[23][0] + pts[24][0]) // 2, (pts[23][1] + pts[24][1]) // 2)
        cv2.line(frame, mid_sh, mid_hp, (15, 23, 42), int(3.5 * base_scale + 3), cv2.LINE_AA)
        cv2.line(frame, mid_sh, mid_hp, COLOR_SPINE, max(2, int(3.5 * base_scale)), cv2.LINE_AA)

    # 3. Draw Joint Circle Nodes (Triple-Layer: Dark Border + Vibrant Ring + White Core)
    PRIMARY_JOINTS = {11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32}
    for idx in range(33):
        if idx in pts:
            vis = visibilities.get(idx, 0)
            if vis >= 0.05:
                is_primary = idx in PRIMARY_JOINTS
                outer_r = int((7.5 if is_primary else 4.5) * base_scale)
                inner_r = max(2, int((5.5 if is_primary else 3.0) * base_scale))
                core_r = max(1, int((2.2 if is_primary else 1.2) * base_scale))

                node_color = COLOR_LEFT if idx % 2 != 0 else COLOR_RIGHT
                if idx in (11, 12, 23, 24):
                    node_color = COLOR_TORSO
                elif idx < 11:
                    node_color = COLOR_HEAD

                # Layer 1: Dark outer contrast shadow
                cv2.circle(frame, pts[idx], outer_r + 2, (15, 23, 42), -1, cv2.LINE_AA)
                # Layer 2: Vibrant solid fill
                cv2.circle(frame, pts[idx], outer_r, node_color, -1, cv2.LINE_AA)
                # Layer 3: Solid white inner core dot
                cv2.circle(frame, pts[idx], core_r, (255, 255, 255), -1, cv2.LINE_AA)

    # 4. Draw Floating Joint Angle Callout Badges
    if frame_angles:
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.38 * min(1.6, base_scale)
        font_thick = 1

        def draw_angle_pill(pt, text, border_color=(56, 189, 248)):
            if not pt or not text:
                return
            (tw, th), bl = cv2.getTextSize(text, font, font_scale, font_thick)
            x1 = pt[0] + int(10 * base_scale)
            y1 = pt[1] - th - int(6 * base_scale)
            x2 = x1 + tw + int(12 * base_scale)
            y2 = pt[1] + int(6 * base_scale)
            # Frame boundaries
            if x2 >= w:
                x1 = pt[0] - tw - int(18 * base_scale)
                x2 = pt[0] - int(6 * base_scale)
            if y1 < 0:
                y1 = pt[1] + int(6 * base_scale)
                y2 = y1 + th + int(12 * base_scale)

            cv2.rectangle(frame, (x1, y1), (x2, y2), (15, 23, 42), -1)
            cv2.rectangle(frame, (x1, y1), (x2, y2), border_color, 1)
            cv2.putText(frame, text, (x1 + int(6 * base_scale), y2 - int(5 * base_scale)), font, font_scale, (255, 255, 255), font_thick, cv2.LINE_AA)

        # Left Knee angle callout
        if 25 in pts and frame_angles.get("left_knee") is not None:
            draw_angle_pill(pts[25], f"L: {frame_angles['left_knee']:.0f}deg", border_color=(235, 120, 37))

        # Right Knee angle callout
        if 26 in pts and frame_angles.get("right_knee") is not None:
            draw_angle_pill(pts[26], f"R: {frame_angles['right_knee']:.0f}deg", border_color=(68, 68, 239))

def render_hud_telemetry(frame, timestamp_s, angles, movement_type, quality_flag):
    """Renders semi-transparent HUD banner with live joint angles and tracking status."""
    h, w = frame.shape[:2]
    base_scale = max(1.0, min(w, h) / 480.0)
    hud_w = int(min(380 * base_scale, w - 20))
    hud_h = int(90 * base_scale)
    
    # Create semi-transparent dark overlay for top-left HUD
    overlay = frame.copy()
    cv2.rectangle(overlay, (10, 10), (10 + hud_w, 10 + hud_h), (15, 23, 42), -1)
    cv2.addWeighted(overlay, 0.78, frame, 0.22, 0, frame)
    cv2.rectangle(frame, (10, 10), (10 + hud_w, 10 + hud_h), (51, 65, 85), 1)

    f_scale = 0.42 * min(1.8, base_scale)

    # Brand header
    cv2.putText(frame, "AthletiQ Motion Tracking", (int(20 * base_scale), int(28 * base_scale)), cv2.FONT_HERSHEY_SIMPLEX, f_scale * 1.1, (255, 255, 255), 1, cv2.LINE_AA)
    
    # Quality status indicator dot
    dot_color = (34, 197, 94) if quality_flag == "OK" else (234, 179, 8) if quality_flag == "OCCLUSION" else (239, 68, 68)
    cv2.circle(frame, (hud_w - int(10 * base_scale), int(25 * base_scale)), int(5 * base_scale), dot_color, -1, cv2.LINE_AA)

    # Telemetry readout text
    l_knee_str = f"L Knee: {angles.get('left_knee', '--')}deg"
    r_knee_str = f"R Knee: {angles.get('right_knee', '--')}deg"
    trunk_str = f"Trunk: {angles.get('trunk_lean', '--')}deg"
    t_str = f"T: {timestamp_s:.2f}s  [{movement_type.capitalize()}]"

    cv2.putText(frame, t_str, (int(20 * base_scale), int(48 * base_scale)), cv2.FONT_HERSHEY_SIMPLEX, f_scale * 0.9, (148, 163, 184), 1, cv2.LINE_AA)
    cv2.putText(frame, f"{l_knee_str}  |  {r_knee_str}", (int(20 * base_scale), int(68 * base_scale)), cv2.FONT_HERSHEY_SIMPLEX, f_scale * 0.9, (226, 232, 240), 1, cv2.LINE_AA)
    cv2.putText(frame, trunk_str, (int(20 * base_scale), int(84 * base_scale)), cv2.FONT_HERSHEY_SIMPLEX, f_scale * 0.85, (56, 189, 248), 1, cv2.LINE_AA)

def process_video_pipeline(db: Session, video_id: int):
    """
    Production-grade Pose Estimation and Video Processing Engine:
    - Normalizes resolution and frame-rate.
    - MediaPipe Pose Landmarker tracking (head, upper body, hips, knees, ankles, feet).
    - Multi-person handling with primary focal athlete detection.
    - Full joint angle telemetry (left/right knee, hip, trunk lean, ankle).
    - Motion trajectory tracking (hip path, ankle displacement).
    - Occlusion and confidence quality evaluation.
    - Progress updates in database.
    - Annotated video with skeleton overlay and HUD telemetry.
    """
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video or video.status not in ("uploaded", "processing"):
        return

    # Update database state to processing
    video.status = "processing"
    video.processing_progress = 5
    db.commit()

    input_path = video.file_path
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_video_path = os.path.join(settings.UPLOAD_DIR, f"{base_name}_annotated.mp4")
    output_json_path = os.path.join(settings.UPLOAD_DIR, f"{base_name}_landmarks.json")

    try:
        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            raise Exception("Cannot open video file for frame decoding.")

        raw_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        raw_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        raw_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Target dimensions (capped to standard resolution for speed and memory)
        target_w, target_h = compute_target_dimensions(raw_width, raw_height, max_dim=1280)
        
        import imageio
        out = imageio.get_writer(output_video_path, fps=raw_fps, codec='libx264', pixelformat='yuv420p', format='FFMPEG')

        # Model selection: Full model for precision with lite fallback
        current_dir = os.path.dirname(os.path.abspath(__file__))
        full_model_path = os.path.abspath(os.path.join(current_dir, "..", "models_ml", "pose_landmarker_full.task"))
        lite_model_path = os.path.abspath(os.path.join(current_dir, "..", "models_ml", "pose_landmarker_lite.task"))
        model_path = full_model_path if os.path.exists(full_model_path) else lite_model_path

        if not os.path.exists(model_path):
            raise Exception(f"MediaPipe Pose Landmarker model asset not found at {model_path}")

        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            output_segmentation_masks=False,
            min_pose_detection_confidence=0.25,
            min_pose_presence_confidence=0.25,
            min_tracking_confidence=0.25,
            running_mode=vision.RunningMode.VIDEO
        )

        output_data = {
            "athlete_id": video.athlete_id,
            "video_id": video.id,
            "movement_type": video.movement_type or "general",
            "fps": raw_fps,
            "width": target_w,
            "height": target_h,
            "total_frames": total_frames,
            "frames": [],
            "trajectories": {
                "hip": [],
                "left_ankle": [],
                "right_ankle": []
            },
            "summary_kinematics": {}
        }

        hip_trajectory_queue = deque(maxlen=30)
        tracked_frames_count = 0
        occlusion_frames_count = 0
        all_left_knees = []
        all_right_knees = []
        all_leans = []

        with vision.PoseLandmarker.create_from_options(options) as landmarker:
            frame_idx = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                # Resize if downscaling is required
                if (raw_width, raw_height) != (target_w, target_h):
                    frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)

                # Light contrast enhancement if scene is dimly lit
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                enhanced_rgb = enhance_frame_contrast(rgb_frame)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=enhanced_rgb)

                timestamp_ms = int((frame_idx / raw_fps) * 1000)
                results = landmarker.detect_for_video(mp_image, timestamp_ms)

                annotated_frame = frame.copy()
                frame_angles = {}
                quality_flag = "OK"
                frame_landmarks_list = []

                if results.pose_landmarks and len(results.pose_landmarks) > 0:
                    primary_pose = get_primary_pose(results.pose_landmarks)
                    tracked_frames_count += 1

                    # Extract coordinates for angles
                    lm_pixel = {}
                    for idx, lm in enumerate(primary_pose):
                        vis = getattr(lm, "visibility", 0.0)
                        lm_pixel[idx] = (lm.x * target_w, lm.y * target_h)
                        name = LANDMARK_NAMES[idx] if idx < len(LANDMARK_NAMES) else f"landmark_{idx}"
                        frame_landmarks_list.append({
                            "name": name,
                            "x": float(lm.x),
                            "y": float(lm.y),
                            "z": float(getattr(lm, "z", 0.0)),
                            "visibility": float(vis)
                        })

                    # Calculate joint angles
                    # Left knee (hip 23, knee 25, ankle 27)
                    l_knee = calculate_angle_2d(lm_pixel.get(23), lm_pixel.get(25), lm_pixel.get(27))
                    # Right knee (hip 24, knee 26, ankle 28)
                    r_knee = calculate_angle_2d(lm_pixel.get(24), lm_pixel.get(26), lm_pixel.get(28))
                    # Left hip (shoulder 11, hip 23, knee 25)
                    l_hip = calculate_angle_2d(lm_pixel.get(11), lm_pixel.get(23), lm_pixel.get(25))
                    # Right hip (shoulder 12, hip 24, knee 26)
                    r_hip = calculate_angle_2d(lm_pixel.get(12), lm_pixel.get(24), lm_pixel.get(26))
                    # Ankle flexion
                    l_ankle = calculate_angle_2d(lm_pixel.get(25), lm_pixel.get(27), lm_pixel.get(31))
                    r_ankle = calculate_angle_2d(lm_pixel.get(26), lm_pixel.get(28), lm_pixel.get(32))

                    # Torso lean
                    mid_sh = ((lm_pixel[11][0] + lm_pixel[12][0]) / 2, (lm_pixel[11][1] + lm_pixel[12][1]) / 2) if 11 in lm_pixel and 12 in lm_pixel else None
                    mid_hp = ((lm_pixel[23][0] + lm_pixel[24][0]) / 2, (lm_pixel[23][1] + lm_pixel[24][1]) / 2) if 23 in lm_pixel and 24 in lm_pixel else None
                    trunk_lean = calculate_trunk_lean(mid_sh, mid_hp)

                    frame_angles = {
                        "left_knee": l_knee,
                        "right_knee": r_knee,
                        "left_hip": l_hip,
                        "right_hip": r_hip,
                        "left_ankle": l_ankle,
                        "right_ankle": r_ankle,
                        "trunk_lean": trunk_lean
                    }

                    # Check for lower-extremity occlusion
                    critical_vis = [getattr(primary_pose[i], "visibility", 0) for i in (23, 24, 25, 26, 27, 28)]
                    if any(v < 0.45 for v in critical_vis):
                        quality_flag = "OCCLUSION"
                        occlusion_frames_count += 1

                    if l_knee: all_left_knees.append(l_knee)
                    if r_knee: all_right_knees.append(r_knee)
                    if trunk_lean: all_leans.append(trunk_lean)

                    # Update trajectories
                    if mid_hp:
                        norm_hip = (mid_hp[0] / target_w, mid_hp[1] / target_h)
                        hip_trajectory_queue.append(norm_hip)
                        output_data["trajectories"]["hip"].append({"x": norm_hip[0], "y": norm_hip[1], "t": timestamp_ms})
                    if 27 in lm_pixel:
                        output_data["trajectories"]["left_ankle"].append({"x": primary_pose[27].x, "y": primary_pose[27].y, "t": timestamp_ms})
                    if 28 in lm_pixel:
                        output_data["trajectories"]["right_ankle"].append({"x": primary_pose[28].x, "y": primary_pose[28].y, "t": timestamp_ms})

                    # Draw Custom High-Visibility Skeleton
                    draw_custom_skeleton(annotated_frame, primary_pose, target_w, target_h, hip_trajectory_queue, frame_angles)
                else:
                    quality_flag = "NO_SUBJECT"

                # Render On-screen HUD Telemetry
                render_hud_telemetry(annotated_frame, timestamp_ms / 1000.0, frame_angles, video.movement_type or "general", quality_flag)

                output_data["frames"].append({
                    "frame_index": frame_idx,
                    "timestamp_ms": timestamp_ms,
                    "quality_flag": quality_flag,
                    "angles": frame_angles,
                    "landmarks": frame_landmarks_list
                })

                # Write annotated frame to output video
                annotated_rgb = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                out.append_data(annotated_rgb)

                frame_idx += 1

                # Update progress periodically
                if total_frames > 0 and frame_idx % max(1, total_frames // 10) == 0:
                    progress = int(10 + (frame_idx / total_frames) * 85)
                    video.processing_progress = min(progress, 95)
                    db.commit()

        cap.release()
        out.close()

        # Quality & Visibility Evaluation
        effective_total = max(1, frame_idx)
        quality_score = round((tracked_frames_count / effective_total) * 100, 1)

        # Kinematic Summary
        sym_diff = round(abs(min(all_left_knees) - min(all_right_knees)), 1) if all_left_knees and all_right_knees else None
        output_data["summary_kinematics"] = {
            "min_left_knee": min(all_left_knees) if all_left_knees else None,
            "min_right_knee": min(all_right_knees) if all_right_knees else None,
            "max_trunk_lean": max(all_leans) if all_leans else None,
            "symmetry_index": sym_diff,
            "tracked_percentage": quality_score
        }

        # Check suitability for analysis
        quality_issues = None
        if quality_score < 15.0:
            video.status = "error"
            video.error_message = (
                f"Insufficient subject visibility: Only {quality_score}% of frames had detectable pose keypoints. "
                "Ensure the athlete's full body (head to feet) is continuously in camera view in good lighting without heavy occlusion."
            )
            video.processing_progress = 0
            db.commit()
            return

        if occlusion_frames_count > (effective_total * 0.35):
            quality_issues = f"Partial occlusion observed in {round(occlusion_frames_count / effective_total * 100)}% of frames."

        # Save artifacts
        with open(output_json_path, "w") as f:
            json.dump(output_data, f)

        video.status = "completed"
        video.processing_progress = 100
        video.quality_score = quality_score
        video.quality_issues = quality_issues
        video.error_message = None
        db.commit()
        logger.info(f"Video #{video_id} processing completed successfully. Quality={quality_score}%")

        # Module 11: Trigger Notification & Alert System
        try:
            from app.services.notification_service import notification_service
            notification_service.generate_alerts_for_video(db, video_id)
        except Exception as alert_err:
            logger.warning(f"Could not generate post-processing alerts for video #{video_id}: {alert_err}")

    except Exception as e:
        logger.error(f"Failed to process video {video_id}: {str(e)}")
        video.status = "error"
        video.error_message = f"Processing pipeline failure: {str(e)}"
        video.processing_progress = 0
        db.commit()
