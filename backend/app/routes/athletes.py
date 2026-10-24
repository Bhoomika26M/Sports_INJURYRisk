from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.models.athlete import Athlete
from app.schemas.athlete import AthleteCreate
from app.models.user import User

router = APIRouter(
    prefix="/athletes",
    tags=["Athletes"]
)


def _ensure_initial_athlete(db: Session):
    defaults = [
        {
            "athlete_id": "ATH-101",
            "sport_type": "Basketball",
            "position": "Point Guard",
            "age": 22,
            "height": 188.0,
            "weight": 84.0,
            "injury_history": "Mild left ankle sprain (2024)",
            "training_load": 82.0
        },
        {
            "athlete_id": "ATH-102",
            "sport_type": "Volleyball",
            "position": "Outside Hitter",
            "age": 24,
            "height": 194.0,
            "weight": 88.0,
            "injury_history": "Patellar tendinopathy (2023)",
            "training_load": 74.0
        },
        {
            "athlete_id": "ATH-103",
            "sport_type": "Track & Field",
            "position": "100m Sprinter",
            "age": 21,
            "height": 182.0,
            "weight": 76.0,
            "injury_history": "Grade 1 hamstring strain (2025)",
            "training_load": 88.0
        },
        {
            "athlete_id": "ATH-104",
            "sport_type": "Soccer",
            "position": "Central Midfielder",
            "age": 23,
            "height": 178.0,
            "weight": 72.0,
            "injury_history": "Lateral collateral ligament sprain",
            "training_load": 68.0
        }
    ]
    for d in defaults:
        if not db.query(Athlete).filter(Athlete.athlete_id == d["athlete_id"]).first():
            db.add(Athlete(**d))
    db.commit()


@router.post("/")
def create_athlete(
    athlete: AthleteCreate,
    db: Session = Depends(get_db)
):
    existing_athlete = db.query(Athlete).filter(
        Athlete.athlete_id == athlete.athlete_id
    ).first()

    if existing_athlete:
        raise HTTPException(
            status_code=400,
            detail="Athlete ID already exists"
        )

    new_athlete = Athlete(
        athlete_id=athlete.athlete_id,
        sport_type=athlete.sport_type,
        position=athlete.position,
        age=athlete.age,
        height=athlete.height,
        weight=athlete.weight,
        injury_history=athlete.injury_history,
        training_load=athlete.training_load
    )

    db.add(new_athlete)
    db.commit()
    db.refresh(new_athlete)

    return {
        "message": "Athlete created successfully",
        "athlete_id": new_athlete.id,
        "athlete_code": new_athlete.athlete_id
    }


@router.get("/")
def get_athletes(
    db: Session = Depends(get_db)
):
    _ensure_initial_athlete(db)
    athletes = db.query(Athlete).all()
    return athletes


@router.get("/{athlete_id}")
def get_athlete(
    athlete_id: str,
    db: Session = Depends(get_db)
):
    _ensure_initial_athlete(db)
    athlete = None
    if athlete_id.isdigit():
        athlete = db.query(Athlete).filter(Athlete.id == int(athlete_id)).first()
    if not athlete:
        athlete = db.query(Athlete).filter(Athlete.athlete_id == athlete_id).first()

    if not athlete:
        # Fallback to first athlete if exists
        athlete = db.query(Athlete).first()
        if not athlete:
            raise HTTPException(
                status_code=404,
                detail="Athlete not found"
            )

    return athlete


@router.put("/{athlete_id}")
def update_athlete(
    athlete_id: str,
    athlete_data: AthleteCreate,
    db: Session = Depends(get_db)
):
    athlete = None
    if athlete_id.isdigit():
        athlete = db.query(Athlete).filter(Athlete.id == int(athlete_id)).first()
    if not athlete:
        athlete = db.query(Athlete).filter(Athlete.athlete_id == athlete_id).first()

    if not athlete:
        raise HTTPException(
            status_code=404,
            detail="Athlete not found"
        )

    athlete.athlete_id = athlete_data.athlete_id
    athlete.sport_type = athlete_data.sport_type
    athlete.position = athlete_data.position
    athlete.age = athlete_data.age
    athlete.height = athlete_data.height
    athlete.weight = athlete_data.weight
    athlete.injury_history = athlete_data.injury_history
    athlete.training_load = athlete_data.training_load

    db.commit()
    db.refresh(athlete)

    return {
        "message": "Athlete updated successfully",
        "athlete": athlete
    }


@router.delete("/{athlete_id}")
def delete_athlete(
    athlete_id: str,
    db: Session = Depends(get_db)
):
    athlete = None
    if athlete_id.isdigit():
        athlete = db.query(Athlete).filter(Athlete.id == int(athlete_id)).first()
    if not athlete:
        athlete = db.query(Athlete).filter(Athlete.athlete_id == athlete_id).first()

    if not athlete:
        raise HTTPException(
            status_code=404,
            detail="Athlete not found"
        )

    db.delete(athlete)
    db.commit()

    return {
        "message": "Athlete deleted successfully"
    }
