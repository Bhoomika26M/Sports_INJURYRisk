"""add password_otps table

Revision ID: 9f1c2ab7d4e5
Revises: 6b665630b4e1
Create Date: 2026-10-19 10:00:00.000000

Adds the purpose-scoped, single-use, expiring email OTP table used by the
password-recovery and authenticated password-change workflows. Non-destructive:
it only creates a new table and its indexes.

Portable across SQLite and PostgreSQL (no dialect-specific types).
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9f1c2ab7d4e5'
down_revision = '6b665630b4e1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'password_otps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('purpose', sa.String(), nullable=False),
        sa.Column('otp_hash', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_attempts', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('used_at', sa.DateTime(), nullable=True),
        sa.Column('invalidated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_password_otps_id', 'password_otps', ['id'], unique=False)
    op.create_index('ix_password_otps_user_id', 'password_otps', ['user_id'], unique=False)
    op.create_index('ix_password_otps_purpose', 'password_otps', ['purpose'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_password_otps_purpose', table_name='password_otps')
    op.drop_index('ix_password_otps_user_id', table_name='password_otps')
    op.drop_index('ix_password_otps_id', table_name='password_otps')
    op.drop_table('password_otps')
