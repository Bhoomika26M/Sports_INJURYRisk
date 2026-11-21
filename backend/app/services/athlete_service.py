from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.athlete import Athlete
from app.models.user import User
from app.schemas.athlete import AthleteCreate, AthleteUpdate


def create_athlete(db: Session, athlete_data: AthleteCreate, current_user: User) -> Athlete:
    # Check if athlete_id already exists
    existing_athlete = db.query(Athlete).filter(Athlete.athlete_id == athlete_data.athlete_id).first()
    if existing_athlete:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Athlete ID already exists"
        )
    
    # If user_id is provided, verify it exists
    if athlete_data.user_id:
        user = db.query(User).filter(User.id == athlete_data.user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
    
    db_athlete = Athlete(**athlete_data.model_dump())
    db.add(db_athlete)
    db.commit()
    db.refresh(db_athlete)
    return db_athlete


def get_athlete(db: Session, athlete_id: int) -> Athlete:
    athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()
    if not athlete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found"
        )
    return athlete


def get_athlete_by_public_id(db: Session, public_id: str) -> Athlete:
    athlete = db.query(Athlete).filter(Athlete.athlete_id == public_id).first()
    if not athlete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Athlete not found"
        )
    return athlete


def get_all_athletes(db: Session, skip: int = 0, limit: int = 100, current_user: Optional[User] = None) -> List[Athlete]:
    # Privacy rule: Athletes can only see their own athlete profile
    if current_user and current_user.role == "athlete":
        own = db.query(Athlete).filter(Athlete.user_id == current_user.id).all()
        return own

    # Administrators see all athletes
    if current_user and current_user.role == "administrator":
        return db.query(Athlete).offset(skip).limit(limit).all()

    # For other roles (coach, physiotherapist, sports_scientist):
    # Only return athlete profiles for which an invite has been accepted (plus benchmark models)
    if current_user and current_user.role in ["coach", "physiotherapist", "sports_scientist"]:
        from app.models.access_invitation import AccessInvitation
        accepted_athlete_ids = [
            inv.athlete_id for inv in db.query(AccessInvitation).filter(
                AccessInvitation.professional_user_id == current_user.id,
                AccessInvitation.status == "accepted"
            ).all()
        ]
        
        # Include accepted athletes and system benchmark athletes
        return db.query(Athlete).filter(
            (Athlete.id.in_(accepted_athlete_ids)) |
            (Athlete.athlete_id == "BENCHMARK-GOLD") |
            (Athlete.user_id == None)
        ).offset(skip).limit(limit).all()

    athletes = db.query(Athlete).offset(skip).limit(limit).all()
    return athletes


def update_athlete(db: Session, athlete_id: int, athlete_data: AthleteUpdate, current_user: User) -> Athlete:
    athlete = get_athlete(db, athlete_id)
    
    update_data = athlete_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(athlete, field, value)
    
    db.commit()
    db.refresh(athlete)
    return athlete


def delete_athlete(db: Session, athlete_id: int, current_user: User) -> Athlete:
    athlete = get_athlete(db, athlete_id)
    
    # Only administrators can delete athletes
    if current_user.role != "administrator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can delete athletes"
        )
    
    db.delete(athlete)
    db.commit()
    return athlete


def get_athlete_for_user(db: Session, user_id: int) -> Optional[Athlete]:
    return db.query(Athlete).filter(Athlete.user_id == user_id).first()
