"""add videos.analysis and risk_scores.assessment (nullable JSONB)

videos.analysis       pose-analysis report: quality grade/warnings, rep & gait analysis
risk_scores.assessment full AI-engine assessment: component scores, the five PDF sub-scores,
                       per-injury-category risk, baseline info, engine version

Both nullable: existing rows stay valid. A risk_scores row with NULL assessment (or an older
engine_version) is recomputed automatically on its next read.

(The biomechanical_metrics.confidence VARCHAR(10) -> VARCHAR(20) widening that the engine rebuild
originally carried here is already done by 0003, so it is not repeated.)

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-02
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('videos', sa.Column('analysis', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('risk_scores', sa.Column('assessment', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column('risk_scores', 'assessment')
    op.drop_column('videos', 'analysis')
