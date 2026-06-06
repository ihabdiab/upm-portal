# ADR-002 — Single-writer via DuckDB Gateway

**Status:** Accepted

## Decision
Exactly one process opens the DuckDB file read-write: the **DuckDB Gateway**. Ingestion never
writes DuckDB — it extracts to a Parquet landing zone and hands a load command to the Gateway,
which serializes writes (staging → atomic swap) and fans out read-only cursors. In the MVP the
Gateway is an in-process module inside the backend; the same interface lifts into a standalone
single-instance service later.

## Why
A DuckDB file permits only one read-write process. Routing every write through one owner makes
the single-writer invariant structural rather than conventional.

## Trade-off / trigger to revisit
The Gateway is a single instance (a scaling ceiling, not a read SPOF if a read replica file is
kept). Promote to a standalone service when ADR-001 triggers are hit.

## Implementation
`packages/dataplane` (`DuckDBGateway`). Load command transport: Redis list `upm:duckdb:load`
consumed by the backend (`upm_backend/loadconsumer.py`); dev mode loads inline.
