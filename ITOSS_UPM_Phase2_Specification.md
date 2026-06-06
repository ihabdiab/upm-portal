# ITOSS UPM Phase 2 – Project Specification

## Overview
This document defines the remaining feature gaps and integration requirements to merge Phase 2 into the ITOSS UPM production platform. All features must maintain **portability and containerization** — the entire project ships to DevOps with zero environmental friction.

---

## 1. Real Data Ingestion & Schema Inference

### Current State
- Platform currently uses dummy placeholder data
- No multi-source ingestion capability
- Single Oracle connection; no schema flexibility

### Phase 2 Requirements

#### 1.1 Multi-Source Data Ingestion Interface
Create a unified ingestion menu with three distinct pathways:

##### Option A: Oracle Connection (Existing Data Sources)
- User selects an existing **connection** from the Airflow-like connection registry (see §4)
- Query builder or table selector to choose source data
- Automatic schema inference from Oracle metadata
- Data preview before committing to ingestion

##### Option B: External CSV File(s)
- File upload interface (drag-and-drop or file picker)
- Support **multiple CSV files** simultaneously
- Automatic schema inference:
  - Data type detection (numeric, string, date, boolean)
  - Header detection
  - Delimiter inference (comma, semicolon, tab, pipe)
- CSV parsing validation with error reporting
- Data preview before committing to ingestion

##### Option C: DuckDB Direct Query
- Query editor window with:
  - **Syntax highlighting** (SQL mode)
  - **Autocomplete** suggesting available tables in DuckDB
  - Real-time syntax validation
  - Server-side query execution with error feedback
- Results preview and validation
- Automatic schema inference from query output

#### 1.2 Schema Inference Engine
- Detect column names, types, and constraints
- Handle missing/null values gracefully
- Present inferred schema to user for review/correction before final load
- Store schema metadata for later use in job building

#### 1.3 Integration with Builder
- Ingested datasets appear as selectable sources in the **Extraction Jobs** builder
- Support **CSV sources** as first-class data sources (alongside Oracle)
- Enable job creation directly from ingested data

---

## 2. Data Ingestion – Test Scenario

### CS File (Customer Satisfaction)
- **Action**: Replace all dummy data with actual CS dataset
- **Integration point**: Load at platform initialization (or via ingestion UI)
- **Expected outcome**: CS data immediately visible in dashboards and available for job creation

### PS File (Partner Satisfaction)
- **Action**: User will test CSV ingestion feature using PS dataset
- **Expected outcome**: Demonstrates end-to-end ingestion, schema inference, and integration into builder
- **Ownership**: User performs this test post-delivery

---

## 3. AI Chat Integration

### Requirements

#### 3.1 Chat Interface Component
- Clean, intuitive chat window (bottom-right or sidebar)
- Message history with scrollback
- Input field with send button
- Visual distinction between user and assistant messages
- Loading indicator during API calls

#### 3.2 LLM Backend Flexibility
Support **multiple LLM providers**:
- **Anthropic Claude Opus** (primary; user provides API key for testing)
- **Claude Agent interface** for agentic tasks
- **Qwen 3.6** (internal; already available)
- Pluggable provider selection in UI/config

#### 3.3 API Key Management
- Secure input field for Anthropic API key (testing)
- Store in environment or secure config (never in version control)
- Support `.env` file for local development
- Document Dockerfile/container setup for production

#### 3.4 Chat Capabilities
- General-purpose Q&A about the platform
- Contextual help (hover tooltips → LLM summaries)
- Data exploration queries ("What trends are in this dataset?")
- Job building assistance ("Create a DAG that extracts X and aggregates Y")

---

## 4. Connection Registry (Airflow-like Interface)

### Requirements

#### 4.1 Connection Management UI
- **List view** of all saved connections
- **Create new connection** button → form
- **Edit/delete** existing connections
- **Test connection** button (validates credentials before saving)

