from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime, timezone
from app.database import Base


class ReportRecord(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    report_title = Column(String, nullable=False)
    report_type = Column(String, default="BIOMECHANICAL_ASSESSMENT")  # BIOMECHANICAL_ASSESSMENT, INJURY_RISK, REHABILITATION, TEAM_SUMMARY
    athlete_id = Column(String, nullable=True, index=True)
    athlete_name = Column(String, nullable=True)
    generated_by = Column(String, default="System")
    summary = Column(Text, default="")
    data_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
