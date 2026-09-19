"""add_missing_check_constraints

Revision ID: c8da7db24603
Revises: d993def14f93
Create Date: 2026-07-10 18:41:21.212518
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c8da7db24603'
down_revision: Union[str, None] = 'd993def14f93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_check_constraint(
        "ck_videos_camera_view", "videos",
        "camera_view IN ('sagittal', 'frontal', 'other')"
    )
    op.create_check_constraint(
        "ck_biomechanical_metrics_plane", "biomechanical_metrics",
        "plane IN ('sagittal', 'frontal', 'transverse')"
    )
    op.create_check_constraint(
        "ck_biomechanical_metrics_confidence", "biomechanical_metrics",
        "confidence IN ('validated', 'qualitative')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_biomechanical_metrics_confidence", "biomechanical_metrics", type_="check")
    op.drop_constraint("ck_biomechanical_metrics_plane", "biomechanical_metrics", type_="check")
    op.drop_constraint("ck_videos_camera_view", "videos", type_="check")
