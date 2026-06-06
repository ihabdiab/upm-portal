# Recovery runbook — rebuild the analytics plane without Oracle

The DuckDB analytics store is recoverable from local artifacts ([ADR-006](adr/006-durability-parquet-replay.md)).
Oracle is **not** required for recovery.

## Artifacts
- **Parquet replay log** — `data/landing/{table}/{run_id}.parquet` (retained N days, default 30).
- **Snapshots** — `data/exports/{date}/` from scheduled `EXPORT DATABASE`.
- **Control plane** — Postgres (`table_registry`, `job_runs` tell you what was loaded and the
  last good watermark per table).

## Scenario A — corrupt/lost DuckDB file, snapshot available
1. Stop the backend (it owns the file).
2. Restore the latest export:
   ```sql
   -- in a fresh DuckDB file
   IMPORT DATABASE 'data/exports/<latest>';
   ```
3. Replay any landing Parquet newer than the snapshot, per table, in `run_id` order (upsert is
   idempotent; full-refresh takes the newest).
4. Start the backend; confirm `table_registry` freshness and `/api/catalog/tables`.

## Scenario B — no snapshot, replay log only
1. Stop the backend.
2. For each table, recreate it from its Parquet files in `run_id` order using the recorded
   `load_mode` (full → newest file; append/upsert → replay all, idempotent).
3. Restart; resume the schedule. Watermarks in `table_registry` ensure the next scheduled run
   continues from the last committed point.

## Scenario C — Oracle/WAN outage (no recovery needed)
Dashboards keep serving local DuckDB data; affected tables show the **stale badge**. When Oracle
returns, the scheduled jobs catch up from their watermarks automatically.

## Verify after recovery
- `GET /api/catalog/tables` → expected `row_count`, `last_load_status=success`.
- Spot-check a dashboard widget: `data_as_of` should match the last good load.
