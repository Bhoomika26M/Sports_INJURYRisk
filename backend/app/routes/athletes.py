from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.athlete import Athlete
from app.schemas.athlete import AthleteCreate
from app.models.user import User
from app.utils.security import require_role


router = APIRouter(
    prefix="/athletes",
    tags=["Athletes"]
)


@router.post("/")
def create_athlete(
    athlete: AthleteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role([
            "ADMINISTRATOR",
            "COACH"
        ])
    )
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
        "athlete_id": new_athlete.id
    }


@router.get("/")
def get_athletes(
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role([
            "ADMINISTRATOR",
            "COACH",
            "PHYSIOTHERAPIST",
            "SPORTS_SCIENTIST",
            "ATHLETE"
        ])
    )
):
    athletes = db.query(Athlete).all()

    return athletes


@router.get("/{athlete_id}")
def get_athlete(
    athlete_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role([
            "ADMINISTRATOR",
            "COACH",
            "PHYSIOTHERAPIST",
            "SPORTS_SCIENTIST",
            "ATHLETE"
        ])
    )
):
    athlete = db.query(Athlete).filter(
        Athlete.id == athlete_id
    ).first()

    if not athlete:
        raise HTTPException(
            status_code=404,
            detail="Athlete not found"
        )

    return athlete


@router.put("/{athlete_id}")
def update_athlete(
    athlete_id: int,
    athlete_data: AthleteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role([
            "ADMINISTRATOR",
            "COACH",
            "PHYSIOTHERAPIST"
        ])
    )
):
    athlete = db.query(Athlete).filter(
        Athlete.id == athlete_id
    ).first()

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
        "message": "Athlete updated successfully"
    }


@router.delete("/{athlete_id}")
def delete_athlete(
    athlete_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role([
            "ADMINISTRATOR"
        ])
    )
):
    athlete = db.query(Athlete).filter(
        Athlete.id == athlete_id
    ).first()

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