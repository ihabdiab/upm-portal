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
    landing_path: str
    load_mode: LoadMode
    key_columns: list[str] = []
    watermark_value: str | None = None
    rows_read: int = 0


class LoadResult(BaseModel):
    table: str
    rows_written: int
    row_count: int
    table_version: int
