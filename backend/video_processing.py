import cv2
import os
import uuid
import math
import numpy as np

try:
    import mediapipe as mp
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
except (ImportError, AttributeError):
    mp = None
    mp_pose = None
    mp_drawing = None

def calculate_angle(a, b, c):
    """Calculate the angle between 3 points (x, y)."""
    ang = math.degrees(math.atan2(c[1]-b[1], c[0]-b[0]) - math.atan2(a[1]-b[1], a[0]-b[0]))
    return ang + 360 if ang < 0 else ang

def process_video_with_mediapipe(input_path: str, output_dir: str, activity: str = "Unknown", surface_type: str = "Unknown", footwear: str = "Unknown", rpe: int = 5, sleep_quality: int = 5):
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        raise Exception("Error opening video stream or file")

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    # Video Quality Validation
    if width < 320 or height < 240:
        cap.release()
        raise Exception(f"Video resolution too low: {width}x{height}. Minimum required is 320x240.")
    if frame_count < fps * 1: # less than 1 second
        cap.release()
        raise Exception(f"Video too short. Minimum duration is 1 second.")

    filename = f"{uuid.uuid4()}.mp4"
    output_path = os.path.join(output_dir, filename)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    risk_flags = []
    min_knee_angle = 180
    max_knee_extension = 0
    
    # Trajectory tracking (Motion trajectory analysis)
    trajectory_points = []

    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while cap.isOpened():
            success, image = cap.read()
            if not success:
                break

            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image_rgb.flags.writeable = False
            results = pose.process(image_rgb)
            
            image_rgb.flags.writeable = True
            image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
            
            if results.pose_landmarks:
                mp_drawing.draw_landmarks(
                    image_bgr,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=mp_drawing.DrawingSpec(color=(245,117,66), thickness=2, circle_radius=2),
                    connection_drawing_spec=mp_drawing.DrawingSpec(color=(245,66,230), thickness=2, circle_radius=2)
                )

                landmarks = results.pose_landmarks.landmark
                
                # Keypoint extraction & Key Body Points
                try:
                    head = [landmarks[mp_pose.PoseLandmark.NOSE.value].x, landmarks[mp_pose.PoseLandmark.NOSE.value].y]
                    shoulder = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]
                    elbow = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].x, landmarks[mp_pose.PoseLandmark.LEFT_ELBOW.value].y]
                    wrist = [landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].x, landmarks[mp_pose.PoseLandmark.LEFT_WRIST.value].y]
                    hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]
                    knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x, landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
                    ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x, landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
                    foot = [landmarks[mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value].x, landmarks[mp_pose.PoseLandmark.LEFT_FOOT_INDEX.value].y]
                    
                    # Track ankle trajectory
                    px_ankle = tuple(np.multiply(ankle, [width, height]).astype(int))
                    trajectory_points.append(px_ankle)
                    
                    # Draw trajectory
                    for i in range(1, len(trajectory_points)):
                        cv2.line(image_bgr, trajectory_points[i-1], trajectory_points[i], (0, 255, 255), 2)
                        
                    # Calculate Knee Angle
                    angle = calculate_angle(hip, knee, ankle)
                    if angle > 180:
                        angle = 360 - angle
                        
                    min_knee_angle = min(min_knee_angle, angle)
                    max_knee_extension = max(max_knee_extension, angle)
                    
                    cv2.putText(image_bgr, str(int(angle)), 
                           tuple(np.multiply(knee, [width, height]).astype(int)), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA)
                except Exception as e:
                    pass

            out.write(image_bgr)

    cap.release()
    out.release()
    
    # Assess risk based on activity
    risk_score = 0
    if activity in ["Squatting", "Jumping", "Landing"]:
        if min_knee_angle < 70:
            risk_flags.append("Extreme knee flexion detected (High Risk)")
            risk_score += 40
        elif min_knee_angle < 90:
            risk_flags.append("Deep knee flexion detected (Moderate Risk)")
            risk_score += 20
    elif activity in ["Running", "Sprinting"]:
        if max_knee_extension > 175:
            risk_flags.append("Knee overextension (High Risk of hamstring injury)")
            risk_score += 30
    elif activity in ["Throwing"]:
        risk_flags.append("Shoulder/Elbow dynamics monitored")
    elif activity in ["Cutting Movements"]:
        risk_flags.append("Monitoring knee valgus and sudden directional changes")
        risk_score += 15
            
    # Environmental & Equipment Modifiers
    if surface_type == "Artificial Turf" and footwear == "Cleats":
        risk_flags.append("Turf + Cleats detected (Increased ACL strain risk)")
        risk_score += 15
    elif surface_type == "Hardwood" and footwear == "Running Shoes":
        risk_flags.append("Hardwood + Running shoes (Potential grip/slip hazard)")
        risk_score += 10

    # Subjective Wellness Modifiers
    fatigue_modifier = 0
    if rpe > 7:
        fatigue_modifier += 10
        risk_flags.append("High Perceived Exertion (Fatigue risk)")
    if sleep_quality < 5:
        fatigue_modifier += 15
        risk_flags.append("Poor Sleep Quality (CNS fatigue risk)")
        
    risk_score += fatigue_modifier
            
    if not risk_flags:
        risk_flags.append("Optimal biomechanics observed")
        
    # Risk level categorization
    total_risk = min(risk_score, 100)
    if total_risk < 20:
        risk_level = "Low"
    elif total_risk < 50:
        risk_level = "Moderate"
    elif total_risk < 80:
        risk_level = "High"
    else:
        risk_level = "Critical"
        
    return {
        "filename": filename,
        "analytics": {
            "activity_analyzed": activity,
            "min_knee_angle": round(min_knee_angle, 2),
            "max_knee_extension": round(max_knee_extension, 2),
            "risk_score": total_risk,
            "risk_level": risk_level,
            "risk_flags": risk_flags,
            "surface_type": surface_type,
            "footwear": footwear,
            "rpe": rpe,
            "sleep_quality": sleep_quality,
            "frame_count": frame_count,
            "fps": fps
        }
    }
