from fastapi import Depends, HTTPException, status
from typing import List
from app.core.security import get_current_active_user
from app.models.user import User


def require_role(*allowed_roles: str):
    def role_checker(current_user: User = Depends(get_current_active_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions"
            )
        return current_user
    return role_checker


def require_admin(current_user: User = Depends(get_current_active_user)) -> User:
    if current_user.role != "administrator":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required"
        )
    return current_user
