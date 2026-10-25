from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.api import deps
from app.schemas.recommendation import RecommendationResponse
from app.services.recommendation_service import recommendation_service

router = APIRouter()

@router.get("/{video_id}", response_model=RecommendationResponse)
def get_recommendations(
    video_id: int,
    activity: str = Query("running", description="Activity type for assessment context"),
    db: Session = Depends(deps.get_db),
    current_user = Depends(deps.get_current_user)
) -> RecommendationResponse:
    """
    Get explainable, rule-based recommendations based on movement analysis.
    Preserves role-based access by requiring authentication.
    """
    # Any authenticated user can get recommendations for their video for now.
    # In a full app, check if video belongs to user.
    response = recommendation_service.generate_recommendations(db, video_id, activity)
    if not response:
        raise HTTPException(status_code=404, detail="Could not generate recommendations")
    return response
