import pytest
from app.models.notification import Notification
from app.models.athlete import AthleteProfile
from app.services.notification_service import notification_service
from app.schemas.notification import NotificationType, NotificationSeverity

def test_create_and_get_notification(db_session, test_user):
    # Create profile
    profile = AthleteProfile(
        user_id=test_user.id,
        sport_type="Basketball",
        training_load={"acute_load": 1800, "chronic_load": 1000, "sessions_per_week": 5}
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    # Create notification
    notif = notification_service.create_notification(
        db=db_session,
        notification_type=NotificationType.HIGH_RISK_MOVEMENT.value,
        severity=NotificationSeverity.CRITICAL.value,
        title="Dynamic Knee Valgus Alert",
        message="Medial knee collapse observed during deceleration.",
        athlete_id=profile.id,
        user_id=test_user.id,
        data={"metric": "knee_valgus", "value": 0.72}
    )

    assert notif.id is not None
    assert notif.severity == "critical"
    assert not notif.is_read

    # Retrieve notifications
    items = notification_service.get_notifications(db=db_session, athlete_id=profile.id)
    assert len(items) >= 1
    assert items[0].title == "Dynamic Knee Valgus Alert"

    # Summary
    summary = notification_service.get_summary(db=db_session, athlete_id=profile.id)
    assert summary.total_count >= 1
    assert summary.unread_count >= 1
    assert summary.critical_count >= 1

    # Mark as read
    marked = notification_service.mark_as_read(db_session, notif.id)
    assert marked.is_read

    # Mark all read
    count = notification_service.mark_all_read(db_session, athlete_id=profile.id)
    assert count == 0 # already marked read

def test_training_load_and_recovery_alerts(db_session, test_user):
    profile = AthleteProfile(
        user_id=test_user.id,
        sport_type="Football",
        training_load={"acute_load": 2200, "chronic_load": 1200, "sessions_per_week": 7}
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    # Generate training load alerts
    load_alerts = notification_service.generate_training_load_alerts(db_session, profile.id)
    assert len(load_alerts) >= 1
    types = [a.notification_type for a in load_alerts]
    assert NotificationType.TRAINING_LOAD.value in types

    # Generate recovery reminders
    rec_alerts = notification_service.generate_recovery_reminders(db_session, profile.id)
    assert len(rec_alerts) >= 1
    assert rec_alerts[0].notification_type == NotificationType.RECOVERY_REMINDER.value
