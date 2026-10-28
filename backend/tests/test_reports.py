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
