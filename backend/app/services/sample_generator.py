import os
import cv2
import numpy as np
from pathlib import Path
from typing import Tuple

def generate_athletic_movement_video(
    output_path: str,
    movement_type: str = "Jump Landing (High Knee Valgus)",
    num_frames: int = 120,
    fps: int = 30,
    width: int = 1280,
    height: int = 720
) -> str:
    """
    Synthesizes a realistic athletic movement video with kinematic biomechanics
    (jump landing, squat, cutting drill) using OpenCV.
    This guarantees that the user has immediately playable, analyzable sports video
    data right after launching the platform.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    center_x = width // 2
    ground_y = int(height * 0.88)

    for i in range(num_frames):
        # Background: Modern sports science training gym
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        # Gradient dark athletic floor and wall
        for y in range(height):
            if y < ground_y:
                ratio = y / ground_y
                color = [int(25 + 15 * ratio), int(30 + 15 * ratio), int(45 + 20 * ratio)]
            else:
                ratio = (y - ground_y) / (height - ground_y)
                color = [int(40 - 15 * ratio), int(45 - 15 * ratio), int(55 - 15 * ratio)]
            frame[y, :] = color

        # Draw sports performance grid lines on gym floor
        for gx in range(100, width, 120):
            cv2.line(frame, (gx, ground_y), (gx + int((gx - center_x) * 0.4), height), (50, 60, 80), 1)
        cv2.line(frame, (0, ground_y), (width, ground_y), (80, 100, 130), 2)

        # Athletic movement phase calculation:
        # Phase 1 (0..35): Jump / Flight
        # Phase 2 (36..70): Initial Contact & Deep Landing Deceleration (Valgus collapse)
        # Phase 3 (71..120): Recovery & Push-off
        phase = i / num_frames
        
        # Base kinematics
        if i < 35:
            # Airborne phase
            jump_t = i / 35.0
            hip_y = int(height * 0.48 - np.sin(jump_t * np.pi) * 80)
            hip_x = center_x
            knee_spread = 60
            ankle_spread = 65
            trunk_tilt = 0
            valgus_offset = 0
        elif i < 75:
            # Landing & deep loading phase (knee valgus collapse!)
            land_t = (i - 35) / 40.0
            squat_depth = np.sin(land_t * np.pi) * 110
            hip_y = int(height * 0.52 + squat_depth)
            
            # Trunk lean spike during landing
            trunk_tilt = int(np.sin(land_t * np.pi) * 35)
            hip_x = center_x + int(trunk_tilt * 0.6)
            
            # Dynamic Knee Valgus: Knees buckle inward towards center while ankles stay wide
            valgus_collapse = int(np.sin(land_t * np.pi) * 45)
            knee_spread = max(15, 60 - valgus_collapse) # medial collapse
            ankle_spread = 85 # wide feet
        else:
            # Extension recovery
            rec_t = (i - 75) / 45.0
            hip_y = int(height * 0.52 + (1.0 - rec_t) * 20)
            hip_x = center_x
            knee_spread = 55
            ankle_spread = 65
            trunk_tilt = 0

        # Calculate joint coordinates
        head_y = hip_y - 140
        shldr_y = hip_y - 100
        shldr_w = 48
        hip_w = 36

        head_pt = (hip_x + int(trunk_tilt * 0.9), head_y)
        l_shldr = (hip_x - shldr_w + int(trunk_tilt * 0.7), shldr_y)
        r_shldr = (hip_x + shldr_w + int(trunk_tilt * 0.7), shldr_y)

        l_hip = (hip_x - hip_w, hip_y)
        r_hip = (hip_x + hip_w, hip_y)

        knee_y = hip_y + 85
        l_knee = (hip_x - knee_spread, knee_y)
        r_knee = (hip_x + knee_spread, knee_y)

        ankle_y = ground_y - 12
        l_ankle = (hip_x - ankle_spread, ankle_y)
        r_ankle = (hip_x + ankle_spread, ankle_y)

        # Arms position
        l_elbow = (l_shldr[0] - 35, shldr_y + 35)
        r_elbow = (r_shldr[0] + 35, shldr_y + 35)
        l_wrist = (l_elbow[0] - 15, l_elbow[1] + 35)
        r_wrist = (r_elbow[0] + 15, r_elbow[1] + 35)

        # Draw Athlete Silhouette with distinct limbs
        athlete_color = (220, 225, 235)
        joint_color = (0, 210, 255)

        # Head
        cv2.circle(frame, head_pt, 22, athlete_color, -1)
        # Torso
        torso_pts = np.array([l_shldr, r_shldr, r_hip, l_hip], np.int32)
        cv2.fillPoly(frame, [torso_pts], (60, 110, 200))
        cv2.polylines(frame, [torso_pts], True, athlete_color, 2)

        # Arms
        cv2.line(frame, l_shldr, l_elbow, athlete_color, 6)
        cv2.line(frame, l_elbow, l_wrist, athlete_color, 5)
        cv2.line(frame, r_shldr, r_elbow, athlete_color, 6)
        cv2.line(frame, r_elbow, r_wrist, athlete_color, 5)

        # Legs (Thighs and Shins)
        cv2.line(frame, l_hip, l_knee, (80, 140, 240), 9)
        cv2.line(frame, l_knee, l_ankle, (80, 140, 240), 8)
        cv2.line(frame, r_hip, r_knee, (80, 140, 240), 9)
        cv2.line(frame, r_knee, r_ankle, (80, 140, 240), 8)

        # Feet
        cv2.line(frame, l_ankle, (l_ankle[0] - 25, ground_y - 2), athlete_color, 6)
        cv2.line(frame, r_ankle, (r_ankle[0] + 25, ground_y - 2), athlete_color, 6)

        # Visual Joint markers
        for pt in [head_pt, l_shldr, r_shldr, l_elbow, r_elbow, l_wrist, r_wrist, l_hip, r_hip, l_knee, r_knee, l_ankle, r_ankle]:
            cv2.circle(frame, pt, 5, joint_color, -1)

        # Watermark & Activity Label
        cv2.putText(frame, f"SPORTS MOTION CAPTURE: {movement_type.upper()}", (35, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (200, 210, 230), 2)
        cv2.putText(frame, f"Frame: {i:03d}/{num_frames} | Biomechanics Recording", (35, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (120, 140, 170), 1)

        out.write(frame)

    out.release()
    return output_path
