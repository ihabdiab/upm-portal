"""Pick the source for a job by its declared kind (§1.1)."""

from __future__ import annotations

from upm_shared.enums import SourceKind
from upm_shared.jobs import JobDefinition

from upm_ingestion.config import IngestionConfig
from upm_ingestion.sources.base import Source


def get_source(job: JobDefinition, config: IngestionConfig | None = None) -> Source:
    cfg = config or IngestionConfig.from_env()
    kind = job.source.kind

    if kind is SourceKind.CSV:
        from upm_ingestion.sources.csv_source import CsvSource

        return CsvSource()

    if kind is SourceKind.CONNECTION:
        from upm_ingestion.sources.connection_source import ConnectionSource

        return ConnectionSource()

    if kind is SourceKind.DUCKDB_QUERY:
        raise NotImplementedError(
            "duckdb_query job source runs Gateway-side and is deferred to a later iteration"
        )

    # kind == ORACLE: real Oracle when configured, else the synthetic generator.
    if cfg.source_type == "oracle" and cfg.oracle_dsn and cfg.oracle_user and cfg.oracle_password:
        from upm_ingestion.sources.oracle import OracleSource

        return OracleSource(cfg.oracle_dsn, cfg.oracle_user, cfg.oracle_password, cfg.allowed_schemas)

    from upm_ingestion.sources.synthetic import SyntheticSource

    return SyntheticSource()
