# ULTRAPLAN PROMPT (v2) — Telecom ITOSS UPM Platform

> Paste everything below this line into Claude Code after `/ultraplan`.

---

## 1. Mission

Plan (do **not** write code yet) a centralized, self-service **Telecom IT-OSS Unified Performance Management (UPM)** web platform.

The platform has **two builder surfaces** and **two audiences**:
- **Builders** define how data gets in (an Extraction Job Builder) and how it is shown (a Dashboard Builder).
- **Viewers** only consume the dashboards they are granted; they create nothing.

Underneath sits a **permanent, materialized columnar store (DuckDB)**: scheduled extraction jobs pull data from a remote Oracle warehouse and **land it permanently** in DuckDB (this is a normal persistent database, NOT on-the-fly query federation). Every dashboard then queries DuckDB only — fast and Oracle-independent.

Treat this as a greenfield monorepo. I want a deep, opinionated architecture and a phased delivery plan, not code.

## 2. My environment and skills (build to these)

- Telecom data engineer. Strong in **Python/FastAPI, Oracle PL/SQL, Linux, Docker / Docker Compose, and Celery** (I run Airflow on CeleryExecutor with Postgres + Redis in production).
- Source data: a **remote Oracle warehouse** (schema `SON`, e.g. `hybrid_cs_cell`, `hybrid_ps_cell` — cell-level circuit-switched and packet-switched KPIs). **Not co-located** — assume WAN latency / intermittent connectivity.
- Some tables hold **site data with latitude/longitude** for map visualization.
- An **on-prem Qwen 3.6 LLM** runs on other company machines, reachable via an OpenAI-compatible HTTP API (likely an open-weight 3.6 variant served via vLLM/SGLang, ~262K context). No public cloud LLMs. On-prem deployment only.

## 3. Core architecture principle (do not violate)

Oracle is touched in **exactly one place** — the extraction jobs. Everything users see comes from data **already materialized in DuckDB**. There is a **write path** (extraction) and a **read path** (serving) that meet only at DuckDB:
- **Write path:** Oracle → scheduler/ingestion → DuckDB (permanent).
- **Read path:** dashboards/viewers → backend → DuckDB (read-only).
- The Dashboard Builder has **no path to Oracle**. If a column isn't in a materialized DuckDB table, it can't be charted until an extraction job brings it in.

## 4. Services (functional requirements)

### Service A — Frontend (Material 3)
- React + Material-3 library, Vite, deployed twice (**dev + prod**, separate ports/config).
- **Extraction Job Builder** (Builders only): pick Oracle source (e.g. `SON.hybrid_cs_cell`), define SELECT/filters/params, name the **target DuckDB table**, set interval, **load mode**, and watermark column.
- **Dashboard Builder** (Builders only): pick a **registered DuckDB table → columns → filters → chart/map type → grid layout**. Standard charts (line, bar, area, pie, scatter, KPI tiles, tables) plus **map widgets** for lat/long site data. Dashboards grouped into **projects**.
- **Viewer experience:** browse and read assigned project dashboards; no create/edit anywhere.
- **AI chat panel** (final phase, see §8): calls the on-prem Qwen 3.6.

### Service B — Columnar Analytics Store (permanent)
- **DuckDB** as a **permanent materialized store** (assumption; evaluate/justify). Starts with `hybrid_cs_cell` and `hybrid_ps_cell`; any job-created table can be registered later.
- `spatial` extension for lat/long. A **table registry**: a successful job registers its target table so the Dashboard Builder can see it.

### Service C — Backend Data Plane (fault-tolerant)
- FastAPI service that **solely owns the DuckDB connection** (serializes writes, fans out concurrent reads).
- APIs: auth, schema introspection (list registered tables/columns/types), dashboard CRUD, query execution (paginated/cached), job CRUD, AI-chat proxy.

### Service D — Scheduler / Job Maker
- Turns UI job configs into **recurring interval jobs**. The Ingestion Worker executes them with **incremental, idempotent, watermarked** loads (staging table → atomic swap).
- **Load modes per job:** full refresh · append · upsert-by-key.
- Job definitions are **config rows** — adding a feed never touches code.

### Cross-cutting: everything is UI-driven, config is data
Creating extraction jobs, building dashboards, and managing users/roles are all done from the UI. Configs live in a control-plane database; services react to them.

## 5. Architecture decisions I want adopted (challenge with reasons if wrong)

