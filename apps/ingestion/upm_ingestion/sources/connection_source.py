"""Connection source (§1.1 Option A + §4). Extracts from a saved RDBMS connection via
SQLAlchemy, so the same code path serves Oracle/Postgres/MySQL/MSSQL/generic.

SQLAlchemy's text() binds (`:name`) are translated to each driver's paramstyle, so the
watermark predicate is portable. Identifiers are validated (bare) to stay dialect-neutral.
"""

from __future__ import annotations

from datetime import date, datetime

from upm_shared.enums import SourceMode
from upm_shared.jobs import JobDefinition
from upm_sql_tools.identifiers import validate_ident
from upm_sql_tools.validate import assert_select_only

from upm_ingestion.sources.base import ExtractResult
from upm_ingestion.sources.util import rows_to_parquet


def _build_select(job: JobDefinition, watermark_value: str | None) -> tuple[str, dict]:
    src = job.source
    if src.mode is SourceMode.RAW:
        assert_select_only(src.raw_sql or "", dialect=None)
        binds = {"watermark": watermark_value} if watermark_value is not None else {}
        return src.raw_sql, binds

    cols = ", ".join(validate_ident(c) for c in src.columns)
    table = validate_ident(src.table)
    ident = f"{validate_ident(src.schema_name)}.{table}" if src.schema_name else table
    sql = f"SELECT {cols} FROM {ident}"
    binds: dict = {}
    wm_col = job.watermark.column if job.watermark else None
    if wm_col and watermark_value is not None:
        sql += f" WHERE {validate_ident(wm_col)} > :watermark"
        binds["watermark"] = watermark_value
    if wm_col:
        sql += f" ORDER BY {validate_ident(wm_col)} ASC"
    return sql, binds


class ConnectionSource:
    def _engine(self, connection_id: int):
        from sqlalchemy import create_engine
        from upm_control_plane import session_scope
        from upm_control_plane.crypto import decrypt
        from upm_control_plane.models import Connection
        from upm_shared.connections import build_sqlalchemy_url
        from upm_shared.enums import ConnectionKind

        with session_scope() as session:
            conn = session.get(Connection, connection_id)
            if conn is None:
                raise LookupError(f"connection {connection_id} not found")
            url = build_sqlalchemy_url(
                ConnectionKind(conn.kind),
                host=conn.host, port=conn.port, database=conn.database,
                username=conn.username, password=decrypt(conn.encrypted_password),
                extra=conn.extra, generic_url=decrypt(conn.encrypted_url),
            )
        return create_engine(url)

    def extract(
        self,
        job: JobDefinition,
        *,
        watermark_value: str | None,
        landing_path: str,
        row_cap: int,
    ) -> ExtractResult:
        from sqlalchemy import text

        sql, binds = _build_select(job, watermark_value)
        engine = self._engine(job.source.connection_id)
        try:
            with engine.connect() as conn:
                result = conn.execute(text(sql), binds)
                columns = [str(c) for c in result.keys()]
                rows = result.fetchmany(int(row_cap))
        finally:
            engine.dispose()

        tuples = [tuple(r) for r in rows]
        n = rows_to_parquet(columns, tuples, landing_path)

        new_wm = watermark_value
        wm_col = job.watermark.column if job.watermark else None
        if wm_col and wm_col in columns and tuples:
            idx = columns.index(wm_col)
            mx = max(r[idx] for r in tuples if r[idx] is not None)
            new_wm = mx.isoformat() if isinstance(mx, datetime | date) else str(mx)

        return ExtractResult(
            landing_path=landing_path, rows_read=n, new_watermark=new_wm, columns=columns
        )

    def preview(self, job: JobDefinition, *, n: int = 20) -> list[dict]:
        from sqlalchemy import text

        sql, binds = _build_select(job, None)
        engine = self._engine(job.source.connection_id)
        try:
            with engine.connect() as conn:
                result = conn.execute(text(sql), binds)
                names = list(result.keys())
                rows = result.fetchmany(n)
        finally:
            engine.dispose()
        return [dict(zip(names, r, strict=False)) for r in rows]
