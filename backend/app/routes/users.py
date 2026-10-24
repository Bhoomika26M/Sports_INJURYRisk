from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel, ConfigDict

from app.database import get_db
from app.models.user import User

router = APIRouter(
    prefix="/users",
    tags=["User Management"]
)


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str

    model_config = ConfigDict(from_attributes=True)


class RoleUpdateRequest(BaseModel):
    role: str


def _seed_initial_users(db: Session):
    if db.query(User).count() == 0:
        from app.utils.security import hash_password
        users = [
            User(name="Marcus Vance", email="athlete@sportguard.ai", password=hash_password("athlete123"), role="ATHLETE"),
            User(name="Coach Michael Roberts", email="coach@sportguard.ai", password=hash_password("coach123"), role="COACH"),
            User(name="Dr. Sarah Jenkins", email="physio@sportguard.ai", password=hash_password("physio123"), role="PHYSIOTHERAPIST"),
            User(name="Dr. David Chen", email="science@sportguard.ai", password=hash_password("science123"), role="SPORTS_SCIENTIST"),
            User(name="System Administrator", email="admin@sportguard.ai", password=hash_password("admin123"), role="ADMINISTRATOR")
        ]
        db.add_all(users)
        db.commit()


@router.get("/", response_model=List[UserOut])
def get_all_users(db: Session = Depends(get_db)):
    """Fetch all registered users for administration."""
    _seed_initial_users(db)
    users = db.query(User).all()
    return users


@router.put("/{user_id}/role")
def update_user_role(user_id: int, req: RoleUpdateRequest, db: Session = Depends(get_db)):
    """Update role for a user (ATHLETE, COACH, PHYSIOTHERAPIST, SPORTS_SCIENTIST, ADMINISTRATOR)."""
    valid_roles = ["ATHLETE", "COACH", "PHYSIOTHERAPIST", "SPORTS_SCIENTIST", "ADMINISTRATOR"]
    normalized_role = req.role.upper().strip()
    if normalized_role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of {valid_roles}")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = normalized_role
    db.commit()
    db.refresh(user)
    return {"message": "Role updated successfully", "user_id": user.id, "new_role": user.role}


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Remove a user from the platform."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully", "user_id": user_id}
