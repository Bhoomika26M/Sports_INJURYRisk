import io
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.video import VideoRecord
from app.models.athlete import Athlete
from app.models.biomechanics import BiomechanicalAnalysis
from app.models.injury_risk import InjuryRiskAssessment

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

# openpyxl imports for Excel generation
import openpyxl
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

router = APIRouter(prefix="/reports", tags=["Reports & Analytics Exports"])

@router.get("/{video_id}/pdf")
def export_pdf_report(video_id: int, db: Session = Depends(get_db)):
    video = db.query(VideoRecord).filter(VideoRecord.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video record not found")

    analysis = db.query(BiomechanicalAnalysis).filter(BiomechanicalAnalysis.video_id == video_id).first()
    risk = db.query(InjuryRiskAssessment).filter(InjuryRiskAssessment.video_id == video_id).first()

    athlete = None
    if video.athlete_id:
        athlete = db.query(Athlete).filter(Athlete.id == video.athlete_id).first()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a")
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b")
    )
    heading2_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=10,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#334155")
    )
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#64748b")
    )

    story = []

    # Title & Subtitle Header
    story.append(Paragraph("KINEMATIX", title_style))
    story.append(Paragraph("Sports Movement Biomechanics &amp; Injury Risk Intelligence Report", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=12))

    # Metadata Table
    athlete_name = athlete.name if athlete else "Unassigned Athlete"
    athlete_code = athlete.athlete_code if athlete else "N/A"
    sport_type = athlete.sport_type if athlete else video.activity_type
    acwr_val = str(athlete.acwr) if athlete else "1.15"

    meta_data = [
        [
            Paragraph(f"<b>Athlete:</b> {athlete_name} ({athlete_code})", body_style),
            Paragraph(f"<b>Sport:</b> {sport_type}", body_style),
            Paragraph(f"<b>ACWR:</b> {acwr_val}", body_style)
        ],
        [
            Paragraph(f"<b>Session Title:</b> {video.title}", body_style),
            Paragraph(f"<b>Activity:</b> {video.activity_type}", body_style),
            Paragraph(f"<b>Duration / FPS:</b> {video.duration_seconds}s / {video.fps} fps", body_style)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[200, 170, 170])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # Section 1: Overall Risk Summary
    story.append(Paragraph("1. Overall Injury Risk &amp; Weighted Scoring", heading2_style))
    risk_score = risk.overall_injury_risk_score if risk else 0.0
    risk_cat = risk.risk_category if risk else "Low Risk"

    risk_data = [
        ["Composite Risk Score", f"{risk_score} / 100", f"Category: {risk_cat}"],
        ["Biomechanical Deviations (35%)", f"{risk.biomechanical_deviation_score if risk else 0.0}", "Frontal valgus, trunk lean, impact shock"],
        ["Historical Injury Factors (20%)", f"{risk.historical_injury_factor_score if risk else 0.0}", "Prior surgical or soft-tissue vulnerability"],
        ["Movement Asymmetry Index (20%)", f"{risk.movement_asymmetry_score if risk else 0.0}", "Bilateral kinetic discrepancy"],
        ["Training Load Indicator (15%)", f"{risk.training_load_indicator_score if risk else 0.0}", "Acute-to-Chronic Workload Ratio (ACWR)"],
        ["Kinematic Fatigue Drift (10%)", f"{risk.fatigue_indicator_score if risk else 0.0}", "Temporal technique decay across session"],
    ]
    risk_table = Table(risk_data, colWidths=[220, 110, 210])
    risk_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#ffffff")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(risk_table)
    story.append(Spacer(1, 12))

    # Section 2: Biomechanical Metrics
    story.append(Paragraph("2. Biomechanical Measurements &amp; Normative Baselines", heading2_style))
    m = analysis if analysis else None

    bio_data = [
        ["Measurement Metric", "Athlete Value", "Reference Benchmark", "Clinical Assessment"],
        ["Dynamic Knee Valgus (L Peak)", f"{m.knee_valgus_left_max if m else 0.0}°", "< 10.0°", "Nominal" if (m and m.knee_valgus_left_max < 10) else "Elevated ACL Risk"],
        ["Dynamic Knee Valgus (R Peak)", f"{m.knee_valgus_right_max if m else 0.0}°", "< 10.0°", "Nominal" if (m and m.knee_valgus_right_max < 10) else "Severe Medial Collapse" if (m and m.knee_valgus_right_max > 15) else "Elevated"],
        ["Lateral Trunk Lean (Peak)", f"{m.trunk_lean_lateral_max if m else 0.0}°", "< 6.0°", "Nominal" if (m and m.trunk_lean_lateral_max < 6) else "Compensatory Shear"],
        ["Pelvic Drop (Trendelenburg)", f"{m.pelvic_drop_deg if m else 0.0}°", "< 2.5°", "Stable" if (m and m.pelvic_drop_deg < 2.5) else "Gluteus Medius Weakness"],
        ["Landing Mechanics Score", f"{m.landing_mechanics_score if m else 0.0} / 100", "> 75 (Soft Landing)", "Controlled" if (m and m.landing_mechanics_score >= 75) else "Stiff Contact Loading"],
        ["Movement Symmetry Score", f"{m.movement_symmetry_score if m else 0.0}%", "> 88% Concordance", "Balanced" if (m and m.movement_symmetry_score >= 88) else "Bilateral Asymmetry Deficit"],
        ["Ground Impact Force Proxy", f"{m.force_impact_estimation_g if m else 0.0} G", "< 3.0 G Multiplier", "Acceptable" if (m and m.force_impact_estimation_g < 3.0) else "High Deceleration Shock"]
    ]
    bio_table = Table(bio_data, colWidths=[180, 100, 130, 130])
    bio_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("FONTSIZE", (0, 0), (-1, -1), 8.5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(bio_table)
    story.append(Spacer(1, 12))

    # Section 3: Specific Injury Categories
    story.append(Paragraph("3. Specific Injury Category Predictions", heading2_style))
    cat_risks = risk.category_risks if risk and risk.category_risks else {}
    cat_rows = [["Injury Risk Category", "Score", "Probability", "Risk Level", "Primary Biomechanical Factors"]]

    for k, item in cat_risks.items():
        factors_str = "; ".join(item.get("primary_factors", [])[:2])
        cat_rows.append([
            item.get("category_name", k),
            str(item.get("risk_score", 0)),
            f"{int(item.get('probability', 0) * 100)}%",
            item.get("risk_level", "Low"),
            factors_str
        ])

    if len(cat_rows) > 1:
        cat_table = Table(cat_rows, colWidths=[130, 50, 65, 80, 215])
        cat_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
        ]))
        story.append(cat_table)

    story.append(Spacer(1, 14))

    # Section 4: Corrective Action Plan
    story.append(Paragraph("4. Prescribed Interventions &amp; Recovery Plan", heading2_style))
    recs = risk.corrective_recommendations if risk and risk.corrective_recommendations else {}
    exercises = recs.get("exercises", [])
    if exercises:
        ex_text = "<br/>".join([f"• <b>{e.get('name')}</b> ({e.get('sets')}, {e.get('reps')} - {e.get('target_area')})" for e in exercises[:3]])
        story.append(Paragraph(ex_text, body_style))
    story.append(Spacer(1, 6))

    rec_plans = recs.get("recovery_planning", [])
    if rec_plans:
        story.append(Paragraph("<b>Recovery Protocol:</b> " + " ".join(rec_plans[:2]), body_style))

    # Methodology Disclaimer
    story.append(Spacer(1, 18))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#94a3b8"), spaceAfter=6))
    story.append(Paragraph(
        "<b>Methodological Notice:</b> Kinematix uses deterministic mathematical formulas calibrated against peer-reviewed sports biomechanics literature and clinical angle thresholds. Risk estimations are intended strictly for athletic screening and training volume guidance, and do not constitute clinical medical diagnosis or prognosis.",
        disclaimer_style
    ))

    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    filename = f"kinematix_assessment_report_video_{video_id}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@router.get("/{video_id}/excel")
