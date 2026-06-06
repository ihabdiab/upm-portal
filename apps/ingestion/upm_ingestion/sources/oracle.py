"""Oracle source (python-oracledb, thin mode).

Used when UPM_SOURCE_TYPE=oracle and creds are provisioned. Talks to the read-only
service account, renders the extraction SELECT via sql-tools, applies call_timeout +
FETCH FIRST guards, and writes the delta to Parquet. Not exercised in the no-Oracle
demo; kept code-complete for the real deployment (§11.2, §15).
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

import duckdb
from upm_shared.jobs import JobDefinition
from upm_sql_tools.oracle_builder import build_extract_select

from upm_ingestion.sources.base import ExtractResult


def _duck_type(value_sample) -> str:
    if isinstance(value_sample, (datetime, date)):
        return "TIMESTAMP"
    if isinstance(value_sample, (int, float, Decimal)):
        return "DOUBLE"
    return "VARCHAR"


class OracleSource:
    def __init__(self, dsn: str, user: str, password: str, allowed_schemas: set[str]) -> None:
        self._dsn = dsn
        self._user = user
        self._password = password
        self._allowed = {s.lower() for s in allowed_schemas}

    def _connect(self, timeout_s: int):
        import oracledb

        con = oracledb.connect(user=self._user, password=self._password, dsn=self._dsn)
        con.call_timeout = max(1, timeout_s) * 1000  # ms
        return con

    def _run(self, job: JobDefinition, *, watermark_value, row_cap):
        wm_col = job.watermark.column if job.watermark else None
        sql, binds = build_extract_select(
            job.source,
            watermark_column=wm_col,
            watermark_value=watermark_value,
            limit=row_cap,
            allowed_schemas=self._allowed,
        )
        con = self._connect(job.guards.timeout_s)
        try:
            cur = con.cursor()
            cur.execute(sql, binds)
            columns = [d[0].lower() for d in cur.description]
            rows = cur.fetchall()
        finally:
            con.close()
        return columns, rows, wm_col

    def extract(
        self,
        job: JobDefinition,
        *,
        watermark_value: str | None,
        landing_path: str,
        row_cap: int,
    ) -> ExtractResult:
        columns, rows, wm_col = self._run(job, watermark_value=watermark_value, row_cap=row_cap)

        # Normalize Decimals to float for Parquet friendliness.
        norm = [
            tuple(float(v) if isinstance(v, Decimal) else v for v in row) for row in rows
        ]

        Path(landing_path).parent.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect()
        try:
            sample = norm[0] if norm else [None] * len(columns)
            coldefs = ", ".join(
                f'"{c}" {_duck_type(sample[i])}' for i, c in enumerate(columns)
            )
            con.execute(f"CREATE TABLE staging ({coldefs})")
            if norm:
                ph = ", ".join("?" for _ in columns)
                con.executemany(f"INSERT INTO staging VALUES ({ph})", norm)
            out = str(landing_path).replace("\\", "/")
            con.execute(f"COPY staging TO '{out}' (FORMAT PARQUET)")
        finally:
            con.close()

        new_wm = watermark_value
        if wm_col and wm_col in columns and norm:
            idx = columns.index(wm_col)
            mx = max(r[idx] for r in norm)
            new_wm = mx.isoformat() if isinstance(mx, (datetime, date)) else str(mx)

        return ExtractResult(
            landing_path=landing_path, rows_read=len(norm), new_watermark=new_wm, columns=columns
        )

    def preview(self, job: JobDefinition, *, n: int = 20) -> list[dict]:
        columns, rows, _ = self._run(job, watermark_value=None, row_cap=n)
        return [dict(zip(columns, r, strict=False)) for r in rows[:n]]
