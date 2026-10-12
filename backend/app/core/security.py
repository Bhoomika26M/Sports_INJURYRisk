from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets
import uuid
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.database import get_db
from app.models.user import User
from app.models.session import Session as UserSession

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> dict:
    """Create JWT token with session ID for revocation support."""
    to_encode = data.copy()
    
    # Generate unique session ID (jti)
    jti = str(uuid.uuid4())
    to_encode.update({"jti": jti})
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return {"access_token": encoded_jwt, "jti": jti, "expires_at": expire}


def create_user_session(db: Session, user: User, jti: str, expires_at: datetime) -> UserSession:
    """Create a server-side session record for revocation support."""
    session = UserSession(
        user_id=user.id,
        session_id=jti,
        expires_at=expires_at
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def revoke_session(db: Session, jti: str) -> bool:
    """Revoke a session by marking it as revoked."""
    session = db.query(UserSession).filter(UserSession.session_id == jti).first()
    if session:
        session.revoked_at = datetime.utcnow()
        db.commit()
        return True
    return False


def revoke_all_user_sessions(db: Session, user_id: int) -> int:
    """Revoke all active sessions for a user (e.g., after password change)."""
    sessions = db.query(UserSession).filter(
        UserSession.user_id == user_id
    ).all()
    
    count = 0
    for session in sessions:
        if session.revoked_at is None:
            session.revoked_at = datetime.utcnow()
            count += 1
    
    db.commit()
    return count


def is_session_valid(db: Session, jti: str) -> bool:
    """Check if a session is valid (not revoked and not expired)."""
    session = db.query(UserSession).filter(UserSession.session_id == jti).first()
    if not session:
        return False
    if session.revoked_at is not None:
        return False
    if session.expires_at < datetime.utcnow():
        return False
    return True


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        jti: str = payload.get("jti")
        if email is None or jti is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Check if session is valid (not revoked)
    if not is_session_valid(db, jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked or expired"
        )
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_user_with_jti(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> tuple:
    """Get current user and jti for session management."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        jti: str = payload.get("jti")
        if email is None or jti is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # Check if session is valid (not revoked)
    if not is_session_valid(db, jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has been revoked or expired"
        )
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user, jti


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
