"""Project listing scoped to the caller's memberships (Admin sees all)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from upm_control_plane.models import Project

from upm_backend.db import get_session
from upm_backend.deps import UserContext, get_user_context

router = APIRouter(tags=["projects"])


class ProjectOut(BaseModel):
    id: int
    name: str
    description: str | None = None
    role: str


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(
    ctx: UserContext = Depends(get_user_context),
    session: Session = Depends(get_session),
) -> list[ProjectOut]:
    if not ctx.memberships:
        return []
    rows = session.query(Project).filter(Project.id.in_(ctx.memberships.keys())).all()
    return [
        ProjectOut(id=p.id, name=p.name, description=p.description, role=ctx.memberships[p.id])
        for p in rows
    ]
