"""initial_schema

Revision ID: 0001_initial_schema
Revises: 
Create Date: 2026-09-18 21:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Define PostgreSQL ENUMs
user_role_enum = postgresql.ENUM(
    "admin",
    "coach",
    "physiotherapist",
    "sports_scientist",
    "athlete",
    name="user_role_enum",
    create_type=False,
)

biological_sex_enum = postgresql.ENUM(
    "male",
    "female",
    "other",
    name="biological_sex_enum",
    create_type=False,
)

dominant_leg_enum = postgresql.ENUM(
    "left",
    "right",
    "ambidextrous",
    name="dominant_leg_enum",
    create_type=False,
)

anatomical_side_enum = postgresql.ENUM(
    "left",
    "right",
    "bilateral",
    name="anatomical_side_enum",
    create_type=False,
)

injury_type_enum = postgresql.ENUM(
    "acl_tear",
    "ankle_sprain",
    "hamstring_strain",
    "patellar_tendinopathy",
    "meniscus_tear",
    "groin_strain",
    "other",
    name="injury_type_enum",
    create_type=False,
)

movement_type_enum = postgresql.ENUM(
    "squat",
    "jump_landing",
    "running",
    name="movement_type_enum",
    create_type=False,
)

camera_view_enum = postgresql.ENUM(
    "frontal",
    "sagittal",
    "oblique",
    name="camera_view_enum",
    create_type=False,
)

processing_status_enum = postgresql.ENUM(
    "pending_upload",
    "uploaded",
    "preprocessing",
    "pose_estimation",
    "biomechanics_calc",
    "completed",
    "failed",
    name="processing_status_enum",
    create_type=False,
)

risk_tier_enum = postgresql.ENUM(
    "low",
    "moderate",
    "high",
    name="risk_tier_enum",
    create_type=False,
)


def upgrade() -> None:
    # 1. Create PostgreSQL ENUM types
    sa.Enum("admin", "coach", "physiotherapist", "sports_scientist", "athlete", name="user_role_enum").create(op.get_bind(), checkfirst=True)
    sa.Enum("male", "female", "other", name="biological_sex_enum").create(op.get_bind(), checkfirst=True)
    sa.Enum("left", "right", "ambidextrous", name="dominant_leg_enum").create(op.get_bind(), checkfirst=True)
    sa.Enum("left", "right", "bilateral", name="anatomical_side_enum").create(op.get_bind(), checkfirst=True)
    sa.Enum("acl_tear", "ankle_sprain", "hamstring_strain", "patellar_tendinopathy", "meniscus_tear", "groin_strain", "other", name="injury_type_enum").create(op.get_bind(), checkfirst=True)
    sa.Enum("squat", "jump_landing", "running", name="movement_type_enum").create(op.get_bind(), checkfirst=True)
    sa.Enum("frontal", "sagittal", "oblique", name="camera_view_enum").create(op.get_bind(), checkfirst=True)
    sa.Enum("pending_upload", "uploaded", "preprocessing", "pose_estimation", "biomechanics_calc", "completed", "failed", name="processing_status_enum").create(op.get_bind(), checkfirst=True)
    sa.Enum("low", "moderate", "high", name="risk_tier_enum").create(op.get_bind(), checkfirst=True)

    # 2. Table: users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("role", user_role_enum, nullable=False, server_default="athlete"),
        sa.Column("phone_number", sa.String(length=30), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # 3. Table: athletes
    op.create_table(
        "athletes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("date_of_birth", sa.Date(), nullable=False),
        sa.Column("biological_sex", biological_sex_enum, nullable=False),
        sa.Column("height_cm", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("weight_kg", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("dominant_leg", dominant_leg_enum, nullable=False, server_default="right"),
        sa.Column("primary_sport", sa.String(length=100), nullable=False),
        sa.Column("team_affiliation", sa.String(length=150), nullable=True),
        sa.Column("position", sa.String(length=80), nullable=True),
        sa.Column("competitive_level", sa.String(length=50), nullable=False, server_default="collegiate"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("height_cm > 50 AND height_cm < 260", name="chk_athlete_height"),
        sa.CheckConstraint("weight_kg > 20 AND weight_kg < 300", name="chk_athlete_weight"),
    )
    op.create_index("idx_athletes_user_id", "athletes", ["user_id"])
    op.create_index("idx_athletes_team", "athletes", ["team_affiliation"])

    # 4. Table: injury_history
    op.create_table(
        "injury_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("athlete_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("injury_type", injury_type_enum, nullable=False),
        sa.Column("anatomical_side", anatomical_side_enum, nullable=False),
        sa.Column("diagnosis_details", sa.String(length=255), nullable=True),
        sa.Column("injury_date", sa.Date(), nullable=False),
        sa.Column("severity_grade", sa.String(length=20), nullable=True),
        sa.Column("surgical_intervention", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("return_to_play_date", sa.Date(), nullable=True),
        sa.Column("fully_resolved", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("clinical_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("idx_injury_history_athlete_id", "injury_history", ["athlete_id"])
    op.create_index("idx_injury_history_type", "injury_history", ["injury_type"])

    # 5. Table: training_profiles
    op.create_table(
        "training_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("athlete_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("effective_date", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=False),
        sa.Column("weekly_training_hours", sa.Numeric(precision=4, scale=1), nullable=False),
        sa.Column("sessions_per_week", sa.Integer(), nullable=False),
        sa.Column("strength_sessions_per_week", sa.Integer(), nullable=False, server_default="2"),
        sa.Column("current_training_phase", sa.String(length=50), nullable=False, server_default="in_season"),
        sa.Column("acute_chronic_workload_ratio", sa.Numeric(precision=4, scale=2), nullable=True),
        sa.Column("resting_heart_rate_bpm", sa.Integer(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("weekly_training_hours >= 0", name="chk_training_hours"),
        sa.CheckConstraint("sessions_per_week >= 1", name="chk_sessions_per_week"),
        sa.CheckConstraint("acute_chronic_workload_ratio IS NULL OR acute_chronic_workload_ratio >= 0", name="chk_acwr_positive"),
    )
    op.create_index("idx_training_profiles_athlete_id", "training_profiles", ["athlete_id"])

    # 6. Table: physical_assessments
    op.create_table(
        "physical_assessments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("athlete_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assessor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("assessment_date", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=False),
        sa.Column("assessment_type", sa.String(length=80), nullable=False, server_default="pre_season_baseline"),
        sa.Column("weight_at_assessment_kg", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("ankle_dorsiflexion_left_cm", sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column("ankle_dorsiflexion_right_cm", sa.Numeric(precision=4, scale=1), nullable=True),
        sa.Column("single_leg_hop_left_cm", sa.Numeric(precision=5, scale=1), nullable=True),
        sa.Column("single_leg_hop_right_cm", sa.Numeric(precision=5, scale=1), nullable=True),
        sa.Column("y_balance_composite_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("clinical_observations", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
    )
    op.create_index("idx_assessments_athlete_id", "physical_assessments", ["athlete_id"])
    op.create_index("idx_assessments_assessor_id", "physical_assessments", ["assessor_id"])

    # 7. Table: coach_athlete_assignments
    op.create_table(
        "coach_athlete_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("coach_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("athlete_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assignment_role", sa.String(length=50), nullable=False, server_default="head_coach"),
        sa.Column("assigned_at", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.UniqueConstraint("coach_id", "athlete_id", "assignment_role", name="uq_coach_athlete_role"),
    )
    op.create_index("idx_coach_athlete_coach_id", "coach_athlete_assignments", ["coach_id"])
    op.create_index("idx_coach_athlete_athlete_id", "coach_athlete_assignments", ["athlete_id"])

    # 8. Table: videos
    op.create_table(
        "videos",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("athlete_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("athletes.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assessment_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("physical_assessments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("uploaded_by_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("mime_type", sa.String(length=50), nullable=False, server_default="video/mp4"),
        sa.Column("duration_seconds", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("frame_rate_fps", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("frame_width", sa.Integer(), nullable=True),
        sa.Column("frame_height", sa.Integer(), nullable=True),
        sa.Column("movement_type", movement_type_enum, nullable=False),
        sa.Column("camera_view", camera_view_enum, nullable=False, server_default="frontal"),
        sa.Column("processing_status", processing_status_enum, nullable=False, server_default="pending_upload"),
        sa.Column("calculated_metrics_summary", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("overall_risk_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("risk_tier", risk_tier_enum, nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("overall_risk_score IS NULL OR (overall_risk_score >= 0 AND overall_risk_score <= 100)", name="chk_video_risk_score_range"),
    )
    op.create_index("idx_videos_athlete_id", "videos", ["athlete_id"])
    op.create_index("idx_videos_status", "videos", ["processing_status"], postgresql_where=sa.text("processing_status != 'completed'"))
    op.create_index("idx_videos_risk_tier", "videos", ["risk_tier"])
    op.create_index("idx_videos_movement_created", "videos", ["movement_type", sa.text("created_at DESC")])
    op.create_index("idx_videos_metrics_gin", "videos", ["calculated_metrics_summary"], postgresql_using="gin")


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table("videos")
    op.drop_table("coach_athlete_assignments")
    op.drop_table("physical_assessments")
    op.drop_table("training_profiles")
    op.drop_table("injury_history")
    op.drop_table("athletes")
    op.drop_table("users")

    # Drop PostgreSQL ENUM types
    sa.Enum(name="risk_tier_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="processing_status_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="camera_view_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="movement_type_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="injury_type_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="anatomical_side_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="dominant_leg_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="biological_sex_enum").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_role_enum").drop(op.get_bind(), checkfirst=True)
