"""DuckDB direct-query support (§1.1 Option C).

Builders can run a SELECT over already-loaded DuckDB tables to preview/derive datasets.
Validation is server-side (sqlglot, single-statement SELECT only); execution goes through
the Gateway's read-only path with a hard row cap. Creating a *job* from such a query is a
transform load the Gateway executes itself (see orchestrator + LoadCommand.duckdb_sql).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field
from upm_sql_tools.validate import SqlValidationError, assert_select_only

from upm_backend.deps import UserContext, get_services, require_cap

router = APIRouter(tags=["duckdb"], prefix="/duckdb")

PREVIEW_CAP = 200


class SqlBody(BaseModel):
    sql: str = Field(min_length=1, max_length=20_000)


@router.post("/validate")
def validate_sql(
    body: SqlBody,
    _: UserContext = Depends(require_cap("job:author")),
) -> dict:
    try:
        assert_select_only(body.sql, dialect="duckdb")
    except SqlValidationError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return {"ok": True}


@router.post("/preview")
def preview_sql(
    body: SqlBody,
    _: UserContext = Depends(require_cap("job:author")),
    services=Depends(get_services),
) -> dict:
    try:
        assert_select_only(body.sql, dialect="duckdb")
    except SqlValidationError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    try:
        columns, rows = services.gateway.execute_read(
            f"SELECT * FROM ({body.sql}) LIMIT {PREVIEW_CAP}", []
        )
    except Exception as e:  # noqa: BLE001 - surface DuckDB errors (bad column etc.) as 400
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"query failed: {e}")
    return {"columns": columns, "rows": jsonable_encoder(rows), "capped_at": PREVIEW_CAP}
