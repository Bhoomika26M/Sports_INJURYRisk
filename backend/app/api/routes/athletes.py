from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.schemas.athlete import AthleteCreate, AthleteUpdate, AthleteResponse
from app.services.athlete_service import (
    create_athlete, 
    get_athlete, 
    get_all_athletes, 
    update_athlete, 
    delete_athlete,
    get_athlete_for_user
)
from app.core.security import get_current_active_user
from app.core.dependencies import require_role
from app.models.user import User

router = APIRouter(prefix="/athletes", tags=["Athletes"])


@router.post("/", response_model=AthleteResponse, status_code=status.HTTP_201_CREATED)
def create_athlete_endpoint(
    athlete_data: AthleteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("administrator", "coach", "physiotherapist", "sports_scientist"))
):
    """
    Create a new athlete profile.
    
    Available to: administrator, coach, physiotherapist, sports_scientist
    
    - **athlete_id**: Public athlete identifier (must be unique)
    - **user_id**: Optional link to user account
    - **sport_type**: Type of sport
    - **position**: Position in sport
    - **age**: Age in years
    - **height**: Height in cm
    - **weight**: Weight in kg
    - **injury_history**: Injury history
    - **training_load**: Training load information
    """
    return create_athlete(db, athlete_data, current_user)


@router.get("/", response_model=List[AthleteResponse])
def get_athletes(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all athletes.
    
    Available to all authenticated users.
    
    - **skip**: Number of athletes to skip
    - **limit**: Maximum number of athletes to return
    """
    return get_all_athletes(db, skip=skip, limit=limit)


@router.get("/me", response_model=AthleteResponse)
def get_my_athlete_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("athlete"))
):
    """
    Get the current athlete's profile.
    
    Available to athletes only.
    """
    athlete = get_athlete_for_user(db, current_user.id)
    if not athlete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No athlete profile found for this user"
        )
    return athlete


@router.get("/{athlete_id}", response_model=AthleteResponse)
def get_athlete_endpoint(
    athlete_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific athlete by ID.
    
    Available to all authenticated users.
    """
    return get_athlete(db, athlete_id)


@router.put("/{athlete_id}", response_model=AthleteResponse)
def update_athlete_endpoint(
    athlete_id: int,
    athlete_data: AthleteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Update an athlete profile.
    
    Athletes can only update their own profile.
    Other roles can update any athlete profile.
    
    - **sport_type**: Type of sport
    - **position**: Position in sport
    - **age**: Age in years
    - **height**: Height in cm
    - **weight**: Weight in kg
    - **injury_history**: Injury history
    - **training_load**: Training load information
    """
    return update_athlete(db, athlete_id, athlete_data, current_user)


@router.delete("/{athlete_id}", response_model=AthleteResponse)
def delete_athlete_endpoint(
    athlete_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Delete an athlete profile.
    
    Available to administrators only.
    """
    return delete_athlete(db, athlete_id, current_user)
