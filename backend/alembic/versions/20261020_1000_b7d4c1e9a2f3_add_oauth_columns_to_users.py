"""add oauth columns to users

Revision ID: b7d4c1e9a2f3
Revises: 9f1c2ab7d4e5
Create Date: 2026-10-20 10:00:00.000000

Adds nullable federated-identity columns to ``users`` for Google Sign-In:
``oauth_provider`` (e.g. "google") and ``oauth_subject`` (the provider's stable
user id). Both are null for password-only accounts, so this is additive and
non-destructive.

Implemented as separate ``add_column`` calls (rather than a batch table
recreate) so it is a cheap, portable ``ALTER TABLE ADD COLUMN`` on both SQLite
and PostgreSQL.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b7d4c1e9a2f3'
down_revision = '9f1c2ab7d4e5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('oauth_provider', sa.String(), nullable=True))
    op.add_column('users', sa.Column('oauth_subject', sa.String(), nullable=True))
    op.create_index('ix_users_oauth_provider', 'users', ['oauth_provider'], unique=False)
    op.create_index('ix_users_oauth_subject', 'users', ['oauth_subject'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_users_oauth_subject', table_name='users')
    op.drop_index('ix_users_oauth_provider', table_name='users')
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_column('oauth_subject')
        batch_op.drop_column('oauth_provider')