def export_excel_report(video_id: int, db: Session = Depends(get_db)):
    video = db.query(VideoRecord).filter(VideoRecord.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="Video record not found")

    analysis = db.query(BiomechanicalAnalysis).filter(BiomechanicalAnalysis.video_id == video_id).first()
    risk = db.query(InjuryRiskAssessment).filter(InjuryRiskAssessment.video_id == video_id).first()
    athlete = db.query(Athlete).filter(Athlete.id == video.athlete_id).first() if video.athlete_id else None

    wb = openpyxl.Workbook()

    # Style presets
    header_fill = PatternFill(start_color="0F172A", end_color="0F172A", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    bold_font = Font(name="Calibri", size=11, bold=True)
    regular_font = Font(name="Calibri", size=10)
    thin_border = Border(
        left=Side(style='thin', color='CBD5E1'),
        right=Side(style='thin', color='CBD5E1'),
        top=Side(style='thin', color='CBD5E1'),
        bottom=Side(style='thin', color='CBD5E1')
    )

    # Sheet 1: Summary & Risk Breakdown
    ws_summary = wb.active
    ws_summary.title = "Summary & Risk"
    ws_summary.append(["KINEMATIX SPORTS BIOMECHANICS & INJURY RISK ASSESSMENT"])
    ws_summary.cell(row=1, column=1).font = Font(size=14, bold=True, color="0284C7")
    ws_summary.append([])

    ws_summary.append(["Athlete Name", athlete.name if athlete else "Unassigned", "Athlete Code", athlete.athlete_code if athlete else "N/A"])
    ws_summary.append(["Sport Type", athlete.sport_type if athlete else video.activity_type, "ACWR Workload", athlete.acwr if athlete else 1.15])
    ws_summary.append(["Session Video", video.title, "Duration / FPS", f"{video.duration_seconds}s / {video.fps}fps"])
    ws_summary.append([])

    ws_summary.append(["RISK SCORE COMPONENT", "SCORE (/100)", "WEIGHT", "WEIGHTED CONTRIBUTION"])
    for col_num in range(1, 5):
        cell = ws_summary.cell(row=6, column=col_num)
        cell.fill = header_fill
        cell.font = header_font

    risk_rows = [
        ["Biomechanical Deviations", risk.biomechanical_deviation_score if risk else 0.0, "35%", round(0.35 * (risk.biomechanical_deviation_score if risk else 0.0), 1)],
        ["Historical Injury Factors", risk.historical_injury_factor_score if risk else 0.0, "20%", round(0.20 * (risk.historical_injury_factor_score if risk else 0.0), 1)],
        ["Movement Asymmetry Index", risk.movement_asymmetry_score if risk else 0.0, "20%", round(0.20 * (risk.movement_asymmetry_score if risk else 0.0), 1)],
        ["Training Load Indicators", risk.training_load_indicator_score if risk else 0.0, "15%", round(0.15 * (risk.training_load_indicator_score if risk else 0.0), 1)],
        ["Kinematic Fatigue Drift", risk.fatigue_indicator_score if risk else 0.0, "10%", round(0.10 * (risk.fatigue_indicator_score if risk else 0.0), 1)],
        ["OVERALL INJURY RISK SCORE", risk.overall_injury_risk_score if risk else 0.0, "100%", risk.risk_category if risk else "Low Risk"]
    ]
    for r in risk_rows:
        ws_summary.append(r)

    # Sheet 2: Biomechanical Metrics
    ws_bio = wb.create_sheet(title="Biomechanical Metrics")
    ws_bio.append(["BIOMECHANICAL METRIC", "MEASURED VALUE", "UNIT", "REFERENCE BENCHMARK", "CLINICAL STATUS"])
    for c in range(1, 6):
        ws_bio.cell(row=1, column=c).fill = header_fill
        ws_bio.cell(row=1, column=c).font = header_font

    m = analysis
    metrics_rows = [
        ["Dynamic Knee Valgus (Left Peak)", m.knee_valgus_left_max if m else 0.0, "deg", "< 10.0 deg", "Nominal" if (m and m.knee_valgus_left_max < 10) else "Elevated"],
        ["Dynamic Knee Valgus (Right Peak)", m.knee_valgus_right_max if m else 0.0, "deg", "< 10.0 deg", "Severe Collapse" if (m and m.knee_valgus_right_max > 15) else "Nominal"],
        ["Average Knee Valgus", m.knee_valgus_avg if m else 0.0, "deg", "< 6.0 deg", "Nominal"],
        ["Hip Stability Score", m.hip_stability_score if m else 0.0, "/100", "> 80", "Controlled"],
        ["Pelvic Drop Angle", m.pelvic_drop_deg if m else 0.0, "deg", "< 2.5 deg", "Stable"],
        ["Lateral Trunk Lean (Peak)", m.trunk_lean_lateral_max if m else 0.0, "deg", "< 6.0 deg", "Nominal" if (m and m.trunk_lean_lateral_max < 6) else "Compensatory Tilt"],
        ["Forward Trunk Lean (Peak)", m.trunk_lean_forward_max if m else 0.0, "deg", "< 15.0 deg", "Nominal"],
        ["Landing Mechanics Score", m.landing_mechanics_score if m else 0.0, "/100", "> 75", "Controlled Soft Landing"],
        ["Initial Contact Knee Flexion", m.initial_contact_knee_flexion_deg if m else 0.0, "deg", "> 35.0 deg", "Nominal"],
        ["Movement Symmetry Score", m.movement_symmetry_score if m else 0.0, "%", "> 88%", "Bilateral Balance"],
        ["Range of Motion Score", m.range_of_motion_score if m else 0.0, "/100", "> 80", "Normal Mobility"],
        ["Force Impact Multiplier", m.force_impact_estimation_g if m else 0.0, "G", "< 3.0 G", "Normal Deceleration"]
    ]
    for r in metrics_rows:
        ws_bio.append(r)

    # Sheet 3: Category Risks
    ws_cat = wb.create_sheet(title="Injury Categories")
    ws_cat.append(["INJURY RISK AREA", "RISK SCORE (/100)", "PROBABILITY (%)", "RISK LEVEL", "DESCRIPTION", "CONTRIBUTING FACTORS"])
    for c in range(1, 7):
        ws_cat.cell(row=1, column=c).fill = header_fill
        ws_cat.cell(row=1, column=c).font = header_font

    cat_risks = risk.category_risks if risk and risk.category_risks else {}
    for k, item in cat_risks.items():
        ws_cat.append([
            item.get("category_name", k),
            item.get("risk_score", 0),
            f"{int(item.get('probability', 0) * 100)}%",
            item.get("risk_level", "Low"),
            item.get("description", ""),
            "; ".join(item.get("primary_factors", []))
        ])

    # Sheet 4: Frame Telemetry Data
    ws_frames = wb.create_sheet(title="Frame Telemetry")
    ws_frames.append(["FRAME", "TIME (s)", "DETECTED", "KNEE_VALGUS_L", "KNEE_VALGUS_R", "KNEE_ANGLE_L", "KNEE_ANGLE_R", "TRUNK_LEAN", "ASYMMETRY (%)", "ANOMALY_SCORE"])
    for c in range(1, 11):
        ws_frames.cell(row=1, column=c).fill = header_fill
        ws_frames.cell(row=1, column=c).font = header_font

    time_series = analysis.time_series_data if analysis and analysis.time_series_data else []
    for f in time_series:
        ws_frames.append([
            f.get("frame"),
            f.get("time"),
            f.get("detected"),
            f.get("knee_valgus_l"),
            f.get("knee_valgus_r"),
            f.get("knee_angle_l"),
            f.get("knee_angle_r"),
            f.get("trunk_lateral_lean"),
            f.get("bilateral_asymmetry"),
            f.get("anomaly_score")
        ])

    # Autofit columns across sheets
    for ws in [ws_summary, ws_bio, ws_cat, ws_frames]:
        for col in ws.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            col_letter = openpyxl.utils.get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    output = io.BytesIO()
    wb.save(output)
    excel_bytes = output.getvalue()
    output.close()

    filename = f"kinematix_biomechanics_data_video_{video_id}.xlsx"
    return Response(
        content=excel_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
