"""Extraction Job Builder API (§6, Phase 2). cap: job:author."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from upm_control_plane.models import JobConfig, JobRun, TableRegistry
from upm_shared.enums import SourceKind, SourceMode
from upm_shared.jobs import JobDefinition
from upm_sql_tools.oracle_builder import build_extract_select

from upm_backend.audit import record_audit
from upm_backend.config import Settings, get_settings
from upm_backend.db import get_session
from upm_backend.deps import UserContext, get_services, require_cap
from upm_backend.jobmap import definition_to_kwargs, row_to_definition

router = APIRouter(tags=["jobs"])


class JobOut(BaseModel):
    id: int
    is_enabled: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    definition: JobDefinition


class RunOut(BaseModel):
    id: int
    attempt: int
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    rows_read: int
    rows_written: int
    watermark_after: str | None = None
    error: str | None = None


def _job_out(row: JobConfig) -> JobOut:
    return JobOut(
        id=row.id,
        is_enabled=row.is_enabled,
        created_at=row.created_at,
        updated_at=row.updated_at,
        definition=row_to_definition(row),
    )


@router.get("/jobs", response_model=list[JobOut])
def list_jobs(
    _: UserContext = Depends(require_cap("job:author")),
    session: Session = Depends(get_session),
) -> list[JobOut]:
    return [_job_out(r) for r in session.query(JobConfig).order_by(JobConfig.name).all()]


@router.post("/jobs", response_model=JobOut, status_code=status.HTTP_201_CREATED)
def create_job(
    body: JobDefinition,
    ctx: UserContext = Depends(require_cap("job:author")),
    session: Session = Depends(get_session),
) -> JobOut:
    if session.query(JobConfig).filter(JobConfig.name == body.name).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "job name already exists")
    if session.query(JobConfig).filter(JobConfig.target_table == body.target_table).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "target_table already used by another job")

    row = JobConfig(**definition_to_kwargs(body, created_by=ctx.user.id), created_by=ctx.user.id)
    session.add(row)
    session.flush()

    # Pre-register the target so it appears in the catalog (invisible until first load).
    if session.get(TableRegistry, body.target_table) is None:
        session.add(
            TableRegistry(table_name=body.target_table, source_job_id=row.id, is_visible=False)
        )
    record_audit(
        session, actor_id=ctx.user.id, action="create", entity_type="job_config",
        entity_id=row.id, after=definition_to_kwargs(body),
    )
    return _job_out(row)


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(
    job_id: int,
    _: UserContext = Depends(require_cap("job:author")),
    session: Session = Depends(get_session),
) -> JobOut:
    row = session.get(JobConfig, job_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found")
    return _job_out(row)


@router.put("/jobs/{job_id}", response_model=JobOut)
def update_job(
    job_id: int,
    body: JobDefinition,
    ctx: UserContext = Depends(require_cap("job:author")),
    session: Session = Depends(get_session),
) -> JobOut:
    row = session.get(JobConfig, job_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found")
    before = definition_to_kwargs(row_to_definition(row))
    for k, v in definition_to_kwargs(body, created_by=row.created_by).items():
        setattr(row, k, v)
    record_audit(
        session, actor_id=ctx.user.id, action="update", entity_type="job_config",
        entity_id=row.id, before=before, after=definition_to_kwargs(body),
    )
    return _job_out(row)


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(
    job_id: int,
    ctx: UserContext = Depends(require_cap("job:author")),
    session: Session = Depends(get_session),
) -> None:
    row = session.get(JobConfig, job_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found")
    record_audit(
        session, actor_id=ctx.user.id, action="delete", entity_type="job_config", entity_id=row.id
    )
    session.delete(row)


@router.post("/jobs/{job_id}/run")
def run_job(
    job_id: int,
    ctx: UserContext = Depends(require_cap("job:author")),
    session: Session = Depends(get_session),
    services=Depends(get_services),
) -> dict:
    row = session.get(JobConfig, job_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "job not found")
    record_audit(
        session, actor_id=ctx.user.id, action="run", entity_type="job_config", entity_id=row.id
    )
    session.commit()
    return services.job_runner.run(job_id)


@router.get("/jobs/{job_id}/runs", response_model=list[RunOut])
def job_runs(
    job_id: int,
    _: UserContext = Depends(require_cap("job:author")),
    session: Session = Depends(get_session),
) -> list[RunOut]:
    runs = (
        session.query(JobRun)
        .filter(JobRun.job_config_id == job_id)
        .order_by(JobRun.id.desc())
        .limit(50)
        .all()
    )
    return [
        RunOut(
            id=r.id, attempt=r.attempt, status=r.status, started_at=r.started_at,
            finished_at=r.finished_at, rows_read=r.rows_read, rows_written=r.rows_written,
            watermark_after=r.watermark_after, error=r.error,
        )
        for r in runs
    ]


@router.post("/jobs/validate")
def validate_job(
    body: JobDefinition,
    _: UserContext = Depends(require_cap("job:author")),
    settings: Settings = Depends(get_settings),
) -> dict:
    """Dry-run validation, per source kind. RDBMS sources render + validate the extraction
    SQL (and would EXPLAIN PLAN against a live Oracle); CSV/connection confirm the spec."""
    warnings: list[str] = []
    columns = list(body.source.columns)

    if body.source.kind is SourceKind.ORACLE:
        try:
            sql, _binds = build_extract_select(
                body.source,
                watermark_column=body.watermark.column if body.watermark else None,
                watermark_value="<watermark>",
                limit=body.guards.row_cap,
                allowed_schemas={s.lower() for s in settings.allowed_schemas_set},
            )
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"validation failed: {e}")
        if body.source.mode is SourceMode.RAW:
            warnings.append("raw SQL mode: executes behind read-only Oracle account + caps")
        return {"ok": True, "rendered_sql": sql, "columns": columns, "warnings": warnings}

    if body.source.kind is SourceKind.CSV:
        if not body.source.upload_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "csv source requires an upload_id")
        return {"ok": True, "rendered_sql": None, "columns": columns,
                "warnings": ["csv load is full-refresh by default"]}

    if body.source.kind is SourceKind.CONNECTION:
        return {"ok": True, "rendered_sql": None, "columns": columns,
                "warnings": ["extracts via the saved connection using SQLAlchemy"]}

    if body.source.kind is SourceKind.DUCKDB_QUERY:
        from upm_sql_tools.validate import SqlValidationError, assert_select_only

        try:
            assert_select_only(body.source.duckdb_sql or "", dialect="duckdb")
        except SqlValidationError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"validation failed: {e}")
        return {"ok": True, "rendered_sql": body.source.duckdb_sql, "columns": [],
                "warnings": ["transform load: the Gateway executes this SELECT itself"]}

    raise HTTPException(status.HTTP_400_BAD_REQUEST, f"unsupported source kind {body.source.kind}")


@router.post("/jobs/preview")
def preview_job(
    body: JobDefinition,
    _: UserContext = Depends(require_cap("job:author")),
    services=Depends(get_services),
) -> dict:
    """Bounded sample from the (unsaved) source, for the Builder's preview step."""
    from fastapi.encoders import jsonable_encoder

    if body.source.kind is SourceKind.DUCKDB_QUERY:
        from upm_sql_tools.validate import SqlValidationError, assert_select_only

        try:
            assert_select_only(body.source.duckdb_sql or "", dialect="duckdb")
            _cols, rows = services.gateway.execute_read(
                f"SELECT * FROM ({body.source.duckdb_sql}) LIMIT 20", []
            )
        except SqlValidationError as e:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"preview failed: {e}")
        except Exception as e:  # noqa: BLE001
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"preview failed: {e}")
        return {"rows": jsonable_encoder(rows), "count": len(rows)}

    from upm_ingestion.sources import get_source

    try:
        source = get_source(body)
        rows = source.preview(body, n=20)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"preview failed: {e}")
    return {"rows": jsonable_encoder(rows), "count": len(rows)}
