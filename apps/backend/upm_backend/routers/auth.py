"""Auth & identity endpoints (§6)."""

from __future__ import annotations

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from upm_control_plane.models import Project, User
from upm_shared.auth import (
    LoginRequest,
    MeResponse,
    ProjectMembership,
    TokenResponse,
    UserOut,
)

from upm_backend.db import get_session
from upm_backend.deps import UserContext, get_user_context
from upm_backend.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)

router = APIRouter(tags=["auth"])


def _user_out(u: User) -> UserOut:
    return UserOut(id=u.id, email=u.email, full_name=u.full_name, is_active=u.is_active)


@router.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, session: Session = Depends(get_session)) -> TokenResponse:
    user = session.query(User).filter(User.email == body.email).one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid credentials")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "user disabled")
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user=_user_out(user),
    )


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/auth/refresh", response_model=TokenResponse)
def refresh(body: RefreshRequest, session: Session = Depends(get_session)) -> TokenResponse:
    try:
        payload = decode_token(body.refresh_token, expected_type="refresh")
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid refresh token")
    user = session.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user inactive")
    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=MeResponse)
def me(
    ctx: UserContext = Depends(get_user_context),
    session: Session = Depends(get_session),
) -> MeResponse:
    names = {
        p.id: p.name
        for p in session.query(Project).filter(Project.id.in_(ctx.memberships.keys() or [-1])).all()
    }
    projects = [
        ProjectMembership(project_id=pid, project_name=names.get(pid, f"#{pid}"), role=role)
        for pid, role in ctx.memberships.items()
    ]
    return MeResponse(
        user=_user_out(ctx.user),
        capabilities=sorted(ctx.capabilities),
        projects=projects,
    )
