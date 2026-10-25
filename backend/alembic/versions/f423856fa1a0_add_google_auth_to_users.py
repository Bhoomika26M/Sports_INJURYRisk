"""add_google_auth_to_users

Revision ID: f423856fa1a0
Revises: 4e30bbb9f979
Create Date: 2026-10-24 17:49:06.739247

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f423856fa1a0'
down_revision: Union[str, Sequence[str], None] = '4e30bbb9f979'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('auth_provider', sa.String(), nullable=True, server_default='local'))
    op.add_column('users', sa.Column('google_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_users_google_id'), 'users', ['google_id'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_users_google_id'), table_name='users')
    op.drop_column('users', 'google_id')
    op.drop_column('users', 'auth_provider')
