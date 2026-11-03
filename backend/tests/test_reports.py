import io
import pytest
from app.models.athlete import AthleteProfile
from app.services.report_service import report_service

def test_report_generation_all_five_types(db_session, test_user):
    profile = AthleteProfile(
        user_id=test_user.id,
        sport_type="Track & Field",
        age=23,
        height_cm=182,
        weight_kg=74,
        training_load={"acute_load": 1500, "chronic_load": 1100, "sessions_per_week": 4}
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    report_types = ["injury_risk", "biomechanical", "movement_analysis", "athlete_performance", "rehabilitation"]

    for r_type in report_types:
        report_data = report_service.get_report_data(
            db=db_session,
            athlete_id=profile.id,
            report_type=r_type
        )
        assert report_data is not None
        assert report_data.metadata.athlete_id == profile.id
        assert report_data.metadata.report_type == r_type
        assert len(report_data.sections) >= 1
        assert "CONFIDENTIAL" in report_data.metadata.disclaimer

def test_pdf_export(db_session, test_user):
    profile = AthleteProfile(
        user_id=test_user.id,
        sport_type="Basketball",
        training_load={"acute_load": 1200, "chronic_load": 1000}
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    report_data = report_service.get_report_data(
        db=db_session,
        athlete_id=profile.id,
        report_type="injury_risk"
    )

    pdf_bytes = report_service.generate_pdf_report(report_data)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 500
    # PDF starts with magic header %PDF
    assert pdf_bytes.startswith(b"%PDF")

def test_excel_export(db_session, test_user):
    profile = AthleteProfile(
        user_id=test_user.id,
        sport_type="Volleyball",
        training_load={"acute_load": 1400, "chronic_load": 1000}
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    report_data = report_service.get_report_data(
        db=db_session,
        athlete_id=profile.id,
        report_type="biomechanical"
    )

    excel_bytes = report_service.generate_excel_report(report_data)
    assert isinstance(excel_bytes, bytes)
    assert len(excel_bytes) > 500
    # ZIP / XLSX starts with PK\x03\x04
    assert excel_bytes.startswith(b"PK\x03\x04")

def test_report_generation_with_completed_video(db_session, test_user):
    from app.models.video import Video
    profile = AthleteProfile(
        user_id=test_user.id,
        sport_type="Basketball",
        age=22,
        height_cm=185,
        weight_kg=80,
        training_load={"acute_load": 1500, "chronic_load": 1200}
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    video = Video(
        athlete_id=profile.id,
        uploader_id=test_user.id,
        filename="test_video_rep.mp4",
        original_filename="test_video.mp4",
        file_path="uploads/test_video_rep.mp4",
        format="mp4",
        size_bytes=1000,
        status="completed",
        movement_type="jump"
    )
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)

    report_data = report_service.get_report_data(
        db=db_session,
        athlete_id=profile.id,
        report_type="injury_risk",
        video_id=video.id
    )
    assert report_data is not None
    assert len(report_data.sections) >= 1
    # Verify component rows parsed correctly without 'str' object has no attribute 'name'
    comp_section = next((s for s in report_data.sections if s.title == "Multifactorial Risk Component Breakdown"), None)
    assert comp_section is not None
    assert len(comp_section.table_rows) > 0

    # Also test all 5 types with video to ensure zero runtime crashes
    for rt in ["biomechanical", "movement_analysis", "athlete_performance", "rehabilitation"]:
        r_data = report_service.get_report_data(
            db=db_session,
            athlete_id=profile.id,
            report_type=rt,
            video_id=video.id
        )
        assert r_data is not None

    # Test PDF and Excel export with this video-backed data
    pdf_bytes = report_service.generate_pdf_report(report_data)
    assert pdf_bytes.startswith(b"%PDF")

    excel_bytes = report_service.generate_excel_report(report_data)
    assert excel_bytes.startswith(b"PK\x03\x04")

def test_consolidated_individual_report_and_team_excel(db_session, test_user):
    from app.models.user import User, UserRole
    from app.models.video import Video
    from app.services import athlete_service
    from openpyxl import load_workbook

    # Create coach
    coach = User(
        email="coach_test@example.com",
        hashed_password="hash",
        full_name="Coach Miller",
        role=UserRole.COACH.value,
        is_active=True
    )
    db_session.add(coach)
    db_session.commit()
    db_session.refresh(coach)

    # Create athlete assigned to coach
    profile = AthleteProfile(
        user_id=test_user.id,
        sport_type="Basketball",
        position="Forward",
        age=23,
        height_cm=190,
        weight_kg=85,
        coach_id=coach.id
    )
    db_session.add(profile)
    db_session.commit()
    db_session.refresh(profile)

    # Also associate in athlete_assignments
    athlete_service.assign_staff_to_athlete(db_session, athlete_id=profile.id, staff_id=coach.id)

    # Completed video trial
    video = Video(
        athlete_id=profile.id,
        uploader_id=test_user.id,
        filename="jump_test.mp4",
        original_filename="jump.mp4",
        file_path="uploads/jump_test.mp4",
        format="mp4",
        size_bytes=2048,
        status="completed",
        movement_type="jump",
        duration_sec=3.5,
        fps=30.0,
        width=1920,
        height=1080
    )
    db_session.add(video)
    db_session.commit()
    db_session.refresh(video)

    # 1. Test Comprehensive Consolidated Individual Report
    rep = report_service.get_report_data(
        db=db_session,
        athlete_id=profile.id,
        report_type="comprehensive",
        video_id=video.id
    )
    assert rep is not None
    assert rep.summary["title"] == "Comprehensive Movement & Injury Risk Screening Report"
    assert len(rep.sections) >= 6
    assert any("Measured Biomechanical" in s.title for s in rep.sections)
    assert any("Movement Quality" in s.title for s in rep.sections)
    assert any("Musculoskeletal Injury Risk" in s.title for s in rep.sections)

    # Verify single PDF generation for comprehensive report
    pdf = report_service.generate_pdf_report(rep)
    assert pdf.startswith(b"%PDF")

    # 2. Test 4-Sheet Team Excel Workbook for Coach
    team_excel = report_service.generate_team_excel_report(
        db=db_session,
        staff_user=coach
    )
    assert team_excel.startswith(b"PK\x03\x04")

    # Verify exact 4 sheets
    wb = load_workbook(io.BytesIO(team_excel))
    sheet_names = wb.sheetnames
    assert "Team Overview" in sheet_names
    assert "Athlete Risk Summary" in sheet_names
    assert "Biomechanical Analysis" in sheet_names
    assert "Analysis History" in sheet_names



