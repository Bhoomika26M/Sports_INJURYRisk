"""add_video_and_analysis_tables

Revision ID: 1223d6c89f83
Revises: 003
Create Date: 2026-10-06 12:03:53.283599

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1223d6c89f83'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create videos table
    op.create_table(
        'videos',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('athlete_id', sa.Integer(), nullable=False),
        sa.Column('uploaded_by', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(), nullable=False),
        sa.Column('original_filename', sa.String(), nullable=False),
        sa.Column('storage_path', sa.String(), nullable=False),
        sa.Column('activity_type', sa.String(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('fps', sa.Float(), nullable=True),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('processing_status', sa.String(), nullable=False),
        sa.Column('processing_error', sa.String(), nullable=True),
        sa.Column('processing_started_at', sa.DateTime(), nullable=True),
        sa.Column('processing_completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['athlete_id'], ['athletes.id']),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('filename')
    )
    op.create_index(op.f('ix_videos_athlete_id'), 'videos', ['athlete_id'], unique=False)
    op.create_index(op.f('ix_videos_id'), 'videos', ['id'], unique=False)
    
    # Create pose_analyses table
    op.create_table(
        'pose_analyses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('video_id', sa.Integer(), nullable=False),
        sa.Column('pose_model', sa.String(), nullable=False),
        sa.Column('pose_model_version', sa.String(), nullable=True),
        sa.Column('analysis_version', sa.String(), nullable=False),
        sa.Column('total_frames', sa.Integer(), nullable=True),
        sa.Column('processed_frames', sa.Integer(), nullable=True),
        sa.Column('frame_sample_rate', sa.Float(), nullable=True),
        sa.Column('pose_quality', sa.JSON(), nullable=True),
        sa.Column('keypoints_data', sa.JSON(), nullable=True),
        sa.Column('normalized_skeleton', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['video_id'], ['videos.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('video_id')
    )
    op.create_index(op.f('ix_pose_analyses_id'), 'pose_analyses', ['id'], unique=False)
    
    # Create movement_windows table
    op.create_table(
        'movement_windows',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pose_analysis_id', sa.Integer(), nullable=False),
        sa.Column('start_frame', sa.Integer(), nullable=False),
        sa.Column('end_frame', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.Float(), nullable=False),
        sa.Column('end_time', sa.Float(), nullable=False),
        sa.Column('activity', sa.String(), nullable=False),
        sa.Column('repetition_number', sa.Integer(), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('quality_notes', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['pose_analysis_id'], ['pose_analyses.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_movement_windows_id'), 'movement_windows', ['id'], unique=False)
    op.create_index(op.f('ix_movement_windows_pose_analysis_id'), 'movement_windows', ['pose_analysis_id'], unique=False)
    
    # Create biomechanical_analyses table
    op.create_table(
        'biomechanical_analyses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('pose_analysis_id', sa.Integer(), nullable=False),
        sa.Column('joint_angles', sa.JSON(), nullable=True),
        sa.Column('rom', sa.JSON(), nullable=True),
        sa.Column('symmetry', sa.JSON(), nullable=True),
        sa.Column('knee_alignment', sa.JSON(), nullable=True),
        sa.Column('trunk_lean', sa.JSON(), nullable=True),
        sa.Column('hip_stability', sa.JSON(), nullable=True),
        sa.Column('balance', sa.JSON(), nullable=True),
        sa.Column('velocity', sa.JSON(), nullable=True),
        sa.Column('acceleration', sa.JSON(), nullable=True),
        sa.Column('smoothness', sa.JSON(), nullable=True),
        sa.Column('landing_mechanics', sa.JSON(), nullable=True),
        sa.Column('running_features', sa.JSON(), nullable=True),
        sa.Column('fatigue_analysis', sa.JSON(), nullable=True),
        sa.Column('movement_quality', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['pose_analysis_id'], ['pose_analyses.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('pose_analysis_id')
    )
    op.create_index(op.f('ix_biomechanical_analyses_id'), 'biomechanical_analyses', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_biomechanical_analyses_id'), table_name='biomechanical_analyses')
    op.drop_table('biomechanical_analyses')
    op.drop_index(op.f('ix_movement_windows_pose_analysis_id'), table_name='movement_windows')
    op.drop_index(op.f('ix_movement_windows_id'), table_name='movement_windows')
    op.drop_table('movement_windows')
    op.drop_index(op.f('ix_pose_analyses_id'), table_name='pose_analyses')
    op.drop_table('pose_analyses')
    op.drop_index(op.f('ix_videos_id'), table_name='videos')
    op.drop_index(op.f('ix_videos_athlete_id'), table_name='videos')
    op.drop_table('videos')
