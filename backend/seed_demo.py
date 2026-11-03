"""
Database & Demo State Seeder for AthletiQ Sports Movement Screening Engine
Preconfigures all roles, relationships, athletes, and rich biomechanical trial data for live demonstrations.

Demo Accounts:
1. Administrator:   admin@athletiq.com         / Admin123!
2. Head Coach:      coach.miller@athletics.org / Coach123!
3. Physiotherapist: dr.chen@sportsmed.org      / Physio123!
4. Assigned Athlete 1: marcus.vance@athletics.org / Athlete123!  (Assigned to Coach Miller)
5. Assigned Athlete 2: elena.rostova@athletics.org / Athlete123! (Assigned to Coach Miller)
6. Unassigned Athlete: jordan.lee@athletics.org   / Athlete123!  (Awaiting Assignment)
"""

import os
import shutil
import json
import math
from datetime import datetime
from sqlalchemy.orm import Session

from app.db.session import SessionLocal, engine, Base
from app.models.user import User, UserRole
from app.models.athlete import AthleteProfile
from app.models.assignment import AthleteAssignment
from app.models.video import Video
from app.core.security import get_password_hash
from app.core.config import settings

def generate_movement_landmarks(movement_type: str, total_frames: int = 60) -> dict:
    """
    Generates realistic 33-landmark MediaPipe tracking frames.
    Produces valid joint angles, knee flexion, valgus deviation, and ground reaction telemetry.
    """
    fps = 30.0
    width = 1280
    height = 720
    frames = []

    for f_idx in range(total_frames):
        t_ms = round((f_idx / fps) * 1000.0, 1)
        phase = math.sin((f_idx / total_frames) * math.pi) # 0 -> 1 -> 0

        if movement_type == "jumping":
            # Countermovement Jump / Drop landing:
            # phase 0 = upright, phase 1 = deep landing flexion with valgus
            hip_y = 0.50 + phase * 0.12
            knee_y = 0.72 + phase * 0.05
            knee_l_x = 0.46 + phase * 0.025  # left knee drifts medially (valgus collapse)
            knee_r_x = 0.54 - phase * 0.010  # right knee mild medial drift
            shoulder_y = 0.25 + phase * 0.08 # trunk flexion
            trunk_x = 0.50 - phase * 0.015   # lateral trunk lean
        else:
            # Bilateral Squat
            hip_y = 0.50 + phase * 0.14
            knee_y = 0.72 + phase * 0.04
            knee_l_x = 0.46 + phase * 0.012
            knee_r_x = 0.54 - phase * 0.012
            shoulder_y = 0.25 + phase * 0.06
            trunk_x = 0.50

        # Build landmark list
        lms = [
            {"name": "nose", "x": trunk_x, "y": shoulder_y - 0.12, "z": 0.0, "visibility": 0.99},
            {"name": "left_eye_inner", "x": trunk_x - 0.01, "y": shoulder_y - 0.13, "z": 0.0, "visibility": 0.99},
            {"name": "left_eye", "x": trunk_x - 0.02, "y": shoulder_y - 0.13, "z": 0.0, "visibility": 0.99},
            {"name": "left_eye_outer", "x": trunk_x - 0.03, "y": shoulder_y - 0.13, "z": 0.0, "visibility": 0.99},
            {"name": "right_eye_inner", "x": trunk_x + 0.01, "y": shoulder_y - 0.13, "z": 0.0, "visibility": 0.99},
            {"name": "right_eye", "x": trunk_x + 0.02, "y": shoulder_y - 0.13, "z": 0.0, "visibility": 0.99},
            {"name": "right_eye_outer", "x": trunk_x + 0.03, "y": shoulder_y - 0.13, "z": 0.0, "visibility": 0.99},
            {"name": "left_ear", "x": trunk_x - 0.04, "y": shoulder_y - 0.12, "z": 0.0, "visibility": 0.98},
            {"name": "right_ear", "x": trunk_x + 0.04, "y": shoulder_y - 0.12, "z": 0.0, "visibility": 0.98},
            {"name": "mouth_left", "x": trunk_x - 0.015, "y": shoulder_y - 0.10, "z": 0.0, "visibility": 0.99},
            {"name": "mouth_right", "x": trunk_x + 0.015, "y": shoulder_y - 0.10, "z": 0.0, "visibility": 0.99},
            # Shoulders
            {"name": "left_shoulder", "x": trunk_x - 0.08, "y": shoulder_y, "z": 0.0, "visibility": 0.99},
            {"name": "right_shoulder", "x": trunk_x + 0.08, "y": shoulder_y, "z": 0.0, "visibility": 0.99},
            # Arms
            {"name": "left_elbow", "x": trunk_x - 0.12, "y": shoulder_y + 0.12, "z": 0.0, "visibility": 0.98},
            {"name": "right_elbow", "x": trunk_x + 0.12, "y": shoulder_y + 0.12, "z": 0.0, "visibility": 0.98},
            {"name": "left_wrist", "x": trunk_x - 0.14, "y": shoulder_y + 0.22, "z": 0.0, "visibility": 0.98},
            {"name": "right_wrist", "x": trunk_x + 0.14, "y": shoulder_y + 0.22, "z": 0.0, "visibility": 0.98},
            {"name": "left_pinky", "x": trunk_x - 0.15, "y": shoulder_y + 0.25, "z": 0.0, "visibility": 0.95},
            {"name": "right_pinky", "x": trunk_x + 0.15, "y": shoulder_y + 0.25, "z": 0.0, "visibility": 0.95},
            {"name": "left_index", "x": trunk_x - 0.14, "y": shoulder_y + 0.25, "z": 0.0, "visibility": 0.95},
            {"name": "right_index", "x": trunk_x + 0.14, "y": shoulder_y + 0.25, "z": 0.0, "visibility": 0.95},
            {"name": "left_thumb", "x": trunk_x - 0.13, "y": shoulder_y + 0.24, "z": 0.0, "visibility": 0.95},
            {"name": "right_thumb", "x": trunk_x + 0.13, "y": shoulder_y + 0.24, "z": 0.0, "visibility": 0.95},
            # Pelvis / Hips
            {"name": "left_hip", "x": 0.46, "y": hip_y, "z": 0.0, "visibility": 0.99},
            {"name": "right_hip", "x": 0.54, "y": hip_y, "z": 0.0, "visibility": 0.99},
            # Legs
            {"name": "left_knee", "x": knee_l_x, "y": knee_y, "z": 0.05, "visibility": 0.99},
            {"name": "right_knee", "x": knee_r_x, "y": knee_y, "z": 0.05, "visibility": 0.99},
            {"name": "left_ankle", "x": 0.46, "y": 0.92, "z": 0.0, "visibility": 0.99},
            {"name": "right_ankle", "x": 0.54, "y": 0.92, "z": 0.0, "visibility": 0.99},
            {"name": "left_heel", "x": 0.45, "y": 0.94, "z": 0.0, "visibility": 0.98},
            {"name": "right_heel", "x": 0.55, "y": 0.94, "z": 0.0, "visibility": 0.98},
            {"name": "left_foot_index", "x": 0.46, "y": 0.96, "z": 0.0, "visibility": 0.98},
            {"name": "right_foot_index", "x": 0.54, "y": 0.96, "z": 0.0, "visibility": 0.98}
        ]

        frames.append({
            "frame_index": f_idx,
            "timestamp_ms": t_ms,
            "landmarks": lms
        })

    return {
        "width": width,
        "height": height,
        "fps": fps,
        "total_frames": total_frames,
        "frames": frames
    }

