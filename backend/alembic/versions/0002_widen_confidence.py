"""widen movement_metrics.confidence to VARCHAR(20)

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-30
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column('movement_metrics', 'confidence', type_=sa.String(20), existing_type=sa.String(10))


def downgrade() -> None:
    op.alter_column('movement_metrics', 'confidence', type_=sa.String(10), existing_type=sa.String(20))
