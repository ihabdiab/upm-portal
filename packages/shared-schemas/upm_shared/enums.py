"""Enumerations shared across the platform. Keep values stable — they are persisted."""

from __future__ import annotations

from enum import Enum


class LoadMode(str, Enum):
    """How a job's extracted Parquet is merged into the DuckDB target table."""

    FULL = "full"        # CREATE OR REPLACE from the parquet snapshot
    APPEND = "append"    # insert rows, no dedup
    UPSERT = "upsert"    # delete-by-key then insert (idempotent on replay)


class SourceMode(str, Enum):
    """Structured (safe builder) vs raw (validated power-user SQL)."""

    STRUCTURED = "structured"
    RAW = "raw"


class RetentionStrategy(str, Enum):
    KEEP_FOREVER = "keep_forever"
    ROLLING_WINDOW = "rolling_window"


class FilterOp(str, Enum):
    EQ = "="
    NEQ = "!="
    GT = ">"
    GTE = ">="
    LT = "<"
    LTE = "<="
    IN = "in"
    NOT_IN = "not_in"
    LIKE = "like"
    BETWEEN = "between"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class WidgetType(str, Enum):
    LINE = "line"
    BAR = "bar"
    AREA = "area"
    PIE = "pie"
    SCATTER = "scatter"
    KPI = "kpi"
    TABLE = "table"
    MAP = "map"


class Capability(str, Enum):
    """RBAC capabilities. Roles are sets of these (ADR-008)."""

    USER_MANAGE = "user:manage"
    JOB_AUTHOR = "job:author"
    DASHBOARD_AUTHOR = "dashboard:author"
    PROJECT_VIEW = "project:view"
