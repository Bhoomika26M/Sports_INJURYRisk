"""videos.coverage_caveat — honest note for partial coverage / multi-person footage

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-02

Additive and nullable. NULL = a single clearly-tracked athlete at full pose coverage.
"""
from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('videos', sa.Column('coverage_caveat', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('videos', 'coverage_caveat')
