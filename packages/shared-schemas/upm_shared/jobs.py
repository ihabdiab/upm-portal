"""Job definition contract (§8 of the architecture plan)."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from upm_shared.enums import LoadMode, RetentionStrategy, SourceMode
from upm_shared.query import Filter


class JobSource(BaseModel):
    schema_name: str = Field(alias="schema")
    table: str
    mode: SourceMode = SourceMode.STRUCTURED
    columns: list[str] = Field(default_factory=list)
    filters: list[Filter] = Field(default_factory=list)
    raw_sql: str | None = None

    model_config = {"populate_by_name": True}

    @model_validator(mode="after")
    def _raw_requires_sql(self) -> JobSource:
        if self.mode is SourceMode.RAW and not self.raw_sql:
            raise ValueError("raw mode requires raw_sql")
        if self.mode is SourceMode.STRUCTURED and not self.columns:
            raise ValueError("structured mode requires at least one column")
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
        if self.load_mode in (LoadMode.APPEND, LoadMode.UPSERT) and not self.watermark:
            raise ValueError("incremental load_mode requires a watermark")
        return self
