from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.db.session import get_db
from app.api import deps
from app.models.user import User
from app.models.athlete import AthleteProfile
from app.schemas.notification import (
    NotificationResponse, 
    NotificationSummaryResponse,
    NotificationType,
    NotificationSeverity
)
from app.services.notification_service import notification_service

router = APIRouter()

@router.get("", response_model=List[NotificationResponse])
def get_notifications(
    unread_only: bool = False,
    notification_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
    athlete_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Retrieve notification alerts for the current user or athlete.
    """
    # If athlete role, target their athlete profile
    target_athlete_id = None
    target_user_id = current_user.id
    
    if current_user.role == "athlete":
        profile = db.query(AthleteProfile).filter(AthleteProfile.user_id == current_user.id).first()
        if profile:
            target_athlete_id = profile.id
    elif athlete_id is not None:
        target_athlete_id = athlete_id
        target_user_id = None

    return notification_service.get_notifications(
        db=db,
        athlete_id=target_athlete_id,
        user_id=target_user_id,
        unread_only=unread_only,
        notification_type=notification_type,
        limit=limit
    )

@router.get("/summary", response_model=NotificationSummaryResponse)
def get_notification_summary(
    athlete_id: Optional[int] = None,
    limit: int = Query(20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Get alert summary counts (unread, critical, warning, info) and recent notifications.
    """
    target_athlete_id = None
    target_user_id = current_user.id
    
    if current_user.role == "athlete":
        profile = db.query(AthleteProfile).filter(AthleteProfile.user_id == current_user.id).first()
        if profile:
            target_athlete_id = profile.id
    elif athlete_id is not None:
        target_athlete_id = athlete_id
        target_user_id = None

    return notification_service.get_summary(
        db=db,
        athlete_id=target_athlete_id,
        user_id=target_user_id,
        limit=limit
    )

@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Mark an individual notification as read.
    """
    notif = notification_service.mark_as_read(db, notification_id)
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notif

@router.post("/mark-all-read")
def mark_all_notifications_read(
    athlete_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Mark all notifications as read for the current user or athlete.
    """
    target_athlete_id = None
    target_user_id = current_user.id

    if current_user.role == "athlete":
        profile = db.query(AthleteProfile).filter(AthleteProfile.user_id == current_user.id).first()
        if profile:
            target_athlete_id = profile.id
    elif athlete_id is not None:
        target_athlete_id = athlete_id
        target_user_id = None

    count = notification_service.mark_all_read(
        db=db,
        athlete_id=target_athlete_id,
        user_id=target_user_id
    )
    return {"status": "success", "marked_read_count": count}

@router.post("/sync")
def sync_athlete_alerts(
    athlete_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Manually scan and sync alerts (training load warnings, recovery reminders, video alerts).
    """
    target_athlete_id = athlete_id
    if current_user.role == "athlete" or target_athlete_id is None:
        profile = db.query(AthleteProfile).filter(AthleteProfile.user_id == current_user.id).first()
        if profile:
            target_athlete_id = profile.id

    if not target_athlete_id:
        return {"status": "no_athlete_found", "alerts_created": 0}

    # Generate training load & recovery reminders
    load_alerts = notification_service.generate_training_load_alerts(db, target_athlete_id)
    rec_alerts = notification_service.generate_recovery_reminders(db, target_athlete_id)

    return {
        "status": "success",
        "athlete_id": target_athlete_id,
        "alerts_created": len(load_alerts) + len(rec_alerts)
    }
