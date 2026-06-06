# ADR-001 — Columnar store: DuckDB (permanent, materialized)

**Status:** Accepted

## Decision
Materialize telecom KPI data permanently in DuckDB and serve all dashboard reads from it.
Use the `spatial` extension for lat/long.

## Why
Read-heavy KPI aggregations over append-mostly data; embedded, zero-ops, excellent columnar
scan performance; no separate cluster to operate on-prem.

## Trade-off / trigger to revisit
Single read-write process per file (mitigated by the Gateway, [ADR-002](002-single-writer-gateway.md)).
Move to ClickHouse if sustained >2B rows/table, >~50 concurrent heavy viewers, or write
throughput exceeds a single serialized writer. The Gateway interface is the swap seam.
