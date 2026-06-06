"""How `POST /jobs/{id}/run` actually runs a job.

- dev (no Redis): InlineJobRunner extracts + loads in-process through the Gateway. The
  backend is the sole DuckDB owner, so this is safe and needs no broker.
- prod (Redis): CeleryJobRunner dispatches the extraction task to the worker pool; the
  worker writes Parquet and enqueues a LoadCommand that the backend's load consumer
  applies. The backend never blocks on extraction.
"""

from __future__ import annotations

from typing import Protocol

from upm_shared.constants import EXTRACTION_QUEUE, TASK_RUN_EXTRACTION


class JobRunner(Protocol):
    def run(self, job_config_id: int) -> dict: ...


class InlineJobRunner:
    """Single-process extract+load (dev/demo)."""

    def __init__(self, gateway) -> None:
        self._gateway = gateway

    def run(self, job_config_id: int) -> dict:
        from upm_ingestion.orchestrator import run_job_inline

        result = run_job_inline(job_config_id, gateway=self._gateway)
        return {"mode": "inline", **result}


class CeleryJobRunner:
    """Dispatch extraction to the Celery worker pool (prod)."""

    def __init__(self, redis_url: str) -> None:
        from celery import Celery

        self._app = Celery("upm-backend", broker=redis_url, backend=redis_url)

    def run(self, job_config_id: int) -> dict:
        async_result = self._app.send_task(
            TASK_RUN_EXTRACTION, args=[job_config_id], queue=EXTRACTION_QUEUE
        )
        return {"mode": "celery", "task_id": async_result.id}
