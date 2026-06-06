"""UPM shared contracts — one source of truth for API/job/dashboard schemas.

Imported by backend, ingestion, dataplane and sql-tools. No runtime deps beyond Pydantic.
"""

from upm_shared.auth import LoginRequest, MeResponse, TokenResponse, UserOut
from upm_shared.catalog import ColumnInfo, Freshness, TableDetail, TableSummary
from upm_shared.dashboards import DashboardDefinition, Widget
from upm_shared.enums import (
    Capability,
    FilterOp,
    LoadMode,
    RetentionStrategy,
    SourceMode,
    WidgetType,
)
from upm_shared.jobs import JobDefinition, JobGuards, JobSource, Retention, Schedule, Watermark
from upm_shared.loadcmd import LoadCommand, LoadResult
from upm_shared.query import Aggregation, Filter, QueryRequest, QueryResponse, Sort

__all__ = [
    "Aggregation",
    "Capability",
    "ColumnInfo",
    "DashboardDefinition",
    "Filter",
    "FilterOp",
    "Freshness",
    "JobDefinition",
    "JobGuards",
    "JobSource",
    "LoadCommand",
    "LoadMode",
    "LoadResult",
    "LoginRequest",
    "MeResponse",
    "QueryRequest",
    "QueryResponse",
    "Retention",
    "RetentionStrategy",
    "Schedule",
    "Sort",
    "SourceMode",
    "TableDetail",
    "TableSummary",
    "TokenResponse",
    "UserOut",
    "Watermark",
    "Widget",
    "WidgetType",
]
