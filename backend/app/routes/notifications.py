from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app.models.notification import Notification
from app.schemas.notification import NotificationCreate, NotificationOut

router = APIRouter(
    prefix="/notifications",
    tags=["Notifications & Alerts"]
)


def _seed_initial_notifications(db: Session):
    count = db.query(Notification).count()
    if count == 0:
        samples = [
            Notification(
                athlete_id="ATH-101",
                athlete_name="Marcus Vance",
                severity="CRITICAL",
                category="HIGH_RISK_MOVEMENT",
                title="Dynamic Knee Valgus Exceeds 14°",
                message="Marcus Vance exhibited severe knee valgus collapse (14.2°) during squat landing under 85% training load. Immediate ACL preventative review recommended.",
                is_read=False
            ),
            Notification(
                athlete_id="ATH-102",
                athlete_name="Elena Rostova",
                severity="WARNING",
                category="TRAINING_OVERLOAD",
                title="Training Load Surge Detected (88%)",
                message="Elena Rostova's 7-day acute:chronic workload ratio reached 1.48. High fatigue risk for hamstring strain.",
                is_read=False
            ),
            Notification(
                athlete_id="ATH-103",
                athlete_name="David Chen",
                severity="INFO",
                category="ASSESSMENT_COMPLETE",
                title="Biomechanical Assessment Generated",
                message="Jump-landing analysis completed with movement quality score of 84/100 (Grade: EXCELLENT).",
                is_read=False
            ),
            Notification(
                athlete_id="ATH-101",
                athlete_name="Marcus Vance",
                severity="WARNING",
                category="RECOVERY_REMINDER",
                title="Eccentric Hamstring Protocol Scheduled",
                message="Nordic hamstring curl progression due today for post-injury bilateral balance.",
                is_read=True
            )
        ]
        db.add_all(samples)
        db.commit()


@router.get("/", response_model=List[NotificationOut])
def get_notifications(
    unread_only: bool = Query(False),
    athlete_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """Fetch notifications and early warning alerts."""
    _seed_initial_notifications(db)
    query = db.query(Notification)
    if unread_only:
        query = query.filter(Notification.is_read == False)
    if athlete_id:
        query = query.filter(Notification.athlete_id == athlete_id)

    return query.order_by(Notification.created_at.desc()).all()


@router.post("/", response_model=NotificationOut)
def create_notification(req: NotificationCreate, db: Session = Depends(get_db)):
    """Create a new alert / notification."""
    notif = Notification(
        athlete_id=req.athlete_id,
        athlete_name=req.athlete_name,
        severity=req.severity.upper(),
        category=req.category.upper(),
        title=req.title,
        message=req.message,
        is_read=False
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


@router.put("/{notif_id}/read")
def mark_as_read(notif_id: int, db: Session = Depends(get_db)):
    """Mark a notification as read."""
    notif = db.query(Notification).filter(Notification.id == notif_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")
    notif.is_read = True
    db.commit()
    return {"message": "Notification marked as read", "id": notif_id}


@router.post("/mark-all-read")
def mark_all_as_read(db: Session = Depends(get_db)):
    """Mark all unread notifications as read."""
    db.query(Notification).filter(Notification.is_read == False).update({"is_read": True})
    db.commit()
    return {"message": "All notifications marked as read"}
