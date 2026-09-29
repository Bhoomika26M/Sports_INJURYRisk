import cv2
import os
import uuid

try:
    import mediapipe as mp
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
except (ImportError, AttributeError):
    mp = None
    mp_pose = None
    mp_drawing = None


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

def process_video_with_mediapipe(input_path: str, output_dir: str, activity: str = "Unknown"):
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

    with mp_pose.Pose(min_detection_confidence=0.5, min_tracking_confidence=0.5) as pose:
        while cap.isOpened():
            success, image = cap.read()
            if not success:
                break

            # Convert the BGR image to RGB
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image_rgb.flags.writeable = False

            # Process the image and find poses
            results = pose.process(image_rgb)

            # Draw the pose annotation on the image
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

                # Motion Enhancement / Specific Analytics based on activity
                landmarks = results.pose_landmarks.landmark
                
                # Get coordinates for Left Hip, Left Knee, Left Ankle
                try:
                    hip = [landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].x, landmarks[mp_pose.PoseLandmark.LEFT_HIP.value].y]
                    knee = [landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].x, landmarks[mp_pose.PoseLandmark.LEFT_KNEE.value].y]
                    ankle = [landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].x, landmarks[mp_pose.PoseLandmark.LEFT_ANKLE.value].y]
                    
                    angle = calculate_angle(hip, knee, ankle)
                    if angle > 180:
                        angle = 360 - angle
                        
                    min_knee_angle = min(min_knee_angle, angle)
                    
                    # Visualize angle on video
                    cv2.putText(image_bgr, str(int(angle)), 
                           tuple(np.multiply(knee, [width, height]).astype(int)), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2, cv2.LINE_AA
                                )
                except:
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
            
    if not risk_flags:
        risk_flags.append("Optimal biomechanics observed")
        
    return {
        "filename": filename,
        "analytics": {
            "activity_analyzed": activity,
            "min_knee_angle": round(min_knee_angle, 2),
            "risk_score": min(risk_score, 100),
            "risk_flags": risk_flags,
            "frame_count": frame_count,
            "fps": fps
        }
    }
