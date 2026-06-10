"""Run a job: extract the watermarked delta to Parquet, then load it.

Two entry points share the same extract step:
  * run_job_inline(job_id, gateway)  -> dev/CLI: extract + load in one process.
  * extract_and_enqueue(job_id, redis) -> worker: extract + LPUSH a LoadCommand for the
    backend's Gateway-owning consumer to apply.

Per-run bookkeeping lives in `job_runs`; idempotency comes from the watermark advancing
only on a committed load and from upsert keys deduping a replayed Parquet file (§9.2).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path

from upm_control_plane import session_scope
from upm_control_plane.mapping import row_to_definition
from upm_control_plane.models import JobConfig, JobRun, TableRegistry
from upm_shared.constants import LOAD_QUEUE
from upm_shared.loadcmd import LoadCommand

from upm_ingestion.config import IngestionConfig
from upm_ingestion.sources import get_source

log = logging.getLogger("upm.ingestion")


def _utcnow() -> datetime:
    return datetime.now(UTC)


def resolve_job_id(job: str | int) -> int:
    if isinstance(job, int) or (isinstance(job, str) and job.isdigit()):
        return int(job)
    with session_scope() as session:
        row = session.query(JobConfig).filter(JobConfig.name == str(job)).one_or_none()
        if row is None:
            raise LookupError(f"no job named {job!r}")
        return row.id


def _landing_path(landing_dir: str, target_table: str, run_id: int) -> str:
    return str(Path(landing_dir) / target_table / f"{run_id}.parquet")


def _begin_run(session, job_id: int) -> tuple[JobRun, str | None]:
    reg = session.get(TableRegistry, _target_table(session, job_id))
    watermark_before = reg.last_watermark_value if reg else None
    run = JobRun(
        job_config_id=job_id,
        attempt=1,
        status="running",
        started_at=_utcnow(),
        watermark_before=watermark_before,
    )
    session.add(run)
    session.flush()
    return run, watermark_before


def _target_table(session, job_id: int) -> str:
    job = session.get(JobConfig, job_id)
    if job is None:
        raise LookupError(f"job {job_id} not found")
    return job.target_table


def _extract(job_id: int) -> tuple[dict, str | None, int, str | None]:
    """Create the run row, extract to Parquet. Returns (load_kwargs, run_id, rows_read, wm)."""
    cfg = IngestionConfig.from_env()

    with session_scope() as session:
        job_row = session.get(JobConfig, job_id)
        if job_row is None:
            raise LookupError(f"job {job_id} not found")
        jd = row_to_definition(job_row)
        run, watermark_before = _begin_run(session, job_id)
        run_id = run.id
        target_table = job_row.target_table

    source = get_source(jd, cfg)

    landing_path = _landing_path(cfg.landing_dir, target_table, run_id)
    try:
        result = source.extract(
            jd,
            watermark_value=watermark_before,
            landing_path=landing_path,
            row_cap=jd.guards.row_cap,
        )
    except Exception as e:  # noqa: BLE001
        with session_scope() as session:
            run = session.get(JobRun, run_id)
            run.status = "failed"
            run.finished_at = _utcnow()
            run.error = f"extract failed: {e}"
        log.exception("extract failed for job %s", job_id)
        raise

    with session_scope() as session:
        run = session.get(JobRun, run_id)
        run.rows_read = result.rows_read
        run.landing_path = result.landing_path
        run.watermark_after = result.new_watermark

    load_kwargs = {
        "run_id": str(run_id),
        "job_config_id": job_id,
        "table": target_table,
        "landing_path": result.landing_path,
        "load_mode": jd.load_mode,
        "key_columns": jd.key_columns,
        "watermark_value": result.new_watermark,
        "rows_read": result.rows_read,
    }
    return load_kwargs, str(run_id), result.rows_read, result.new_watermark


def run_job_inline(job_id: int, *, gateway) -> dict:
    """Dev/CLI path: extract, then load through the passed-in Gateway (same process)."""
    load_kwargs, run_id, rows_read, _wm = _extract(job_id)
    cmd = LoadCommand(**load_kwargs)
    try:
        result = gateway.load(cmd)
    except Exception as e:  # noqa: BLE001
        with session_scope() as session:
            run = session.get(JobRun, int(run_id))
            run.status = "failed"
            run.finished_at = _utcnow()
            run.error = f"load failed: {e}"
        raise

    with session_scope() as session:
        run = session.get(JobRun, int(run_id))
        run.status = "success"
        run.finished_at = _utcnow()
        run.rows_written = result.rows_written

    return {
        "run_id": run_id,
        "table": result.table,
        "rows_read": rows_read,
        "rows_written": result.rows_written,
        "row_count": result.row_count,
        "table_version": result.table_version,
    }


def extract_and_enqueue(job_id: int, redis_client) -> dict:
    """Worker path: extract, then hand a LoadCommand to the Gateway via Redis."""
    load_kwargs, run_id, rows_read, wm = _extract(job_id)
    cmd = LoadCommand(**load_kwargs)
    redis_client.lpush(LOAD_QUEUE, cmd.model_dump_json())
    log.info("enqueued load for %s (run %s, %s rows)", cmd.table, run_id, rows_read)
    return {"run_id": run_id, "table": cmd.table, "rows_read": rows_read, "enqueued": True, "watermark": wm}
