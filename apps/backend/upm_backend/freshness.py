"""Freshness as a first-class concern (§10). Staleness is shown, never hidden."""

from __future__ import annotations

import re
from datetime import UTC, datetime

from upm_shared.catalog import Freshness

_EVERY_RE = re.compile(r"^\s*(\d+)\s*([smhd])\s*$")
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}
DEFAULT_INTERVAL_S = 3600


def schedule_interval_seconds(schedule: dict | None) -> int:
    """Best-effort interval in seconds from a job schedule dict ('every'/'cron')."""
    if not schedule:
        return DEFAULT_INTERVAL_S
    every = schedule.get("every")
    if isinstance(every, str):
        m = _EVERY_RE.match(every)
        if m:
            return int(m.group(1)) * _UNIT_SECONDS[m.group(2)]
    # cron or unknown -> fall back to a conservative default
    return DEFAULT_INTERVAL_S


def is_stale(last_success: datetime | None, interval_s: int, k: float) -> bool:
    if last_success is None:
        return True
    if last_success.tzinfo is None:
        last_success = last_success.replace(tzinfo=UTC)
    age = (datetime.now(UTC) - last_success).total_seconds()
    return age > interval_s * k


def compute_freshness(reg, schedule: dict | None, k: float) -> Freshness:
    interval = schedule_interval_seconds(schedule)
    stale = reg is None or is_stale(reg.last_load_succeeded_at, interval, k)
    if reg is None:
        return Freshness(stale=True)
    return Freshness(
        last_load_started_at=reg.last_load_started_at,
        last_load_succeeded_at=reg.last_load_succeeded_at,
        last_load_status=reg.last_load_status,
        last_watermark_value=reg.last_watermark_value,
        table_version=reg.table_version,
        row_count=reg.row_count,
        stale=stale,
    )
