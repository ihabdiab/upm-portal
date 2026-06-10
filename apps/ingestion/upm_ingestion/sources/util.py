"""Shared helpers for sources that produce rows in memory (connection-based extract)."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import duckdb


def _duck_type(sample) -> str:
    if isinstance(sample, datetime | date):
        return "TIMESTAMP"
    if isinstance(sample, bool):
        return "BOOLEAN"
    if isinstance(sample, int | float | Decimal):
        return "DOUBLE"
    return "VARCHAR"


def rows_to_parquet(columns: list[str], rows: list[tuple], landing_path: str) -> int:
    """Write rows to a Parquet file at landing_path; return row count. Decimals -> float."""
    norm = [tuple(float(v) if isinstance(v, Decimal) else v for v in row) for row in rows]
    Path(landing_path).parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    try:
        sample = norm[0] if norm else [None] * len(columns)
        coldefs = ", ".join(f'"{c}" {_duck_type(sample[i])}' for i, c in enumerate(columns))
        con.execute(f"CREATE TABLE staging ({coldefs})")
        if norm:
            ph = ", ".join("?" for _ in columns)
            con.executemany(f"INSERT INTO staging VALUES ({ph})", norm)
        out = str(landing_path).replace("\\", "/")
        con.execute(f"COPY staging TO '{out}' (FORMAT PARQUET)")
    finally:
        con.close()
    return len(norm)
