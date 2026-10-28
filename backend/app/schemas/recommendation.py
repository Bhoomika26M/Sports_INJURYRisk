from pydantic import BaseModel, Field
from typing import List, Optional

class Recommendation(BaseModel):
    id: str
    title: str
    triggering_finding: str
    rationale: str
    intended_audience: str
    limitations: str
    source_review_status: str
    description: str
    action_type: str = Field(..., description="'consult_professional', 'educational', 'technique_review'")
    
    # Module 9: Corrective Recommendation Categories
    category: str = Field(
        "exercise", 
        description="'exercise', 'mobility', 'strengthening', 'recovery', 'training_modification', 'consult_professional', 'technique_review'"
    )
    target_region: Optional[str] = None
    sets_and_reps: Optional[str] = None
    frequency: Optional[str] = None

class RecommendationResponse(BaseModel):
    video_id: Optional[int] = None
    athlete_id: Optional[int] = None
    recommendations: List[Recommendation]
    disclaimer: str = "These recommendations are strictly educational and do not constitute medical advice, diagnosis, or rehabilitation prescriptions. Always consult a qualified healthcare or sports professional."
    
    # Categorized buckets for Module 9
    exercise_recommendations: List[Recommendation] = []
    mobility_suggestions: List[Recommendation] = []
    strengthening_recommendations: List[Recommendation] = []
    recovery_plan: List[Recommendation] = []
    training_modifications: List[Recommendation] = []
