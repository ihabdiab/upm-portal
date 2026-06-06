"""Ingestion config — reads the same UPM_* env the backend sets (no backend import)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class IngestionConfig:
    source_type: str
    landing_dir: str
    redis_url: str | None
    oracle_dsn: str | None
    oracle_user: str | None
    oracle_password: str | None
    allowed_schemas: set[str]

    @staticmethod
    def from_env() -> IngestionConfig:
        schemas = {
            s.strip()
            for s in os.environ.get("UPM_ALLOWED_SOURCE_SCHEMAS", "SON").split(",")
            if s.strip()
        }
        return IngestionConfig(
            source_type=os.environ.get("UPM_SOURCE_TYPE", "synthetic"),
            landing_dir=os.environ.get("UPM_LANDING_DIR", "./data/landing"),
            redis_url=os.environ.get("UPM_REDIS_URL"),
            oracle_dsn=os.environ.get("UPM_ORACLE_DSN"),
            oracle_user=os.environ.get("UPM_ORACLE_USER"),
            oracle_password=os.environ.get("UPM_ORACLE_PASSWORD"),
            allowed_schemas=schemas,
        )
