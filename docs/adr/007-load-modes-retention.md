# ADR-007 — Load modes + retention per job

**Status:** Accepted

## Decision
Per-job load mode — `full` (full-refresh) · `append` · `upsert-by-key` — and per-job retention —
`keep_forever` or `rolling_window(N)` with scheduled compaction.

## Why
Different feeds have different shapes: dimension-like tables full-refresh; high-volume fact
tables append/upsert with a watermark. Idempotency comes from the watermark advancing only on a
committed load and upsert keys deduping a replayed Parquet file.

## Default proposal (confirm)
Rolling 13 months + monthly compaction; Parquet replay kept 30 days.

## Implementation
`upm_shared.jobs.JobDefinition` (load_mode, watermark, key_columns, retention) and
`DuckDBGateway.load`.
