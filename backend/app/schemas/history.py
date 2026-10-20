"""Schemas for athlete analysis history and baseline comparison."""

from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime


class MetricDelta(BaseModel):
    """One metric compared against the athlete's rolling baseline."""

    metric: str
    label: str
    unit: str = ""
    current: float
    baseline: float
    delta: float
    percent_change: Optional[float] = None
    z_score: float
    verdict: str  # deterioration | improvement | neutral
    notable: bool
    baseline_range: List[float] = []


class BaselineMetric(BaseModel):
    """One reference value from the athlete's rolling baseline."""

    metric: str
    label: str
    unit: str = ""
    mean: float
    min: float
    max: float
    samples: int = 0


class BaselineComparison(BaseModel):
    """How one analysis compares with the athlete's prior same-activity work."""

    status: str  # no_history | insufficient_history | stable | changed
    baseline_size: int = 0
    baseline_window: int = 0
    summary: str = ""
    deltas: List[MetricDelta] = []
    flags: List[MetricDelta] = []
    deteriorations: List[str] = []
    improvements: List[str] = []
    # The reference values themselves, so the baseline can be shown even when
    # there is not enough history to produce a comparison.
    baseline_metrics: List[BaselineMetric] = []


class HistoryEntry(BaseModel):
    """A single point in an athlete's analysis timeline."""

    id: int
    video_id: int
    activity_type: str
    sequence_index: int
    performed_at: datetime
    overall_risk_score: float
    risk_level: str
    findings_count: int
    metrics: Dict[str, Any] = {}
    baseline_comparison: Optional[BaselineComparison] = None

    class Config:
        from_attributes = True


class TrendSummary(BaseModel):
    """Aggregate trend for one activity type across the athlete's history."""

    activity_type: str
    analysis_count: int
    first_risk_score: Optional[float] = None
    latest_risk_score: Optional[float] = None
    mean_risk_score: Optional[float] = None
    risk_change: Optional[float] = None
    direction: str = "unknown"  # improving | worsening | stable | unknown
    latest_performed_at: Optional[datetime] = None


class AthleteHistoryResponse(BaseModel):
    """Full history payload for an athlete."""

    athlete_id: int
    athlete_public_id: Optional[str] = None
    total_analyses: int
    trends: List[TrendSummary] = []
    entries: List[HistoryEntry] = []
