"""Wire backend Settings into the environment that the shared libraries read.

control_plane and dataplane read UPM_DATABASE_URL / UPM_DUCKDB_PATH from os.environ so
they can be used outside the backend (worker, CLI). The backend is the place that owns
Settings, so at startup it pushes the resolved values back into the environment and
resets the cached engine/gateway. Idempotent.
"""

from __future__ import annotations

import os

from upm_backend.config import Settings, get_settings


def apply_runtime_env(settings: Settings | None = None) -> Settings:
    s = settings or get_settings()
    os.environ.setdefault("UPM_DATABASE_URL", s.database_url)
    # These two are authoritative from Settings (override env defaults).
    os.environ["UPM_DATABASE_URL"] = s.database_url
    os.environ["UPM_DUCKDB_PATH"] = s.duckdb_path
    os.environ["UPM_DUCKDB_LOAD_SPATIAL"] = "1" if s.duckdb_load_spatial else "0"

    from upm_control_plane import reset_engine
    from upm_dataplane import reset_gateway

    reset_engine()
    reset_gateway()
    return s
