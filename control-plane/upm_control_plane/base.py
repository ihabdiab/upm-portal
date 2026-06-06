"""Engine / session factory for the control plane.

Reads UPM_DATABASE_URL (default: a local SQLite file for the zero-dependency demo).
Compose sets it to the Postgres DSN. JSON columns use JSONB on Postgres, JSON on SQLite.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache

from sqlalchemy import JSON, create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_SQLITE_URL = "sqlite+pysqlite:///./control.sqlite3"

# Portable JSON: JSONB where we have Postgres, plain JSON on SQLite.
JsonType = JSON().with_variant(JSONB, "postgresql")


class Base(DeclarativeBase):
    pass


def _database_url() -> str:
    return os.environ.get("UPM_DATABASE_URL", DEFAULT_SQLITE_URL)


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    url = _database_url()
    kwargs: dict = {"pool_pre_ping": True, "future": True}
    if url.startswith("sqlite"):
        # Allow use across threads (FastAPI + background load consumer).
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(url, **kwargs)


@lru_cache(maxsize=1)
def get_sessionmaker() -> sessionmaker[Session]:
    return sessionmaker(bind=get_engine(), autoflush=False, expire_on_commit=False)


def reset_engine() -> None:
    """Drop cached engine/sessionmaker (used by tests that switch DB URLs)."""
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()


@contextmanager
def session_scope() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
