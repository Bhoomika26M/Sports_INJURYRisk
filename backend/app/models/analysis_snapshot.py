from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    DateTime,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base


class AnalysisSnapshot(Base):
    """A durable, denormalized record of one completed analysis.

    Why this exists
    ---------------
    Before this table, an athlete's "history" could only be reconstructed by
    joining ``videos`` -> ``pose_analyses`` -> ``biomechanical_analyses`` and
    **recomputing** the injury-risk score from raw keypoints on every request
    (see ``GET /api/v1/risk/{video_id}``, which is not persisted). That made
    trends impossible to query cheaply and meant there was nothing stable to
    compare a new video against.

    A snapshot is written once when processing completes. It stores the risk
    result and the handful of headline metrics we want to trend, plus the
    comparison against the athlete's rolling baseline of **prior, same-activity**
    analyses. Reading history is then a single indexed query.

    Design notes
    ------------
    * ``athlete_id`` is denormalized onto the row (it is also reachable via
      ``video``), so history queries never need to touch ``videos``.
    * ``activity_type`` is denormalized for the same reason and because
      comparisons are only valid within one activity.
    * ``sequence_index`` is the 1-based position of this analysis within the
      athlete+activity timeline, assigned at insert time. It makes ordering
      deterministic even when two analyses share a ``created_at``.
    * ``baseline_comparison`` stores the *result* of the comparison at the time
      the analysis completed. It is a historical fact ("how did this session
      compare to what came before it?") and must not be recomputed later, since
      later analyses would change a rolling baseline.
    * ``metrics`` holds the trended headline numbers (risk score plus selected
      biomechanical/quality metrics). Full fidelity remains in
      ``pose_analyses`` / ``biomechanical_analyses``.
    """

    __tablename__ = "analysis_snapshots"

    id = Column(Integer, primary_key=True, index=True)

    athlete_id = Column(
        Integer, ForeignKey("athletes.id"), nullable=False, index=True
    )
    video_id = Column(Integer, ForeignKey("videos.id"), nullable=False, unique=True)
    pose_analysis_id = Column(
        Integer, ForeignKey("pose_analyses.id"), nullable=True
    )

    # Denormalized context (see class docstring).
    activity_type = Column(String, nullable=False)
    sequence_index = Column(Integer, nullable=False)

    # Timing. ``performed_at`` is the video's own upload/created time if known,
    # otherwise the analysis completion time; it is what we sort history by.
    performed_at = Column(DateTime, nullable=False, index=True)

    # Headline risk result (mirrors RiskAssessment).
    overall_risk_score = Column(Float, nullable=False, default=0.0)
    risk_level = Column(String, nullable=False, default="low")
    findings_count = Column(Integer, nullable=False, default=0)

    # Trended metrics: {"risk_score": .., "knee_asymmetry": .., ...}
    metrics = Column(JSON, nullable=True)

    # The baseline this analysis was measured against, frozen at completion.
    # {metric: {mean, mad, count, min, max}} - stored so the baseline itself can
    # be displayed even for the first analysis (which has no comparison).
    baseline = Column(JSON, nullable=True)

    # Comparison vs the rolling baseline of prior same-activity analyses.
    # {status, baseline_size, deltas: {...}, flags: [...], summary: "..."}
    baseline_comparison = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    athlete = relationship("Athlete", backref="analysis_snapshots")
    video = relationship("Video", backref="analysis_snapshot")

    __table_args__ = (
        Index(
            "ix_analysis_snapshots_athlete_activity_time",
            "athlete_id",
            "activity_type",
            "performed_at",
        ),
    )
