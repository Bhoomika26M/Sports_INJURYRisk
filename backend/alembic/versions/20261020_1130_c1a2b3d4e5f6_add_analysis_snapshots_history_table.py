"""add analysis_snapshots history table

Revision ID: c1a2b3d4e5f6
Revises: b7d4c1e9a2f3
Create Date: 2026-10-20 11:30:00.000000

Creates ``analysis_snapshots``: a durable, denormalized record of each completed
analysis (risk score, trended metrics, and the comparison against the athlete's
rolling same-activity baseline).

This is purely additive - no existing table is touched, so it is safe to run
against a populated database. Before this table, history could only be
reconstructed by re-deriving risk from raw keypoints on every request, which
left nothing stable to compare a new video against.

``athlete_id`` is intentionally denormalized onto the row (it is also reachable
through ``video_id``) so timeline queries need a single indexed read.
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c1a2b3d4e5f6"
down_revision = "b7d4c1e9a2f3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analysis_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("athlete_id", sa.Integer(), nullable=False),
        sa.Column("video_id", sa.Integer(), nullable=False),
        sa.Column("pose_analysis_id", sa.Integer(), nullable=True),
        sa.Column("activity_type", sa.String(), nullable=False),
        sa.Column("sequence_index", sa.Integer(), nullable=False),
        sa.Column("performed_at", sa.DateTime(), nullable=False),
        sa.Column("overall_risk_score", sa.Float(), nullable=False),
        sa.Column("risk_level", sa.String(), nullable=False),
        sa.Column("findings_count", sa.Integer(), nullable=False),
        sa.Column("metrics", sa.JSON(), nullable=True),
        sa.Column("baseline", sa.JSON(), nullable=True),
        sa.Column("baseline_comparison", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["athlete_id"], ["athletes.id"]),
        sa.ForeignKeyConstraint(["video_id"], ["videos.id"]),
        sa.ForeignKeyConstraint(["pose_analysis_id"], ["pose_analyses.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("video_id"),
    )
    op.create_index(
        "ix_analysis_snapshots_id", "analysis_snapshots", ["id"], unique=False
    )
    op.create_index(
        "ix_analysis_snapshots_athlete_id",
        "analysis_snapshots",
        ["athlete_id"],
        unique=False,
    )
    op.create_index(
        "ix_analysis_snapshots_performed_at",
        "analysis_snapshots",
        ["performed_at"],
        unique=False,
    )
    # Composite index for the timeline/baseline query pattern.
    op.create_index(
        "ix_analysis_snapshots_athlete_activity_time",
        "analysis_snapshots",
        ["athlete_id", "activity_type", "performed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_analysis_snapshots_athlete_activity_time", table_name="analysis_snapshots"
    )
    op.drop_index(
        "ix_analysis_snapshots_performed_at", table_name="analysis_snapshots"
    )
    op.drop_index(
        "ix_analysis_snapshots_athlete_id", table_name="analysis_snapshots"
    )
    op.drop_index("ix_analysis_snapshots_id", table_name="analysis_snapshots")
    op.drop_table("analysis_snapshots")
