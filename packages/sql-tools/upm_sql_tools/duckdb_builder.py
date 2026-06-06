"""Render a structured QueryRequest into a parameterized DuckDB SELECT.

Returns (sql, params) where params is a positional list bound with DuckDB '?' markers.
Identifiers are validated+quoted; all *values* are bound, never interpolated.
"""

from __future__ import annotations

from upm_shared.enums import FilterOp
from upm_shared.query import Aggregation, Filter, QueryRequest

from upm_sql_tools.identifiers import quote_ident

_AGG_RENDER = {
    "sum": lambda c: f"sum({c})",
    "avg": lambda c: f"avg({c})",
    "min": lambda c: f"min({c})",
    "max": lambda c: f"max({c})",
    "median": lambda c: f"median({c})",
    "stddev": lambda c: f"stddev({c})",
    "count": lambda c: f"count({c})" if c else "count(*)",
    "count_distinct": lambda c: f"count(DISTINCT {c})",
}


def _render_agg(a: Aggregation) -> str:
    col_sql = quote_ident(a.col) if a.col else None
    expr = _AGG_RENDER[a.fn](col_sql)
    return f"{expr} AS {quote_ident(a.as_)}"


def _render_filter(f: Filter, params: list) -> str:
    col = quote_ident(f.col)
    op = f.op
    if op in (FilterOp.IS_NULL, FilterOp.IS_NOT_NULL):
        return f"{col} IS {'NOT ' if op is FilterOp.IS_NOT_NULL else ''}NULL"
    if op in (FilterOp.IN, FilterOp.NOT_IN):
        values = list(f.value or [])
        if not values:
            # Empty IN: render a contradiction / tautology so SQL stays valid.
            return "1=0" if op is FilterOp.IN else "1=1"
        marks = ", ".join("?" for _ in values)
        params.extend(values)
        keyword = "IN" if op is FilterOp.IN else "NOT IN"
        return f"{col} {keyword} ({marks})"
    if op is FilterOp.BETWEEN:
        lo, hi = f.value
        params.extend([lo, hi])
        return f"{col} BETWEEN ? AND ?"
    if op is FilterOp.LIKE:
        params.append(f.value)
        return f"{col} LIKE ?"
    # Scalar comparisons
    params.append(f.value)
    return f"{col} {op.value} ?"


def build_read_select(q: QueryRequest) -> tuple[str, list]:
    params: list = []

    # SELECT list
    select_parts: list[str] = []
    if q.aggregations:
        select_parts.extend(quote_ident(c) for c in q.group_by)
        select_parts.extend(_render_agg(a) for a in q.aggregations)
    elif q.columns:
        select_parts.extend(quote_ident(c) for c in q.columns)
    else:
        select_parts.append("*")

    sql = f"SELECT {', '.join(select_parts)} FROM {quote_ident(q.table)}"

    # WHERE
    if q.filters:
        clauses = [_render_filter(f, params) for f in q.filters]
        sql += " WHERE " + " AND ".join(clauses)

    # GROUP BY
    if q.aggregations and q.group_by:
        sql += " GROUP BY " + ", ".join(quote_ident(c) for c in q.group_by)

    # ORDER BY
    if q.sort:
        order = ", ".join(f"{quote_ident(s.col)} {s.dir.upper()}" for s in q.sort)
        sql += " ORDER BY " + order

    # LIMIT / OFFSET (pagination)
    offset = (q.page - 1) * q.limit
    sql += " LIMIT ? OFFSET ?"
    params.extend([q.limit, offset])

    return sql, params


def build_count_select(q: QueryRequest) -> tuple[str, list]:
    """COUNT(*) over the same filtered (pre-aggregation, pre-limit) row set."""
    params: list = []
    sql = f"SELECT count(*) AS n FROM {quote_ident(q.table)}"
    if q.filters:
        clauses = [_render_filter(f, params) for f in q.filters]
        sql += " WHERE " + " AND ".join(clauses)
    return sql, params
