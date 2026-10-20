from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, require_roles
from app.db.session import get_db
from app.models.athlete import (
    Athlete,
    AthleteAccess,
    InjuryRecord,
    PhysicalAssessment,
    TrainingLoadEntry,
)
from app.models.user import Role, User
from app.schemas.athlete import (
    AccessGrant,
    AccessOut,
    AssessmentCreate,
    AssessmentOut,
    AthleteCreate,
    AthleteOut,
    AthleteUpdate,
    InjuryCreate,
    InjuryOut,
    TrainingLoadCreate,
    TrainingLoadOut,
)
from app.services.access import accessible_athletes_query, get_athlete_for

router = APIRouter(prefix="/athletes", tags=["athletes"])

CAN_CREATE = (Role.athlete.value, Role.coach.value, Role.physiotherapist.value, Role.administrator.value)
GRANTABLE = {Role.coach.value, Role.physiotherapist.value, Role.sports_scientist.value}


@router.post("", response_model=AthleteOut, status_code=201)
def create_athlete(
    payload: AthleteCreate, db: Session = Depends(get_db), user: User = Depends(require_roles(*CAN_CREATE))
):
    data = payload.model_dump()
    if user.role == Role.athlete.value:
        if db.scalar(select(Athlete).where(Athlete.user_id == user.id)):
            raise HTTPException(status_code=409, detail="You already have an athlete profile")
        athlete = Athlete(**{**data, "full_name": data["full_name"] or user.full_name, "user_id": user.id})
    else:
        if not data["full_name"]:
            raise HTTPException(status_code=422, detail="full_name is required")
        athlete = Athlete(**data)
    db.add(athlete)
    db.flush()
    if user.role in (Role.coach.value, Role.physiotherapist.value):
        db.add(AthleteAccess(athlete_id=athlete.id, user_id=user.id, access_role=user.role))
    db.commit()
    db.refresh(athlete)
    return athlete


@router.get("", response_model=list[AthleteOut])
def list_athletes(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return db.scalars(accessible_athletes_query(user).order_by(Athlete.full_name)).all()


@router.get("/{athlete_id}", response_model=AthleteOut)
def get_athlete(athlete_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_athlete_for(db, user, athlete_id)


@router.patch("/{athlete_id}", response_model=AthleteOut)
def update_athlete(
    athlete_id: int, payload: AthleteUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    athlete = get_athlete_for(db, user, athlete_id, write=True)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(athlete, key, value)
    db.commit()
    return athlete


# --- Injury history ----------------------------------------------------------


@router.post("/{athlete_id}/injuries", response_model=InjuryOut, status_code=201)
def add_injury(athlete_id: int, payload: InjuryCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    athlete = get_athlete_for(db, user, athlete_id, write=True)
    record = InjuryRecord(athlete_id=athlete.id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/{athlete_id}/injuries", response_model=list[InjuryOut])
def list_injuries(athlete_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_athlete_for(db, user, athlete_id).injuries


@router.patch("/{athlete_id}/injuries/{injury_id}", response_model=InjuryOut)
def update_injury(
    athlete_id: int, injury_id: int, payload: InjuryCreate, db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    athlete = get_athlete_for(db, user, athlete_id, write=True)
    record = db.get(InjuryRecord, injury_id)
    if record is None or record.athlete_id != athlete.id:
        raise HTTPException(status_code=404, detail="Injury not found")
    for key, value in payload.model_dump().items():
        setattr(record, key, value)
    db.commit()
    return record


# --- Training load -----------------------------------------------------------


@router.post("/{athlete_id}/training-load", response_model=TrainingLoadOut, status_code=201)
def add_training_load(
    athlete_id: int, payload: TrainingLoadCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    athlete = get_athlete_for(db, user, athlete_id, write=True)
    entry = TrainingLoadEntry(
        athlete_id=athlete.id,
        entry_date=payload.entry_date,
        duration_min=payload.duration_min,
        rpe=payload.rpe,
        load_au=payload.duration_min * payload.rpe,
        notes=payload.notes,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/{athlete_id}/training-load", response_model=list[TrainingLoadOut])
def list_training_load(athlete_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_athlete_for(db, user, athlete_id).training_loads


# --- Physical assessments ----------------------------------------------------


@router.post("/{athlete_id}/assessments", response_model=AssessmentOut, status_code=201)
def add_assessment(
    athlete_id: int, payload: AssessmentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    athlete = get_athlete_for(db, user, athlete_id, write=True)
    record = PhysicalAssessment(athlete_id=athlete.id, assessed_by=user.id, notes=payload.notes, metrics=payload.metrics)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/{athlete_id}/assessments", response_model=list[AssessmentOut])
def list_assessments(athlete_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return get_athlete_for(db, user, athlete_id).assessments


# --- Sharing: the athlete (or an admin) decides who can see their data --------


@router.get("/{athlete_id}/access", response_model=list[AccessOut])
def list_access(athlete_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    athlete = get_athlete_for(db, user, athlete_id)
    return [
        AccessOut(user_id=g.user_id, email=g.user.email, full_name=g.user.full_name, access_role=g.access_role)
        for g in athlete.access
    ]


def _require_owner_or_admin(user: User, athlete: Athlete) -> None:
    if user.role != Role.administrator.value and athlete.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only the athlete or an administrator can manage access")


@router.post("/{athlete_id}/access", response_model=AccessOut, status_code=201)
def grant_access(
    athlete_id: int, payload: AccessGrant, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    athlete = get_athlete_for(db, user, athlete_id)
    _require_owner_or_admin(user, athlete)
    target = db.scalar(select(User).where(User.email == payload.email.lower()))
    if target is None or target.role not in GRANTABLE:
        raise HTTPException(status_code=404, detail="No coach, physiotherapist or sports scientist with that email")
    if db.scalar(select(AthleteAccess).where(AthleteAccess.athlete_id == athlete.id, AthleteAccess.user_id == target.id)):
        raise HTTPException(status_code=409, detail="Access already granted")
    grant = AthleteAccess(athlete_id=athlete.id, user_id=target.id, access_role=target.role)
    db.add(grant)
    db.commit()
    return AccessOut(user_id=target.id, email=target.email, full_name=target.full_name, access_role=target.role)


@router.delete("/{athlete_id}/access/{user_id}", status_code=204)
def revoke_access(athlete_id: int, user_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    athlete = get_athlete_for(db, user, athlete_id)
    _require_owner_or_admin(user, athlete)
    grant = db.scalar(select(AthleteAccess).where(AthleteAccess.athlete_id == athlete.id, AthleteAccess.user_id == user_id))
    if grant is None:
        raise HTTPException(status_code=404, detail="Access grant not found")
    db.delete(grant)
    db.commit()
