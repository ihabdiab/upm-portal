"""Beat app. RedBeat keeps the schedule in Redis so it can be edited at runtime from
job_configs without a redeploy.

Run: `celery -A upm_scheduler.celery_app:app beat --scheduler redbeat.RedBeatScheduler`
"""

from __future__ import annotations

import os

from celery import Celery


def make_celery() -> Celery:
    redis_url = os.environ.get("UPM_REDIS_URL", "redis://localhost:6379/0")
    app = Celery("upm-scheduler", broker=redis_url, backend=redis_url)
    app.conf.update(
        beat_scheduler="redbeat.RedBeatScheduler",
        redbeat_redis_url=redis_url,
        redbeat_lock_timeout=90,
        timezone="UTC",
    )
    return app


app = make_celery()
