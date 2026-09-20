from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.schemas.user import UserResponse
from app.core.security import get_current_active_user
from app.core.dependencies import require_admin
from app.models.user import User

router = APIRouter(prefix="/users", tags=["Users"])


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
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own profile"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user
