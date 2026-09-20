"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2026-09-20 13:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password_hash', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)
    op.create_index('ix_users_id', 'users', ['id'], unique=False)
    
    # Create athletes table
    op.create_table(
        'athletes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('athlete_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('sport_type', sa.String(), nullable=False),
        sa.Column('position', sa.String(), nullable=True),
        sa.Column('age', sa.Integer(), nullable=False),
        sa.Column('height', sa.Float(), nullable=False),
        sa.Column('weight', sa.Float(), nullable=False),
        sa.Column('injury_history', sa.Text(), nullable=True),
        sa.Column('training_load', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_athletes_athlete_id', 'athletes', ['athlete_id'], unique=True)
    op.create_index('ix_athletes_id', 'athletes', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_athletes_id', table_name='athletes')
    op.drop_index('ix_athletes_athlete_id', table_name='athletes')
    op.drop_table('athletes')
    op.drop_index('ix_users_id', table_name='users')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
