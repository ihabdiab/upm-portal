"""Admin surface (§6). cap: user:manage."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from upm_control_plane.models import Project, Role, User, UserProjectRole
from upm_shared.auth import UserOut

from upm_backend.audit import record_audit
from upm_backend.db import get_session
from upm_backend.deps import UserContext, require_cap
from upm_backend.security import hash_password

router = APIRouter(tags=["admin"], prefix="/admin")


class CreateUser(BaseModel):
    email: EmailStr
    password: str
    full_name: str | None = None


class PatchUser(BaseModel):
    full_name: str | None = None
    is_active: bool | None = None
    password: str | None = None


class AssignRole(BaseModel):
    project_id: int
    role: str


class CreateProject(BaseModel):
    name: str
    description: str | None = None


def _user_out(u: User) -> UserOut:
    return UserOut(id=u.id, email=u.email, full_name=u.full_name, is_active=u.is_active)


@router.get("/users", response_model=list[UserOut])
def list_users(
    _: UserContext = Depends(require_cap("user:manage")),
    session: Session = Depends(get_session),
) -> list[UserOut]:
    return [_user_out(u) for u in session.query(User).order_by(User.email).all()]


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: CreateUser,
    ctx: UserContext = Depends(require_cap("user:manage")),
    session: Session = Depends(get_session),
) -> UserOut:
    if session.query(User).filter(User.email == body.email).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")
    u = User(
        email=str(body.email),
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        is_active=True,
    )
    session.add(u)
    session.flush()
    record_audit(session, actor_id=ctx.user.id, action="create", entity_type="user", entity_id=u.id)
    return _user_out(u)


@router.patch("/users/{user_id}", response_model=UserOut)
def patch_user(
    user_id: int,
    body: PatchUser,
    ctx: UserContext = Depends(require_cap("user:manage")),
    session: Session = Depends(get_session),
) -> UserOut:
    u = session.get(User, user_id)
    if u is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")
    if body.full_name is not None:
        u.full_name = body.full_name
    if body.is_active is not None:
        u.is_active = body.is_active
    if body.password:
        u.hashed_password = hash_password(body.password)
    record_audit(session, actor_id=ctx.user.id, action="update", entity_type="user", entity_id=u.id)
    return _user_out(u)


@router.post("/users/{user_id}/project-roles", status_code=status.HTTP_204_NO_CONTENT)
def assign_project_role(
    user_id: int,
    body: AssignRole,
    ctx: UserContext = Depends(require_cap("user:manage")),
    session: Session = Depends(get_session),
) -> None:
    if session.get(User, user_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")
    if session.get(Project, body.project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "project not found")
    role = session.query(Role).filter(Role.name == body.role).one_or_none()
    if role is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unknown role '{body.role}'")
    existing = session.get(UserProjectRole, (user_id, body.project_id, role.id))
    if existing is None:
        session.add(
            UserProjectRole(user_id=user_id, project_id=body.project_id, role_id=role.id)
        )
    record_audit(
        session, actor_id=ctx.user.id, action="assign_role", entity_type="user", entity_id=user_id,
        after={"project_id": body.project_id, "role": body.role},
    )


@router.post("/projects", status_code=status.HTTP_201_CREATED)
def create_project(
    body: CreateProject,
    ctx: UserContext = Depends(require_cap("user:manage")),
    session: Session = Depends(get_session),
) -> dict:
    p = Project(name=body.name, description=body.description, created_by=ctx.user.id)
    session.add(p)
    session.flush()
    record_audit(session, actor_id=ctx.user.id, action="create", entity_type="project", entity_id=p.id)
    return {"id": p.id, "name": p.name, "description": p.description}
