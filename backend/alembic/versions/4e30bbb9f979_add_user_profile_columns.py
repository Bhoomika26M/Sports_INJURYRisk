"""add_user_profile_columns

Revision ID: 4e30bbb9f979
Revises: b26b790fcebe
Create Date: 2026-10-23 22:20:47.450161

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e30bbb9f979'
down_revision: Union[str, Sequence[str], None] = 'b26b790fcebe'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('bio', sa.String(), nullable=True))
    op.add_column('users', sa.Column('phone_number', sa.String(), nullable=True))
    op.add_column('users', sa.Column('organization', sa.String(), nullable=True))
    op.add_column('users', sa.Column('specialization', sa.String(), nullable=True))

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'specialization')
    op.drop_column('users', 'organization')
    op.drop_column('users', 'phone_number')
    op.drop_column('users', 'bio')

