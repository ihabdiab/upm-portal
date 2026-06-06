"""Alembic environment — pulls the URL from UPM_DATABASE_URL and target metadata
from the ORM models so migrations stay in lockstep with the model definitions.
"""

from __future__ import annotations

import os

from alembic import context
from sqlalchemy import engine_from_config, pool

# Import models so Base.metadata is fully populated.
from upm_control_plane import models  # noqa: F401
from upm_control_plane.base import DEFAULT_SQLITE_URL, Base

config = context.config
config.set_main_option(
    "sqlalchemy.url", os.environ.get("UPM_DATABASE_URL", DEFAULT_SQLITE_URL)
)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
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
            target_metadata=target_metadata,
            render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
