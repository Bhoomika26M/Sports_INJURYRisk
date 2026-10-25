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

class RecommendationResponse(BaseModel):
    video_id: Optional[int] = None
    athlete_id: Optional[int] = None
    recommendations: List[Recommendation]
    disclaimer: str = "These recommendations are strictly educational and do not constitute medical advice, diagnosis, or rehabilitation prescriptions. Always consult a qualified healthcare or sports professional."
