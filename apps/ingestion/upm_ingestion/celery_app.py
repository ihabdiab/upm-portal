"""Celery app for ingestion workers (ADR-004). Broker + result backend = Redis.

Run: `celery -A upm_ingestion.celery_app:app worker -Q extraction --concurrency 4`
(Oracle I/O is parallel-safe; workers never touch DuckDB, so concurrency > 1 is fine.)
"""

from __future__ import annotations

import os

from celery import Celery
from upm_shared.constants import EXTRACTION_QUEUE


def make_celery() -> Celery:
    redis_url = os.environ.get("UPM_REDIS_URL", "redis://localhost:6379/0")
    app = Celery("upm-ingestion", broker=redis_url, backend=redis_url)
    app.conf.update(
        task_default_queue=EXTRACTION_QUEUE,
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        task_track_started=True,
        timezone="UTC",
    )
    return app


app = make_celery()

# Import for side-effect: registers tasks on the app.
from upm_ingestion import tasks  # noqa: E402,F401
