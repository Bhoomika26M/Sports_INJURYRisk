from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import Role, User
from app.schemas.user import AdminUserUpdate, UserCreate, UserOut, UserProfileUpdate

router = APIRouter(prefix="/users", tags=["users"])
admin_only = require_roles(Role.administrator.value)


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return db.scalars(select(User).order_by(User.id)).all()


@router.patch("/me", response_model=UserOut)
def update_my_profile(
    payload: UserProfileUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    if payload.full_name:
        user.full_name = payload.full_name
    if payload.password:
        user.hashed_password = hash_password(payload.password)
    db.commit()
    return user


@router.patch("/{user_id}", response_model=UserOut)
def admin_update_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(admin_only),
):
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == admin.id and (payload.is_active is False or (payload.role and payload.role != admin.role)):
        raise HTTPException(status_code=400, detail="Administrators cannot demote or disable themselves")
    if payload.role is not None:
        target.role = payload.role
    if payload.is_active is not None:
        target.is_active = payload.is_active
    db.commit()
    return target


@router.post("/admin-create", response_model=UserOut, status_code=201)
def admin_create_user(
    payload: UserCreate, role: str = Role.athlete.value, db: Session = Depends(get_db),
    _: User = Depends(admin_only),
):
    """Administrators can create any user, including other administrators."""
    if role not in {r.value for r in Role}:
        raise HTTPException(status_code=422, detail="Unknown role")
    email = payload.email.lower()
    if db.scalar(select(User).where(User.email == email)):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = User(email=email, full_name=payload.full_name, hashed_password=hash_password(payload.password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