#### 4.2 Supported Connection Types
- **Oracle**: Host, Port, SID/Service Name, Username, Password
- **PostgreSQL**: Host, Port, Database, Username, Password
- **MySQL**: Host, Port, Database, Username, Password
- **Microsoft SQL Server**: Host, Port, Database, Username, Password
- **Generic RDBMS**: Connection string + credentials

#### 4.3 Connection Form Fields
- Connection name (unique identifier)
- Connection type (dropdown)
- Type-specific fields (dynamically rendered)
- Test button (execute lightweight query to validate)
- Save button (persist to config/database)

#### 4.4 Integration Points
- Connections appear in **Option A** (Oracle ingestion)
- Connections available in **Extraction Jobs builder** for data source selection
- Credentials encrypted at rest (use library like `cryptography`)

---

## 5. Map Capability – Status & Visibility

### Current State Assessment
- Status: **Needs clarification** — is Kepler.gl integrated? Partial? Planned?
- Usage: Telecom KPI geolocation visualization

### Phase 2 Action Items
- **Determine**: Current implementation status (MVP, POC, or not started)
- **Decision**: Include in Phase 2 or defer to Phase 3
- **If included**: 
  - Add map viewer panel to dashboard
  - Integrate with KPI data
  - Support drill-down (click region → see metrics)
- **Visibility**: Present a **glimpse/preview** in the main viewer (e.g., small embedded map card)

---

## 6. Jobs & Dashboards in Builder

### Current State
- Viewer mode only (read-only display of data)
- Builder currently supports partial DAG creation

### Phase 2 Requirements

#### 6.1 Extraction Jobs Builder
- **Source selection**: Choose data source (Oracle connection, CSV, DuckDB query)
- **Transformation logic**: Define filters, aggregations, column selection
- **Target**: Choose destination (DuckDB, file export, external DB)
- **Scheduling**: Airflow DAG schedule (cron expression)
- **Validation**: Dry-run before saving

#### 6.2 Dashboard Builder
- **Widget library**: Cards, tables, charts, maps, KPI tiles
- **Drag-and-drop** layout
- **Data binding**: Connect widgets to data sources (jobs, queries, real-time feeds)
- **Filters/parameters**: Add filters that cascade across widgets
- **Export/share**: Save dashboard as reusable template

#### 6.3 Saving & Persistence
- Store jobs/dashboards in configuration layer
- Support version history
- Enable clone/template workflows

---

## 7. Portability & Containerization

### Non-Negotiable Requirements
All Phase 2 features must ship production-ready in Docker/Kubernetes.

#### 7.1 Architecture
- **Microservices**: Frontend, Backend, Scheduler, DuckDB layer (separate containers)
- **No hardcoded paths** or environment-specific configs
- **Secrets management**: Use `.env`, Kubernetes secrets, or HashiCorp Vault
- **Database migrations**: Versioned, automated

#### 7.2 Docker Setup
```dockerfile
# Example structure (details per service)
FROM python:3.11-slim
# Install dependencies
# Copy code
# Expose ports
# Health checks
CMD ["supervisord", "-c", "/etc/supervisor/supervisord.conf"]
```

#### 7.3 Docker Compose (Local Development)
- Frontend (React/Vue on port 3000)
- Backend (FastAPI/Flask on port 5000)
- DuckDB service (or embedded)
- Airflow services (scheduler, webserver)
- Redis (caching, job queue)

#### 7.4 Environment Variables
- `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`
- `ANTHROPIC_API_KEY` (for testing)
- `DUCKDB_PATH`
- `AIRFLOW_HOME`
- Timezone: **Egypt (Africa/Cairo)**

#### 7.5 Deployment Checklist
- [ ] All services start with single `docker-compose up`
- [ ] No missing environment files
- [ ] Migrations run on startup
- [ ] Logging to stdout/stderr (no files)
- [ ] Health checks functional
- [ ] Networks properly isolated

---

## 8. Data Files – Integration Points

### CS File (Customer Satisfaction)
- **Format**: CSV or Oracle export
- **Integration**: Load during platform initialization or via ingestion UI
- **Replacement**: Replaces current dummy CS data
- **Validation**: Schema must match expected KPI structure

