"""Alembic env.py — async migration runner.

Imports all models so autogenerate can detect them.
Reads DATABASE_URL_SYNC from the app config for migration connections.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Add the backend directory to sys.path so app imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import settings
from app.database import Base

# Import all models so they register with Base.metadata
from app.modules.users.models import User, RefreshToken, NotificationPreference  # noqa: F401
from app.modules.athletes.models import Athlete, InjuryHistory, TrainingLoadEntry  # noqa: F401
from app.modules.video.models import Video, PoseFrame, BiomechanicalMetric, MovementType, MovementMetric  # noqa: F401
from app.modules.risk_scoring.models import MovementBaseline, AnomalyScore, RiskScore # noqa: F401
from app.modules.recommendations.models import Recommendation # noqa: F401
from app.modules.notifications.models import Notification # noqa: F401
from app.modules.analytics.models import ReportExport # noqa: F401

# this is the Alembic Config object
config = context.config

# Override sqlalchemy.url from application settings.
# Settings (not os.environ) so alembic honours backend/.env on a host run. Previously this read
# os.environ directly, so a host-side `alembic upgrade head` silently fell through to the
# container-internal default host `postgres:5432` and failed to resolve. Inside Docker,
# compose exports DATABASE_URL_SYNC, and pydantic-settings gives real env vars priority over
# .env, so the container still resolves to postgres:5432.
database_url = settings.database_url_sync
config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
