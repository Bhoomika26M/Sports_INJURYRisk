"""milestone_3

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-11 12:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0002'
down_revision = 'c8da7db24603'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # movement_baselines
    op.create_table('movement_baselines',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('athlete_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('movement_type', sa.String(length=50), nullable=False),
    sa.Column('metric_name', sa.String(length=50), nullable=False),
    sa.Column('mean_value', sa.Float(), nullable=False),
    sa.Column('std_dev', sa.Float(), nullable=False),
    sa.Column('sample_size', sa.Integer(), nullable=False),
    sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('sample_size >= 0', name='movement_baselines_sample_size_check'),
    sa.ForeignKeyConstraint(['athlete_id'], ['athletes.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('athlete_id', 'movement_type', 'metric_name', name='uq_movement_baselines_athlete_movement_metric')
    )

    # anomaly_scores
    op.create_table('anomaly_scores',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('video_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('frame_number', sa.Integer(), nullable=True),
    sa.Column('anomaly_score', sa.Float(), nullable=False),
    sa.Column('method', sa.String(length=30), nullable=False),
    sa.Column('baseline_sample_size', sa.Integer(), nullable=False),
    sa.Column('flagged', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('anomaly_score >= 0 AND anomaly_score <= 100', name='anomaly_scores_score_check'),
    sa.CheckConstraint("method = 'isolation_forest'", name='anomaly_scores_method_check'),
    sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_anomaly_scores_video_id', 'anomaly_scores', ['video_id'], unique=False)

    # risk_scores
    op.create_table('risk_scores',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('video_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('athlete_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('overall_score', sa.Float(), nullable=False),
    sa.Column('risk_category', sa.String(length=20), nullable=False),
    sa.Column('score_breakdown', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('methodology_note', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint('overall_score >= 0 AND overall_score <= 100', name='risk_scores_score_check'),
    sa.CheckConstraint("risk_category IN ('low', 'moderate', 'high', 'critical')", name='risk_scores_category_check'),
    sa.ForeignKeyConstraint(['athlete_id'], ['athletes.id'], ),
    sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('video_id')
    )

    # recommendations
    op.create_table('recommendations',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('risk_score_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('category', sa.String(length=30), nullable=False),
    sa.Column('title', sa.String(length=255), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('priority', sa.SmallInteger(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("category IN ('exercise', 'mobility', 'strengthening', 'recovery', 'training_modification')", name='recommendations_category_check'),
    sa.CheckConstraint('priority >= 1 AND priority <= 5', name='recommendations_priority_check'),
    sa.ForeignKeyConstraint(['risk_score_id'], ['risk_scores.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_recommendations_risk_score_id', 'recommendations', ['risk_score_id'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_recommendations_risk_score_id', table_name='recommendations')
    op.drop_table('recommendations')
    op.drop_table('risk_scores')
    op.drop_index('idx_anomaly_scores_video_id', table_name='anomaly_scores')
    op.drop_table('anomaly_scores')
    op.drop_table('movement_baselines')
