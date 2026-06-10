"""Phase 2 API tests: connection registry + CSV upload -> job -> run -> query."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("UPM_DATABASE_URL", f"sqlite+pysqlite:///{tmp_path / 'control.sqlite3'}")
    monkeypatch.setenv("UPM_DUCKDB_PATH", str(tmp_path / "analytics.duckdb"))
    monkeypatch.setenv("UPM_LANDING_DIR", str(tmp_path / "landing"))
    monkeypatch.setenv("UPM_UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("UPM_SECRET_KEY", "phase2-test-key")
    monkeypatch.delenv("UPM_REDIS_URL", raising=False)

    from upm_backend.config import get_settings
    from upm_control_plane import reset_engine, session_scope
    from upm_control_plane.bootstrap import init_db
    from upm_control_plane.crypto import reset_cache
    from upm_dataplane import reset_gateway

    get_settings.cache_clear()
    reset_engine()
    reset_gateway()
    reset_cache()

    from upm_backend.seed import seed_users_and_project

    init_db()
    with session_scope() as session:
        seed_users_and_project(session)

    from upm_backend.main import create_app

    with TestClient(create_app()) as c:
        yield c

    reset_engine()
    reset_gateway()
    get_settings.cache_clear()


def _auth(client, email="builder@upm.com", password="builder12345"):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_connection_crud_and_test(client):
    h = _auth(client)
    # Generic connection backed by SQLite so the test probe actually connects.
    body = {"name": "scratch", "kind": "generic", "sqlalchemy_url": "sqlite://"}
    r = client.post("/api/connections", headers=h, json=body)
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    assert r.json()["has_password"] is True  # url stored encrypted

    # Saved-connection probe succeeds.
    t = client.post(f"/api/connections/{cid}/test", headers=h)
    assert t.status_code == 200, t.text
    assert t.json()["ok"] is True

    assert any(c["id"] == cid for c in client.get("/api/connections", headers=h).json())

    # Viewer may not manage connections.
    hv = _auth(client, "viewer@upm.com", "viewer12345")
    assert client.get("/api/connections", headers=hv).status_code == 403

    assert client.delete(f"/api/connections/{cid}", headers=h).status_code == 204


def test_csv_upload_job_run_query(client):
    h = _auth(client)
    csv = b"site,region,traffic\nA,North,10\nB,South,20\nC,North,30\n"

    up = client.post(
        "/api/ingest/uploads", headers=h,
        files={"file": ("kpi.csv", csv, "text/csv")},
    )
    assert up.status_code == 201, up.text
    upload = up.json()
    assert upload["schema"]["row_estimate"] == 3
    cols = {c["name"] for c in upload["schema"]["columns"]}
    assert cols == {"site", "region", "traffic"}

    # Create a CSV job from the upload and run it.
    job_body = {
        "name": "load_kpi_csv",
        "source": {"kind": "csv", "upload_id": upload["id"], "columns": []},
        "target_table": "kpi_csv",
        "schedule": {"every": "1d"},
        "load_mode": "full",
    }
    jr = client.post("/api/jobs", headers=h, json=job_body)
    assert jr.status_code == 201, jr.text
    job_id = jr.json()["id"]

    run = client.post(f"/api/jobs/{job_id}/run", headers=h)
    assert run.status_code == 200, run.text
    assert run.json()["rows_written"] == 3

    # The new table is now in the catalog and queryable.
    tables = {t["table_name"] for t in client.get("/api/catalog/tables", headers=h).json()}
    assert "kpi_csv" in tables

    q = client.post("/api/query", headers=h, json={
        "table": "kpi_csv",
        "aggregations": [{"fn": "sum", "col": "traffic", "as": "traffic"}],
        "groupBy": ["region"],
        "sort": [{"col": "region", "dir": "asc"}],
    })
    assert q.status_code == 200, q.text
    rows = {r["region"]: r["traffic"] for r in q.json()["rows"]}
    assert rows == {"North": 40, "South": 20}


def test_csv_preview_without_saving(client):
    h = _auth(client)
    csv = b"a,b\n1,x\n2,y\n"
    up = client.post("/api/ingest/uploads", headers=h, files={"file": ("p.csv", csv, "text/csv")})
    upload_id = up.json()["id"]

    body = {
        "name": "preview_only",
        "source": {"kind": "csv", "upload_id": upload_id, "columns": []},
        "target_table": "preview_only",
        "schedule": {"every": "1d"},
        "load_mode": "full",
    }
    p = client.post("/api/jobs/preview", headers=h, json=body)
    assert p.status_code == 200, p.text
    assert p.json()["count"] == 2
