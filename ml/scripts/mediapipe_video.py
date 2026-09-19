import cv2
import mediapipe as mp
import argparse
import os

def process_video(input_path, output_path):
    mp_pose = mp.solutions.pose
    mp_drawing = mp.solutions.drawing_utils
    mp_drawing_styles = mp.solutions.drawing_styles

    if not os.path.exists(input_path):
        print(f"Error: Input video not found at {input_path}")
        return

    cap = cv2.VideoCapture(input_path)
    
    # Get video properties for writer
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    print(f"Processing video {input_path}...")
    
    with mp_pose.Pose(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        model_complexity=1) as pose:
        
        while cap.isOpened():
            success, image = cap.read()
            if not success:
                break

            # Convert the BGR image to RGB.
            image.flags.writeable = False
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            # Process the image and get pose landmarks
            results = pose.process(image_rgb)

            # Draw the pose annotation on the image.
            image.flags.writeable = True
            
            if results.pose_landmarks:
                mp_drawing.draw_landmarks(
                    image,
                    results.pose_landmarks,
                    mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=mp_drawing_styles.get_default_pose_landmarks_style())
            
            # Write out the frame
            out.write(image)

    cap.release()
    out.release()
    print(f"Processing complete. Annotated video saved to {output_path}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Run MediaPipe Pose on a video.')
    parser.add_argument('--input', type=str, required=True, help='Path to the input video.')
    parser.add_argument('--output', type=str, required=True, help='Path to save the output video.')
    
    args = parser.parse_args()
    process_video(args.input, args.output)
