from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from datetime import datetime
from app.database import Base

class InjuryRiskAssessment(Base):
    __tablename__ = "injury_risk_assessments"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False)
    athlete_id = Column(Integer, ForeignKey("athletes.id"), nullable=True)
    analysis_id = Column(Integer, ForeignKey("biomechanical_analyses.id"), nullable=False)

    # Weighted Scoring Model
    # Injury Risk Score = Biomechanical Deviations (35%) + Historical Injury Factors (20%) + Movement Asymmetry (20%) + Training Load (15%) + Fatigue (10%)
    overall_injury_risk_score = Column(Float, nullable=False) # 0 - 100
    risk_category = Column(String(50), nullable=False) # Low Risk, Moderate Risk, High Risk, Critical Risk

    # Component Scores
    biomechanical_deviation_score = Column(Float, default=0.0) # 0 - 100
    historical_injury_factor_score = Column(Float, default=0.0)
    movement_asymmetry_score = Column(Float, default=0.0)
    training_load_indicator_score = Column(Float, default=0.0)
    fatigue_indicator_score = Column(Float, default=0.0)

    movement_quality_score = Column(Float, default=0.0) # 0 - 100
    biomechanical_efficiency_score = Column(Float, default=0.0)
    fatigue_risk_score = Column(Float, default=0.0)
    overall_athlete_health_score = Column(Float, default=0.0)

    # Specific Injury Categories Breakdown
    # ACL, Hamstring, Ankle Sprain, Shoulder, Lower Back, Overuse
    category_risks = Column(JSON, default=dict)

    # Movement Anomaly Detection Events
    anomalies_detected = Column(JSON, default=list)

    # Corrective Recommendations
    # exercises, mobility, strengthening, recovery, training modifications
    corrective_recommendations = Column(JSON, default=dict)

    created_at = Column(DateTime, default=datetime.utcnow)
