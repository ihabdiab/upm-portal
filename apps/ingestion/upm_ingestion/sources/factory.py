"""Pick the configured source. Default synthetic; oracle when creds are present."""

from __future__ import annotations

from upm_ingestion.config import IngestionConfig
from upm_ingestion.sources.base import Source


def get_source(config: IngestionConfig | None = None) -> Source:
    cfg = config or IngestionConfig.from_env()
    if cfg.source_type == "oracle":
        if not (cfg.oracle_dsn and cfg.oracle_user and cfg.oracle_password):
            raise RuntimeError("UPM_SOURCE_TYPE=oracle but Oracle DSN/user/password are unset")
        from upm_ingestion.sources.oracle import OracleSource

        return OracleSource(cfg.oracle_dsn, cfg.oracle_user, cfg.oracle_password, cfg.allowed_schemas)

    from upm_ingestion.sources.synthetic import SyntheticSource

    return SyntheticSource()
