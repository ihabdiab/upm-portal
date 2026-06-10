"""LoadCommand — the message a worker hands to the DuckDB Gateway (§9.1).

Workers never open DuckDB. They extract Oracle->Parquet, then enqueue one of these on
the Redis single-consumer queue. The Gateway (sole RW process) consumes them serially.
"""

from __future__ import annotations

from pydantic import BaseModel

from upm_shared.enums import LoadMode


class LoadCommand(BaseModel):
    run_id: str
    job_config_id: int | None = None
    table: str
    # Exactly one of these two is the load input:
    #  - landing_path: a Parquet file extracted by a worker (oracle/connection/csv)
    #  - duckdb_sql:   a SELECT over existing DuckDB tables, executed by the Gateway
    #                  itself (transform load — workers never open DuckDB, §9.1)
    landing_path: str | None = None
    duckdb_sql: str | None = None
    load_mode: LoadMode
    key_columns: list[str] = []
    watermark_value: str | None = None
    rows_read: int = 0


class LoadResult(BaseModel):
    table: str
    rows_written: int
    row_count: int
    table_version: int
