"""Synthetic telecom-KPI source — the no-Oracle path (§15 mentions Parquet fixtures).

Generates deterministic-per-(cell, hour) rows so an upsert replay reproduces identical
values (demonstrating idempotency). Shapes columns to whatever the structured job asks
for, so it works for hybrid_cs_cell, hybrid_ps_cell, or any ad-hoc structured job.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from pathlib import Path

import duckdb
from upm_shared.jobs import JobDefinition

from upm_ingestion.sources.base import ExtractResult

REGIONS = ["North", "South", "East", "West"]
NUM_CELLS = 12
FULL_WINDOW_HOURS = 48

_TRAFFIC_BASE = {"North": 42.0, "South": 31.0, "East": 26.0, "West": 37.0}
_THROUGHPUT_BASE = {"North": 135.0, "South": 90.0, "East": 70.0, "West": 110.0}

_STR_COLUMNS = {"cell_id", "region"}


def _sql_type(col: str) -> str:
    if col == "timestamp":
        return "TIMESTAMP"
    if col in _STR_COLUMNS or col.endswith("_id") or col == "name":
        return "VARCHAR"
    return "DOUBLE"


def _hour_floor(dt: datetime) -> datetime:
    return dt.replace(minute=0, second=0, microsecond=0)


def _metric(col: str, region: str, rnd: random.Random) -> float:
    if col == "traffic_erl":
        return round(max(0.0, rnd.gauss(_TRAFFIC_BASE[region], _TRAFFIC_BASE[region] * 0.2)), 3)
    if col == "drop_rate":
        return round(max(0.0, rnd.gauss(0.8, 0.4)), 4)
    if col == "throughput_mbps":
        base = _THROUGHPUT_BASE[region]
        return round(max(0.0, rnd.gauss(base, base * 0.25)), 2)
    if col == "latency_ms":
        return round(max(1.0, rnd.gauss(35.0, 10.0)), 2)
    return round(rnd.uniform(0.0, 100.0), 3)


def _cell(i: int) -> tuple[str, str]:
    return f"CELL_{i:04d}", REGIONS[i % len(REGIONS)]


class SyntheticSource:
    def _time_points(self, watermark_value: str | None, incremental: bool) -> list[datetime]:
        now = _hour_floor(datetime.now(UTC))
        if incremental and watermark_value:
            try:
                start = _hour_floor(datetime.fromisoformat(watermark_value))
            except ValueError:
                start = now - timedelta(hours=FULL_WINDOW_HOURS)
            start = start + timedelta(hours=1)  # watermark is exclusive
        else:
            start = now - timedelta(hours=FULL_WINDOW_HOURS)
        points: list[datetime] = []
        t = start
        while t <= now:
            points.append(t)
            t += timedelta(hours=1)
        return points

    def _rows(self, columns: list[str], points: list[datetime], row_cap: int):
        rows = []
        latest: datetime | None = None
        for ts in points:
            for i in range(NUM_CELLS):
                cell_id, region = _cell(i)
                rnd = random.Random(f"{cell_id}|{ts.isoformat()}")
                row = []
                for col in columns:
                    if col == "timestamp":
                        row.append(ts)
                    elif col == "cell_id":
                        row.append(cell_id)
                    elif col == "region":
                        row.append(region)
                    else:
                        row.append(_metric(col, region, rnd))
                rows.append(tuple(row))
                latest = ts if latest is None or ts > latest else latest
                if len(rows) >= row_cap:
                    return rows, latest
        return rows, latest

    def extract(
        self,
        job: JobDefinition,
        *,
        watermark_value: str | None,
        landing_path: str,
        row_cap: int,
    ) -> ExtractResult:
        columns = list(job.source.columns)
        if "timestamp" not in columns:
            columns = ["timestamp", *columns]
        incremental = job.watermark is not None
        points = self._time_points(watermark_value, incremental)
        rows, latest = self._rows(columns, points, row_cap)

        Path(landing_path).parent.mkdir(parents=True, exist_ok=True)
        con = duckdb.connect()
        try:
            coldefs = ", ".join(f'"{c}" {_sql_type(c)}' for c in columns)
            con.execute(f"CREATE TABLE staging ({coldefs})")
            if rows:
                placeholders = ", ".join("?" for _ in columns)
                con.executemany(f"INSERT INTO staging VALUES ({placeholders})", rows)
            out = str(landing_path).replace("\\", "/")
            con.execute(f"COPY staging TO '{out}' (FORMAT PARQUET)")
        finally:
            con.close()

        new_wm = latest.isoformat() if (latest and incremental) else watermark_value
        return ExtractResult(
            landing_path=landing_path,
            rows_read=len(rows),
            new_watermark=new_wm,
            columns=columns,
        )

    def preview(self, job: JobDefinition, *, n: int = 20) -> list[dict]:
        columns = list(job.source.columns)
        if "timestamp" not in columns:
            columns = ["timestamp", *columns]
        now = _hour_floor(datetime.now(UTC))
        points = [now - timedelta(hours=h) for h in range(2)]
        rows, _ = self._rows(columns, points, n)
        return [dict(zip(columns, r, strict=False)) for r in rows[:n]]
