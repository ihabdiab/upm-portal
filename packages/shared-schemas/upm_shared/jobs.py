"""Job definition contract (§8 of the architecture plan)."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from upm_shared.enums import LoadMode, RetentionStrategy, SourceKind, SourceMode
from upm_shared.query import Filter


class JobSource(BaseModel):
    # `kind` selects the ingestion pathway (§1.1). Defaults to oracle for back-compat.
    kind: SourceKind = SourceKind.ORACLE

    # RDBMS (oracle / connection) fields:
    schema_name: str | None = Field(default=None, alias="schema")
    table: str | None = None
    mode: SourceMode = SourceMode.STRUCTURED
    columns: list[str] = Field(default_factory=list)
    filters: list[Filter] = Field(default_factory=list)
    raw_sql: str | None = None
    connection_id: int | None = None  # for kind=connection

    # CSV (Option B) fields:
    upload_id: str | None = None      # for kind=csv -> references uploads.id

    # DuckDB direct query (Option C):
    duckdb_sql: str | None = None     # for kind=duckdb_query

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def _coherent(self) -> JobSource:
        if self.kind in (SourceKind.ORACLE, SourceKind.CONNECTION):
            if self.kind is SourceKind.CONNECTION and self.connection_id is None:
                raise ValueError("connection source requires connection_id")
            if self.mode is SourceMode.RAW and not self.raw_sql:
                raise ValueError("raw mode requires raw_sql")
            if self.mode is SourceMode.STRUCTURED and not (self.table and self.columns):
                raise ValueError("structured RDBMS source requires table + columns")
        elif self.kind is SourceKind.CSV:
            if not self.upload_id:
                raise ValueError("csv source requires upload_id")
        elif self.kind is SourceKind.DUCKDB_QUERY:
            if not self.duckdb_sql:
                raise ValueError("duckdb_query source requires duckdb_sql")
        return self


class Schedule(BaseModel):
    # Minimal cron-ish surface for v1: every N of a unit, or an explicit cron string.
    every: str | None = None        # "1h", "15m", "1d"
    cron: str | None = None         # "0 * * * *"
    timezone: str = "UTC"

    @model_validator(mode="after")
    def _one_of(self) -> Schedule:
        if not self.every and not self.cron:
            raise ValueError("schedule needs 'every' or 'cron'")
        return self


class Watermark(BaseModel):
    column: str
    type: str = "timestamp"  # timestamp | integer


class Retention(BaseModel):
    strategy: RetentionStrategy = RetentionStrategy.ROLLING_WINDOW
    window_days: int | None = 395  # ~13 months default


class JobGuards(BaseModel):
    row_cap: int = 5_000_000
    timeout_s: int = 300


class JobDefinition(BaseModel):
    name: str
    source: JobSource
    target_table: str
    schedule: Schedule
    load_mode: LoadMode = LoadMode.UPSERT
    watermark: Watermark | None = None
    key_columns: list[str] = Field(default_factory=list)
    retention: Retention = Field(default_factory=Retention)
    guards: JobGuards = Field(default_factory=JobGuards)
    is_enabled: bool = True

    @model_validator(mode="after")
    def _coherent(self) -> JobDefinition:
        if self.load_mode is LoadMode.UPSERT and not self.key_columns:
            raise ValueError("upsert load_mode requires key_columns")
        # Watermarks only make sense for incremental DB extraction; CSV/query loads carry
        # the full delta in the file/result, so they don't need one.
        rdbms = self.source.kind in (SourceKind.ORACLE, SourceKind.CONNECTION)
        if rdbms and self.load_mode in (LoadMode.APPEND, LoadMode.UPSERT) and not self.watermark:
            raise ValueError("incremental DB load_mode requires a watermark")
        return self
