import os
import cv2
import imageio_ffmpeg
import numpy as np
from pathlib import Path
from typing import Tuple

def generate_athletic_movement_video(
    output_path: str,
    movement_type: str = "Drop Jump",
    num_frames: int = 120,
    fps: int = 30,
    width: int = 1280,
    height: int = 720
) -> str:
    """
    Creates a clearly labeled synthetic movement clip for testing and pipeline demonstrations.
    This is computer-generated synthetic test footage using OpenCV primitives, not real athlete recordings.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    output_width = width + (width % 2)
    output_height = height + (height % 2)
    encoder = imageio_ffmpeg.write_frames(
        output_path,
        size=(output_width, output_height),
        fps=fps,
        codec="libx264",
        pix_fmt_in="rgb24",
        pix_fmt_out="yuv420p",
        macro_block_size=1,
        output_params=["-crf", "26", "-preset", "veryfast", "-movflags", "+faststart"],
    )
    encoder.send(None)

    center_x = width // 2
    ground_y = int(height * 0.88)

    movement_key = movement_type.lower()

    for i in range(num_frames):
        phase = i / num_frames
        frame = np.zeros((height, width, 3), dtype=np.uint8)

        # Background: Modern sports performance lab floor and wall
        for y in range(height):
            if y < ground_y:
                ratio = y / ground_y
                color = [int(22 + 12 * ratio), int(26 + 14 * ratio), int(38 + 18 * ratio)]
            else:
                ratio = (y - ground_y) / (height - ground_y)
                color = [int(36 - 12 * ratio), int(40 - 12 * ratio), int(48 - 12 * ratio)]
            frame[y, :] = color

        # Performance grid lines on the floor
        for gx in range(80, width, 120):
            cv2.line(frame, (gx, ground_y), (gx + int((gx - center_x) * 0.45), height), (45, 55, 75), 1)
        cv2.line(frame, (0, ground_y), (width, ground_y), (75, 95, 125), 2)

        # Kinematic model variables
        trunk_tilt = 0
        l_arm_mode = "neutral"
        r_arm_mode = "neutral"

        if "squat" in movement_key:
            # Deep Squat: Bilateral descending and ascending mechanics
            squat_depth = np.sin(phase * np.pi) ** 2
            hip_y = int(height * 0.44 + squat_depth * 135)
            hip_x = center_x
            knee_spread = int(55 + squat_depth * 28)
            ankle_spread = 68
            trunk_tilt = int(squat_depth * 14)
            knee_y = hip_y + int(70 - squat_depth * 15)
            ankle_y = ground_y - 12
            l_knee = (hip_x - knee_spread, knee_y)
            r_knee = (hip_x + knee_spread, knee_y)
            l_ankle = (hip_x - ankle_spread, ankle_y)
            r_ankle = (hip_x + ankle_spread, ankle_y)
            l_arm_mode = "squat"
            r_arm_mode = "squat"

        elif "cut" in movement_key or "side" in movement_key:
            # Side Cut: Lateral approach, sharp deceleration plant step, trunk lean
            lateral = np.sin(phase * 2 * np.pi)
            plant = max(0.0, np.sin(phase * np.pi))
            hip_y = int(height * 0.50 + plant * 40)
            hip_x = center_x + int(lateral * 130)
            knee_spread = int(58 - plant * 16)
            ankle_spread = 82
            trunk_tilt = int(-lateral * plant * 28)
            knee_y = hip_y + 80
            ankle_y = ground_y - 12
            l_knee = (hip_x - knee_spread - int(plant * 15), knee_y)
            r_knee = (hip_x + knee_spread, knee_y)
            l_ankle = (hip_x - ankle_spread, ankle_y)
            r_ankle = (hip_x + ankle_spread, ankle_y)
            l_arm_mode = "cut"
            r_arm_mode = "cut"

        elif "sprint" in movement_key:
            # Sprinting: High velocity gait, aggressive forward lean, high knee drive
            cycle = (phase * 6) % 1.0
            hip_y = int(height * 0.46 + np.sin(cycle * 2 * np.pi) * 12)
            hip_x = center_x + int((phase - 0.5) * 80)
            trunk_tilt = 24  # Strong forward acceleration lean
            knee_y_base = hip_y + 75
            ankle_y_base = ground_y - 12
            leg_phase = np.sin(cycle * 2 * np.pi)
            l_knee = (hip_x - 30 + int(leg_phase * 45), knee_y_base - int(max(0, leg_phase) * 55))
            r_knee = (hip_x + 30 - int(leg_phase * 45), knee_y_base - int(max(0, -leg_phase) * 55))
            l_ankle = (hip_x - 35 + int(leg_phase * 65), min(ground_y - 8, ankle_y_base - int(max(0, leg_phase) * 60)))
            r_ankle = (hip_x + 35 - int(leg_phase * 65), min(ground_y - 8, ankle_y_base - int(max(0, -leg_phase) * 60)))
            l_arm_mode = "sprint_l"
            r_arm_mode = "sprint_r"

        elif "run" in movement_key:
            # Running: Moderate cadence gait cycle, reciprocating leg & arm swing
            cycle = (phase * 4) % 1.0
            hip_y = int(height * 0.48 + np.sin(cycle * 2 * np.pi) * 16)
            hip_x = center_x
            trunk_tilt = 8  # Slight forward lean
            knee_y_base = hip_y + 80
            ankle_y_base = ground_y - 12
            leg_phase = np.sin(cycle * 2 * np.pi)
            l_knee = (hip_x - 28 + int(leg_phase * 35), knee_y_base - int(max(0, leg_phase) * 35))
            r_knee = (hip_x + 28 - int(leg_phase * 35), knee_y_base - int(max(0, -leg_phase) * 35))
            l_ankle = (hip_x - 32 + int(leg_phase * 50), min(ground_y - 8, ankle_y_base - int(max(0, leg_phase) * 45)))
            r_ankle = (hip_x + 32 - int(leg_phase * 50), min(ground_y - 8, ankle_y_base - int(max(0, -leg_phase) * 45)))
            l_arm_mode = "run_l"
            r_arm_mode = "run_r"

        elif "throw" in movement_key:
            # Throwing: Windup, step forward, torso rotation, arm acceleration & release follow-through
            if phase < 0.35:
                # Windup: weight on back foot, arm cocking
                t = phase / 0.35
                hip_y = int(height * 0.50)
                hip_x = center_x - int(t * 30)
                trunk_tilt = -int(t * 15)
                l_knee = (hip_x - 45, hip_y + 80)
                r_knee = (hip_x + 35, hip_y + 85)
                l_ankle = (hip_x - 65, ground_y - 12)
                r_ankle = (hip_x + 45, ground_y - 12)
                l_arm_mode = "throw_windup_l"
                r_arm_mode = "throw_windup_r"
            elif phase < 0.65:
                # Step forward and explosive arm release
                t = (phase - 0.35) / 0.30
                hip_y = int(height * 0.50 + t * 15)
                hip_x = center_x - 30 + int(t * 70)
                trunk_tilt = int(-15 + t * 35)
                l_knee = (hip_x - 20, hip_y + 75)
                r_knee = (hip_x + 50, hip_y + 90)
                l_ankle = (hip_x - 40, ground_y - 12)
                r_ankle = (hip_x + 85, ground_y - 12)
                l_arm_mode = "throw_release_l"
                r_arm_mode = "throw_release_r"
            else:
                # Follow-through
                t = (phase - 0.65) / 0.35
                hip_y = int(height * 0.51 - t * 8)
                hip_x = center_x + 40
                trunk_tilt = int(20 - t * 10)
                l_knee = (hip_x - 25, hip_y + 80)
                r_knee = (hip_x + 45, hip_y + 85)
                l_ankle = (hip_x - 45, ground_y - 12)
                r_ankle = (hip_x + 70, ground_y - 12)
                l_arm_mode = "throw_follow_l"
                r_arm_mode = "throw_follow_r"

        else:
            # Drop Jump: Descent, landing compression with medial knee valgus, and rebound
            if phase < 0.30:
                jump_t = phase / 0.30
                hip_y = int(height * 0.46 - np.sin(jump_t * np.pi) * 75)
                hip_x = center_x
                knee_spread = 58
                ankle_spread = 65
                trunk_tilt = 0
            elif phase < 0.70:
                land_t = (phase - 0.30) / 0.40
                squat_depth = np.sin(land_t * np.pi)
                hip_y = int(height * 0.50 + squat_depth * 115)
                trunk_tilt = int(squat_depth * 32)
                hip_x = center_x + int(trunk_tilt * 0.5)
                valgus_collapse = int(squat_depth * 42)
                knee_spread = max(16, 58 - valgus_collapse)
                ankle_spread = 82
            else:
                rec_t = (phase - 0.70) / 0.30
                hip_y = int(height * 0.50 + (1.0 - rec_t) * 20)
                hip_x = center_x
                knee_spread = 52
                ankle_spread = 65
                trunk_tilt = 0

            knee_y = hip_y + 85
            ankle_y = ground_y - 12
            l_knee = (hip_x - knee_spread, knee_y)
            r_knee = (hip_x + knee_spread, knee_y)
            l_ankle = (hip_x - ankle_spread, ankle_y)
            r_ankle = (hip_x + ankle_spread, ankle_y)

        # Upper Body coordinates
        head_y = hip_y - 140
        shldr_y = hip_y - 100
        shldr_w = 48
        hip_w = 36

        head_pt = (hip_x + int(trunk_tilt * 0.9), head_y)
        l_shldr = (hip_x - shldr_w + int(trunk_tilt * 0.7), shldr_y)
        r_shldr = (hip_x + shldr_w + int(trunk_tilt * 0.7), shldr_y)
        l_hip = (hip_x - hip_w, hip_y)
        r_hip = (hip_x + hip_w, hip_y)

        # Dynamic Arm Positions based on movement mode
        if l_arm_mode == "squat":
            l_elbow = (l_shldr[0] - 25, shldr_y + 15)
            r_elbow = (r_shldr[0] + 25, shldr_y + 15)
            l_wrist = (l_elbow[0] + 20, l_elbow[1] - 30)
            r_wrist = (r_elbow[0] - 20, r_elbow[1] - 30)
        elif l_arm_mode == "sprint_l":
            cycle = (phase * 6) % 1.0
            arm_p = np.sin(cycle * 2 * np.pi)
            l_elbow = (l_shldr[0] - 30, shldr_y + int(arm_p * 35))
            r_elbow = (r_shldr[0] + 30, shldr_y - int(arm_p * 35))
            l_wrist = (l_elbow[0] + int(arm_p * 25), l_elbow[1] - 35)
            r_wrist = (r_elbow[0] - int(arm_p * 25), r_elbow[1] - 35)
        elif l_arm_mode == "run_l":
            cycle = (phase * 4) % 1.0
            arm_p = np.sin(cycle * 2 * np.pi)
            l_elbow = (l_shldr[0] - 25, shldr_y + 20 + int(arm_p * 25))
            r_elbow = (r_shldr[0] + 25, shldr_y + 20 - int(arm_p * 25))
            l_wrist = (l_elbow[0] + 15, l_elbow[1] - 25)
            r_wrist = (r_elbow[0] - 15, r_elbow[1] - 25)
        elif l_arm_mode == "throw_windup_l":
            l_elbow = (l_shldr[0] - 30, shldr_y + 20)
            l_wrist = (l_elbow[0] - 15, l_elbow[1] - 10)
            r_elbow = (r_shldr[0] + 45, shldr_y - 25)
            r_wrist = (r_elbow[0] + 15, r_elbow[1] - 40)
        elif l_arm_mode == "throw_release_l":
            l_elbow = (l_shldr[0] - 25, shldr_y + 35)
            l_wrist = (l_elbow[0] - 10, l_elbow[1] + 20)
            r_elbow = (r_shldr[0] + 40, shldr_y - 15)
            r_wrist = (r_elbow[0] + 45, r_elbow[1] + 25)
        elif l_arm_mode == "throw_follow_l":
            l_elbow = (l_shldr[0] - 20, shldr_y + 40)
            l_wrist = (l_elbow[0] - 5, l_elbow[1] + 25)
            r_elbow = (r_shldr[0] - 10, shldr_y + 35)
            r_wrist = (r_elbow[0] - 35, r_elbow[1] + 30)
        else:
            l_elbow = (l_shldr[0] - 35, shldr_y + 35)
            r_elbow = (r_shldr[0] + 35, shldr_y + 35)
            l_wrist = (l_elbow[0] - 15, l_elbow[1] + 35)
            r_wrist = (r_elbow[0] + 15, r_elbow[1] + 35)

        # Drawing Colors
        athlete_color = (220, 225, 235)
        joint_color = (0, 210, 255)

        # Head with facial anchors (MediaPipe uses eye/nose/mouth keypoints)
        cv2.circle(frame, head_pt, 24, athlete_color, -1)
        eye_y = head_pt[1] - 4
        nose_y = head_pt[1] + 3
        mouth_y = head_pt[1] + 10
        cv2.circle(frame, (head_pt[0] - 7, eye_y), 3, (30, 30, 40), -1)
        cv2.circle(frame, (head_pt[0] + 7, eye_y), 3, (30, 30, 40), -1)
        cv2.circle(frame, (head_pt[0], nose_y), 2, (60, 60, 70), -1)
        cv2.line(frame, (head_pt[0] - 6, mouth_y), (head_pt[0] + 6, mouth_y), (40, 40, 50), 2)

        # Torso
        torso_pts = np.array([l_shldr, r_shldr, r_hip, l_hip], np.int32)
        cv2.fillPoly(frame, [torso_pts], (60, 110, 200))
        cv2.polylines(frame, [torso_pts], True, athlete_color, 2)

        # Arms
        cv2.line(frame, l_shldr, l_elbow, athlete_color, 12)
        cv2.line(frame, l_elbow, l_wrist, athlete_color, 10)
        cv2.line(frame, r_shldr, r_elbow, athlete_color, 12)
        cv2.line(frame, r_elbow, r_wrist, athlete_color, 10)

        # Legs (Thighs and Shins)
        cv2.line(frame, l_hip, l_knee, (80, 140, 240), 16)
        cv2.line(frame, l_knee, l_ankle, (80, 140, 240), 14)
        cv2.line(frame, r_hip, r_knee, (80, 140, 240), 16)
        cv2.line(frame, r_knee, r_ankle, (80, 140, 240), 14)

        # Feet
        cv2.line(frame, l_ankle, (l_ankle[0] - 25, ground_y - 2), athlete_color, 10)
        cv2.line(frame, r_ankle, (r_ankle[0] + 25, ground_y - 2), athlete_color, 10)

        # Visual Joint markers
        for pt in [head_pt, l_shldr, r_shldr, l_elbow, r_elbow, l_wrist, r_wrist, l_hip, r_hip, l_knee, r_knee, l_ankle, r_ankle]:
            cv2.circle(frame, pt, 5, joint_color, -1)

        # Transparent and Honest Watermark & Metadata
        cv2.putText(frame, f"SYNTHETIC DEMO: {movement_type.upper()}", (35, 45), cv2.FONT_HERSHEY_SIMPLEX, 0.70, (210, 220, 240), 2)
        cv2.putText(frame, "Computer-generated synthetic test clip - Not athlete footage", (35, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (140, 160, 190), 1)
        cv2.putText(frame, f"Frame: {i+1:03d}/{num_frames} | {fps} FPS | Kinematix Test Suite", (35, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (110, 130, 160), 1)

        encoder.send(np.ascontiguousarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).tobytes())

    encoder.close()
    return output_path
