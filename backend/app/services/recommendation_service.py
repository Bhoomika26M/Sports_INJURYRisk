from typing import List, Dict, Any
from sqlalchemy.orm import Session
from app.schemas.recommendation import Recommendation, RecommendationResponse
from app.services.anomaly_service import anomaly_service
from app.services.assessment_service import get_assessment
from app.models.athlete import AthleteProfile

class RecommendationEngine:
    def __init__(self):
        # A curated library of generic educational suggestions.
        self.library = {
            "professional_assessment_asymmetry": Recommendation(
                id="professional_assessment_asymmetry",
                title="Seek Assessment by a Physiotherapist",
                triggering_finding="High knee asymmetry or persistent movement imbalance detected.",
                rationale="Significant asymmetry can sometimes lead to compensatory patterns. A clinical professional can accurately measure strength and mobility deficits.",
                intended_audience="Athletes experiencing pain or showing persistent, significant movement imbalances.",
                limitations="This is a general screening finding, not a diagnosis of an underlying injury.",
                source_review_status="General Sports Science Consensus (Educational)",
                description="Consider booking a consultation with a qualified physiotherapist to undergo a formal musculoskeletal assessment.",
                action_type="consult_professional"
            ),
            "coach_technique_trunk": Recommendation(
                id="coach_technique_trunk",
                title="Discuss Trunk Control with a Qualified Coach",
                triggering_finding="Excessive forward trunk lean observed during movement.",
                rationale="Trunk lean can alter center of mass and load distribution. Coaching feedback can help cue proper postural control.",
                intended_audience="Athletes refining their jump, landing, or running mechanics.",
                limitations="Does not address potential underlying core weakness or mobility restrictions, which require physical assessment.",
                source_review_status="Coaching Best Practices (Educational)",
                description="Review your movement technique with a qualified coach to ensure appropriate postural alignment during dynamic tasks.",
                action_type="technique_review"
            ),
            "data_quality_reassess": Recommendation(
                id="data_quality_reassess",
                title="Re-record with Better Quality or Seek Professional Input",
                triggering_finding="Low confidence data, tracking errors, or missing landmarks.",
                rationale="Computer vision algorithms cannot safely or accurately analyze movement when the input video is poor, leading to potentially dangerous misinterpretations.",
                intended_audience="Users recording videos for analysis.",
                limitations="No kinematic conclusions can be drawn.",
                source_review_status="System Quality Control",
                description="The video quality was insufficient. Please re-record ensuring full body visibility and good lighting, or seek an in-person professional assessment rather than relying on estimated data.",
                action_type="consult_professional"
            ),
            "review_training_load": Recommendation(
                id="review_training_load",
                title="Review Training Progression",
                triggering_finding="Movement variability or potential fatigue indicators.",
                rationale="Unusual movement variability might indicate emerging fatigue or lack of movement familiarity.",
                intended_audience="Athletes managing high training volumes.",
                limitations="Does not replace clinical monitoring for overtraining syndrome.",
                source_review_status="General Load Management Principles (Educational)",
                description="Discuss your current training volumes and recovery periods with your coach or sports scientist to ensure safe progressions.",
                action_type="educational"
            )
        }

    def generate_recommendations(self, db: Session, video_id: int, activity: str = "running") -> RecommendationResponse:
        recs: List[Recommendation] = []
        added_ids = set()
        
        def add_rec(rec_id: str):
            if rec_id not in added_ids and rec_id in self.library:
                recs.append(self.library[rec_id])
                added_ids.add(rec_id)

        # 1. Gather anomalies
        anomaly_data = anomaly_service.detect_anomalies(db, video_id)
        has_quality_issues = any(e.is_data_quality_issue for e in anomaly_data.events)
        
        # 2. Gather assessment
        assessment = get_assessment(db, video_id, activity)
        flags = assessment.get("flags", []) if assessment else []
        warnings = assessment.get("warnings", []) if assessment else []
        
        # Rule Evaluation
        
        # Rule A: Conflicting or Insufficient Input
        # If there are data quality issues, we shouldn't recommend anything except re-assessment
        if has_quality_issues or any("unreliable" in w.lower() for w in warnings):
            add_rec("data_quality_reassess")
            return RecommendationResponse(video_id=video_id, recommendations=recs)
            
        # Rule B: Trunk lean
        has_trunk_lean = any("trunk lean" in f.lower() for f in flags) or any(e.metric == "trunk_lean" for e in anomaly_data.events)
        if has_trunk_lean:
            add_rec("coach_technique_trunk")
            
        # Rule C: Asymmetry
        has_asymmetry = any("asymmetrical" in f.lower() or "symmetry" in f.lower() for f in flags) or any(e.metric == "knee_asymmetry" for e in anomaly_data.events)
        if has_asymmetry:
            add_rec("professional_assessment_asymmetry")
            
        # Rule D: Variability
        has_variability = any(e.metric == "movement_variability" for e in anomaly_data.events)
        if has_variability:
            add_rec("review_training_load")
            
        return RecommendationResponse(video_id=video_id, recommendations=recs)

recommendation_service = RecommendationEngine()
