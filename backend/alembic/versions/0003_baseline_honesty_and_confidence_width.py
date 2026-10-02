"""baseline rows say "unknown" honestly; widen biomechanical_metrics.confidence

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-02

1. movement_baselines.mean_value / std_dev become NULLable. Insufficient baselines used to be
   stored as 0.0 +/- 0.0, a plausible-looking wrong number. NULL means "we don't know".
2. movement_baselines gains video_count / athlete_count so the row states its own unit
   (sample_size counts per-metric FRAME rows, not people).
3. Every pre-existing baseline row is set to NULL mean/std: they were computed under the old
   frame-count gate, which admitted a single video of a single athlete. Re-run
   POST /api/v1/baselines/recompute to rebuild them under the video/athlete gate.
4. biomechanical_metrics.confidence VARCHAR(10) -> VARCHAR(20). The structural tier value
   'qualitative' is 11 characters and could not be inserted (0002 only widened movement_metrics).
"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('biomechanical_metrics', 'confidence',
                    type_=sa.String(20), existing_type=sa.String(10), existing_nullable=False)

    op.alter_column('movement_baselines', 'mean_value', existing_type=sa.Float(), nullable=True)
    op.alter_column('movement_baselines', 'std_dev', existing_type=sa.Float(), nullable=True)
    op.add_column('movement_baselines', sa.Column('video_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('movement_baselines', sa.Column('athlete_count', sa.Integer(), nullable=False, server_default='0'))
    op.execute("UPDATE movement_baselines SET mean_value = NULL, std_dev = NULL")


def downgrade() -> None:
    # Restoring NOT NULL requires a value; 0.0 is the old (dishonest) convention. Lossy by necessity.
    op.execute("UPDATE movement_baselines SET mean_value = 0.0 WHERE mean_value IS NULL")
    op.execute("UPDATE movement_baselines SET std_dev = 0.0 WHERE std_dev IS NULL")
    op.drop_column('movement_baselines', 'athlete_count')
    op.drop_column('movement_baselines', 'video_count')
    op.alter_column('movement_baselines', 'std_dev', existing_type=sa.Float(), nullable=False)
    op.alter_column('movement_baselines', 'mean_value', existing_type=sa.Float(), nullable=False)

    # Fails if any 'qualitative' rows exist (they no longer fit in 10 chars): by design, never truncate.
    op.alter_column('biomechanical_metrics', 'confidence',
                    type_=sa.String(10), existing_type=sa.String(20), existing_nullable=False)
