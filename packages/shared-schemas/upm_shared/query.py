"""Query contract — the shape Dashboard Builder emits and the read path executes.

This is a *structured* query (table -> columns -> typed predicates). No raw SQL crosses
the wire on the read path; sql-tools renders it to a parameterized DuckDB SELECT.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from upm_shared.enums import FilterOp

# Aggregation functions we are willing to render. Allow-list, never free text.
AGG_FUNCTIONS = {"sum", "avg", "min", "max", "count", "count_distinct", "median", "stddev"}


class Filter(BaseModel):
    col: str
    op: FilterOp
    # value is unused for IS_NULL/IS_NOT_NULL; a 2-list for BETWEEN; a list for IN/NOT_IN.
    value: Any | None = None


class Aggregation(BaseModel):
    fn: str
    col: str | None = None  # None allowed only for count(*)
    as_: str = Field(alias="as")

    model_config = {"populate_by_name": True}

    @field_validator("fn")
    @classmethod
    def _known_fn(cls, v: str) -> str:
        v = v.lower()
        if v not in AGG_FUNCTIONS:
            raise ValueError(f"unsupported aggregation '{v}'")
        return v


class Sort(BaseModel):
    col: str
    dir: str = "asc"

    @field_validator("dir")
    @classmethod
    def _dir(cls, v: str) -> str:
        v = v.lower()
        if v not in ("asc", "desc"):
            raise ValueError("sort dir must be 'asc' or 'desc'")
        return v


class QueryRequest(BaseModel):
    table: str
    columns: list[str] = Field(default_factory=list)
    aggregations: list[Aggregation] = Field(default_factory=list)
    group_by: list[str] = Field(default_factory=list, alias="groupBy")
    filters: list[Filter] = Field(default_factory=list)
    sort: list[Sort] = Field(default_factory=list)
    limit: int = Field(default=1000, ge=1, le=100_000)
    page: int = Field(default=1, ge=1)
    # Pin a specific materialization for reproducibility (None = latest).
    table_version_pin: int | None = None

    model_config = {"populate_by_name": True}


class QueryResponse(BaseModel):
    rows: list[dict[str, Any]]
    page: int
    total: int | None = None
    table_version: int
    data_as_of: datetime | None = None
    stale: bool = False
    cached: bool = False
