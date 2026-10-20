from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.database import get_db
from app.schemas.athlete import AthleteCreate, AthleteUpdate, AthleteResponse
from app.schemas.history import AthleteHistoryResponse, HistoryEntry
from app.services.athlete_service import (
    create_athlete, 
    get_athlete, 
    get_all_athletes, 
    update_athlete, 
    delete_athlete,
    get_athlete_for_user
)
from app.services import baseline_service
from app.services.video_service import VideoService
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
    athlete = get_athlete(db, athlete_id)
    
    # IDOR protection: Athletes can only view their own profile
    if current_user.role == "athlete" and athlete.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own profile"
        )
    
    return athlete


@router.get("/{athlete_id}/history", response_model=AthleteHistoryResponse)
def get_athlete_history_endpoint(
    athlete_id: int,
    activity: Optional[str] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get an athlete's analysis history and risk trends.

    Returns every completed analysis for the athlete in chronological order,
    each with its recorded risk score, trended metrics, and the comparison that
    was made against the athlete's rolling baseline at the time it completed.

    - **activity**: optional filter (e.g. `squat`, `jump`, `running`)
    - **limit**: maximum number of entries to return (oldest first)

    Available to all authenticated users; athletes may only read their own.
    """
    # Reuse the shared athlete-access check so IDOR rules stay in one place.
    VideoService.check_athlete_access(current_user, athlete_id, db)

    # Clamp the page size rather than trusting the client blindly.
    limit = max(1, min(limit, 500))

    rows = baseline_service.get_athlete_history(
        db, athlete_id, activity=activity, limit=limit
    )
    athlete = baseline_service.resolve_athlete(db, athlete_id)
    trends = baseline_service.summarize_trends(rows)

    return AthleteHistoryResponse(
        athlete_id=athlete_id,
        athlete_public_id=(athlete.athlete_id if athlete else None),
        total_analyses=len(rows),
        trends=trends,
        entries=[HistoryEntry.model_validate(row) for row in rows],
    )


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
    athlete = get_athlete(db, athlete_id)
    
    # IDOR protection: Athletes can only update their own profile
    if current_user.role == "athlete" and athlete.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own profile"
        )
    
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
