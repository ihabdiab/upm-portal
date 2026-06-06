"""Render a structured JobSource into a parameterized Oracle extraction SELECT.

Returns (sql, binds) where binds is a dict for python-oracledb named binds.
Structured mode renders from validated identifiers + typed predicates. Raw mode is
validated as single-statement SELECT (schema allow-listed) and passed through.
"""

from __future__ import annotations

from upm_shared.enums import FilterOp, SourceMode
from upm_shared.jobs import JobSource
from upm_shared.query import Filter

from upm_sql_tools.identifiers import quote_ident, quote_qualified
from upm_sql_tools.validate import assert_select_only


def _render_filter(f: Filter, binds: dict, idx: list[int]) -> str:
    col = quote_ident(f.col)
    op = f.op
    if op in (FilterOp.IS_NULL, FilterOp.IS_NOT_NULL):
        return f"{col} IS {'NOT ' if op is FilterOp.IS_NOT_NULL else ''}NULL"
    if op in (FilterOp.IN, FilterOp.NOT_IN):
        values = list(f.value or [])
        if not values:
            return "1=0" if op is FilterOp.IN else "1=1"
        names = []
        for v in values:
            key = f"b{idx[0]}"
            idx[0] += 1
            binds[key] = v
            names.append(f":{key}")
        keyword = "IN" if op is FilterOp.IN else "NOT IN"
        return f"{col} {keyword} ({', '.join(names)})"
    if op is FilterOp.BETWEEN:
        lo_key, hi_key = f"b{idx[0]}", f"b{idx[0] + 1}"
        idx[0] += 2
        binds[lo_key], binds[hi_key] = f.value
        return f"{col} BETWEEN :{lo_key} AND :{hi_key}"
    key = f"b{idx[0]}"
    idx[0] += 1
    binds[key] = f.value
    sql_op = "LIKE" if op is FilterOp.LIKE else op.value
    return f"{col} {sql_op} :{key}"


def build_extract_select(
    source: JobSource,
    *,
    watermark_column: str | None = None,
    watermark_value=None,
    limit: int | None = None,
    allowed_schemas: set[str] | None = None,
) -> tuple[str, dict]:
    if source.mode is SourceMode.RAW:
        sql = source.raw_sql or ""
        assert_select_only(
            sql, dialect="oracle", allowed_schemas=allowed_schemas, require_bounded=True
        )
        binds: dict = {}
        if watermark_value is not None:
            binds["watermark"] = watermark_value
        return sql, binds

    # structured
    binds = {}
    idx = [0]
    cols = ", ".join(quote_ident(c) for c in source.columns)
    table = quote_qualified(source.schema_name, source.table, dialect="oracle")
    sql = f"SELECT {cols} FROM {table}"

    where_clauses: list[str] = [_render_filter(f, binds, idx) for f in source.filters]
    if watermark_column is not None and watermark_value is not None:
        binds["watermark"] = watermark_value
        where_clauses.append(f"{quote_ident(watermark_column)} > :watermark")
    if where_clauses:
        sql += " WHERE " + " AND ".join(where_clauses)

    if watermark_column is not None:
        sql += f" ORDER BY {quote_ident(watermark_column)} ASC"
    if limit is not None:
        binds["row_cap"] = limit
        sql += " FETCH FIRST :row_cap ROWS ONLY"

    return sql, binds
