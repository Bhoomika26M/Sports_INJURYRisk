from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.auth import UserRegister, UserLogin, Token
from app.schemas.user import UserResponse
from app.services.auth_service import register_user, authenticate_user, create_user_token
from app.core.security import get_current_active_user
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user.
    
    - **email**: User's email address (must be unique)
    - **password**: User's password
    - **full_name**: User's full name
    - **role**: User's role (athlete, coach, physiotherapist, sports_scientist, administrator)
    """
    user = register_user(db, user_data)
    return user


@router.post("/login", response_model=Token)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    Login with email and password to get access token.
    
    - **email**: User's email address
    - **password**: User's password
    
    Returns a JWT access token that should be used in the Authorization header for subsequent requests.
    """
    user = authenticate_user(db, user_data)
    access_token = create_user_token(user)
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
def get_current_user_info(current_user: User = Depends(get_current_active_user)):
    """
    Get current user information.
    
    Requires a valid JWT token in the Authorization header.
    """
    return current_user
