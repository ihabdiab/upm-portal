"""Audit trail. Every write endpoint and every job run appends here (§6, §11.3)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session
from upm_control_plane.models import AuditLog


def record_audit(
    session: Session,
    *,
    actor_id: int | None,
    action: str,
    entity_type: str,
    entity_id: str | int | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditLog(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            before=before,
            after=after,
        )
    )
