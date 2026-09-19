"""
Authentication routes:
  POST /auth/register   – public, athlete-only registration
  POST /auth/login      – returns JWT access + refresh tokens
  GET  /auth/me         – authenticated: returns current user
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, create_refresh_token, hash_password, verify_password
from app.deps import get_current_user, get_db
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.auth import TokenResponse, UserLogin, UserRead, UserRegister

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# POST /auth/register
# ---------------------------------------------------------------------------
@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Public athlete registration",
    description="Registers a new user. Role is always forced to **athlete** regardless of any supplied value.",
)
async def register(payload: UserRegister, db: AsyncSession = Depends(get_db)) -> UserRead:
    # Check email uniqueness
    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=UserRole.ATHLETE,   # ALWAYS athlete – never trust caller
        phone_number=payload.phone_number,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    await db.flush()   # get the generated id without committing yet
    await db.refresh(user)
    return UserRead.model_validate(user)


# ---------------------------------------------------------------------------
# POST /auth/login
# ---------------------------------------------------------------------------
@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login – returns access + refresh tokens",
)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)) -> TokenResponse:
    result = await db.execute(select(User).where(User.email == payload.email.lower()))
    user: User | None = result.scalar_one_or_none()

    if not user or not user.hashed_password or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return TokenResponse(
        access_token=create_access_token(str(user.id), user.role.value),
        refresh_token=create_refresh_token(str(user.id)),
    )


# ---------------------------------------------------------------------------
# GET /auth/me
# ---------------------------------------------------------------------------
@router.get(
    "/me",
    response_model=UserRead,
    summary="Return current authenticated user",
)
async def me(current_user: User = Depends(get_current_user)) -> UserRead:
    return UserRead.model_validate(current_user)