1. **Single-writer DuckDB.** Backend is the sole writer; the scheduler enqueues load jobs to a single ingestion worker. Staging → atomic swap. Note ClickHouse as the upgrade path if volume/concurrency grows; MotherDuck likely excluded (on-prem).
2. **Two stores.** A **PostgreSQL control plane** (users, roles, projects, dashboards, job configs, run history, audit) kept fully separate from the **DuckDB analytics plane**.
3. **Table registry** drives the Dashboard Builder; build schema introspection early.
4. **Scheduler:** lightweight **Celery + Redis**, config-driven (reuses my experience; no DAG files). Justify vs APScheduler / Airflow.
5. **Load modes + retention:** per-job load mode; a **retention/compaction strategy** because the store is permanent and grows (confirm: keep-forever vs rolling window).
6. **RBAC:** three roles — **Admin** (all + user management), **Builder/Editor** (create jobs + dashboards), **Viewer** (read-only, assigned projects, creates nothing). Access scoped per project.
7. **Maps:** MapLibre GL for production dashboards; Kepler.gl for exploration; DuckDB `spatial` backend.
8. Stack to validate: React + Material 3, **FastAPI**, **DuckDB (+spatial)**, **PostgreSQL**, **Celery + Redis**, **python-oracledb**, **Docker Compose**, Nginx/Traefik.

## 6. Non-functional requirements
- **Fault tolerance:** retries w/ backoff, dead-letter, idempotent watermarked loads, staging→swap, per-service health checks, graceful degradation when Oracle/LLM unreachable. **Dashboards must keep working during Oracle/WAN outages** (data is local).
- **Security:** JWT/OAuth2, three-role RBAC, project-scoped access, parameterized/validated SQL, secrets management, audit trail of every change and job run.
- **Observability:** structured logging, job run history, basic metrics.
- **Performance:** responsive dashboards, query caching, pagination.

## 7. AI chat — LAST priority (Qwen 3.6)

Build only after the core platform is solid. Then:
- **Text-to-SQL over DuckDB** is the target — Qwen 3.6 is coding-first, so SQL generation is its strength.
- **Schema grounding via large context:** inject the full DuckDB catalog (tables, columns, types, comments, sample rows) into the system prompt — likely no retrieval pipeline needed at ~262K context.
- **Native tool/function calling:** expose `list_tables`, `describe_table`, `run_readonly_sql`, `propose_chart`.
- **Structured JSON output** for chart specs.
- **Thinking mode** on for complex analytical SQL, off for trivial lookups; preserve thinking across multi-turn analysis.
- **Guardrails:** dedicated read-only DuckDB connection; parse SQL (e.g. sqlglot) to allow SELECT-only + schema allow-list + row/time limits; never expose Oracle creds or the write path to chat.
- **Optional bonus (can come earlier):** use Qwen to *assist the builders* — draft Oracle extraction SQL from natural language, or suggest chart + columns for a chosen table.

## 8. What I want this plan to deliver
1. Architecture overview + component/data-flow diagram (text or mermaid) showing the two paths and the control plane.
2. **ADRs** for: columnar DB choice & single-writer pattern, scheduler choice, control-plane DB, load-mode/retention strategy, map library.
3. **Monorepo structure** (one-line purpose per folder).
4. **Service/API contracts** (auth, schema introspection, dashboard CRUD, query execution, job CRUD, AI proxy) at signature level.
5. **Control-plane data model**: users/roles, projects, dashboards/widgets, job_configs, job_runs, table_registry, audit_log.
6. **Dashboard definition schema** (JSON: chart type, table, columns, filters, layout).
7. **Job definition schema** (source SQL/params, target table, interval, load mode, watermark).
8. **Phased roadmap, MVP first.** Suggested order: Phase 0 skeleton → Phase 1 MVP (one job loading `hybrid_cs_cell` + schema introspection + one basic dashboard + **Viewer role**) → Phase 2 Extraction Job Builder (load modes, watermarks, retries, run history, Builder role) → Phase 3 Dashboard Builder (full palette, `hybrid_ps_cell` use-cases) → Phase 4 maps + retention/compaction + RBAC depth + observability → **Phase 5 AI chat (Qwen 3.6), optional/last**.
9. **Deployment plan**: Docker Compose for dev & prod, ports, reverse proxy, where DuckDB/Postgres volumes live.
10. **Testing strategy**, incl. testing against Oracle without the live warehouse (mocks/fixtures).
11. **Risk register + open questions** with the assumptions you made and decisions you need me to confirm.

## 9. Ground rules
- This is a **planning request** — produce the plan and ask clarifying questions; no implementation code yet.
- Be opinionated and concrete; where you disagree with §5, say so with trade-offs.
- Keep the stack within my skill set (Python/FastAPI, Celery, Docker, Postgres, Oracle) unless a deviation is clearly worth it.
- Optimize for a quickly demo-able MVP, then a clean path to the full system.

## 10. Open questions to resolve in the plan
- Row counts & growth for `hybrid_cs/ps_cell` (DuckDB vs ClickHouse)?
- Job refresh interval (minutes/hourly/daily)?
- Retention: keep forever vs roll off after N months?
- Oracle read-only service account + network path?
- Which Qwen 3.6 variant/endpoint, context window, rate limits?
- Peak concurrent viewers; single VM vs multiple hosts?
