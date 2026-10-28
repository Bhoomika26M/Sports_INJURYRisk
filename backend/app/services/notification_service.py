from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.notification import Notification
from app.models.athlete import AthleteProfile
from app.models.video import Video
from app.schemas.notification import (
    NotificationCreate, 
    NotificationResponse, 
    NotificationSummaryResponse,
    NotificationType,
    NotificationSeverity
)
from app.services.anomaly_service import anomaly_service
from app.services.risk_scoring_service import risk_scoring_service
from app.services.recommendation_service import recommendation_service

class NotificationService:
    def create_notification(
        self,
        db: Session,
        notification_type: str,
        severity: str,
        title: str,
        message: str,
        athlete_id: Optional[int] = None,
        user_id: Optional[int] = None,
        video_id: Optional[int] = None,
        data: Optional[Dict[str, Any]] = None
    ) -> Notification:
        # Check if identical unread notification already exists to avoid spamming
        existing = db.query(Notification).filter(
            Notification.athlete_id == athlete_id,
            Notification.video_id == video_id,
            Notification.notification_type == notification_type,
            Notification.title == title,
            Notification.is_read == False
        ).first()

        if existing:
            return existing

        notif = Notification(
            athlete_id=athlete_id,
            user_id=user_id,
            video_id=video_id,
            notification_type=notification_type,
            severity=severity,
            title=title,
            message=message,
            data=data or {},
            is_read=False
        )
        db.add(notif)
        db.commit()
        db.refresh(notif)
        return notif

    def get_notifications(
        self,
        db: Session,
        athlete_id: Optional[int] = None,
        user_id: Optional[int] = None,
        unread_only: bool = False,
        notification_type: Optional[str] = None,
        limit: int = 50
    ) -> List[Notification]:
        query = db.query(Notification)
        
        if athlete_id is not None:
            query = query.filter(Notification.athlete_id == athlete_id)
        elif user_id is not None:
            query = query.filter(Notification.user_id == user_id)
            
        if unread_only:
            query = query.filter(Notification.is_read == False)
            
        if notification_type:
            query = query.filter(Notification.notification_type == notification_type)
            
        return query.order_by(desc(Notification.created_at)).limit(limit).all()

    def get_summary(
        self,
        db: Session,
        athlete_id: Optional[int] = None,
        user_id: Optional[int] = None,
        limit: int = 20
    ) -> NotificationSummaryResponse:
        notifications = self.get_notifications(
            db, athlete_id=athlete_id, user_id=user_id, unread_only=False, limit=limit
        )
        
        query = db.query(Notification)
        if athlete_id is not None:
            query = query.filter(Notification.athlete_id == athlete_id)
        elif user_id is not None:
            query = query.filter(Notification.user_id == user_id)

        all_items = query.all()
        total_count = len(all_items)
        unread_count = sum(1 for n in all_items if not n.is_read)
        critical_count = sum(1 for n in all_items if n.severity == "critical" and not n.is_read)
        warning_count = sum(1 for n in all_items if n.severity == "warning" and not n.is_read)
        info_count = sum(1 for n in all_items if n.severity == "info" and not n.is_read)

        return NotificationSummaryResponse(
            total_count=total_count,
            unread_count=unread_count,
            critical_count=critical_count,
            warning_count=warning_count,
            info_count=info_count,
            notifications=[NotificationResponse.model_validate(n) for n in notifications]
        )

    def mark_as_read(self, db: Session, notification_id: int) -> Optional[Notification]:
        notif = db.query(Notification).filter(Notification.id == notification_id).first()
        if notif:
            notif.is_read = True
            db.commit()
            db.refresh(notif)
        return notif

    def mark_all_read(
        self,
        db: Session,
        athlete_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> int:
        query = db.query(Notification).filter(Notification.is_read == False)
        if athlete_id is not None:
            query = query.filter(Notification.athlete_id == athlete_id)
        elif user_id is not None:
            query = query.filter(Notification.user_id == user_id)

        count = query.update({Notification.is_read: True}, synchronize_session=False)
        db.commit()
        return count

    def generate_alerts_for_video(self, db: Session, video_id: int) -> List[Notification]:
        """
        Scans video results to generate:
        1. Assessment completion alert
        2. High-risk movement alerts (valgus, severe asymmetry, excessive trunk lean, pelvic drop)
        3. Injury risk notifications (overall high/critical score, specific joint risks)
        """
        video = db.query(Video).filter(Video.id == video_id).first()
        if not video:
            return []

        athlete_id = video.athlete_id
        athlete = db.query(AthleteProfile).filter(AthleteProfile.id == athlete_id).first()
        user_id = athlete.user_id if athlete else None

        generated: List[Notification] = []

        # 1. Assessment Completion Alert
        comp_notif = self.create_notification(
            db=db,
            notification_type=NotificationType.ASSESSMENT_COMPLETION.value,
            severity=NotificationSeverity.INFO.value,
            title="Biomechanical Assessment Complete",
            message=f"Kinematic assessment and joint point-plotting for video #{video.id} ({video.movement_type}) have finished processing.",
            athlete_id=athlete_id,
            user_id=user_id,
            video_id=video_id,
            data={"movement_type": video.movement_type, "duration_sec": video.duration_sec}
        )
        generated.append(comp_notif)

        # 2. Movement Anomalies -> High-Risk Movement Alerts
        try:
            anomalies = anomaly_service.detect_anomalies(db, video_id)
            if anomalies and anomalies.events:
                valgus_events = [e for e in anomalies.events if e.metric == "knee_valgus"]
                asymmetry_events = [e for e in anomalies.events if e.metric == "knee_asymmetry"]
                trunk_events = [e for e in anomalies.events if e.metric == "trunk_lean"]
                pelvic_events = [e for e in anomalies.events if e.metric == "pelvic_drop"]

                if valgus_events:
                    worst_valgus = min((e.observed_value for e in valgus_events if e.observed_value is not None), default=0.7)
                    notif = self.create_notification(
                        db=db,
                        notification_type=NotificationType.HIGH_RISK_MOVEMENT.value,
                        severity=NotificationSeverity.CRITICAL.value if worst_valgus < 0.75 else NotificationSeverity.WARNING.value,
                        title="High-Risk Movement: Dynamic Knee Valgus",
                        message=f"Observed medial knee displacement (valgus ratio {worst_valgus:.2f}). Increases anterior cruciate ligament tension during deceleration.",
                        athlete_id=athlete_id,
                        user_id=user_id,
                        video_id=video_id,
                        data={"metric": "knee_valgus", "value": worst_valgus, "threshold": 0.85}
                    )
                    generated.append(notif)

                if asymmetry_events:
                    worst_asym = max((e.observed_value for e in asymmetry_events if e.observed_value is not None), default=25.0)
                    if worst_asym >= 20.0:
                        notif = self.create_notification(
                            db=db,
                            notification_type=NotificationType.HIGH_RISK_MOVEMENT.value,
                            severity=NotificationSeverity.WARNING.value,
                            title="High-Risk Movement: Bilateral Knee Asymmetry",
                            message=f"Knee flexion imbalance reached {worst_asym:.1f}% between left and right limbs, indicating asymmetric loading.",
                            athlete_id=athlete_id,
                            user_id=user_id,
                            video_id=video_id,
                            data={"metric": "knee_asymmetry", "value": worst_asym, "threshold": 15.0}
                        )
                        generated.append(notif)

                if trunk_events:
                    worst_trunk = max((e.observed_value for e in trunk_events if e.observed_value is not None), default=30.0)
                    notif = self.create_notification(
                        db=db,
                        notification_type=NotificationType.HIGH_RISK_MOVEMENT.value,
                        severity=NotificationSeverity.WARNING.value,
                        title="High-Risk Movement: Excessive Trunk Lean",
                        message=f"Trunk lean reached {worst_trunk:.1f}°, exceeding the recommended 30.0° threshold and altering core load distribution.",
                        athlete_id=athlete_id,
                        user_id=user_id,
                        video_id=video_id,
                        data={"metric": "trunk_lean", "value": worst_trunk, "threshold": 30.0}
                    )
                    generated.append(notif)

                if pelvic_events:
                    worst_pelvic = max((e.observed_value for e in pelvic_events if e.observed_value is not None), default=8.0)
                    notif = self.create_notification(
                        db=db,
                        notification_type=NotificationType.HIGH_RISK_MOVEMENT.value,
                        severity=NotificationSeverity.WARNING.value,
                        title="High-Risk Movement: Contralateral Pelvic Drop",
                        message=f"Pelvic obliquity reached {worst_pelvic:.1f}°, suggesting dynamic gluteus medius stabilization deficits.",
                        athlete_id=athlete_id,
                        user_id=user_id,
                        video_id=video_id,
                        data={"metric": "pelvic_drop", "value": worst_pelvic, "threshold": 8.0}
                    )
                    generated.append(notif)
        except Exception as e:
            print(f"Error checking anomaly alerts for video #{video_id}: {e}")

        # 3. Injury Risk Predictions -> Injury Risk Notifications
        try:
            risk_score = risk_scoring_service.calculate_risk_score(db, video_id=video_id)
            if risk_score and risk_score.injury_risk_score is not None:
                score_val = risk_score.injury_risk_score
                if score_val >= 75.0:
                    notif = self.create_notification(
                        db=db,
                        notification_type=NotificationType.INJURY_RISK.value,
                        severity=NotificationSeverity.CRITICAL.value,
                        title="Critical Injury Risk Score Flagged",
                        message=f"Overall screening risk score reached {score_val:.1f}/100 (Critical Risk Band). Immediate load reduction and clinical consultation recommended.",
                        athlete_id=athlete_id,
                        user_id=user_id,
                        video_id=video_id,
                        data={"score": score_val, "risk_category": "Critical"}
                    )
                    generated.append(notif)
                elif score_val >= 50.0:
                    notif = self.create_notification(
                        db=db,
                        notification_type=NotificationType.INJURY_RISK.value,
                        severity=NotificationSeverity.WARNING.value,
                        title="Elevated Injury Risk Score Detected",
                        message=f"Overall screening risk score is {score_val:.1f}/100 (High Risk Band). Review technique and movement quality suggestions.",
                        athlete_id=athlete_id,
                        user_id=user_id,
                        video_id=video_id,
                        data={"score": score_val, "risk_category": "High"}
                    )
                    generated.append(notif)

            # Check specific categories (ACL, Hamstrings)
            predictions = risk_scoring_service.predict_injury_risks(db, athlete_id=athlete_id, video_id=video_id)
            for cat_id, pred in (predictions.categories.items() if isinstance(predictions.categories, dict) else []):
                if pred.risk_level in ["High", "Critical"]:
                    notif = self.create_notification(
                        db=db,
                        notification_type=NotificationType.INJURY_RISK.value,
                        severity=NotificationSeverity.CRITICAL.value if pred.risk_level == "Critical" else NotificationSeverity.WARNING.value,
                        title=f"{pred.name} Alert ({pred.risk_level} Risk)",
                        message=f"Model estimated {pred.probability_pct:.1f}% risk for {pred.name}. Primary contributing factors: {', '.join(pred.risk_factors[:2]) if pred.risk_factors else 'Kinematic load'}.",
                        athlete_id=athlete_id,
                        user_id=user_id,
                        video_id=video_id,
                        data={"category": pred.name, "probability": pred.probability_pct, "risk_level": pred.risk_level}
                    )
                    generated.append(notif)
        except Exception as e:
            print(f"Error checking injury risk alerts for video #{video_id}: {e}")

        # Also trigger training load and recovery checks for this athlete
        if athlete_id:
            load_notifs = self.generate_training_load_alerts(db, athlete_id)
            rec_notifs = self.generate_recovery_reminders(db, athlete_id)
            generated.extend(load_notifs)
            generated.extend(rec_notifs)

        return generated

    def generate_training_load_alerts(self, db: Session, athlete_id: int) -> List[Notification]:
        """
        Module 11: Training load warnings
        Checks acute-to-chronic workload ratio (ACWR), session frequency, and fatigue markers.
        """
        athlete = db.query(AthleteProfile).filter(AthleteProfile.id == athlete_id).first()
        if not athlete:
            return []

        user_id = athlete.user_id
        training_load = athlete.training_load or {}
        generated: List[Notification] = []

        # Check acute vs chronic ratio
        acute_load = training_load.get("acute_load", 0)
        chronic_load = training_load.get("chronic_load", 0)
        sessions_per_week = training_load.get("sessions_per_week", 0)

        # Standard sports science ACWR: acute / chronic
        acwr = (acute_load / chronic_load) if chronic_load and chronic_load > 0 else None

        if acwr and acwr > 1.5:
            notif = self.create_notification(
                db=db,
                notification_type=NotificationType.TRAINING_LOAD.value,
                severity=NotificationSeverity.WARNING.value,
                title="Training Load Warning: ACWR Spike (> 1.5)",
                message=f"Acute-to-chronic workload ratio reached {acwr:.2f}. Rapid volume surges significantly elevate neuromuscular fatigue and tissue strain.",
                athlete_id=athlete_id,
                user_id=user_id,
                data={"acwr": acwr, "acute_load": acute_load, "chronic_load": chronic_load}
            )
            generated.append(notif)
        elif sessions_per_week >= 6:
            notif = self.create_notification(
                db=db,
                notification_type=NotificationType.TRAINING_LOAD.value,
                severity=NotificationSeverity.WARNING.value,
                title="Training Load Warning: High Session Frequency",
                message=f"Recorded {sessions_per_week} weekly training sessions. Ensure structured deload intervals to mitigate cumulative tendon fatigue.",
                athlete_id=athlete_id,
                user_id=user_id,
                data={"sessions_per_week": sessions_per_week}
            )
            generated.append(notif)

        return generated

    def generate_recovery_reminders(self, db: Session, athlete_id: int) -> List[Notification]:
        """
        Module 11: Recovery reminders
        Generates targeted active flush protocols, mobility sessions, and sleep/hydration guidelines.
        """
        athlete = db.query(AthleteProfile).filter(AthleteProfile.id == athlete_id).first()
        if not athlete:
            return []

        user_id = athlete.user_id
        generated: List[Notification] = []

        # Check recent recommendations for recovery protocols
        recent_video = db.query(Video).filter(
            Video.athlete_id == athlete_id,
            Video.status == "completed"
        ).order_by(desc(Video.created_at)).first()

        video_id = recent_video.id if recent_video else None
        
        try:
            recs = recommendation_service.generate_recommendations(
                db, video_id=video_id, athlete_id=athlete_id
            )
            recovery_items = recs.recovery_plan
            if recovery_items:
                top_item = recovery_items[0]
                notif = self.create_notification(
                    db=db,
                    notification_type=NotificationType.RECOVERY_REMINDER.value,
                    severity=NotificationSeverity.INFO.value,
                    title=f"Recovery Reminder: {top_item.title}",
                    message=f"{top_item.description} ({top_item.frequency or 'Post-session'}).",
                    athlete_id=athlete_id,
                    user_id=user_id,
                    video_id=video_id,
                    data={"target_region": top_item.target_region, "frequency": top_item.frequency}
                )
                generated.append(notif)
            else:
                # Default targeted recovery protocol
                notif = self.create_notification(
                    db=db,
                    notification_type=NotificationType.RECOVERY_REMINDER.value,
                    severity=NotificationSeverity.INFO.value,
                    title="Recovery Protocol: Post-Session Mobility & Hydration",
                    message="Perform 10 minutes of low-intensity cool-down cycling and targeted hamstring/hip flexor dynamic stretching.",
                    athlete_id=athlete_id,
                    user_id=user_id,
                    video_id=video_id,
                    data={"focus": "hip_mobility_and_hydration"}
                )
                generated.append(notif)
        except Exception as e:
            print(f"Error generating recovery reminders: {e}")

        return generated

notification_service = NotificationService()
