# UPM Platform — Telecom IT-OSS Unified Performance Management

A self-service platform where **Builders** define how telecom KPI data gets in (Extraction Job
Builder) and how it's shown (Dashboard Builder), and **Viewers** consume the dashboards they're
granted. Data is materialized permanently in **DuckDB**; dashboards query DuckDB only and never
touch Oracle.

This repository is the **v1** build of the design in
[`docs/architecture-plan.md`](docs/architecture-plan.md) — Phase 0 (skeleton) + Phase 1 (a
demo-able end-to-end MVP), with the structural seams for Phases 2–5 in place.

> Because no live Oracle warehouse is attached, the ingestion source is pluggable and defaults to
> a **synthetic telecom-KPI source**, so the whole pipeline runs end-to-end with no Oracle. Set
> `UPM_SOURCE_TYPE=oracle` (+ creds) to use the real `python-oracledb` adapter.

---

## The five inviolable principles (and where they live)

1. **Oracle is touched in exactly one place** — the extract step (`apps/ingestion`). Nothing on
   the read path can reach it.
2. **Write and read paths meet only at DuckDB.** Write: Oracle → extract → Parquet → Gateway →
   DuckDB. Read: viewer → backend → Gateway → DuckDB (read-only).
3. **One process owns the DuckDB file** — the `DuckDBGateway` (`packages/dataplane`). Everyone
   else is a client.
4. **Config is data.** Jobs, dashboards, users, roles are rows in Postgres. Adding a feed or a
   chart never touches code.
5. **Dashboards survive Oracle/WAN outages.** Data is local; staleness is shown, not hidden
   (the amber "stale" badge).

---

## Quickstart A — local, no Docker (fastest)

Requires [`uv`](https://docs.astral.sh/uv/) and Node ≥ 20. Uses SQLite + an in-process Gateway
(single process, no Redis/Postgres needed).

```bash
uv sync                      # create the venv, install all workspace members (Python 3.12)
uv run upm demo              # init DB + seed demo + load both jobs (synthetic) into DuckDB
uv run uvicorn upm_backend.main:app --port 8000   # serve the API (hosts the Gateway)
```

In another terminal:

```bash
cd apps/frontend && npm install && npm run dev     # http://localhost:5173 (proxies /api -> :8000)
```

Open http://localhost:5173 and log in:

| Role    | Email             | Password       |
|---------|-------------------|----------------|
| Admin   | admin@upm.com     | `admin12345`   |
| Builder | builder@upm.com   | `builder12345` |
| Viewer  | viewer@upm.com    | `viewer12345`  |

The Viewer sees the **Hybrid Cell Overview** dashboard (KPIs, line/bar charts) with a
"data as of …" badge. The Builder additionally gets the **Jobs** page with a **Run now** button
and run history.

## Quickstart B — full stack with Docker Compose (prod-shaped)

Postgres + Redis + backend + Celery worker + Celery beat (RedBeat) + frontend (nginx) + Traefik +
Prometheus + Grafana.

```bash
cp .env.example .env         # then edit UPM_JWT_SECRET (and any creds)
docker compose -f infra/compose/docker-compose.dev.yml --env-file .env up --build
```

- Frontend: http://localhost:8080  (or http://localhost via Traefik)
- API: http://localhost:8000/api/health
- Grafana: http://localhost:3000

The backend migrates (Alembic) and seeds on boot. To materialize data in this mode, log in as the
Builder and click **Run now** — that exercises the real pipeline: Celery worker extracts → Parquet
→ enqueues a `LoadCommand` → the backend's Gateway-owning consumer loads it into DuckDB. (Or wait
for the hourly schedule.)

---

## Architecture (what runs where)

```
WRITE  Oracle/Synthetic ──extract──▶ Parquet landing ──LoadCommand──▶ DuckDB Gateway ──▶ DuckDB
        (Celery worker, parallel)     (replay log)      (Redis queue)   (sole RW owner)

READ   Frontend ──▶ Backend API ──▶ Gateway (read-only) ──▶ DuckDB        cache+freshness by table_version

CTRL   PostgreSQL  (users/roles/projects/dashboards/job_configs/job_runs/table_registry/audit_log)
       Redis       (Celery broker + query cache + load queue)
```

