from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.models.video import Video
from app.services import athlete_service
from app.api.deps import get_current_active_user
from app.services.assessment_service import get_assessment

router = APIRouter()

@router.get("/{video_id}")
def get_video_assessment(
    video_id: int,
    activity: str = Query(..., description="Activity type (e.g., squatting, running)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video not found")
        
    profile = athlete_service.get_profile_by_id(db, video.athlete_id)
    if current_user.role == "athlete":
        if profile.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Not authorized to access this assessment")
    elif current_user.role != "administrator":
        is_assigned = athlete_service.check_staff_assigned_to_athlete(db, staff_id=current_user.id, athlete_id=profile.id)
        if not is_assigned:
            raise HTTPException(status_code=403, detail="Not authorized to access this assessment")

    assessment = get_assessment(db, video_id, activity)
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment data not available")
        
    return assessment
