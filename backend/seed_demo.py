"""Create demo accounts for every role. Safe to run more than once.

Usage (from the backend folder, with .venv active):
    python seed_demo.py
"""
from datetime import date, timedelta

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal, init_db
from app.models.athlete import Athlete, AthleteAccess, InjuryRecord, TrainingLoadEntry
from app.models.user import Role, User

PASSWORD = "Demo@1234"
USERS = [
    ("admin@demo.com", "Demo Admin", Role.administrator),
    ("athlete@demo.com", "Demo Athlete", Role.athlete),
    ("coach@demo.com", "Demo Coach", Role.coach),
    ("physio@demo.com", "Demo Physiotherapist", Role.physiotherapist),
    ("scientist@demo.com", "Demo Sports Scientist", Role.sports_scientist),
]


def main() -> None:
    init_db()
    with SessionLocal() as db:
        by_email = {}
        for email, name, role in USERS:
            user = db.scalar(select(User).where(User.email == email))
            if user is None:
                user = User(email=email, full_name=name, role=role.value,
                            hashed_password=hash_password(PASSWORD))
                db.add(user)
                db.flush()
            by_email[email] = user

        ath_user = by_email["athlete@demo.com"]
        athlete = db.scalar(select(Athlete).where(Athlete.user_id == ath_user.id))
        if athlete is None:
            athlete = Athlete(user_id=ath_user.id, full_name="Demo Athlete", sport_type="Football",
                              position="Midfielder", age=22, height_cm=175, weight_kg=70,
                              weekly_training_load=2400)
            db.add(athlete)
            db.flush()
            db.add(InjuryRecord(athlete_id=athlete.id, injury_type="Ankle sprain", body_part="ankle",
                                injury_date=date.today() - timedelta(days=200),
                                severity="moderate", status="recovered"))
            for d in range(28):
                db.add(TrainingLoadEntry(athlete_id=athlete.id, entry_date=date.today() - timedelta(days=d),
                                         duration_min=60, rpe=6 if d > 6 else 8,
                                         load_au=60 * (6 if d > 6 else 8)))

        for email in ("coach@demo.com", "physio@demo.com", "scientist@demo.com"):
            user = by_email[email]
            exists = db.scalar(select(AthleteAccess).where(
                AthleteAccess.athlete_id == athlete.id, AthleteAccess.user_id == user.id))
            if exists is None:
                db.add(AthleteAccess(athlete_id=athlete.id, user_id=user.id, access_role=user.role))
        db.commit()

    print("Demo accounts ready (password for all: %s)" % PASSWORD)
    for email, _, role in USERS:
        print(f"  {role.value:<18} {email}")


if __name__ == "__main__":
    main()