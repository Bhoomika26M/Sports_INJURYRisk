from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.athlete import AthleteProfile
from app.models.assignment import AthleteAssignment
from app.schemas.athlete import AthleteProfileCreate, AthleteProfileUpdate
from app.models.user import User

def get_profile_by_user_id(db: Session, user_id: int) -> Optional[AthleteProfile]:
    return db.query(AthleteProfile).filter(AthleteProfile.user_id == user_id).first()

def get_profile_by_id(db: Session, profile_id: int) -> Optional[AthleteProfile]:
    return db.query(AthleteProfile).filter(AthleteProfile.id == profile_id).first()

def create_profile(db: Session, user_id: int, profile_in: AthleteProfileCreate) -> AthleteProfile:
    data = profile_in.model_dump(exclude_unset=True)
    coach_id = data.pop("coach_id", None)
    physio_id = data.pop("physiotherapist_id", None)

    db_profile = AthleteProfile(
        user_id=user_id,
        **data
    )
    db.add(db_profile)
    db.commit()
    db.refresh(db_profile)

    if coach_id and coach_id > 0:
        assign_staff_to_athlete(db, athlete_id=db_profile.id, staff_id=coach_id)
    if physio_id and physio_id > 0:
        assign_staff_to_athlete(db, athlete_id=db_profile.id, staff_id=physio_id)

    db.refresh(db_profile)
    return db_profile

def update_profile(db: Session, db_profile: AthleteProfile, profile_in: AthleteProfileUpdate) -> AthleteProfile:
    update_data = profile_in.model_dump(exclude_unset=True)
    coach_id = update_data.pop("coach_id", None)
    physio_id = update_data.pop("physiotherapist_id", None)

    for field, value in update_data.items():
        setattr(db_profile, field, value)
    
    db.add(db_profile)
    db.commit()

    # Update coach assignment if specified
    if coach_id is not None:
        for a in list(db_profile.assignments):
            if a.staff and a.staff.role == "coach" and a.staff_id != coach_id:
                db.delete(a)
        if coach_id > 0:
            assign_staff_to_athlete(db, athlete_id=db_profile.id, staff_id=coach_id)
        db.commit()

    # Update physiotherapist assignment if specified
    if physio_id is not None:
        for a in list(db_profile.assignments):
            if a.staff and a.staff.role == "physiotherapist" and a.staff_id != physio_id:
                db.delete(a)
        if physio_id > 0:
            assign_staff_to_athlete(db, athlete_id=db_profile.id, staff_id=physio_id)
        db.commit()

    db.refresh(db_profile)
    return db_profile

def get_all_profiles(db: Session, skip: int = 0, limit: int = 100) -> List[AthleteProfile]:
    return db.query(AthleteProfile).offset(skip).limit(limit).all()

def get_assigned_profiles_for_staff(db: Session, staff_id: int, skip: int = 0, limit: int = 100) -> List[AthleteProfile]:
    assigned_ids = db.query(AthleteAssignment.athlete_id).filter(AthleteAssignment.staff_id == staff_id)
    return db.query(AthleteProfile).filter(
        (AthleteProfile.coach_id == staff_id) | (AthleteProfile.id.in_(assigned_ids))
    ).offset(skip).limit(limit).all()

def check_staff_assigned_to_athlete(db: Session, staff_id: int, athlete_id: int) -> bool:
    profile = db.query(AthleteProfile).filter(AthleteProfile.id == athlete_id).first()
    if profile and profile.coach_id == staff_id:
        return True
    assignment = db.query(AthleteAssignment).filter(
        AthleteAssignment.staff_id == staff_id,
        AthleteAssignment.athlete_id == athlete_id
    ).first()
    return assignment is not None

def assign_staff_to_athlete(db: Session, athlete_id: int, staff_id: int) -> AthleteAssignment:
    staff = db.query(User).filter(User.id == staff_id).first()
    profile = db.query(AthleteProfile).filter(AthleteProfile.id == athlete_id).first()
    
    if profile and staff and staff.role == "coach":
        profile.coach_id = staff_id

    existing = db.query(AthleteAssignment).filter(
        AthleteAssignment.athlete_id == athlete_id,
        AthleteAssignment.staff_id == staff_id
    ).first()
    if existing:
        db.commit()
        return existing
    assignment = AthleteAssignment(athlete_id=athlete_id, staff_id=staff_id)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment

def unassign_staff_from_athlete(db: Session, athlete_id: int, staff_id: int) -> bool:
    profile = db.query(AthleteProfile).filter(AthleteProfile.id == athlete_id).first()
    if profile and profile.coach_id == staff_id:
        profile.coach_id = None

    assignment = db.query(AthleteAssignment).filter(
        AthleteAssignment.athlete_id == athlete_id,
        AthleteAssignment.staff_id == staff_id
    ).first()
    if not assignment and (not profile or profile.coach_id != staff_id):
        db.commit()
        return False
    if assignment:
        db.delete(assignment)
    db.commit()
    return True

def get_staff_for_athlete(db: Session, athlete_id: int) -> List[User]:
    assignments = db.query(AthleteAssignment).filter(AthleteAssignment.athlete_id == athlete_id).all()
    return [a.staff for a in assignments if a.staff]

