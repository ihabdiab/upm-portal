"""CSV source (§1.1 Option B). Reads an uploaded CSV via DuckDB read_csv_auto and writes
the (optionally column-pruned) rows to the Parquet landing zone. Full-load by nature.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
from upm_shared.jobs import JobDefinition
from upm_sql_tools.identifiers import quote_ident

from upm_ingestion.sources.base import ExtractResult


def _reader(path: str) -> str:
    p = str(path).replace("\\", "/").replace("'", "''")
    return f"read_csv_auto('{p}')"


class CsvSource:
    def _upload(self, upload_id: str) -> str:
        from upm_control_plane import session_scope
        from upm_control_plane.models import Upload

        with session_scope() as session:
            up = session.get(Upload, upload_id)
            if up is None:
                raise LookupError(f"upload {upload_id!r} not found")
            return up.stored_path

    def extract(
        self,
        job: JobDefinition,
        *,
        watermark_value: str | None,
        landing_path: str,
        row_cap: int,
    ) -> ExtractResult:
        path = self._upload(job.source.upload_id)
        cols = list(job.source.columns)
        select = ", ".join(quote_ident(c) for c in cols) if cols else "*"
        reader = _reader(path)

        Path(landing_path).parent.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect()
        try:
            con.execute(f"CREATE TABLE staging AS SELECT {select} FROM {reader} LIMIT {int(row_cap)}")
            n = int(con.execute("SELECT count(*) FROM staging").fetchone()[0])
            out = str(landing_path).replace("\\", "/")
            con.execute(f"COPY staging TO '{out}' (FORMAT PARQUET)")
        finally:
            con.close()

        return ExtractResult(
            landing_path=landing_path, rows_read=n, new_watermark=None, columns=cols
        )

    def preview(self, job: JobDefinition, *, n: int = 20) -> list[dict]:
        path = self._upload(job.source.upload_id)
        con = duckdb.connect()
        try:
            cur = con.execute(f"SELECT * FROM {_reader(path)} LIMIT {int(n)}")
            names = [d[0] for d in cur.description]
            return [dict(zip(names, r, strict=False)) for r in cur.fetchall()]
        finally:
            con.close()
