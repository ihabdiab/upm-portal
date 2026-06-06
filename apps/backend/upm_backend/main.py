"""FastAPI application assembly.

Startup: push Settings into the shared env, (dev) create tables + seed RBAC, build the
service container (Gateway, cache, job runner), and start the Redis load consumer in prod.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from upm_backend.config import get_settings
from upm_backend.routers import admin, ai, auth, catalog, dashboards, health, jobs, projects, query
from upm_backend.runtime import apply_runtime_env
from upm_backend.services import build_services

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s"
)
log = logging.getLogger("upm.backend")


def _ensure_dev_schema() -> None:
    """In dev (SQLite), create tables + seed RBAC so `uvicorn` just works."""
    from upm_control_plane import session_scope
    from upm_control_plane.bootstrap import init_db, seed_rbac

    init_db()
    with session_scope() as session:
        seed_rbac(session)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = apply_runtime_env(get_settings())
    if settings.database_url.startswith("sqlite"):
        _ensure_dev_schema()

    services = build_services(settings)
    app.state.services = services
    if services.consumer is not None:
        services.consumer.start()
    log.info("backend ready (mode=%s, source=%s)", "dev" if settings.dev_mode else "prod",
             settings.source_type)
    try:
        yield
    finally:
        if services.consumer is not None:
            services.consumer.stop()
        services.gateway.close()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="UPM Platform API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for r in (health, auth, projects, admin, catalog, query, jobs, dashboards, ai):
        app.include_router(r.router, prefix="/api")
    return app


app = create_app()
