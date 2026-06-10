"""add connections + uploads tables (Phase 2)

Additive snapshot: create_all has checkfirst=True, so on a fresh DB (where 0001 already
built the full current metadata) this is a no-op, and on a v1 DB it adds just the two new
tables. Downgrade drops them explicitly.

Revision ID: 0002_connections_uploads
Revises: 0001_initial
Create Date: 2026-06-06
"""

from __future__ import annotations

from alembic import op
from upm_control_plane import models  # noqa: F401  (populate metadata)
from upm_control_plane.base import Base

revision = "0002_connections_uploads"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())  # checkfirst=True -> only missing tables


def downgrade() -> None:
    bind = op.get_bind()
    Base.metadata.tables["uploads"].drop(bind=bind, checkfirst=True)
    Base.metadata.tables["connections"].drop(bind=bind, checkfirst=True)
