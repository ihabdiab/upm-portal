"""Dashboards CRUD (§6, §7). read: project:view · write: dashboard:author."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from upm_control_plane.models import Dashboard, Project
from upm_shared.dashboards import DashboardDefinition

from upm_backend.audit import record_audit
from upm_backend.db import get_session
from upm_backend.deps import (
    UserContext,
    ensure_project_view,
    get_user_context,
    require_cap,
)

router = APIRouter(tags=["dashboards"])


class DashboardIn(BaseModel):
    name: str
    definition: DashboardDefinition = Field(default_factory=DashboardDefinition)


class DashboardSummary(BaseModel):
    id: int
    project_id: int
    name: str
    version: int
    updated_at: datetime | None = None


class DashboardOut(DashboardSummary):
    definition: DashboardDefinition


def _summary(d: Dashboard) -> DashboardSummary:
    return DashboardSummary(
        id=d.id, project_id=d.project_id, name=d.name, version=d.version, updated_at=d.updated_at
    )


def _out(d: Dashboard) -> DashboardOut:
    return DashboardOut(
        id=d.id, project_id=d.project_id, name=d.name, version=d.version,
        updated_at=d.updated_at, definition=DashboardDefinition.model_validate(d.definition),
    )


@router.get("/projects/{project_id}/dashboards", response_model=list[DashboardSummary])
def list_dashboards(
    project_id: int,
    ctx: UserContext = Depends(get_user_context),
    session: Session = Depends(get_session),
) -> list[DashboardSummary]:
    ensure_project_view(ctx, project_id)
    rows = (
        session.query(Dashboard)
        .filter(Dashboard.project_id == project_id)
        .order_by(Dashboard.name)
        .all()
    )
    return [_summary(d) for d in rows]


@router.post(
    "/projects/{project_id}/dashboards",
    response_model=DashboardOut,
    status_code=status.HTTP_201_CREATED,
)
def create_dashboard(
    project_id: int,
    body: DashboardIn,
    ctx: UserContext = Depends(require_cap("dashboard:author")),
    session: Session = Depends(get_session),
) -> DashboardOut:
    ensure_project_view(ctx, project_id)
    if session.get(Project, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
    d = Dashboard(
        project_id=project_id,
        name=body.name,
        definition=body.definition.model_dump(by_alias=True, mode="json"),
        version=body.definition.version,
        created_by=ctx.user.id,
    )
    session.add(d)
    session.flush()
    record_audit(
        session, actor_id=ctx.user.id, action="create", entity_type="dashboard", entity_id=d.id
    )
    return _out(d)


@router.get("/dashboards/{dashboard_id}", response_model=DashboardOut)
def get_dashboard(
    dashboard_id: int,
    ctx: UserContext = Depends(get_user_context),
    session: Session = Depends(get_session),
) -> DashboardOut:
    d = session.get(Dashboard, dashboard_id)
    if d is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "dashboard not found")
    ensure_project_view(ctx, d.project_id)
    return _out(d)


@router.put("/dashboards/{dashboard_id}", response_model=DashboardOut)
def update_dashboard(
    dashboard_id: int,
    body: DashboardIn,
    ctx: UserContext = Depends(require_cap("dashboard:author")),
    session: Session = Depends(get_session),
) -> DashboardOut:
    d = session.get(Dashboard, dashboard_id)
    if d is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "dashboard not found")
    ensure_project_view(ctx, d.project_id)
    d.name = body.name
    d.definition = body.definition.model_dump(by_alias=True, mode="json")
    d.version = body.definition.version
    record_audit(
        session, actor_id=ctx.user.id, action="update", entity_type="dashboard", entity_id=d.id
    )
    return _out(d)


@router.delete("/dashboards/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_dashboard(
    dashboard_id: int,
    ctx: UserContext = Depends(require_cap("dashboard:author")),
    session: Session = Depends(get_session),
) -> None:
    d = session.get(Dashboard, dashboard_id)
    if d is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "dashboard not found")
    ensure_project_view(ctx, d.project_id)
    record_audit(
        session, actor_id=ctx.user.id, action="delete", entity_type="dashboard", entity_id=d.id
    )
    session.delete(d)
