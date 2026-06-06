"""Celery tasks. Extraction with retries/backoff; exhausted retries land in the DLQ and
mark the run failed (§9.3)."""

from __future__ import annotations

import os

import redis as redislib
from upm_shared.constants import TASK_RUN_EXTRACTION

from upm_ingestion.celery_app import app
from upm_ingestion.orchestrator import extract_and_enqueue


@app.task(
    name=TASK_RUN_EXTRACTION,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=5,
    acks_late=True,
)
def run_extraction_job(job_id: int) -> dict:
    redis_url = os.environ.get("UPM_REDIS_URL", "redis://localhost:6379/0")
    client = redislib.from_url(redis_url)
    return extract_and_enqueue(job_id, client)
