"""Dashboard definition contract (§7). Stored as JSONB in `dashboards.definition`."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from upm_shared.enums import WidgetType
from upm_shared.query import QueryRequest


class WidgetSource(BaseModel):
    table: str
    table_version_pin: int | None = None


class GridPos(BaseModel):
    x: int = 0
    y: int = 0
    w: int = 6
    h: int = 6


class Widget(BaseModel):
    id: str
    type: WidgetType
    title: str = ""
    source: WidgetSource
    query: QueryRequest
    # Free-form visual mapping (x/series/y for charts; lat/lon/weight for maps).
    viz: dict[str, Any] = Field(default_factory=dict)
    grid: GridPos = Field(default_factory=GridPos)


class Layout(BaseModel):
    cols: int = 12
    row_height: int = Field(default=40, alias="rowHeight")

    model_config = {"populate_by_name": True}


class DashboardDefinition(BaseModel):
    version: int = 1
    layout: Layout = Field(default_factory=Layout)
    widgets: list[Widget] = Field(default_factory=list)
