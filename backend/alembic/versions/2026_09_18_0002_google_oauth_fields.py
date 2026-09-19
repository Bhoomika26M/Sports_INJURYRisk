"""Add google_id and avatar_url to users; make hashed_password nullable

Revision ID: 0002_google_oauth_fields
Revises: 0001_initial_schema
Create Date: 2026-09-18 22:23:00

Changes
-------
* users.hashed_password  → ALTER COLUMN … DROP NOT NULL
* users.google_id        → VARCHAR(128) UNIQUE NULLABLE, indexed
* users.avatar_url       → VARCHAR(512) NULLABLE
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "0002_google_oauth_fields"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Make hashed_password nullable (OAuth users have no password)
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(255),
        nullable=True,
    )

    # 2. Add google_id column (unique, indexed)
    op.add_column(
        "users",
        sa.Column("google_id", sa.String(128), nullable=True),
    )
    op.create_unique_constraint("uq_users_google_id", "users", ["google_id"])
    op.create_index("idx_users_google_id", "users", ["google_id"])

    # 3. Add avatar_url column
    op.add_column(
        "users",
        sa.Column("avatar_url", sa.String(512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "avatar_url")
    op.drop_index("idx_users_google_id", table_name="users")
    op.drop_constraint("uq_users_google_id", "users", type_="unique")
    op.drop_column("users", "google_id")
    op.alter_column(
        "users",
        "hashed_password",
        existing_type=sa.String(255),
        nullable=False,
    )
