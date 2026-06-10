"""DuckDBGateway — single-writer owner of the analytics file.

Design (ADR-002, §9):
  * Exactly one DuckDB connection per process, guarded by a re-entrant lock. Every read
    and write goes through it, so a separate worker can never open the file concurrently.
  * Writes follow extract->Parquet->staging->atomic-swap. The Parquet file is the load
    input *and* the replay log (ADR-006); re-running a command is idempotent.
  * On every successful load the Gateway updates `table_registry` (row_count,
    table_version++, freshness timestamps) — freshness and cache invalidation share the
    `table_version` lever (§10).
"""

from __future__ import annotations

import os
import threading
from datetime import UTC, datetime
from pathlib import Path

import duckdb
from upm_control_plane import session_scope
from upm_control_plane.models import TableRegistry
from upm_shared.catalog import ColumnInfo
from upm_shared.enums import LoadMode
from upm_shared.loadcmd import LoadCommand, LoadResult
from upm_sql_tools.identifiers import quote_ident, validate_ident


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _pq(path: str) -> str:
    """A safe single-quoted parquet path literal (forward slashes for Windows)."""
    norm = str(path).replace("\\", "/").replace("'", "''")
    return f"read_parquet('{norm}')"


class DuckDBGateway:
    def __init__(self, db_path: str, *, load_spatial: bool = False) -> None:
        self.db_path = db_path
        self._load_spatial = load_spatial
        self._lock = threading.RLock()
        self._conn: duckdb.DuckDBPyConnection | None = None

    # ----- connection -----------------------------------------------------
    def _connection(self) -> duckdb.DuckDBPyConnection:
        if self._conn is None:
            if self.db_path != ":memory:":
                Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
            self._conn = duckdb.connect(self.db_path)
            if self._load_spatial:
                try:
                    self._conn.execute("INSTALL spatial; LOAD spatial;")
                except Exception:  # noqa: BLE001 - offline / no extension is non-fatal
                    pass
        return self._conn

    def close(self) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
                self._conn = None

    # ----- reads (fanned out, read-only) ----------------------------------
    def execute_read(self, sql: str, params: list | None = None) -> tuple[list[str], list[dict]]:
        with self._lock:
            cur = self._connection().cursor()
            cur.execute(sql, params or [])
            columns = [d[0] for d in cur.description] if cur.description else []
            rows = [dict(zip(columns, row, strict=False)) for row in cur.fetchall()]
            return columns, rows

    def table_exists(self, table: str) -> bool:
        validate_ident(table)
        with self._lock:
            row = self._connection().execute(
                "SELECT 1 FROM information_schema.tables WHERE table_name = ?", [table]
            ).fetchone()
            return row is not None

    def table_columns(self, table: str) -> list[ColumnInfo]:
        if not self.table_exists(table):
            return []
        with self._lock:
            rows = self._connection().execute(f"DESCRIBE {quote_ident(table)}").fetchall()
        # DESCRIBE => (column_name, column_type, null, key, default, extra)
        return [ColumnInfo(name=r[0], type=str(r[1])) for r in rows]

    def sample_rows(self, table: str, n: int = 20) -> list[dict]:
        if not self.table_exists(table):
            return []
        cols, rows = self.execute_read(f"SELECT * FROM {quote_ident(table)} LIMIT ?", [n])
        return rows

    def row_count(self, table: str) -> int:
        if not self.table_exists(table):
            return 0
        with self._lock:
            return int(
                self._connection().execute(f"SELECT count(*) FROM {quote_ident(table)}").fetchone()[0]
            )

    # ----- writes (serialized; the only RW path) --------------------------
    def _source_expr(self, cmd: LoadCommand) -> str:
        """The FROM-able source for a load: a Parquet reader, or a validated SELECT
        over existing DuckDB tables (transform load, kind=duckdb_query)."""
        if cmd.duckdb_sql:
            from upm_sql_tools.validate import assert_select_only

            assert_select_only(cmd.duckdb_sql, dialect="duckdb")
            return f"({cmd.duckdb_sql})"
        if not cmd.landing_path:
            raise ValueError("load command needs landing_path or duckdb_sql")
        return _pq(cmd.landing_path)

    def load(self, cmd: LoadCommand) -> LoadResult:
        """Load one Parquet file (or SELECT result) into the target table per its load
        mode, then bump the registry. Serialized by the lock; idempotent for
        full/upsert on replay."""
        with self._lock:
            con = self._connection()
            target = quote_ident(cmd.table)
            staging = quote_ident(f"{cmd.table}__staging")
            src = self._source_expr(cmd)
            self._mark_load_started(cmd.table)

            rows_written = int(con.execute(f"SELECT count(*) FROM {src}").fetchone()[0])

            try:
                if cmd.load_mode is LoadMode.FULL:
                    # staging -> atomic swap (DROP+RENAME inside one transaction)
                    con.execute(f"CREATE OR REPLACE TABLE {staging} AS SELECT * FROM {src}")
                    con.execute("BEGIN TRANSACTION")
                    con.execute(f"DROP TABLE IF EXISTS {target}")
                    con.execute(f"ALTER TABLE {staging} RENAME TO {quote_ident(cmd.table)}")
                    con.execute("COMMIT")

                elif cmd.load_mode is LoadMode.APPEND:
                    con.execute(f"CREATE TABLE IF NOT EXISTS {target} AS SELECT * FROM {src} WHERE 1=0")
                    con.execute("BEGIN TRANSACTION")
                    con.execute(f"INSERT INTO {target} SELECT * FROM {src}")
                    con.execute("COMMIT")

                elif cmd.load_mode is LoadMode.UPSERT:
                    if not cmd.key_columns:
                        raise ValueError("upsert requires key_columns")
                    keys = ", ".join(quote_ident(k) for k in cmd.key_columns)
                    con.execute(f"CREATE TABLE IF NOT EXISTS {target} AS SELECT * FROM {src} WHERE 1=0")
                    con.execute("BEGIN TRANSACTION")
                    con.execute(
                        f"DELETE FROM {target} WHERE ({keys}) IN (SELECT {keys} FROM {src})"
                    )
                    con.execute(f"INSERT INTO {target} SELECT * FROM {src}")
                    con.execute("COMMIT")
                else:  # pragma: no cover - exhaustive
                    raise ValueError(f"unknown load mode {cmd.load_mode}")
            except Exception:
                try:
                    con.execute("ROLLBACK")
                except Exception:  # noqa: BLE001
                    pass
                self._mark_load_failed(cmd.table)
                raise

            new_count = int(con.execute(f"SELECT count(*) FROM {target}").fetchone()[0])
            version = self._mark_load_succeeded(cmd, new_count)
            return LoadResult(
                table=cmd.table,
                rows_written=rows_written,
                row_count=new_count,
                table_version=version,
            )

    # ----- registry (freshness, §10) --------------------------------------
    def _registry_row(self, session, table: str) -> TableRegistry:
        row = session.get(TableRegistry, table)
        if row is None:
            row = TableRegistry(table_name=table, table_version=0, row_count=0)
            session.add(row)
            session.flush()
        return row

    def _mark_load_started(self, table: str) -> None:
        with session_scope() as session:
            row = self._registry_row(session, table)
            row.last_load_started_at = _utcnow()
            row.last_load_status = "running"

    def _mark_load_failed(self, table: str) -> None:
        with session_scope() as session:
            row = self._registry_row(session, table)
            row.last_load_status = "failed"

    def _mark_load_succeeded(self, cmd: LoadCommand, new_count: int) -> int:
        schema = {c.name: c.type for c in self.table_columns(cmd.table)}
        with session_scope() as session:
            row = self._registry_row(session, cmd.table)
            row.source_job_id = cmd.job_config_id
            row.schema_json = schema
            row.row_count = new_count
            row.table_version = (row.table_version or 0) + 1
            row.last_load_succeeded_at = _utcnow()
            row.last_load_status = "success"
            if cmd.watermark_value is not None:
                row.last_watermark_value = cmd.watermark_value
            row.is_visible = True
            version = row.table_version
        return version


# ----- process-wide singleton -------------------------------------------------
_GATEWAY: DuckDBGateway | None = None
_GATEWAY_LOCK = threading.Lock()


def get_gateway() -> DuckDBGateway:
    """Return the process-wide Gateway (shared by request handlers + load consumer)."""
    global _GATEWAY
    if _GATEWAY is None:
        with _GATEWAY_LOCK:
            if _GATEWAY is None:
                path = os.environ.get("UPM_DUCKDB_PATH", "./data/duckdb/analytics.duckdb")
                spatial = os.environ.get("UPM_DUCKDB_LOAD_SPATIAL", "0") in ("1", "true", "True")
                _GATEWAY = DuckDBGateway(path, load_spatial=spatial)
    return _GATEWAY


def reset_gateway() -> None:
    global _GATEWAY
    with _GATEWAY_LOCK:
        if _GATEWAY is not None:
            _GATEWAY.close()
        _GATEWAY = None
