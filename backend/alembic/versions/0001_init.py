"""init schema with all tables

Revision ID: 0001
Revises: 
Create Date: 2026-09-30
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('role', sa.Enum('athlete', 'coach', 'physiotherapist', 'sports_scientist', 'admin', name='user_role', create_constraint=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('google_id', sa.String(length=255), nullable=True),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('google_id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # Refresh tokens
    op.create_table(
        'refresh_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_refresh_tokens_user_id', 'refresh_tokens', ['user_id'], unique=False)

    # Notification preferences
    op.create_table(
        'notification_preferences',
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('notification_type', sa.String(length=30), nullable=False),
        sa.Column('in_app', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('email', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'notification_type'),
    )

    # Athletes
    op.create_table(
        'athletes',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('coach_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('sport_type', sa.String(length=100), nullable=False),
        sa.Column('position', sa.String(length=100), nullable=True),
        sa.Column('date_of_birth', sa.Date(), nullable=False),
        sa.Column('height_cm', sa.Numeric(5, 2), nullable=True),
        sa.Column('weight_kg', sa.Numeric(5, 2), nullable=True),
        sa.Column('dominant_side', sa.String(length=10), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("dominant_side IN ('left', 'right')", name='ck_athletes_dominant_side'),
        sa.ForeignKeyConstraint(['coach_id'], ['users.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id'),
    )
    op.create_index('idx_athletes_coach_id', 'athletes', ['coach_id'], unique=False)

    # Injury history
    op.create_table(
        'injury_history',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('athlete_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('injury_type', sa.String(length=255), nullable=False),
        sa.Column('body_part', sa.String(length=100), nullable=False),
        sa.Column('injury_date', sa.Date(), nullable=False),
        sa.Column('recovery_date', sa.Date(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("severity IN ('minor', 'moderate', 'severe')", name='ck_injury_history_severity'),
        sa.ForeignKeyConstraint(['athlete_id'], ['athletes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_injury_history_athlete_id', 'injury_history', ['athlete_id'], unique=False)

    # Training load entries
    op.create_table(
        'training_load_entries',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('athlete_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('entry_date', sa.Date(), nullable=False),
        sa.Column('session_type', sa.String(length=100), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('rpe', sa.SmallInteger(), nullable=True),
        sa.Column('session_load', sa.Numeric(6, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('rpe BETWEEN 1 AND 10', name='ck_training_load_rpe'),
        sa.ForeignKeyConstraint(['athlete_id'], ['athletes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_training_load_athlete_id', 'training_load_entries', ['athlete_id'], unique=False)

    # Movement types
    op.create_table(
        'movement_types',
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('display_name', sa.String(length=100), nullable=False),
        sa.Column('camera_views', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('phases', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('code'),
    )

    # Movement metrics
    op.create_table(
        'movement_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('movement_type', sa.String(length=50), nullable=False),
        sa.Column('metric_name', sa.String(length=50), nullable=False),
        sa.Column('plane', sa.String(length=20), nullable=False),
        sa.Column('confidence', sa.String(length=10), nullable=False),
        sa.Column('unit', sa.String(length=20), nullable=False, server_default='degrees'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['movement_type'], ['movement_types.code']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('movement_type', 'metric_name', name='uq_movement_metric'),
    )

    # Videos
    op.create_table(
        'videos',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('athlete_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('movement_type', sa.String(length=50), nullable=False),
        sa.Column('storage_key', sa.String(length=500), nullable=False),
        sa.Column('original_filename', sa.String(length=255), nullable=True),
        sa.Column('duration_seconds', sa.Numeric(6, 2), nullable=True),
        sa.Column('fps', sa.Numeric(5, 2), nullable=True),
        sa.Column('resolution_width', sa.Integer(), nullable=True),
        sa.Column('resolution_height', sa.Integer(), nullable=True),
        sa.Column('camera_view', sa.String(length=20), nullable=False),
        sa.Column('processing_status', sa.Enum('pending_upload', 'uploaded', 'processing', 'completed', 'failed', name='video_processing_status', create_constraint=True), nullable=False, server_default='pending_upload'),
        sa.Column('person_count_detected', sa.Integer(), nullable=True),
        sa.Column('detection_rate', sa.Numeric(4, 3), nullable=True),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('job_id', sa.String(length=255), nullable=True),
        sa.Column('progress_pct', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('annotated_video_key', sa.String(length=500), nullable=True),
        sa.Column('thumbnail_key', sa.String(length=500), nullable=True),
        sa.Column('processing_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['athlete_id'], ['athletes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_videos_athlete_id', 'videos', ['athlete_id'], unique=False)
    op.create_index('idx_videos_processing_status', 'videos', ['processing_status'], unique=False)

    # Pose frames
    op.create_table(
        'pose_frames',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('video_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('frame_number', sa.Integer(), nullable=False),
        sa.Column('timestamp_ms', sa.Integer(), nullable=False),
        sa.Column('keypoints', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('model_used', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('video_id', 'frame_number', name='uq_pose_frames_video_frame'),
    )
    op.create_index('idx_pose_frames_video_id', 'pose_frames', ['video_id'], unique=False)

    # Biomechanical metrics
    op.create_table(
        'biomechanical_metrics',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('video_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('frame_number', sa.Integer(), nullable=False),
        sa.Column('metric_name', sa.String(length=50), nullable=False),
        sa.Column('metric_value', sa.Numeric(8, 3), nullable=False),
        sa.Column('plane', sa.String(length=20), nullable=False),
        sa.Column('confidence', sa.String(length=10), nullable=False),
        sa.Column('movement_phase', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_biomechanical_metrics_video_id', 'biomechanical_metrics', ['video_id'], unique=False)

    # Movement baselines
    op.create_table(
        'movement_baselines',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('athlete_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('movement_type', sa.String(length=50), nullable=False),
        sa.Column('metric_name', sa.String(length=50), nullable=False),
        sa.Column('mean_value', sa.Float(), nullable=False),
        sa.Column('std_dev', sa.Float(), nullable=False),
        sa.Column('sample_size', sa.Integer(), nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('sample_size >= 0', name='movement_baselines_sample_size_check'),
        sa.ForeignKeyConstraint(['athlete_id'], ['athletes.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('athlete_id', 'movement_type', 'metric_name', name='uq_movement_baselines_athlete_movement_metric'),
    )

    # Anomaly scores
    op.create_table(
        'anomaly_scores',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('video_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('frame_number', sa.Integer(), nullable=True),
        sa.Column('anomaly_score', sa.Float(), nullable=False),
        sa.Column('method', sa.String(length=30), nullable=False, server_default='isolation_forest'),
        sa.Column('baseline_sample_size', sa.Integer(), nullable=False),
        sa.Column('flagged', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('anomaly_score >= 0 AND anomaly_score <= 100', name='anomaly_scores_score_check'),
        sa.CheckConstraint("method = 'isolation_forest'", name='anomaly_scores_method_check'),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_anomaly_scores_video_id', 'anomaly_scores', ['video_id'], unique=False)

    # Risk scores
    op.create_table(
        'risk_scores',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('video_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('athlete_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('risk_category', sa.String(length=20), nullable=False),
        sa.Column('score_breakdown', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('methodology_note', sa.Text(), nullable=False, server_default='Composite of movement-pattern anomaly vs. population baseline, a bounded symmetry flag, and a bounded prior-injury flag. Not a trained injury-prediction model. See docs/SCIENCE_CONSTRAINTS.md.'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint('overall_score >= 0 AND overall_score <= 100', name='risk_scores_score_check'),
        sa.CheckConstraint("risk_category IN ('low', 'moderate', 'high', 'critical')", name='risk_scores_category_check'),
        sa.ForeignKeyConstraint(['athlete_id'], ['athletes.id']),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('video_id'),
    )

    # Recommendations
    op.create_table(
        'recommendations',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('risk_score_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('category', sa.String(length=30), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('priority', sa.SmallInteger(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.CheckConstraint("category IN ('exercise', 'mobility', 'strengthening', 'recovery', 'training_modification')", name='recommendations_category_check'),
        sa.CheckConstraint('priority >= 1 AND priority <= 5', name='recommendations_priority_check'),
        sa.ForeignKeyConstraint(['risk_score_id'], ['risk_scores.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_recommendations_risk_score_id', 'recommendations', ['risk_score_id'], unique=False)

    # Notifications
    op.create_table(
        'notifications',
        sa.Column('id', postgresql.UUID(as_uuid=False), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column('type', sa.String(length=30), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('related_athlete_id', postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['related_athlete_id'], ['athletes.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notifications_user_id', 'notifications', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_notifications_user_id', table_name='notifications')
    op.drop_table('notifications')
    op.drop_index('idx_recommendations_risk_score_id', table_name='recommendations')
    op.drop_table('recommendations')
    op.drop_table('risk_scores')
    op.drop_index('idx_anomaly_scores_video_id', table_name='anomaly_scores')
    op.drop_table('anomaly_scores')
    op.drop_table('movement_baselines')
    op.drop_index('idx_biomechanical_metrics_video_id', table_name='biomechanical_metrics')
    op.drop_table('biomechanical_metrics')
    op.drop_index('idx_pose_frames_video_id', table_name='pose_frames')
    op.drop_table('pose_frames')
    op.drop_index('idx_videos_processing_status', table_name='videos')
    op.drop_index('idx_videos_athlete_id', table_name='videos')
    op.drop_table('videos')
    op.drop_table('movement_metrics')
    op.drop_table('movement_types')
    op.drop_index('idx_training_load_athlete_id', table_name='training_load_entries')
    op.drop_table('training_load_entries')
    op.drop_index('idx_injury_history_athlete_id', table_name='injury_history')
    op.drop_table('injury_history')
    op.drop_index('idx_athletes_coach_id', table_name='athletes')
    op.drop_table('athletes')
    op.drop_table('notification_preferences')
    op.drop_index('ix_refresh_tokens_user_id', table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')