### PS File (Partner Satisfaction)
- **Format**: CSV
- **Integration**: User-driven test of CSV ingestion feature (§1.1 Option B)
- **Ownership**: User performs this test
- **Success criteria**: CSV loads, schema inferred, data visible in builder

---

## 9. Feature Checklist

### Phase 2 Deliverables

#### Data Ingestion
- [ ] Multi-source ingestion UI (Oracle/CSV/DuckDB query)
- [ ] Schema inference engine
- [ ] CSV parser with validation
- [ ] DuckDB query editor with autocomplete + syntax highlighting
- [ ] Data preview/validation screens
- [ ] Integration with extraction jobs builder

#### AI Chat
- [ ] Chat UI component
- [ ] Anthropic Claude Opus integration (with API key input)
- [ ] Claude Agent interface
- [ ] Fallback to Qwen 3.6
- [ ] Secure API key handling

#### Connections
- [ ] Connection registry UI (CRUD)
- [ ] Test connection functionality
- [ ] Support for Oracle, PostgreSQL, MySQL, MSSQL
- [ ] Credential encryption
- [ ] Integration with ingestion & job builder

#### Jobs & Dashboards
- [ ] Extraction jobs builder (source → transform → target)
- [ ] Dashboard builder (drag-drop, data binding, filters)
- [ ] Scheduling (cron) integration
- [ ] Save/version/clone workflows

#### Map Capability
- [ ] Status clarification
- [ ] Phase 2 inclusion decision
- [ ] MVP if included: embedded map viewer in dashboard

#### Portability
- [ ] Docker Compose (all services)
- [ ] Environment-based config (no hardcodes)
- [ ] Secrets management (`.env` / Kubernetes)
- [ ] Automated migrations
- [ ] Health checks & monitoring
- [ ] Single-command startup: `docker-compose up`

---

## 10. Success Criteria

1. **Data Ingestion**: CS data loads and replaces dummy data; PS CSV ingests successfully via new UI
2. **AI Chat**: Chat window available; Claude Opus responds to queries (user API key provided)
3. **Connections**: User can create Oracle connection, test it, and use it in job builder
4. **Jobs & Dashboards**: User can create extraction job from CS data and build dashboard widget
5. **Map**: Status clear; visible in UI if Phase 2 scope
6. **Portability**: `docker-compose up` → full platform running in <5 minutes with no manual setup

---

## 11. Assumptions & Dependencies

- CS and PS data files provided (format: CSV or Oracle export)
- Anthropic API key provided by user for testing
- DuckDB columnar layer already exists (Phase 1)
- Basic Airflow scheduler infrastructure in place
- Frontend framework decided (React/Vue)
- Backend framework decided (FastAPI/Flask/Django)

---

## 12. Timeline & Ownership

- **Specification review**: Confirm requirements with stakeholder
- **Development**: Implement features in order of dependency
- **Testing**: User tests CSV ingestion with PS file post-delivery
- **Deployment**: DevOps validates containerized setup

---

## Appendix: File Structure Reference

```
itoss-upm/
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── app/
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── ingestion.py
│   │   │   ├── connections.py
│   │   │   ├── jobs.py
│   │   │   └── chat.py
│   │   └── services/
│   │       ├── schema_inference.py
│   │       ├── duckdb_query.py
│   │       └── llm_provider.py
├── frontend/
│   ├── Dockerfile
│   ├── src/
│   │   ├── components/
│   │   │   ├── IngestionUI.jsx
│   │   │   ├── ChatWindow.jsx
│   │   │   ├── ConnectionRegistry.jsx
│   │   │   ├── JobBuilder.jsx
│   │   │   └── DashboardBuilder.jsx
│   │   └── pages/
├── airflow/
│   ├── Dockerfile
│   ├── dags/
│   │   └── extraction_jobs.py
│   └── config/
├── duckdb/
│   └── data.duckdb
└── README.md
```

---

**Version**: Phase 2.0  
**Last Updated**: [Current Date]  
**Prepared For**: Development Team  
**Status**: Ready for handoff
