"""
FastAPI dependency functions:
  - get_db       – async SQLAlchemy session
  - get_current_user – validates Bearer JWT, returns User ORM object
  - require_roles    – role-gate factory returning a 403 on mismatch
"""
import uuid
from typing import AsyncGenerator, Callable

import jwt as pyjwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.models.enums import UserRole
from app.models.user import User

# ---------------------------------------------------------------------------
# Database session
# ---------------------------------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async SQLAlchemy session.
    Automatically commits on success, rolls back on exception.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ---------------------------------------------------------------------------
# OAuth2 scheme – tokenUrl is the login endpoint
# ---------------------------------------------------------------------------
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

_CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Decode the JWT and return the matching active User.
    Raises 401 on any failure (missing token, invalid token, user not found / inactive).
    """
    try:
        payload = decode_token(token)
    except pyjwt.PyJWTError:
        raise _CREDENTIALS_EXCEPTION

    if payload.get("type") != "access":
        raise _CREDENTIALS_EXCEPTION

    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise _CREDENTIALS_EXCEPTION

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise _CREDENTIALS_EXCEPTION

    result = await db.execute(select(User).where(User.id == user_id))
    user: User | None = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise _CREDENTIALS_EXCEPTION

    return user


# ---------------------------------------------------------------------------
# Role-based access control
# ---------------------------------------------------------------------------
def require_roles(*allowed: UserRole) -> Callable:
    """
    Dependency factory.  Usage::

        @router.get("/admin/users")
        async def admin_endpoint(
            current_user: User = Depends(require_roles(UserRole.ADMIN)),
        ): ...
    """
    allowed_set = set(allowed)

    async def _check(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if current_user.role not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access denied. Required role(s): "
                    f"{[r.value for r in allowed_set]}. "
                    f"Your role: {current_user.role.value}"
                ),
            )
        return current_user

    return _check
