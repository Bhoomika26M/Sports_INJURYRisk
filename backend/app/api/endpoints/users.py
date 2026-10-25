from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.user import (
    UserResponse,
    UserUpdate,
    UserPasswordChange,
    UserRoleUpdate,
    UserCreate
)
from app.api.deps import get_current_active_user, RoleChecker
from app.models.user import User, UserRole
from app.services import user_service

router = APIRouter()

allow_admin = RoleChecker(["administrator"])

ROLE_METADATA = [
    {
        "key": UserRole.ATHLETE.value,
        "name": "Athlete",
        "description": "Uploads movement videos, tracks personal injury risk scores, and receives tailored biomechanical feedback.",
        "badge_color": "green",
        "permissions": ["upload_video", "view_own_dashboard", "edit_athlete_profile"]
    },
    {
        "key": UserRole.COACH.value,
        "name": "Coach",
        "description": "Monitors team performance, injury risk indices, and readiness for assigned athletes.",
        "badge_color": "indigo",
        "permissions": ["view_assigned_athletes", "view_athlete_dashboards", "review_recommendations"]
    },
    {
        "key": UserRole.PHYSIOTHERAPIST.value,
        "name": "Physiotherapist",
        "description": "Analyzes clinical movement anomalies, joint angle deviations, and rehabilitation protocols.",
        "badge_color": "teal",
        "permissions": ["view_assigned_athletes", "view_clinical_anomalies", "view_joint_kinematics", "rehab_recommendations"]
    },
    {
        "key": UserRole.SPORTS_SCIENTIST.value,
        "name": "Sports Scientist",
        "description": "Investigates deep biomechanical kinematics, bilateral symmetry indexes, and movement kinetics.",
        "badge_color": "purple",
        "permissions": ["view_assigned_athletes", "view_biomechanics_telemetry", "export_kinematics_data", "fatigue_load_analysis"]
    },
    {
        "key": UserRole.ADMINISTRATOR.value,
        "name": "Administrator",
        "description": "Full system oversight: user governance, role assignments, staff-athlete matching, and system security.",
        "badge_color": "rose",
        "permissions": ["manage_users", "assign_roles", "manage_assignments", "view_all_athletes", "system_settings"]
    }
]

@router.get("/roles")
def get_available_roles() -> Any:
    """Get list of supported system roles, descriptions, and capabilities."""
    return ROLE_METADATA

@router.get("/staff", response_model=List[UserResponse])
def get_coaching_and_clinical_staff(
    db: Session = Depends(get_db),
    role: Optional[str] = None,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get list of active staff members (coaches, physiotherapists, sports scientists) for athlete assignment."""
    roles = [role.lower().strip()] if role else None
    return user_service.get_staff_users(db, roles=roles)

@router.get("/me", response_model=UserResponse)
def read_user_me(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """Get current user's account profile."""
    return current_user

@router.put("/me", response_model=UserResponse)
def update_user_me(
    *,
    db: Session = Depends(get_db),
    user_in: UserUpdate,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Update current user profile (full name, bio, phone, organization, specialization)."""
    return user_service.update_user_profile(db, user=current_user, user_update=user_in)

@router.put("/me/password")
def change_my_password(
    *,
    db: Session = Depends(get_db),
    pwd_in: UserPasswordChange,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Change current user's password."""
    success = user_service.change_password(
        db,
        user=current_user,
        current_password=pwd_in.current_password,
        new_password=pwd_in.new_password
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    return {"message": "Password changed successfully"}

@router.get("/admin-only", response_model=UserResponse)
def read_admin_only_route(
    current_user: User = Depends(allow_admin),
) -> Any:
    """Test route for admins only."""
    return current_user

# ==================== Administrator User Management ====================

@router.get("/", response_model=List[UserResponse])
def list_all_users(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    role: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(allow_admin)
) -> Any:
    """List all registered users (Administrator only). Filter by role or search query."""
    return user_service.get_all_users(db, skip=skip, limit=limit, role=role, search=search)

@router.post("/", response_model=UserResponse)
def create_user_by_admin(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
    current_user: User = Depends(allow_admin)
) -> Any:
    """Create a user with any role (Administrator only)."""
    existing = user_service.get_user_by_email(db, email=user_in.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists"
        )
    return user_service.create_user(db, user_in=user_in, is_admin=True)

@router.get("/{user_id}", response_model=UserResponse)
def get_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(allow_admin)
) -> Any:
    """Get user details by ID (Administrator only)."""
    user = user_service.get_user(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.put("/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: int,
    *,
    db: Session = Depends(get_db),
    role_in: UserRoleUpdate,
    current_user: User = Depends(allow_admin)
) -> Any:
    """Update a user's role or active status (Administrator only)."""
    updated_user = user_service.update_user_role_and_status(
        db, user_id=user_id, new_role=role_in.role, is_active=role_in.is_active
    )
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")
    return updated_user
