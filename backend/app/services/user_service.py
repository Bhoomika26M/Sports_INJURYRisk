import os
import secrets
from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password
from app.core.config import settings

VALID_ROLES = {
    UserRole.ATHLETE.value,
    UserRole.COACH.value,
    UserRole.PHYSIOTHERAPIST.value,
    UserRole.SPORTS_SCIENTIST.value,
    UserRole.ADMINISTRATOR.value
}

def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email.ilike(email)).first()

def get_user_by_google_id(db: Session, google_id: str) -> Optional[User]:
    return db.query(User).filter(User.google_id == google_id).first()

def create_user(db: Session, user_in: UserCreate, is_admin: bool = False) -> User:
    # Normalize requested role
    requested_role = (user_in.role or UserRole.ATHLETE.value).lower().strip()
    if requested_role not in VALID_ROLES:
        requested_role = UserRole.ATHLETE.value

    # Prevent unauthenticated self-assignment of administrator role without admin code
    if requested_role == UserRole.ADMINISTRATOR.value and not is_admin:
        expected_code = os.getenv("ADMIN_REGISTRATION_CODE", settings.SECRET_KEY)
        if getattr(user_in, "admin_code", None) != expected_code:
            # Fall back to athlete for unauthorized administrator attempts
            requested_role = UserRole.ATHLETE.value

    db_user = User(
        email=user_in.email.lower(),
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=requested_role,
        bio=getattr(user_in, "bio", None),
        phone_number=getattr(user_in, "phone_number", None),
        organization=getattr(user_in, "organization", None),
        specialization=getattr(user_in, "specialization", None),
        is_active=True
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = get_user_by_email(db, email=email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def authenticate_or_register_google(
    db: Session,
    google_id: str,
    email: str,
    email_verified: bool,
    full_name: Optional[str] = None,
    requested_role: Optional[str] = UserRole.ATHLETE.value,
    admin_code: Optional[str] = None
) -> User:
    """
    Secure Google OAuth2 / OpenID Connect account authentication and linking:
    1. If google_id already matches a user, authenticate that user immediately.
    2. If email exists in database:
       - Requires email_verified=True from Google to prevent account takeover.
       - If user.google_id is already set to a different Google account, raise ValueError.
       - Otherwise, link the Google account to the existing account by updating google_id.
       - Preserve the existing user's role and existing credentials.
    3. If user is brand new:
       - Requires email_verified=True.
       - Enforces role validation (Administrator role requires valid admin_code).
       - Generates secure random password.
       - Creates user with auth_provider='google' and google_id.
    """
    if not email_verified:
        raise ValueError("Google account email is not verified. Unverified emails cannot be used for authentication.")

    # 1. Check if user already linked via google_id
    user_by_gid = get_user_by_google_id(db, google_id)
    if user_by_gid:
        if full_name and not user_by_gid.full_name:
            user_by_gid.full_name = full_name
            db.commit()
            db.refresh(user_by_gid)
        return user_by_gid

    # 2. Check if user exists by email
    user_by_email = get_user_by_email(db, email)
    if user_by_email:
        if user_by_email.google_id and user_by_email.google_id != google_id:
            raise ValueError("This email is already associated with a different Google account.")
        
        user_by_email.google_id = google_id
        if user_by_email.auth_provider == "local":
            user_by_email.auth_provider = "both"
        else:
            user_by_email.auth_provider = "google"
            
        if full_name and not user_by_email.full_name:
            user_by_email.full_name = full_name
            
        db.commit()
        db.refresh(user_by_email)
        return user_by_email

    # 3. Create new user
    valid_role = (requested_role or UserRole.ATHLETE.value).lower().strip()
    if valid_role not in VALID_ROLES:
        valid_role = UserRole.ATHLETE.value
        
    if valid_role == UserRole.ADMINISTRATOR.value:
        expected_code = os.getenv("ADMIN_REGISTRATION_CODE", settings.SECRET_KEY)
        if admin_code != expected_code:
            valid_role = UserRole.ATHLETE.value

    random_pwd = secrets.token_urlsafe(32)
    new_user = User(
        email=email.lower().strip(),
        hashed_password=get_password_hash(random_pwd),
        full_name=full_name or email.split("@")[0].replace(".", " ").title(),
        role=valid_role,
        auth_provider="google",
        google_id=google_id,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def authenticate_or_register_oauth(
    db: Session,
    email: str,
    full_name: Optional[str] = None,
    provider: str = "google",
    role: Optional[str] = UserRole.ATHLETE.value
) -> User:
    """Authenticates existing OAuth user or creates a new one with designated role."""
    user = get_user_by_email(db, email=email)
    if not user:
        random_pwd = secrets.token_urlsafe(32)
        valid_role = (role or UserRole.ATHLETE.value).lower().strip()
        if valid_role not in VALID_ROLES or valid_role == UserRole.ADMINISTRATOR.value:
            valid_role = UserRole.ATHLETE.value

        user = User(
            email=email.lower(),
            hashed_password=get_password_hash(random_pwd),
            full_name=full_name or email.split("@")[0].replace(".", " ").title(),
            role=valid_role,
            is_active=True,
            organization=f"OAuth ({provider.title()})"
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

def update_user_profile(db: Session, user: User, user_update: UserUpdate) -> User:
    if user_update.full_name is not None:
        user.full_name = user_update.full_name
    if user_update.bio is not None:
        user.bio = user_update.bio
    if user_update.phone_number is not None:
        user.phone_number = user_update.phone_number
    if user_update.organization is not None:
        user.organization = user_update.organization
    if user_update.specialization is not None:
        user.specialization = user_update.specialization

    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def change_password(db: Session, user: User, current_password: str, new_password: str) -> bool:
    if not verify_password(current_password, user.hashed_password):
        return False
    user.hashed_password = get_password_hash(new_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return True

def update_user_role_and_status(
    db: Session,
    user_id: int,
    new_role: str,
    is_active: Optional[bool] = None
) -> Optional[User]:
    user = get_user(db, user_id=user_id)
    if not user:
        return None
    normalized_role = new_role.lower().strip()
    if normalized_role in VALID_ROLES:
        user.role = normalized_role
    if is_active is not None:
        user.is_active = is_active
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def get_all_users(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    role: Optional[str] = None,
    search: Optional[str] = None
) -> List[User]:
    query = db.query(User)
    if role:
        query = query.filter(User.role == role.lower().strip())
    if search:
        search_filter = f"%{search.strip()}%"
        query = query.filter(
            User.email.ilike(search_filter) | User.full_name.ilike(search_filter)
        )
    return query.offset(skip).limit(limit).all()

def get_staff_users(db: Session, roles: Optional[List[str]] = None) -> List[User]:
    if not roles:
        roles = [UserRole.COACH.value, UserRole.PHYSIOTHERAPIST.value, UserRole.SPORTS_SCIENTIST.value]
    return db.query(User).filter(User.role.in_(roles), User.is_active == True).all()
