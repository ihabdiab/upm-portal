"""Backend settings. All knobs come from the environment (Docker secrets / .env)."""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="UPM_", env_file=".env", extra="ignore")

    # Stores
    database_url: str = "sqlite+pysqlite:///./control.sqlite3"
    duckdb_path: str = "./data/duckdb/analytics.duckdb"
    duckdb_load_spatial: bool = False
    landing_dir: str = "./data/landing"
    export_dir: str = "./data/exports"
    upload_dir: str = "./data/uploads"
    max_upload_mb: int = 200

    # Redis: when unset, the backend runs in single-process "dev" mode
    # (in-memory cache, inline job runner, no Redis load-consumer thread).
    redis_url: str | None = None

    # Auth + credential encryption (connection registry, §4)
    secret_key: str | None = None  # Fernet key source for encrypting stored credentials
    jwt_secret: str = "dev-insecure-secret-change-me"
    jwt_alg: str = "HS256"
    access_ttl_min: int = 60
    refresh_ttl_days: int = 7

    # Read path / freshness
    stale_k: float = 2.0
    query_cache_ttl_s: int = 300

    # Extraction source
    source_type: str = "synthetic"  # synthetic | oracle
    oracle_dsn: str | None = None
    oracle_user: str | None = None
    oracle_password: str | None = None
    allowed_source_schemas: str = "SON"

    # AI proxy (Phase 5)
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str = "qwen3"

    # Web
    cors_origins: str = "*"

    @property
    def dev_mode(self) -> bool:
        return not self.redis_url

    @property
    def allowed_schemas_set(self) -> set[str]:
        return {s.strip() for s in self.allowed_source_schemas.split(",") if s.strip()}

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