The Gateway runs **in-process inside the backend** for the MVP (§14). The exact same interface
lifts into a standalone single-instance service when ADR-002 triggers are hit — nothing else
changes.

## Monorepo layout

```
packages/
  shared-schemas/   upm_shared        — Pydantic contracts (jobs, dashboards, query, catalog, auth)
  sql-tools/        upm_sql_tools     — sqlglot SELECT-only validators + safe structured builders
  dataplane/        upm_dataplane     — DuckDBGateway (single-writer, staging→swap, registry, reads)
control-plane/      upm_control_plane — SQLAlchemy models, session, Alembic migrations, mapping
apps/
  backend/          upm_backend       — FastAPI: auth, RBAC, catalog, query, jobs, dashboards, AI proxy
  ingestion/        upm_ingestion     — Celery worker, pluggable source (synthetic/oracle), orchestrator
  scheduler/        upm_scheduler     — Celery Beat + RedBeat, schedules from job_configs
  frontend/         React + Vite + MUI v6 + Recharts
infra/
  compose/          Dockerfiles + docker-compose.dev.yml (+ Traefik)
  observability/    Prometheus config (Grafana dashboards: Phase 4)
docs/
  architecture-plan.md · adr/*.md · runbook-recovery.md
```

## Testing

```bash
uv run pytest                       # unit (sql-tools, gateway) + API integration smoke
cd apps/frontend && npm run build   # type-check + production build
```

- `packages/sql-tools/tests` — builder + SELECT-only guard (injection, cross-schema, non-SELECT).
- `packages/dataplane/tests` — full + upsert idempotency + registry update.
- `apps/backend/tests/test_api_smoke.py` — seed → load (synthetic) → login → catalog → query →
  cache hit → RBAC denial → job run + history → validate → dashboards, against the real app.

## v1 status vs. the phased roadmap

| Phase | Scope | Status in v1 |
|-------|-------|--------------|
| 0 | Skeleton, Compose, Postgres+Alembic, Redis, shared-schemas, auth, Gateway interface | **Done** |
| 1 | Structured job → Parquet → swap → registry+freshness; catalog; one dashboard; Viewer + scope; "data as of"; query cache | **Done** |
| 2 | Load modes (append/upsert ✅), watermarks ✅, idempotency ✅, retries/backoff/DLQ ✅, run-history UI ✅, Builder ✅, SQL governance (structured + sqlglot + read-only acct + guards) ✅, validate ✅ | **Mostly done** (preview/EXPLAIN against live Oracle pending) |
| 3 | Full chart palette ✅ (line/bar/area/pie/kpi/table), structured filters ✅, grid layout ✅, projects ✅, cache invalidation on load ✅ | **Core done** (in-app Dashboard *editor* UI pending; dashboards are API-editable) |
| 4 | Maps, retention/compaction jobs, observability dashboards, backup tooling, Gateway promotion | Seams in place; **not yet built** |
| 5 | AI chat (Qwen) | Scaffold + SELECT-only guard shipped; tool-loop pending endpoint |

## §16 defaults adopted (override via `.env`)

Single-writer Gateway now · Parquet replay 30d + scheduled EXPORT · schema-drift → quarantine+alert
(planned) · hourly refresh · rolling 13 months retention · read-only Oracle account · provider-agnostic
LLM client · single VM · MUI M3 theming. See the risk register in the architecture plan for the
real-world numbers still needed (row counts, LLM endpoint, peak viewers).

## CLI

```bash
uv run upm init-db            # create tables + seed RBAC
uv run upm seed               # seed demo users/project/jobs/dashboard (idempotent)
uv run upm run-job <name|id>  # extract+load one job inline (dev)
uv run upm demo               # init + seed + load both demo jobs
uv run upm-ingest enqueue <job>          # worker path: extract + push LoadCommand to Redis
uv run upm-scheduler sync                # push job_configs schedules into RedBeat
```
