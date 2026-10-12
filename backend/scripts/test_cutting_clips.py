import sys
import numpy as np
import cv2
from app.modules.pose.pipeline import track_persons
from app.modules.pose.analysis import clean_track
from app.modules.biomechanics.classification import classify_movement, _view

files = [
    "../data/cutting_90_degree_change_of_direction.mp4",
    "../data/cutting_t_test_agility_rtp.mp4",
    "../data/cutting_y_run_change_of_direction.mp4",
]

for filepath in files:
    print(f"\n====================\nTesting: {filepath}")
    try:
        track, diag, caveat = track_persons(filepath)
        print(f"Tracked: {len(track.xyz)} frames, fps={track.fps_eff:.1f}, caveat={caveat}")
        cleaned = clean_track(track)
        classification = classify_movement(cleaned, None, track.fps_eff)
        print(f"Classification: {classification['movement_type']}, view: {classification['camera_view']}, conf: {classification['confidence']}")
        print(f"Evidence: {classification['evidence']['movement']}")
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        import traceback
        traceback.print_exc()
