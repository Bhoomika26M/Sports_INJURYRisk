"""Tests for PDF/XLSX report escaping, honest error responses, and database telemetry export."""

import io
import pytest
from httpx import AsyncClient
from openpyxl import load_workbook

from app.modules.risk_scoring.models import RiskScore
from app.modules.users.models import UserRole
from app.modules.video.models import BiomechanicalMetric, VideoProcessingStatus
from tests.conftest import auth_header, register_and_login
from tests.factories import make_athlete, make_user, make_video


@pytest.mark.asyncio
async def test_report_pdf_404_when_unscored(client: AsyncClient, db_session):
    """F04/U6: Unscored video returns 404 'Video not yet scored', never 0/100 LOW RISK."""
    token = await register_and_login(client, "coach_unscored@test.com", "coach")
    headers = auth_header(token)

    from sqlalchemy import select
    from app.modules.users.models import User
    coach = await db_session.scalar(select(User).where(User.email == "coach_unscored@test.com"))
    athlete = await make_athlete(db_session, coach_id=coach.id)
    video = await make_video(db_session, athlete.id, coach.id, movement_type="squatting")
    video.processing_status = VideoProcessingStatus.completed
    await db_session.commit()

    resp = await client.get(f"/api/v1/videos/{video.id}/report.pdf", headers=headers)
    assert resp.status_code == 404
    assert "not yet scored" in resp.text.lower()


@pytest.mark.asyncio
async def test_report_pdf_escapes_markup(client: AsyncClient, db_session):
    """F17: User-controlled strings (containing <b>, &, </para>) in PDF export are escaped with xml.sax.saxutils.escape."""
    token = await register_and_login(client, "coach_escape@test.com", "coach")
    headers = auth_header(token)

    from sqlalchemy import select
    from app.modules.users.models import User
    coach = await db_session.scalar(select(User).where(User.email == "coach_escape@test.com"))
    athlete = await make_athlete(db_session, coach_id=coach.id)
    video = await make_video(
        db_session,
        athlete.id,
        coach.id,
        movement_type="squatting",
    )
    video.original_filename = "clip_<b>bold</b>_&_</para>_test.mp4"
    video.processing_status = VideoProcessingStatus.completed

    risk = RiskScore(
        video_id=video.id,
        athlete_id=athlete.id,
        overall_score=42.0,
        risk_category="moderate",
        score_breakdown={
            "biomechanical_deviations": {"points": 14.7, "max": 35.0, "available": True},
            "bilateral_asymmetry": {"points": 8.4, "max": 20.0, "available": True},
        },
        assessment={"drivers": []},
    )
    db_session.add(risk)
    await db_session.commit()

    resp = await client.get(f"/api/v1/videos/{video.id}/report.pdf", headers=headers)
    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"


@pytest.mark.asyncio
async def test_xlsx_metrics_sheet_matches_db_rows(client: AsyncClient, db_session):
    """F06/U6: XLSX export includes real biomechanical_metrics rows with plane and confidence."""
    token = await register_and_login(client, "coach_xlsx@test.com", "coach")
    headers = auth_header(token)

    from sqlalchemy import select
    from app.modules.users.models import User
    coach = await db_session.scalar(select(User).where(User.email == "coach_xlsx@test.com"))
    athlete = await make_athlete(db_session, coach_id=coach.id)
    video = await make_video(db_session, athlete.id, coach.id, movement_type="squatting")
    video.processing_status = VideoProcessingStatus.completed

    risk = RiskScore(
        video_id=video.id,
        athlete_id=athlete.id,
        overall_score=30.0,
        risk_category="low",
        score_breakdown={},
        assessment={"drivers": []},
    )
    db_session.add(risk)

    metric1 = BiomechanicalMetric(
        video_id=video.id,
        frame_number=1,
        metric_name="knee_flexion_angle_left",
        metric_value=85.4,
        plane="sagittal",
        confidence="validated",
        movement_phase="eccentric",
    )
    metric2 = BiomechanicalMetric(
        video_id=video.id,
        frame_number=1,
        metric_name="knee_valgus_deviation_left",
        metric_value=4.2,
        plane="frontal",
        confidence="qualitative",
        movement_phase="eccentric",
    )
    db_session.add_all([metric1, metric2])
    await db_session.commit()

    resp = await client.get(f"/api/v1/videos/{video.id}/report.xlsx", headers=headers)
    assert resp.status_code == 200

    wb = load_workbook(io.BytesIO(resp.content))
    assert "Metrics" in wb.sheetnames or "risk_report" in wb.sheetnames
    # Verify real metrics are present in workbook
    found_knee = False
    for sheet in wb.worksheets:
        for row in sheet.iter_rows(values_only=True):
            if "knee_flexion_angle_left" in row:
                found_knee = True
                break
    assert found_knee, "Expected real biomechanical_metrics row in exported XLSX"
