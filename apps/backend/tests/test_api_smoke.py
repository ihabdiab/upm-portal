"""End-to-end API smoke test: seed + load (synthetic) -> login -> catalog -> query.

Self-contained: builds a throwaway SQLite control plane + DuckDB file in tmp, runs both
demo jobs inline through the Gateway, then drives the real FastAPI app via TestClient.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("UPM_DATABASE_URL", f"sqlite+pysqlite:///{tmp_path / 'control.sqlite3'}")
    monkeypatch.setenv("UPM_DUCKDB_PATH", str(tmp_path / "analytics.duckdb"))
    monkeypatch.setenv("UPM_LANDING_DIR", str(tmp_path / "landing"))
    monkeypatch.delenv("UPM_REDIS_URL", raising=False)

    from upm_backend.config import get_settings
    from upm_control_plane import reset_engine, session_scope
    from upm_control_plane.bootstrap import init_db
    from upm_dataplane import get_gateway, reset_gateway

    get_settings.cache_clear()
    reset_engine()
    reset_gateway()

    # Seed + load both demo jobs inline (single process owns DuckDB here).
    from upm_backend.seed import seed_demo
    from upm_ingestion.orchestrator import resolve_job_id, run_job_inline

    init_db()
    with session_scope() as session:
        info = seed_demo(session)
    gw = get_gateway()
    for name in info["jobs"]:
        run_job_inline(resolve_job_id(name), gateway=gw)
    reset_gateway()

    from upm_backend.main import create_app

    with TestClient(create_app()) as c:
        yield c

    reset_engine()
    reset_gateway()
    get_settings.cache_clear()


def _login(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_viewer_reads_kpi_end_to_end(client):
    token = _login(client, "viewer@upm.com", "viewer12345")

    me = client.get("/api/me", headers=_auth(token)).json()
    assert "project:view" in me["capabilities"]
    assert any(p["role"] == "Viewer" for p in me["projects"])

    tables = client.get("/api/catalog/tables", headers=_auth(token)).json()
    names = {t["table_name"] for t in tables}
    assert {"hybrid_cs_cell", "hybrid_ps_cell"} <= names
    cs = next(t for t in tables if t["table_name"] == "hybrid_cs_cell")
    assert cs["row_count"] == 588
    assert cs["last_load_status"] == "success"
    assert cs["stale"] is False  # just loaded

    detail = client.get("/api/catalog/tables/hybrid_cs_cell", headers=_auth(token)).json()
    colnames = {c["name"] for c in detail["columns"]}
    assert {"timestamp", "cell_id", "region", "traffic_erl", "drop_rate"} <= colnames
    assert detail["freshness"]["table_version"] == 1

    # Line-chart query: avg traffic by timestamp+region.
    body = {
        "table": "hybrid_cs_cell",
        "aggregations": [{"fn": "avg", "col": "traffic_erl", "as": "traffic"}],
        "groupBy": ["timestamp", "region"],
        "sort": [{"col": "timestamp", "dir": "asc"}],
        "limit": 5000,
    }
    r = client.post("/api/query", headers=_auth(token), json=body)
    assert r.status_code == 200, r.text
    payload = r.json()
    assert payload["table_version"] == 1
    assert payload["data_as_of"] is not None
    assert payload["stale"] is False
    assert len(payload["rows"]) > 0
    assert {"timestamp", "region", "traffic"} <= set(payload["rows"][0].keys())

    # Second identical query should be served from cache.
    r2 = client.post("/api/query", headers=_auth(token), json=body)
    assert r2.json()["cached"] is True


def test_viewer_cannot_author_jobs(client):
    token = _login(client, "viewer@upm.com", "viewer12345")
    r = client.get("/api/jobs", headers=_auth(token))
    assert r.status_code == 403


def test_builder_runs_job_and_sees_history(client):
    token = _login(client, "builder@upm.com", "builder12345")
    jobs = client.get("/api/jobs", headers=_auth(token)).json()
    assert len(jobs) == 2
    job_id = jobs[0]["id"]

    run = client.post(f"/api/jobs/{job_id}/run", headers=_auth(token))
    assert run.status_code == 200, run.text
    assert run.json()["mode"] == "inline"

    runs = client.get(f"/api/jobs/{job_id}/runs", headers=_auth(token)).json()
    assert len(runs) >= 1
    assert runs[0]["status"] == "success"


def test_admin_query_validate_and_dashboard(client):
    token = _login(client, "admin@upm.com", "admin12345")

    # Job validation renders extraction SQL.
    jobs = client.get("/api/jobs", headers=_auth(token)).json()
    jd = jobs[0]["definition"]
    v = client.post("/api/jobs/validate", headers=_auth(token), json=jd)
    assert v.status_code == 200, v.text
    assert v.json()["ok"] is True
    assert "SELECT" in v.json()["rendered_sql"]

    # Admin sees the demo project + its dashboard.
    projects = client.get("/api/projects", headers=_auth(token)).json()
    assert any(p["name"] == "SON KPIs" for p in projects)
    pid = next(p["id"] for p in projects if p["name"] == "SON KPIs")
    dashboards = client.get(f"/api/projects/{pid}/dashboards", headers=_auth(token)).json()
    assert any(d["name"] == "Hybrid Cell Overview" for d in dashboards)
