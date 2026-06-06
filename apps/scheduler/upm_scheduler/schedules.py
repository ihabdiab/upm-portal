"""Convert a job_configs schedule dict into a Celery schedule object."""

from __future__ import annotations

import re
from datetime import timedelta

from celery.schedules import crontab

_EVERY_RE = re.compile(r"^\s*(\d+)\s*([smhd])\s*$")
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


def to_celery_schedule(schedule: dict):
    every = (schedule or {}).get("every")
    if isinstance(every, str):
        m = _EVERY_RE.match(every)
        if m:
            return timedelta(seconds=int(m.group(1)) * _UNIT_SECONDS[m.group(2)])
    cron = (schedule or {}).get("cron")
    if isinstance(cron, str) and cron.strip():
        parts = cron.split()
        if len(parts) == 5:
            minute, hour, dom, month, dow = parts
            return crontab(
                minute=minute, hour=hour, day_of_month=dom,
                month_of_year=month, day_of_week=dow,
            )
    return timedelta(hours=1)
