"""Catalog / freshness contracts. Registry-backed — never hits Oracle (§6, §10)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Freshness(BaseModel):
    last_load_started_at: datetime | None = None
    last_load_succeeded_at: datetime | None = None
    last_load_status: str | None = None
    last_watermark_value: str | None = None
    table_version: int = 0
    row_count: int = 0
    stale: bool = False


class TableSummary(BaseModel):
    table_name: str
    row_count: int = 0
    last_load_succeeded_at: datetime | None = None
    last_load_status: str | None = None
    is_visible: bool = True
    stale: bool = False


class ColumnInfo(BaseModel):
    name: str
    type: str
    comment: str | None = None


class TableDetail(BaseModel):
    table_name: str
    columns: list[ColumnInfo]
    freshness: Freshness
    sample_rows: list[dict] | None = None
