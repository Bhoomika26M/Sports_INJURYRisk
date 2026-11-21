from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.models.user import User
from app.models.athlete import Athlete
from app.models.access_invitation import AccessInvitation
from app.schemas.invitation import InvitationCreate, InvitationRespond, InvitationResponse, ProfessionalUserSummary
from app.core.security import get_current_active_user

router = APIRouter(prefix="/invitations", tags=["Access Invitations"])


@router.get("/professionals", response_model=List[ProfessionalUserSummary])
def get_available_professionals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all active professionals (coaches, physiotherapists, sports_scientists)
    that an athlete can choose to invite.
    """
    allowed_roles = ["coach", "physiotherapist", "sports_scientist"]
    pros = db.query(User).filter(
        User.role.in_(allowed_roles),
        User.is_active == True
    ).all()
    return pros


@router.get("/athlete/{athlete_id}", response_model=List[InvitationResponse])
def get_athlete_invitations(
    athlete_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get all invitations and active connections for a given athlete.
    Athletes can view their own; Administrators can view any athlete's care team.
    """
    athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")

    if current_user.role == "athlete" and athlete.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    invitations = db.query(AccessInvitation).filter(
        AccessInvitation.athlete_id == athlete_id
    ).order_by(AccessInvitation.created_at.desc()).all()

    result = []
    for inv in invitations:
        pro_user = db.query(User).filter(User.id == inv.professional_user_id).first()
        result.append(InvitationResponse(
            id=inv.id,
            athlete_id=inv.athlete_id,
            professional_user_id=inv.professional_user_id,
            status=inv.status,
            invited_role=inv.invited_role,
            notes=inv.notes,
            created_at=inv.created_at,
            updated_at=inv.updated_at,
            professional=ProfessionalUserSummary.model_validate(pro_user) if pro_user else None,
            athlete_public_id=athlete.athlete_id
        ))
    return result


@router.post("/athlete/{athlete_id}/invite", response_model=InvitationResponse)
def invite_professional(
    athlete_id: int,
    payload: InvitationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Athlete or Admin sends an invitation / access grant to a coach, physiotherapist, or sports scientist.
    """
    athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")

    if current_user.role == "athlete" and athlete.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only manage invitations for your own athlete profile")

    # Verify target professional
    pro_user = db.query(User).filter(User.id == payload.professional_user_id).first()
    if not pro_user or pro_user.role not in ["coach", "physiotherapist", "sports_scientist"]:
        raise HTTPException(status_code=400, detail="Target user must be an active coach, physiotherapist, or sports scientist")

    # Check if existing pending or accepted invitation exists
    existing = db.query(AccessInvitation).filter(
        AccessInvitation.athlete_id == athlete_id,
        AccessInvitation.professional_user_id == pro_user.id,
        AccessInvitation.status.in_(["pending", "accepted"])
    ).first()

    if existing:
        if existing.status == "accepted":
            raise HTTPException(status_code=400, detail="This professional already has active access.")
        else:
            raise HTTPException(status_code=400, detail="An invitation is already pending with this professional.")

    note_text = payload.notes
    if current_user.role == "administrator":
        note_text = f"[Admin Assigned]: {note_text or 'Access granted by Administrator'}"

    invitation = AccessInvitation(
        athlete_id=athlete_id,
        professional_user_id=pro_user.id,
        status="accepted" if current_user.role == "administrator" else "pending",
        invited_role=pro_user.role,
        notes=note_text
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    return InvitationResponse(
        id=invitation.id,
        athlete_id=invitation.athlete_id,
        professional_user_id=invitation.professional_user_id,
        status=invitation.status,
        invited_role=invitation.invited_role,
        notes=invitation.notes,
        created_at=invitation.created_at,
        updated_at=invitation.updated_at,
        professional=ProfessionalUserSummary.model_validate(pro_user),
        athlete_public_id=athlete.athlete_id
    )


@router.post("/athlete/{athlete_id}/revoke/{invitation_id}")
def revoke_access(
    athlete_id: int,
    invitation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Athlete or Admin withdraws / revokes access from a professional at any time.
    """
    athlete = db.query(Athlete).filter(Athlete.id == athlete_id).first()
    if not athlete:
        raise HTTPException(status_code=404, detail="Athlete not found")

    if current_user.role == "athlete" and athlete.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    invitation = db.query(AccessInvitation).filter(
        AccessInvitation.id == invitation_id,
        AccessInvitation.athlete_id == athlete_id
    ).first()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    invitation.status = "revoked"
    db.commit()
    return {"status": "revoked", "message": "Access successfully revoked"}


@router.get("/notifications", response_model=List[InvitationResponse])
def get_professional_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Get notifications / invitations for the logged-in coach/physiotherapist/sports scientist.
    Shows pending invitations and history.
    """
    invitations = db.query(AccessInvitation).filter(
        AccessInvitation.professional_user_id == current_user.id
    ).order_by(AccessInvitation.created_at.desc()).all()

    result = []
    for inv in invitations:
        athlete = db.query(Athlete).filter(Athlete.id == inv.athlete_id).first()
        athlete_name = athlete.athlete_id if athlete else f"Athlete #{inv.athlete_id}"
        result.append(InvitationResponse(
            id=inv.id,
            athlete_id=inv.athlete_id,
            professional_user_id=inv.professional_user_id,
            status=inv.status,
            invited_role=inv.invited_role,
            notes=inv.notes,
            created_at=inv.created_at,
            updated_at=inv.updated_at,
            professional=ProfessionalUserSummary.model_validate(current_user),
            athlete_public_id=athlete_name
        ))
    return result


@router.post("/notifications/{invitation_id}/respond")
def respond_to_invitation(
    invitation_id: int,
    payload: InvitationRespond,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Accept or reject an invitation sent by an athlete.
    """
    if payload.action not in ["accept", "reject"]:
        raise HTTPException(status_code=400, detail="Action must be 'accept' or 'reject'")

    invitation = db.query(AccessInvitation).filter(
        AccessInvitation.id == invitation_id,
        AccessInvitation.professional_user_id == current_user.id
    ).first()

    if not invitation:
        raise HTTPException(status_code=404, detail="Invitation not found")

    if invitation.status != "pending":
        raise HTTPException(status_code=400, detail=f"Invitation is already {invitation.status}")

    invitation.status = "accepted" if payload.action == "accept" else "rejected"
    db.commit()
    return {"status": invitation.status, "message": f"Invitation {invitation.status}ed successfully"}