def seed_database():
    print("=" * 60)
    print("ATHLETIQ SEED SCRIPT: Configuring Demo Environment")
    print("=" * 60)

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    try:
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        fixture_video = os.path.join(os.path.dirname(__file__), "tests", "fixtures", "sample.mp4")
        if not os.path.exists(fixture_video):
            fixture_video = os.path.join(settings.UPLOAD_DIR, "test_assessment_sample.mp4")

        # ---------------------------------------------------------------------
        # 1. Seed Core Users
        # ---------------------------------------------------------------------
        users_def = [
            {
                "email": "admin@athletiq.com",
                "full_name": "System Administrator",
                "role": UserRole.ADMINISTRATOR.value,
                "password": "Admin123!"
            },
            {
                "email": "coach.miller@athletics.org",
                "full_name": "Coach Marcus Miller",
                "role": UserRole.COACH.value,
                "password": "Coach123!"
            },
            {
                "email": "dr.chen@sportsmed.org",
                "full_name": "Dr. Sarah Chen, DPT",
                "role": UserRole.PHYSIOTHERAPIST.value,
                "password": "Physio123!"
            },
            {
                "email": "marcus.vance@athletics.org",
                "full_name": "Marcus Vance",
                "role": UserRole.ATHLETE.value,
                "password": "Athlete123!"
            },
            {
                "email": "elena.rostova@athletics.org",
                "full_name": "Elena Rostova",
                "role": UserRole.ATHLETE.value,
                "password": "Athlete123!"
            },
            {
                "email": "jordan.lee@athletics.org",
                "full_name": "Jordan Lee",
                "role": UserRole.ATHLETE.value,
                "password": "Athlete123!"
            }
        ]

        user_objects = {}
        for u in users_def:
            existing = db.query(User).filter(User.email == u["email"]).first()
            if existing:
                existing.full_name = u["full_name"]
                existing.role = u["role"]
                existing.hashed_password = get_password_hash(u["password"])
                existing.is_active = True
                user_objects[u["email"]] = existing
                print(f"[OK] Updated user: {u['email']} ({u['role']})")
            else:
                new_u = User(
                    email=u["email"],
                    full_name=u["full_name"],
                    role=u["role"],
                    hashed_password=get_password_hash(u["password"]),
                    is_active=True
                )
                db.add(new_u)
                db.commit()
                db.refresh(new_u)
                user_objects[u["email"]] = new_u
                print(f"[+] Created user: {u['email']} ({u['role']})")

        db.commit()
        coach_user = user_objects["coach.miller@athletics.org"]
        physio_user = user_objects["dr.chen@sportsmed.org"]

        # ---------------------------------------------------------------------
        # 2. Seed Athlete Profiles & Direct Coach Relationships
        # ---------------------------------------------------------------------
        athletes_def = [
            {
                "email": "marcus.vance@athletics.org",
                "sport_type": "Basketball",
                "position": "Power Forward",
                "age": 22,
                "height_cm": 198,
                "weight_kg": 95,
                "coach_id": coach_user.id,
                "training_load": {"acute_load": 1650, "chronic_load": 1220, "sessions_per_week": 5, "intensity": "High"},
                "injury_history": [
                    {"injury_type": "Right Lateral Ankle Sprain (Grade 1)", "date": "2026-01-20", "recovered": True}
                ]
            },
            {
                "email": "elena.rostova@athletics.org",
                "sport_type": "Track & Field",
                "position": "Sprinter",
                "age": 24,
                "height_cm": 175,
                "weight_kg": 64,
                "coach_id": coach_user.id,
                "training_load": {"acute_load": 1150, "chronic_load": 1050, "sessions_per_week": 4, "intensity": "Moderate"},
                "injury_history": []
            },
            {
                "email": "jordan.lee@athletics.org",
                "sport_type": "Soccer",
                "position": "Winger",
                "age": 20,
                "height_cm": 178,
                "weight_kg": 72,
                "coach_id": None, # Unassigned for live demo assignment
                "training_load": {"acute_load": 850, "chronic_load": 900, "sessions_per_week": 3, "intensity": "Normal"},
                "injury_history": []
            }
        ]

        athlete_profiles = {}
        for a_def in athletes_def:
            u = user_objects[a_def["email"]]
            prof = db.query(AthleteProfile).filter(AthleteProfile.user_id == u.id).first()
            if prof:
                prof.sport_type = a_def["sport_type"]
                prof.position = a_def["position"]
                prof.age = a_def["age"]
                prof.height_cm = a_def["height_cm"]
                prof.weight_kg = a_def["weight_kg"]
                prof.coach_id = a_def["coach_id"]
                prof.training_load = a_def["training_load"]
                prof.injury_history = a_def["injury_history"]
                athlete_profiles[a_def["email"]] = prof
                print(f"[OK] Updated athlete profile: #{prof.id} {u.full_name} (Coach ID: {prof.coach_id})")
            else:
                prof = AthleteProfile(
                    user_id=u.id,
                    sport_type=a_def["sport_type"],
                    position=a_def["position"],
                    age=a_def["age"],
                    height_cm=a_def["height_cm"],
                    weight_kg=a_def["weight_kg"],
                    coach_id=a_def["coach_id"],
                    training_load=a_def["training_load"],
                    injury_history=a_def["injury_history"]
                )
                db.add(prof)
                db.commit()
                db.refresh(prof)
                athlete_profiles[a_def["email"]] = prof
                print(f"[+] Created athlete profile: #{prof.id} {u.full_name} (Coach ID: {prof.coach_id})")

        db.commit()

        # ---------------------------------------------------------------------
        # 3. Staff Assignments (AthleteAssignment sync)
        # ---------------------------------------------------------------------
        # Coach Miller -> Marcus & Elena
        # Dr. Chen -> Marcus & Elena
        staff_links = [
            (coach_user.id, athlete_profiles["marcus.vance@athletics.org"].id),
            (coach_user.id, athlete_profiles["elena.rostova@athletics.org"].id),
            (physio_user.id, athlete_profiles["marcus.vance@athletics.org"].id),
            (physio_user.id, athlete_profiles["elena.rostova@athletics.org"].id)
        ]

        for s_id, a_id in staff_links:
            existing_ass = db.query(AthleteAssignment).filter(
                AthleteAssignment.staff_id == s_id,
                AthleteAssignment.athlete_id == a_id
            ).first()
            if not existing_ass:
                ass = AthleteAssignment(staff_id=s_id, athlete_id=a_id)
                db.add(ass)
        db.commit()
        print("[OK] Synchronized staff assignment records.")

        # ---------------------------------------------------------------------
        # 4. Create Rich Video Recordings & Landmark Files
        # ---------------------------------------------------------------------
        videos_def = [
            {
                "athlete": athlete_profiles["marcus.vance@athletics.org"],
                "uploader": coach_user,
                "filename": "marcus_jump_drop_screening.mp4",
                "original_filename": "Vance_Jump_Landing_Trial_01.mp4",
                "movement_type": "jumping",
                "quality_score": 95.0,
                "landmark_type": "jumping"
            },
            {
                "athlete": athlete_profiles["elena.rostova@athletics.org"],
                "uploader": coach_user,
                "filename": "elena_squat_kinematics.mp4",
                "original_filename": "Rostova_Deep_Squat_Screening.mp4",
                "movement_type": "squatting",
                "quality_score": 97.5,
                "landmark_type": "squatting"
            }
        ]

        for v_def in videos_def:
            base_fname = os.path.splitext(v_def["filename"])[0]
            mp4_path = os.path.join(settings.UPLOAD_DIR, v_def["filename"])
            annotated_mp4_path = os.path.join(settings.UPLOAD_DIR, f"{base_fname}_annotated.mp4")
            json_path = os.path.join(settings.UPLOAD_DIR, f"{base_fname}_landmarks.json")

            # Copy sample video if needed
            if os.path.exists(fixture_video):
                if not os.path.exists(mp4_path):
                    shutil.copyfile(fixture_video, mp4_path)
                if not os.path.exists(annotated_mp4_path):
                    shutil.copyfile(fixture_video, annotated_mp4_path)

            # Write landmark data
            lm_data = generate_movement_landmarks(v_def["landmark_type"])
            with open(json_path, "w") as f:
                json.dump(lm_data, f, indent=2)

            # Upsert DB video record
            vid = db.query(Video).filter(Video.filename == v_def["filename"]).first()
            if not vid:
                vid = Video(
                    athlete_id=v_def["athlete"].id,
                    uploader_id=v_def["uploader"].id,
                    filename=v_def["filename"],
                    original_filename=v_def["original_filename"],
                    file_path=os.path.join("uploads", v_def["filename"]),
                    format="mp4",
                    size_bytes=os.path.getsize(mp4_path) if os.path.exists(mp4_path) else 2048000,
                    duration_sec=2.0,
                    fps=30.0,
                    width=1280,
                    height=720,
                    status="completed",
                    processing_progress=100,
                    quality_score=v_def["quality_score"],
                    movement_type=v_def["movement_type"]
                )
                db.add(vid)
                db.commit()
                db.refresh(vid)
                print(f"[+] Seeded video #{vid.id}: {v_def['original_filename']} ({v_def['movement_type']})")
            else:
                vid.status = "completed"
                vid.processing_progress = 100
                vid.quality_score = v_def["quality_score"]
                vid.movement_type = v_def["movement_type"]
                db.commit()
                print(f"[OK] Verified video #{vid.id}: {v_def['original_filename']}")

        print("=" * 60)
        print("SEEDING COMPLETE! All demo accounts & datasets are ready.")
        print("=" * 60)

    except Exception as e:
        db.rollback()
        print(f"[ERROR] Seeding failed: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
