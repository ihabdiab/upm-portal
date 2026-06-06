"""Request-scoped DB session dependency for FastAPI."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session
from upm_control_plane import get_sessionmaker


def get_session() -> Iterator[Session]:
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
