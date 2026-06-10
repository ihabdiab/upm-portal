"""Read path: POST /query -> parameterized, read-only DuckDB SELECT, cached by version.

The body is a *structured* query; sql-tools renders it. Every response carries
data_as_of + table_version + a stale flag so the UI can show "data as of ..." (§10).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from upm_control_plane.models import JobConfig, TableRegistry
from upm_shared.query import QueryRequest, QueryResponse
from upm_sql_tools.duckdb_builder import build_count_select, build_read_select
from upm_sql_tools.identifiers import IdentifierError

from upm_backend.cache import query_cache_key
from upm_backend.config import Settings, get_settings
from upm_backend.db import get_session
from upm_backend.deps import UserContext, get_services, get_user_context
from upm_backend.freshness import is_stale, schedule_interval_seconds

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
def run_query(
    body: QueryRequest,
    _: UserContext = Depends(get_user_context),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    services=Depends(get_services),
) -> QueryResponse:
    reg = session.get(TableRegistry, body.table)
    if reg is None or not reg.is_visible:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"unknown table '{body.table}'")

    version = body.table_version_pin or reg.table_version
    schedule = None
    if reg.source_job_id is not None:
        job = session.get(JobConfig, reg.source_job_id)
        schedule = job.schedule if job else None
    stale = is_stale(
        reg.last_load_succeeded_at, schedule_interval_seconds(schedule), settings.stale_k
    )

    # include_sql must not fragment the cache: key on the query itself only.
    cache_payload = body.model_dump(mode="json", exclude={"include_sql"})
    cache_key = query_cache_key(body.table, version, cache_payload)
    cached = services.cache.get(cache_key)
    if cached is not None:
        resp = QueryResponse(**{**cached, "cached": True, "stale": stale})
        if not body.include_sql:
            resp.sql = None
        return resp

    try:
        sql, params = build_read_select(body)
        _, rows = services.gateway.execute_read(sql, params)
        total = None
        if body.page == 1 and not body.aggregations:
            count_sql, count_params = build_count_select(body)
            _, count_rows = services.gateway.execute_read(count_sql, count_params)
            total = int(count_rows[0]["n"]) if count_rows else 0
    except IdentifierError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"invalid identifier: {e}")
    except Exception as e:  # noqa: BLE001 - surface DuckDB binding/column errors as 400
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"query error: {e}")

    resp = QueryResponse(
        rows=jsonable_encoder(rows),
        page=body.page,
        total=total,
        table_version=version,
        data_as_of=reg.last_load_succeeded_at,
        stale=stale,
        cached=False,
        sql=sql,  # cached entries always carry it; stripped below if not requested
    )
    services.cache.set(cache_key, resp.model_dump(mode="json"), settings.query_cache_ttl_s)
    if not body.include_sql:
        resp.sql = None
    return resp
