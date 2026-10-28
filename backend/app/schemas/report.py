from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class ReportMetadata(BaseModel):
    report_id: str
    report_type: str # "injury_risk", "biomechanical", "movement_analysis", "athlete_performance", "rehabilitation"
    generated_at: str
    athlete_name: str
    athlete_id: int
    sport: str
    video_id: Optional[int] = None
    movement_type: Optional[str] = None
    disclaimer: str

class ReportSection(BaseModel):
    title: str
    description: Optional[str] = None
    data: Dict[str, Any] = {}
    table_headers: Optional[List[str]] = None
    table_rows: Optional[List[List[Any]]] = None
    callouts: Optional[List[str]] = None

class FullReportData(BaseModel):
    metadata: ReportMetadata
    summary: Dict[str, Any]
    sections: List[ReportSection]
    recommendations: Optional[List[Dict[str, Any]]] = None
