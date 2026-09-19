"""
User self-service routes:
  PUT /users/me – update own profile (name, phone, password)
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.auth import UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.put(
    "/me",
    response_model=UserRead,
    status_code=status.HTTP_200_OK,
    summary="Update current user profile",
)
async def update_me(
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserRead:
    if payload.full_name is not None:
        current_user.full_name = payload.full_name.strip()
    if payload.phone_number is not None:
        current_user.phone_number = payload.phone_number
    if payload.password is not None:
        current_user.hashed_password = hash_password(payload.password)

    db.add(current_user)
    await db.flush()
    await db.refresh(current_user)
    return UserRead.model_validate(current_user)
