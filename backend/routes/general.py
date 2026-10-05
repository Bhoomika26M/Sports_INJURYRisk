from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database.database import SessionLocal
from models.athlete import Athlete
from models.user import User
from schemas.athlete import AthleteCreate
from schemas.user import UserCreate
from services.security import hash_password, verify_password, create_access_token
from schemas.login import LoginRequest
from services.auth import get_current_user, require_role

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/")
def home():
    return {"message": "Sports Injury Risk Backend is running!"}


@router.post("/athletes")
def create_athlete(athlete: AthleteCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_role("coach"))):
    new_athlete = Athlete(
        name=athlete.name,
        age=athlete.age,
        gender=athlete.gender,
        sport=athlete.sport
    )

    db.add(new_athlete)
    db.commit()
    db.refresh(new_athlete)

    return new_athlete

@router.get("/athletes")
def get_athletes(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    athletes = db.query(Athlete).all()
    return athletes

@router.get("/athletes/{athlete_id}")
def get_athlete(athlete_id: int, db: Session = Depends(get_db)):
    athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()

    if athlete is None:
        return {"message": "Athlete not found"}

    return athlete

@router.put("/athletes/{athlete_id}")
def update_athlete(
    athlete_id: int,
    athlete_data: AthleteCreate,
    db: Session = Depends(get_db)
):
    athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()

    if athlete is None:
        return {"message": "Athlete not found"}

    athlete.name = athlete_data.name
    athlete.age = athlete_data.age
    athlete.gender = athlete_data.gender
    athlete.sport = athlete_data.sport

    db.commit()
    db.refresh(athlete)

    return athlete

@router.delete("/athletes/{athlete_id}")
def delete_athlete(
    athlete_id: int,
    db: Session = Depends(get_db)
):
    athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()

    if athlete is None:
        return {"message": "Athlete not found"}

    db.delete(athlete)
    db.commit()

    return {"message": "Athlete deleted successfully"}

@router.post("/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user.email).first()

    if existing_user:
        return {"message": "Email already registered"}

    new_user = User(
        name=user.name,
        email=user.email,
        password=hash_password(user.password),
        role=user.role
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return {
        "message": "User registered successfully",
        "user_id": new_user.id
    }

@router.post("/login")
def login_user(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == login_data.email).first()

    if user is None:
        return {"message": "Invalid email or password"}

    if not verify_password(login_data.password, user.password):
        return {"message": "Invalid email or password"}

    access_token = create_access_token(
        user_id=user.id,
        role=user.role
)

    return {
        "message": "Login successful",
        "access_token": access_token,
        "user_id": user.id,
        "name": user.name,
        "role": user.role
    }