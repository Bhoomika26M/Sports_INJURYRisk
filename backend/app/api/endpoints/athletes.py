from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.schemas.athlete import AthleteProfileCreate, AthleteProfileUpdate, AthleteProfileResponse
from app.services import athlete_service, user_service
from app.api.deps import get_current_active_user, RoleChecker

router = APIRouter()

allow_staff = RoleChecker(["coach", "physiotherapist", "sports_scientist", "administrator"])
allow_admin = RoleChecker(["administrator"])

@router.get("/me", response_model=AthleteProfileResponse)
def read_profile_me(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get current user's athlete profile."""
    if current_user.role != "athlete":
        raise HTTPException(status_code=403, detail="Only athletes have a personal athlete profile")
    
    profile = athlete_service.get_profile_by_user_id(db, user_id=current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile

@router.post("/me", response_model=AthleteProfileResponse)
def create_profile_me(
    *,
    db: Session = Depends(get_db),
    profile_in: AthleteProfileCreate,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Create new athlete profile for current user."""
    if current_user.role != "athlete":
        raise HTTPException(status_code=403, detail="Only athletes can create a personal athlete profile")
        
    profile = athlete_service.get_profile_by_user_id(db, user_id=current_user.id)
    if profile:
        raise HTTPException(status_code=400, detail="Profile already exists")
    
    profile = athlete_service.create_profile(db, user_id=current_user.id, profile_in=profile_in)
    return profile

@router.put("/me", response_model=AthleteProfileResponse)
def update_profile_me(
    *,
    db: Session = Depends(get_db),
    profile_in: AthleteProfileUpdate,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Update current user's athlete profile."""
    if current_user.role != "athlete":
        raise HTTPException(status_code=403, detail="Only athletes can update a personal athlete profile")
        
    profile = athlete_service.get_profile_by_user_id(db, user_id=current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    
    profile = athlete_service.update_profile(db, db_profile=profile, profile_in=profile_in)
    return profile


@router.get("/", response_model=List[AthleteProfileResponse])
def read_athletes(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    filter_by: Optional[str] = None,
    current_user: User = Depends(allow_staff)
) -> Any:
    """
    Retrieve athletes. 
    - Administrators see all athletes.
    - Staff members can view their assigned squad, or browse all athletes (filter_by='all') to add them to their squad.
    """
    if current_user.role == "administrator" or filter_by == "all":
        return athlete_service.get_all_profiles(db, skip=skip, limit=limit)
    else:
        assigned = athlete_service.get_assigned_profiles_for_staff(db, staff_id=current_user.id, skip=skip, limit=limit)
        # If coach/staff has no assigned athletes yet, return all athletes so they can build their squad
        if not assigned:
            return athlete_service.get_all_profiles(db, skip=skip, limit=limit)
        return assigned

@router.get("/{athlete_id}", response_model=AthleteProfileResponse)
def read_athlete_by_id(
    athlete_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(allow_staff)
) -> Any:
    """
    Get a specific athlete by profile ID.
    Enforces authorization rules (admin can view any, staff can only view assigned athletes).
    """
    profile = athlete_service.get_profile_by_id(db, profile_id=athlete_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    if current_user.role != "administrator":
        is_assigned = athlete_service.check_staff_assigned_to_athlete(db, staff_id=current_user.id, athlete_id=athlete_id)
        if not is_assigned:
            raise HTTPException(status_code=403, detail="Not authorized to access this athlete's data")

    return profile

@router.post("/{athlete_id}/assign")
def assign_staff(
    athlete_id: int,
    staff_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Connect an athlete with coaching / clinical staff:
    - Administrator can assign any staff to any athlete.
    - Coach / Physiotherapist / Sports Scientist can assign themselves to an athlete.
    - Athlete can assign a coach or physiotherapist to their own profile.
    """
    profile = athlete_service.get_profile_by_id(db, profile_id=athlete_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Athlete not found")

    is_admin = current_user.role == "administrator"
    is_self_staff = current_user.role in ["coach", "physiotherapist", "sports_scientist"] and staff_id == current_user.id
    is_owner_athlete = current_user.role == "athlete" and profile.user_id == current_user.id

    if not (is_admin or is_self_staff or is_owner_athlete):
        raise HTTPException(status_code=403, detail="Not authorized to manage this staff-athlete connection")

    staff = user_service.get_user(db, user_id=staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff user not found")
    if staff.role not in ["coach", "physiotherapist", "sports_scientist", "administrator"]:
        raise HTTPException(status_code=400, detail="Target user is not a staff member")

    assignment = athlete_service.assign_staff_to_athlete(db, athlete_id=athlete_id, staff_id=staff_id)
    return {"message": "Staff successfully connected with athlete", "assignment_id": assignment.id}

@router.delete("/{athlete_id}/assign/{staff_id}")
def unassign_staff(
    athlete_id: int,
    staff_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Remove a staff connection from an athlete."""
    profile = athlete_service.get_profile_by_id(db, profile_id=athlete_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Athlete not found")

    is_admin = current_user.role == "administrator"
    is_self_staff = current_user.role in ["coach", "physiotherapist", "sports_scientist"] and staff_id == current_user.id
    is_owner_athlete = current_user.role == "athlete" and profile.user_id == current_user.id

    if not (is_admin or is_self_staff or is_owner_athlete):
        raise HTTPException(status_code=403, detail="Not authorized to remove this connection")

    removed = athlete_service.unassign_staff_from_athlete(db, athlete_id=athlete_id, staff_id=staff_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return {"message": "Staff connection successfully removed"}

@router.get("/{athlete_id}/staff")
def list_athlete_staff(
    athlete_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """List staff members assigned to this athlete."""
    staff_members = athlete_service.get_staff_for_athlete(db, athlete_id=athlete_id)
    return [
        {
            "id": s.id,
            "email": s.email,
            "full_name": s.full_name or s.email.split("@")[0].title(),
            "role": s.role,
            "organization": getattr(s, "organization", None),
            "specialization": getattr(s, "specialization", None)
        }
        for s in staff_members
    ]

