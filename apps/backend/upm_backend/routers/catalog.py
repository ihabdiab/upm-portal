"""Schema introspection — registry-backed, never hits Oracle (§6)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from upm_control_plane.models import JobConfig, TableRegistry
from upm_shared.catalog import TableDetail, TableSummary

from upm_backend.config import Settings, get_settings
from upm_backend.db import get_session
from upm_backend.deps import UserContext, get_services, get_user_context
from upm_backend.freshness import compute_freshness, is_stale, schedule_interval_seconds

router = APIRouter(tags=["catalog"])


def _schedule_for(session: Session, reg: TableRegistry) -> dict | None:
    if reg.source_job_id is None:
        return None
    job = session.get(JobConfig, reg.source_job_id)
    return job.schedule if job else None


@router.get("/catalog/tables", response_model=list[TableSummary])
def list_tables(
    _: UserContext = Depends(get_user_context),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> list[TableSummary]:
    rows = (
        session.query(TableRegistry)
        .filter(TableRegistry.is_visible.is_(True))
        .order_by(TableRegistry.table_name)
        .all()
    )
    out: list[TableSummary] = []
    for reg in rows:
        interval = schedule_interval_seconds(_schedule_for(session, reg))
        out.append(
            TableSummary(
                table_name=reg.table_name,
                row_count=reg.row_count,
                last_load_succeeded_at=reg.last_load_succeeded_at,
                last_load_status=reg.last_load_status,
                is_visible=reg.is_visible,
                stale=is_stale(reg.last_load_succeeded_at, interval, settings.stale_k),
            )
        )
    return out


@router.get("/catalog/tables/{name}", response_model=TableDetail)
def table_detail(
    name: str,
    sample: bool = Query(default=False),
    _: UserContext = Depends(get_user_context),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    services=Depends(get_services),
) -> TableDetail:
    reg = session.get(TableRegistry, name)
    if reg is None or not reg.is_visible:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "table not found")

    columns = services.gateway.table_columns(name)
    freshness = compute_freshness(reg, _schedule_for(session, reg), settings.stale_k)
    sample_rows = services.gateway.sample_rows(name, 20) if sample else None
    return TableDetail(
        table_name=name, columns=columns, freshness=freshness, sample_rows=sample_rows
    )
