"""skip_broken_migration

Revision ID: 6b665630b4e1
Revises: 500da41fe44d
Create Date: 2026-10-12 19:07:03.792347

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6b665630b4e1'
down_revision = '1223d6c89f83'
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
