import os
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.athlete import Athlete
from app.models.video import VideoRecord
from app.models.biomechanics import BiomechanicalAnalysis
from app.models.injury_risk import InjuryRiskAssessment
from app.services.auth_service import get_password_hash
from app.services.sample_generator import generate_athletic_movement_video
from app.config import SAMPLE_DIR, UPLOAD_DIR

def seed_database(db: Session):
    # Check if already seeded
    if db.query(User).count() > 0:
        return

    print("Seeding initial database with users, athletes, and biomechanics assessments...")

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
        title="Marcus Vance - Drop Jump & Deceleration Landing",
        activity_type="Landing",
        original_filename="marcus_jump_landing.mp4",
        file_path=sample_video_path,
        file_size=os.path.getsize(sample_video_path) if os.path.exists(sample_video_path) else 1024,
        duration_seconds=3.0,
        fps=30.0,
        frame_count=90,
        resolution="1280x720",
        status="analyzed",
        processed_video_path=sample_video_path
    )
    db.add(video_record)
    db.commit()
    db.refresh(video_record)

    # 4. Generate Precomputed Realistic Time-Series for Athlete 1
    time_series = []
    for f in range(90):
        t = round(f / 30.0, 3)
        # Simulate landing spike around frames 30-55
        if 25 <= f <= 60:
            valgus_l = 14.8 + (f % 5) * 0.4
            valgus_r = 17.4 + (f % 4) * 0.5 # High valgus spike!
            knee_l = 105.0 - (f - 25) * 1.5
            knee_r = 98.0 - (f - 25) * 1.8
            trunk_lat = 11.5 + (f % 3) * 0.6
            asym = 19.5
        else:
            valgus_l = 5.2 + (f % 3) * 0.3
            valgus_r = 6.1 + (f % 4) * 0.2
            knee_l = 162.0
            knee_r = 160.0
            trunk_lat = 3.2
            asym = 7.5

        time_series.append({
            "frame": f,
            "time": t,
            "detected": True,
            "knee_angle_l": round(knee_l, 1),
            "knee_angle_r": round(knee_r, 1),
            "knee_valgus_l": round(valgus_l, 1),
            "knee_valgus_r": round(valgus_r, 1),
            "hip_angle_l": 155.0,
            "hip_angle_r": 152.0,
            "elbow_angle_l": 135.0,
            "elbow_angle_r": 138.0,
            "trunk_lateral_lean": round(trunk_lat, 1),
            "trunk_forward_lean": 14.0,
            "pelvic_drop": 3.4,
            "bilateral_asymmetry": round(asym, 1),
            "anomaly_score": 0.85 if 25 <= f <= 60 else 0.12
        })

    # Save BiomechanicalAnalysis
    analysis = BiomechanicalAnalysis(
        video_id=video_record.id,
        athlete_id=1,
        total_frames_analyzed=90,
        mean_fps=30.0,
        knee_valgus_left_max=16.4,
        knee_valgus_right_max=18.9,
        knee_valgus_avg=9.8,
        hip_stability_score=68.0,
        pelvic_drop_deg=3.4,
        trunk_lean_lateral_max=12.7,
        trunk_lean_forward_max=16.2,
        landing_mechanics_score=46.0,
        initial_contact_knee_flexion_deg=152.0,
        stride_length_est=1.55,
        joint_alignment_score=42.0,
        balance_stability_index=58.0,
        movement_symmetry_score=78.5,
        range_of_motion_score=82.0,
        force_impact_estimation_g=3.8,
        time_series_data=time_series
    )
    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    # Save InjuryRiskAssessment
    risk_assessment = InjuryRiskAssessment(
        video_id=video_record.id,
        athlete_id=1,
        analysis_id=analysis.id,
        overall_injury_risk_score=76.8,
        risk_category="High Risk",
        biomechanical_deviation_score=78.5,
        historical_injury_factor_score=75.0,
        movement_asymmetry_score=75.3,
        training_load_indicator_score=85.0,
        fatigue_indicator_score=62.0,
        movement_quality_score=52.0,
        biomechanical_efficiency_score=58.0,
        fatigue_risk_score=62.0,
        overall_athlete_health_score=42.0,
        category_risks={
            "acl_risk": {
                "category_name": "ACL Injury Risk",
                "risk_score": 88.5,
                "probability": 0.89,
                "risk_level": "Critical Risk",
                "primary_factors": [
                    "Dynamic Knee Valgus 18.9° > 15° clinical threshold",
                    "Stiff Ground Impact Landing (< 30° flexion cushion)",
                    "Previous Right ACL Surgical history with residual deficit"
                ],
                "description": "High anterior cruciate ligament strain generated during plant-and-cut or jump landing."
            },
            "hamstring_risk": {
                "category_name": "Hamstring Injury Risk",
                "risk_score": 54.0,
                "probability": 0.54,
                "risk_level": "Moderate Risk",
                "primary_factors": ["Pelvic obliquity 3.4° under deceleration", "High ACWR 1.48"],
                "description": "Risk of eccentric myofibrillar strain during rapid terminal swing or deceleration."
            },
            "ankle_sprain_risk": {
                "category_name": "Ankle Sprain Risk",
                "risk_score": 42.0,
                "probability": 0.42,
                "risk_level": "Moderate Risk",
                "primary_factors": ["High Ground Reaction Force Impact (3.8G)"],
                "description": "Subtalar lateral inversion shear during high impact contact."
            },
            "shoulder_risk": {
                "category_name": "Shoulder Injury Risk",
                "risk_score": 18.0,
                "probability": 0.18,
                "risk_level": "Low Risk",
                "primary_factors": ["Shoulder within safe athletic range"],
                "description": "Minimal upper extremity loading."
            },
            "lower_back_risk": {
                "category_name": "Lower Back Injury Risk",
                "risk_score": 68.0,
                "probability": 0.68,
                "risk_level": "High Risk",
                "primary_factors": ["Lateral Trunk Lean 12.7°", "Compensatory spinal shear"],
                "description": "Lumbopelvic shear stress and core anti-rotation breakdown under dynamic load."
            },
            "overuse_risk": {
                "category_name": "Overuse Injury Risk",
                "risk_score": 78.0,
                "probability": 0.78,
                "risk_level": "High Risk",
                "primary_factors": ["ACWR 1.48 in danger zone", "18.5 weekly training hours"],
                "description": "Microtrauma accumulation exceeding tissue remodeling rate due to training load spikes."
            }
        },
        anomalies_detected=[
            {
                "frame_index": 38,
                "timestamp_sec": 1.27,
                "anomaly_type": "Severe Dynamic Knee Valgus (Right)",
                "severity": "Critical",
                "metric_value": 18.9,
                "threshold_value": 15.0,
                "description": "Dynamic valgus collapse of 18.9° observed. High risk of ACL and MCL strain during loading phase."
            },
            {
                "frame_index": 42,
                "timestamp_sec": 1.40,
                "anomaly_type": "Excessive Lateral Trunk Lean",
                "severity": "High",
                "metric_value": 12.7,
                "threshold_value": 12.0,
                "description": "Trunk tilted 12.7° from vertical. Induces compensatory spinal shear and knee abduction torque."
            },
            {
                "frame_index": 45,
                "timestamp_sec": 1.50,
                "anomaly_type": "Severe Bilateral Kinematic Asymmetry",
                "severity": "Medium",
                "metric_value": 21.5,
                "threshold_value": 20.0,
                "description": "Limb movement discrepancy of 21.5%. Uneven load distribution increases unilateral injury predisposition."
            }
        ],
        corrective_recommendations={
            "exercises": [
                {
                    "name": "Banded Clamshells & Monster Walks",
                    "target_area": "Gluteus Medius & Hip External Rotators",
                    "sets": "3 sets",
                    "reps": "15 reps / 20 steps",
                    "frequency": "4x / week",
                    "difficulty": "Intermediate",
                    "equipment": "Resistance Band",
                    "coaching_cues": [
                        "Keep pelvis neutral without backward rotation",
                        "Drive knee outward against band tension to activate gluteus medius",
                        "Do not let knees collapse inward during walking strides"
                    ]
                },
                {
                    "name": "Drop Jump Soft-Landing Progression",
                    "target_area": "Eccentric Quad Control & Knee Deceleration",
                    "sets": "3 sets",
                    "reps": "6 reps",
                    "frequency": "3x / week",
                    "difficulty": "Advanced",
                    "equipment": "30cm Plyo Box",
                    "coaching_cues": [
                        "Land toe-to-heel quietly ('like a ninja')",
                        "Achieve at least 60° knee flexion upon ground contact",
                        "Keep knees directly tracking over 2nd toe, preventing valgus inward snap"
                    ]
                },
                {
                    "name": "Half-Kneeling Pallof Press with Overhead Raise",
                    "target_area": "Core Anti-Rotation & Lumbopelvic Lateral Stabilizers",
                    "sets": "3 sets",
                    "reps": "10 reps each side",
                    "frequency": "3x / week",
                    "difficulty": "Intermediate",
                    "equipment": "Cable Machine or Resistance Band",
                    "coaching_cues": [
                        "Keep ribcage pulled down and pelvis squared forward",
                        "Resist rotational pull of cable without leaning laterally",
                        "Exhale firmly through each repetition"
                    ]
                }
            ],
            "mobility_suggestions": [
                "Ankle dorsiflexion mobility drill (knee-to-wall test > 10cm required to reduce compensatory knee collapse).",
                "Thoracic spine extension foam roller mobilizing and 90/90 hip flow."
            ],
            "strengthening_plan": [
                "Targeted Gluteus Medius / Minimus isometric holds and single-leg Romanian deadlifts (RDL).",
                "Suitcase carries and side plank with leg elevation."
            ],
            "recovery_planning": [
                "Schedule 48-hour deload from high-velocity cutting, sprinting, and plyometric drills.",
                "Implement 20-minute post-session contrast water therapy (cold plunge 10°C / hot shower) or pneumatic compression boots.",
                "Ensure target sleep duration minimum 8.5 hours with sleep hygiene protocol to accelerate collagen synthesis."
            ],
            "training_modifications": [
                "Decrease high-intensity deceleration volume by 25% until valgus angles stabilize below 10°.",
                "Cap weekly training load to lower Acute:Chronic Workload Ratio back into the 0.9 - 1.2 optimal corridor.",
                "Add 15 minutes of pre-activation neuromuscular warm-up (FIFA 11+ inspired protocol) prior to every team drill."
            ]
        }
    )
    db.add(risk_assessment)
    db.commit()

    print("Database seeding completed successfully!")
