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
    # Settings is authoritative; push resolved values to the env the shared libs read so
    # the in-process worker (dev) and crypto see the same config.
    os.environ["UPM_DATABASE_URL"] = s.database_url
    os.environ["UPM_DUCKDB_PATH"] = s.duckdb_path
    os.environ["UPM_DUCKDB_LOAD_SPATIAL"] = "1" if s.duckdb_load_spatial else "0"
    os.environ["UPM_LANDING_DIR"] = s.landing_dir
    os.environ["UPM_UPLOAD_DIR"] = s.upload_dir
    os.environ["UPM_SOURCE_TYPE"] = s.source_type
    os.environ["UPM_ALLOWED_SOURCE_SCHEMAS"] = s.allowed_source_schemas
    if s.secret_key:
        os.environ["UPM_SECRET_KEY"] = s.secret_key
    if s.redis_url:
        os.environ["UPM_REDIS_URL"] = s.redis_url
    for key, val in (
        ("UPM_ORACLE_DSN", s.oracle_dsn),
        ("UPM_ORACLE_USER", s.oracle_user),
        ("UPM_ORACLE_PASSWORD", s.oracle_password),
    ):
        if val:
            os.environ[key] = val

    from upm_control_plane import reset_engine
    from upm_control_plane.crypto import reset_cache
    from upm_dataplane import reset_gateway

    reset_engine()
    reset_gateway()
    reset_cache()
    return s
