import os
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.athlete import Athlete
from app.models.video import VideoRecord
from app.services.auth_service import get_password_hash
from app.services.sample_generator import generate_athletic_movement_video
from app.config import SAMPLE_DIR

def seed_database(db: Session):
    # Repair the legacy synthetic seed that was incorrectly marked as a real analysis.
    if db.query(User).count() > 0:
        legacy_sample = db.query(VideoRecord).filter(
            VideoRecord.original_filename == "marcus_jump_landing.mp4",
            VideoRecord.file_path == str(SAMPLE_DIR / "marcus_jump_landing.mp4"),
        ).first()
        if legacy_sample:
            legacy_sample.title = "Synthetic Demo - Drop Jump Landing"
            legacy_sample.activity_type = "Drop Jump"
            if legacy_sample.processed_video_path == legacy_sample.file_path and legacy_sample.status == "analyzed":
                legacy_sample.status = "uploaded"
                legacy_sample.processed_video_path = None
            db.commit()
        return

    print("Seeding initial demo users, athlete profiles, and a synthetic video sample...")

    # 1. Seed Roles Users
    users_data = [
        {"email": "athlete@sportsai.com", "full_name": "Marcus Vance", "role": "athlete"},
        {"email": "coach@sportsai.com", "full_name": "Coach Roberto Martinez", "role": "coach"},
        {"email": "physio@sportsai.com", "full_name": "Dr. Sarah Jenkins (PT)", "role": "physiotherapist"},
        {"email": "scientist@sportsai.com", "full_name": "Dr. Alexei Volkov (PhD Biomechanics)", "role": "sports_scientist"},
        {"email": "admin@sportsai.com", "full_name": "System Administrator", "role": "administrator"},
    ]

    for u in users_data:
        user = User(
            email=u["email"],
            full_name=u["full_name"],
            role=u["role"],
            hashed_password=get_password_hash("password123")
        )
        db.add(user)

    db.commit()

    # 2. Seed Athletes
    athletes_data = [
        {
            "athlete_code": "ATH-101",
            "name": "Marcus Vance",
            "sport_type": "Football",
            "position": "Striker",
            "age": 24,
            "height": 185.0,
            "weight": 82.0,
            "training_load": 18.5,
            "acwr": 1.48, # High acute load!
            "injury_history": [
                {"injury_name": "Right Knee ACL Reconstruction", "body_part": "Right Knee", "year_or_date": "2024", "severity": "Surgical", "status": "Vulnerable"}
            ],
            "physical_assessment": {
                "hamstring_to_quad_ratio": 0.52, # Normative is > 0.60
                "single_leg_hop_symmetry": "82%",
                "knee_extension_deficit": "2 deg"
            }
        },
        {
            "athlete_code": "ATH-102",
            "name": "Elena Rostova",
            "sport_type": "Basketball",
            "position": "Point Guard",
            "age": 22,
            "height": 178.0,
            "weight": 68.0,
            "training_load": 14.0,
            "acwr": 1.20,
            "injury_history": [
                {"injury_name": "Lateral Ankle Sprain Grade II", "body_part": "Left Ankle", "year_or_date": "2025", "severity": "Moderate", "status": "Fully Recovered"}
            ],
            "physical_assessment": {
                "ankle_dorsiflexion_rom": "12 cm (WBLT)",
                "countermovement_jump": "48 cm"
            }
        },
        {
            "athlete_code": "ATH-103",
            "name": "David Kim",
            "sport_type": "Track & Field",
            "position": "Sprinter (100m/200m)",
            "age": 26,
            "height": 181.0,
            "weight": 77.0,
            "training_load": 16.0,
            "acwr": 1.35,
            "injury_history": [
                {"injury_name": "Biceps Femoris Strain Grade I", "body_part": "Right Hamstring", "year_or_date": "2025", "severity": "Moderate", "status": "Vulnerable"}
            ],
            "physical_assessment": {
                "nordic_strength_l": "380 N",
                "nordic_strength_r": "310 N (18% deficit)"
            }
        },
        {
            "athlete_code": "ATH-104",
            "name": "Sophia Chen",
            "sport_type": "Tennis",
            "position": "Singles",
            "age": 21,
            "height": 172.0,
            "weight": 62.0,
            "training_load": 13.0,
            "acwr": 1.10,
            "injury_history": [],
            "physical_assessment": {
                "shoulder_internal_rom": "58 deg",
                "shoulder_external_rom": "94 deg"
            }
        },
        {
            "athlete_code": "ATH-105",
            "name": "Liam O'Connor",
            "sport_type": "Rugby",
            "position": "Flanker",
            "age": 27,
            "height": 189.0,
            "weight": 104.0,
            "training_load": 17.0,
            "acwr": 1.42,
            "injury_history": [
                {"injury_name": "L4-L5 Lumbar Facet Strain", "body_part": "Lower Back", "year_or_date": "2024", "severity": "Moderate", "status": "Ongoing Rehab"}
            ],
            "physical_assessment": {
                "sit_and_reach": "+4 cm",
                "isometric_trunk_extension": "145 sec"
            }
        }
    ]

    for a in athletes_data:
        athlete = Athlete(**a)
        db.add(athlete)

    db.commit()

    # 3. Create Sample Video for Athlete 1
    sample_video_path = str(SAMPLE_DIR / "marcus_jump_landing.mp4")
    try:
        generate_athletic_movement_video(
            output_path=sample_video_path,
            movement_type="Jump Landing (High Knee Valgus)",
            num_frames=90,
            fps=30
        )
    except Exception as e:
        print(f"Could not generate initial sample video: {e}")

    video_record = VideoRecord(
        athlete_id=1,
        title="Synthetic Demo - Drop Jump Landing",
        activity_type="Drop Jump",
        original_filename="marcus_jump_landing.mp4",
        file_path=sample_video_path,
        file_size=os.path.getsize(sample_video_path) if os.path.exists(sample_video_path) else 1024,
        duration_seconds=3.0,
        fps=30.0,
        frame_count=90,
        resolution="1280x720",
        status="uploaded",
        processed_video_path=None
    )
    db.add(video_record)
    db.commit()
    db.refresh(video_record)

    # This is a self-generated visual sample only. Analysis is created only when
    # the user runs the real pose-processing pipeline on it.
    print("Database seeding completed successfully!")
