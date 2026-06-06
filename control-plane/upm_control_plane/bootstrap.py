"""DB bootstrap helpers.

`init_db()` creates all tables (used by the SQLite local demo and tests).
For Postgres, prefer Alembic (`alembic upgrade head`). `seed_rbac()` is idempotent and
plants the capability/role reference data both paths rely on.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from upm_control_plane.base import Base, get_engine
from upm_control_plane.models import Capability, Role, RoleCapability

# Capability -> set of roles that hold it (ADR-008, §11.1).
ROLE_CAPS: dict[str, set[str]] = {
    "Admin": {"user:manage", "job:author", "dashboard:author", "project:view"},
    "Builder": {"job:author", "dashboard:author", "project:view"},
    "Viewer": {"project:view"},
}

ALL_CAPABILITIES = sorted({c for caps in ROLE_CAPS.values() for c in caps})


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())


def seed_rbac(session: Session) -> None:
    """Insert capabilities, roles, and their mappings if absent. Idempotent."""
    cap_by_key: dict[str, Capability] = {}
    for key in ALL_CAPABILITIES:
        cap = session.query(Capability).filter_by(key=key).one_or_none()
        if cap is None:
            cap = Capability(key=key)
            session.add(cap)
            session.flush()
        cap_by_key[key] = cap

    for role_name, caps in ROLE_CAPS.items():
        role = session.query(Role).filter_by(name=role_name).one_or_none()
        if role is None:
            role = Role(name=role_name)
            session.add(role)
            session.flush()
        existing = {rc.capability_id for rc in role.capabilities}
        for key in caps:
            cap = cap_by_key[key]
            if cap.id not in existing:
                session.add(RoleCapability(role_id=role.id, capability_id=cap.id))
    session.flush()
