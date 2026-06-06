# ADR-005 — Ingestion via Parquet landing + atomic swap

**Status:** Accepted

## Decision
Workers extract Oracle → Parquet (landing zone). The Gateway loads Parquet → staging table →
transactional swap into the live table.

## Why
Decouples "talk to Oracle" (parallel, I/O-bound, on the worker) from "write DuckDB" (serialized,
on the Gateway). The Parquet files double as the backup/replay log ([ADR-006](006-durability-parquet-replay.md)).

## Trade-off
An extra on-disk hop. Cheap, and it buys idempotent re-loads and free durability.

## Implementation
`apps/ingestion` (extract) → `LoadCommand` → `packages/dataplane` (`load()`), with full / append /
upsert modes.
