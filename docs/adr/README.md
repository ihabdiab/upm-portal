# Architecture Decision Records

Each ADR captures one resolved decision: **decision · why · trade-off / trigger to revisit**.
The authoritative narrative lives in [`../architecture-plan.md`](../architecture-plan.md) §3; these
files are the split-out, individually-referenceable records.

| ADR | Title | Status |
|-----|-------|--------|
| [001](001-columnar-store-duckdb.md) | Columnar store: DuckDB (permanent, materialized) | Accepted |
| [002](002-single-writer-gateway.md) | Single-writer via DuckDB Gateway | Accepted |
| [003](003-two-stores.md) | Two stores (Postgres control + DuckDB analytics) | Accepted |
| [004](004-scheduler-celery-redbeat.md) | Scheduler: Celery + Redis + RedBeat | Accepted |
| [005](005-ingestion-parquet-landing.md) | Ingestion via Parquet landing + atomic swap | Accepted |
| [006](006-durability-parquet-replay.md) | Durability: Parquet replay + scheduled EXPORT | Accepted |
| [007](007-load-modes-retention.md) | Load modes + retention per job | Accepted |
| [008](008-rbac-capabilities.md) | RBAC as capabilities, project-scoped | Accepted |
| [009](009-frontend-react-mui.md) | Frontend: React + Vite + MUI (M3 theming) | Accepted |
| [010](010-maps-maplibre-kepler.md) | Maps: MapLibre + Kepler.gl on DuckDB spatial | Accepted |
| [011](011-ai-openai-compatible-select-only.md) | AI: provider-agnostic, SELECT-only over DuckDB | Accepted |
