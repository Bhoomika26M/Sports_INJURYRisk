from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.database import get_db
from app.models.athlete import Athlete
from app.schemas.athlete import AthleteCreate, AthleteUpdate, AthleteResponse
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/athletes", tags=["Athletes"])

@router.get("", response_model=List[AthleteResponse])
def get_all_athletes(db: Session = Depends(get_db)):
    return db.query(Athlete).order_by(Athlete.id.asc()).all()

@router.post("", response_model=AthleteResponse)
def create_athlete(athlete_in: AthleteCreate, db: Session = Depends(get_db)):
    existing = db.query(Athlete).filter(Athlete.athlete_code == athlete_in.athlete_code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Athlete code already exists")
    
    athlete = Athlete(
        athlete_code=athlete_in.athlete_code,
        name=athlete_in.name,
        sport_type=athlete_in.sport_type,
        position=athlete_in.position,
        age=athlete_in.age,
        height=athlete_in.height,
        weight=athlete_in.weight,
        training_load=athlete_in.training_load,
        acwr=athlete_in.acwr,
        injury_history=athlete_in.injury_history,
        physical_assessment=athlete_in.physical_assessment
    )
    db.add(athlete)
    db.commit()
    db.refresh(athlete)
    return athlete

@router.get("/{athlete_id}", response_model=AthleteResponse)
def get_athlete(athlete_id: int, db: Session = Depends(get_db)):
    athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    return athlete

@router.put("/{athlete_id}", response_model=AthleteResponse)
def update_athlete(athlete_id: int, athlete_in: AthleteUpdate, db: Session = Depends(get_db)):
    athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    
    update_data = athlete_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(athlete, key, value)
    
    db.commit()
    db.refresh(athlete)
    return athlete

@router.post("/{athlete_id}/injuries")
def add_injury_record(athlete_id: int, injury_data: Dict[str, Any], db: Session = Depends(get_db)):
    athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")
    
    current_history = list(athlete.injury_history or [])
    current_history.append(injury_data)
    athlete.injury_history = current_history
    db.commit()
    return {"message": "Injury record logged", "injury_history": athlete.injury_history}
