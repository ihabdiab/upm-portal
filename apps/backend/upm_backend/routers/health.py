"""Liveness/readiness. `/health` per service for the proxy (§12)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from upm_backend.config import Settings, get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health(settings: Settings = Depends(get_settings)) -> dict:
    return {
        "status": "ok",
        "service": "backend",
        "mode": "dev" if settings.dev_mode else "prod",
        "source_type": settings.source_type,
    }
