"""
Alembic environment configuration for CallCoach CRM.
Uses the same DATABASE_URL from app config so migrations always target the correct database.
"""
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context

import sys
from pathlib import Path

# Add project root to path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DATABASE_URL
from app.database import Base

# Import ALL models so Alembic can detect them for autogenerate
from app.models import (
    User, Clinic, Call, CallNote, PipelineDeal,
    DealActivity, CoachingInsight, CallScore, Tag,
    LearningProgress, Certification, WeeklyReport
)

config = context.config

# Override sqlalchemy.url from app config (not alembic.ini)
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Point Alembic at our models
target_metadata = Base.metadata


def run_migrations_offline() -> None:
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
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
