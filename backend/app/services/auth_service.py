from datetime import timedelta
from fastapi import HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.security import (
    verify_password, 
    get_password_hash, 
    create_access_token,
    create_user_session
)
from app.core.config import settings
from app.core.audit import log_login, log_failed_login, log_registration, log_admin_user_created
from app.models.user import User
from app.models.athlete import Athlete
from app.schemas.auth import UserRegister, UserLogin


def register_user(db: Session, user_data: UserRegister, request: Request = None) -> User:
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Public self-registration is restricted to the 'athlete' role.
    # Professional roles (coach, physiotherapist, sports_scientist,
    # administrator) must be provisioned by an administrator via
    # create_user_by_admin(), never chosen by the registrant. This prevents
    # privilege escalation through public sign-up.
    if user_data.role != "athlete":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Public registration only allows the 'athlete' role."
        )
    
    # Create new user with the forced athlete role
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        role="athlete",
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Automatically create athlete profile for athlete role
    if db_user.role == "athlete":
        # Generate a unique athlete_id
        athlete_id = f"ATH{db_user.id:06d}"
        db_athlete = Athlete(
            athlete_id=athlete_id,
            user_id=db_user.id,
            sport_type=user_data.sport_type or "General",
            position=user_data.position,
            age=user_data.age or 18,
            height=user_data.height or 170.0,
            weight=user_data.weight or 70.0,
        )
        db.add(db_athlete)
        db.commit()
    
    # Log registration
    ip_address = request.client.host if request else None
    log_registration(db_user, ip_address)
    
    return db_user


def authenticate_user(db: Session, user_data: UserLogin, request: Request = None) -> User:
    user = db.query(User).filter(User.email == user_data.email).first()
    ip_address = request.client.host if request else None
    
    if not user:
        log_failed_login(user_data.email, ip_address)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not verify_password(user_data.password, user.password_hash):
        log_failed_login(user.email, ip_address)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    if not user.is_active:
        log_failed_login(user.email, ip_address)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    log_login(user, ip_address)
    return user


def create_user_token(user: User, db: Session) -> str:
    """Create JWT token and server-side session."""
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    token_data = create_access_token(
        data={"sub": user.email}, 
        expires_delta=access_token_expires
    )
    
    # Create server-side session for revocation support
    create_user_session(db, user, token_data["jti"], token_data["expires_at"])
    
    return token_data["access_token"]


def create_user_by_admin(db: Session, user_data: UserRegister, admin_user: User, request: Request = None) -> User:
    """
    Create a user with any role (admin-only function).
    This allows administrators to create professional role accounts.
    """
    # Verify requester is administrator
    if admin_user.role != "administrator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can create users with professional roles"
        )
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate role
    valid_roles = ["athlete", "coach", "physiotherapist", "sports_scientist", "administrator"]
    if user_data.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(valid_roles)}"
        )
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        password_hash=hashed_password,
        full_name=user_data.full_name,
        role=user_data.role,
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Keep athlete accounts consistent with public registration by creating
    # their athlete profile too.
    if db_user.role == "athlete":
        athlete_id = f"ATH{db_user.id:06d}"
        db_athlete = Athlete(
            athlete_id=athlete_id,
            user_id=db_user.id,
            sport_type=user_data.sport_type or "General",
            position=user_data.position,
            age=user_data.age or 18,
            height=user_data.height or 170.0,
            weight=user_data.weight or 70.0,
        )
        db.add(db_athlete)
        db.commit()
    
    # Audit the privileged action (never includes the password).
    ip_address = request.client.host if request else None
    log_admin_user_created(db_user, admin_user, ip_address)
    
    return db_user
