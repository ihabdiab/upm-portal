"""Auth + RBAC dependencies (§11). Capabilities are checked server-side on every
request; project access is scoped per-project. Admin is global.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session
from upm_control_plane.models import (
    Capability,
    Project,
    Role,
    RoleCapability,
    User,
    UserProjectRole,
)

from upm_backend.db import get_session
from upm_backend.security import decode_token

bearer = HTTPBearer(auto_error=True)


@dataclass
class UserContext:
    user: User
    capabilities: set[str]
    # project_id -> role name the user holds there
    memberships: dict[int, str] = field(default_factory=dict)
    is_admin: bool = False

    def project_ids(self) -> set[int]:
        return set(self.memberships.keys())


def _load_context(session: Session, user: User) -> UserContext:
    rows = (
        session.query(UserProjectRole, Role)
        .join(Role, Role.id == UserProjectRole.role_id)
        .filter(UserProjectRole.user_id == user.id)
        .all()
    )
    memberships: dict[int, str] = {}
    role_ids: set[int] = set()
    is_admin = False
    for upr, role in rows:
        memberships[upr.project_id] = role.name
        role_ids.add(role.id)
        if role.name == "Admin":
            is_admin = True

    caps: set[str] = set()
    if role_ids:
        cap_rows = (
            session.query(Capability.key)
            .join(RoleCapability, RoleCapability.capability_id == Capability.id)
            .filter(RoleCapability.role_id.in_(role_ids))
            .all()
        )
        caps = {r[0] for r in cap_rows}

    if is_admin:
        # Global admin sees every project and holds every capability.
        all_caps = {c[0] for c in session.query(Capability.key).all()}
        caps |= all_caps
        for (pid,) in session.execute(select(Project.id)).all():
            memberships.setdefault(pid, "Admin")

    return UserContext(user=user, capabilities=caps, memberships=memberships, is_admin=is_admin)


def get_user_context(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    session: Session = Depends(get_session),
) -> UserContext:
    try:
        payload = decode_token(creds.credentials, expected_type="access")
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token expired")
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token")

    user = session.get(User, int(payload["sub"]))
    if user is None or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "user inactive or missing")
    return _load_context(session, user)


def require_cap(cap: str):
    """Dependency factory: 403 unless the caller holds `cap`."""

    def _dep(ctx: UserContext = Depends(get_user_context)) -> UserContext:
        if cap not in ctx.capabilities:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"missing capability: {cap}")
        return ctx

    return _dep


def ensure_project_view(ctx: UserContext, project_id: int) -> None:
    if ctx.is_admin:
        return
    if project_id not in ctx.memberships:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "no access to this project")


def get_services(request: Request):
    """Return the process-wide service container built at startup."""
    return request.app.state.services
