from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.schemas.user import UserResponse
from app.schemas.auth import UserRegister
from app.core.security import get_current_active_user
from app.core.dependencies import require_admin
from app.core.rate_limit import RateLimitDependency
from app.services.auth_service import create_user_by_admin
from app.models.user import User

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    user_data: UserRegister,
    request: Request = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
    _: None = Depends(RateLimitDependency(max_requests=20, window_seconds=60)),
):
    """
    Create a user with any role (Administrator only).

    This is the supported way to provision professional-role accounts (coach,
    physiotherapist, sports_scientist, administrator), which public registration
    deliberately refuses. The creating administrator is recorded in the audit log.
    """
    return create_user_by_admin(db, user_data, current_admin, request)


@router.get("/", response_model=List[UserResponse])
def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin)
):
    """
    Get all users (Administrator only).
    
    - **skip**: Number of users to skip
    - **limit**: Maximum number of users to return
    """
    users = db.query(User).offset(skip).limit(limit).all()
    return users


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get a specific user by ID.
    
    Users can view their own profile. Administrators can view any profile.
    """
    if current_user.role != "administrator" and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own profile"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user
