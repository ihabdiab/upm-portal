"""UPM control plane — transactional metadata (Postgres in prod, SQLite for local demo).

Strictly separate from the DuckDB analytics plane (ADR-003). Never co-mingle.
"""

from upm_control_plane.base import (
    Base,
    get_engine,
    get_sessionmaker,
    reset_engine,
    session_scope,
)

__all__ = ["Base", "get_engine", "get_sessionmaker", "reset_engine", "session_scope"]
