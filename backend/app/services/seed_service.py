"""
Permanent Auto-Seed of Demo Personas for Quick Sign-In and System Benchmarks.
Runs automatically on app startup if any demo persona or benchmark athlete is missing.
"""
from app.models.user import User
from app.models.athlete import Athlete
from app.core.security import get_password_hash
import logging

logger = logging.getLogger(__name__)

DEMO_PERSONAS = [
    {
        "email": "admin@athletics.org",
        "full_name": "System Administrator",
        "role": "administrator",
        "password": "password123"
    },
    {
        "email": "coach@athletics.org",
        "full_name": "Coach Miller",
        "role": "coach",
        "password": "password123"
    },
    {
        "email": "physio@athletics.org",
        "full_name": "Dr. Sarah Lin",
        "role": "physiotherapist",
        "password": "password123"
    },
    {
        "email": "scientist@biomech.lab",
        "full_name": "Dr. Thorne",
        "role": "sports_scientist",
        "password": "password123"
    },
    {
        "email": "athlete@athletics.org",
        "full_name": "Marcus Vance",
        "role": "athlete",
        "password": "password123",
        "athlete_id": "ATH000005",
        "sport_type": "Track & Field",
        "position": "Sprinter",
        "age": 22,
        "height": 182.0,
        "weight": 76.0,
        "injury_history": "Mild right hamstring strain 6 months ago",
        "training_load": "High"
    },
    {
        "email": "erin2006y@gmail.com",
        "full_name": "Erin",
        "role": "athlete",
        "password": "password123",
        "athlete_id": "ATH000001",
        "sport_type": "General Athletics",
        "position": "Athlete",
        "age": 24,
        "height": 175.0,
        "weight": 68.0,
        "injury_history": "None",
        "training_load": "Moderate"
    }
]


def ensure_demo_personas(db):
    """Ensure that all demo personas and athletes exist with valid credentials."""
    try:
        pw_hash = get_password_hash("password123")

        for persona in DEMO_PERSONAS:
            user = db.query(User).filter(User.email == persona["email"]).first()
            if not user:
                user = User(
                    email=persona["email"],
                    password_hash=pw_hash,
                    full_name=persona["full_name"],
                    role=persona["role"],
                    is_active=True
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                logger.info(f"Created demo persona: {user.email}")
            else:
                # Update password hash if needed so quick sign-in NEVER fails
                user.password_hash = pw_hash
                user.is_active = True
                db.commit()

            # If persona is an athlete, ensure an Athlete profile exists
            if persona.get("athlete_id"):
                ath = db.query(Athlete).filter(Athlete.athlete_id == persona["athlete_id"]).first()
                if not ath:
                    ath = Athlete(
                        athlete_id=persona["athlete_id"],
                        user_id=user.id,
                        sport_type=persona.get("sport_type", "Athletics"),
                        position=persona.get("position", "Athlete"),
                        age=persona.get("age", 23),
                        height=persona.get("height", 175.0),
                        weight=persona.get("weight", 70.0),
                        injury_history=persona.get("injury_history", "None"),
                        training_load=persona.get("training_load", "Moderate")
                    )
                    db.add(ath)
                    db.commit()
                    logger.info(f"Created athlete profile: {ath.athlete_id} for {user.email}")
                elif ath.user_id != user.id:
                    ath.user_id = user.id
                    db.commit()

        # Also ensure BENCHMARK-GOLD athlete profile exists
        bench = db.query(Athlete).filter(Athlete.athlete_id == "BENCHMARK-GOLD").first()
        if not bench:
            bench = Athlete(
                athlete_id="BENCHMARK-GOLD",
                sport_type="Benchmark / Reference Standard",
                position="Gold Standard Form",
                age=24,
                height=180.0,
                weight=75.0,
                injury_history="Optimal clinical kinematics form with symmetric loading and stable alignment.",
                training_load="Reference standard"
            )
            db.add(bench)
            db.commit()
            logger.info("Created BENCHMARK-GOLD athlete profile")

    except Exception as e:
        logger.error(f"Error ensuring demo personas: {e}", exc_info=True)
        db.rollback()
