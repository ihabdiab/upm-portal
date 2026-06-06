# ADR-003 — Two stores

**Status:** Accepted

## Decision
PostgreSQL is the control plane (transactional metadata: users, roles, projects, dashboards,
job_configs, job_runs, table_registry, audit_log). DuckDB is the analytics plane (columnar KPI
data). They are never co-mingled.

## Why
The two workloads have opposite shapes: many small transactional writes vs. large columnar
scans. Separating them lets each engine do what it is good at.

## Trade-off / trigger to revisit
Two engines to operate. Accepted — worth it. Local-without-docker swaps Postgres for SQLite via
`UPM_DATABASE_URL`; the ORM uses portable types so models are unchanged.
