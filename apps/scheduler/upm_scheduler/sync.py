"""Sync job_configs -> RedBeat entries.

Reads enabled jobs from the control plane and upserts one RedBeat schedule entry per job
(task=run_extraction_job, args=[job_id]). Disabled/removed jobs have their entries pruned.
Run on demand (`upm-scheduler sync`) or periodically; RedBeat picks up changes live.
"""

from __future__ import annotations

import logging

from upm_control_plane import session_scope
from upm_control_plane.models import JobConfig
from upm_shared.constants import EXTRACTION_QUEUE, TASK_RUN_EXTRACTION

from upm_scheduler.celery_app import app
from upm_scheduler.schedules import to_celery_schedule

log = logging.getLogger("upm.scheduler")

_PREFIX = "upm-job-"


def _entry_name(job_id: int) -> str:
    return f"{_PREFIX}{job_id}"


def sync_schedules() -> dict:
    from redbeat import RedBeatSchedulerEntry
    from redbeat.schedulers import RedBeatConfig

    config = RedBeatConfig(app)

    created, updated, removed = 0, 0, 0
    wanted: set[str] = set()

    with session_scope() as session:
        jobs = session.query(JobConfig).all()
        for job in jobs:
            name = _entry_name(job.id)
            if not job.is_enabled:
                continue
            wanted.add(name)
            entry = RedBeatSchedulerEntry(
                name=name,
                task=TASK_RUN_EXTRACTION,
                schedule=to_celery_schedule(job.schedule),
                args=[job.id],
                app=app,
                options={"queue": EXTRACTION_QUEUE},
            )
            entry.save()
            updated += 1

    # Prune entries for jobs that no longer exist or were disabled.
    try:
        import redis as redislib

        r = redislib.from_url(app.conf.redbeat_redis_url)
        for key in r.scan_iter(match=f"{config.key_prefix}{_PREFIX}*"):
            key_s = key.decode() if isinstance(key, bytes) else key
            short = key_s.split(config.key_prefix, 1)[-1]
            if short not in wanted:
                try:
                    RedBeatSchedulerEntry.from_key(key_s, app=app).delete()
                    removed += 1
                except Exception:  # noqa: BLE001
                    pass
    except Exception:  # noqa: BLE001
        log.warning("could not prune stale schedule entries", exc_info=True)

    log.info("schedule sync: %s upserted, %s removed", updated, removed)
    return {"upserted": updated, "removed": removed, "created": created}
