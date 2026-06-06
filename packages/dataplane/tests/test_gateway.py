
import duckdb
import pytest


@pytest.fixture()
def gateway(tmp_path, monkeypatch):
    monkeypatch.setenv("UPM_DATABASE_URL", f"sqlite+pysqlite:///{tmp_path / 'control.sqlite3'}")
    from upm_control_plane import reset_engine
    from upm_control_plane.bootstrap import init_db

    reset_engine()
    init_db()

    from upm_dataplane.gateway import DuckDBGateway

    gw = DuckDBGateway(str(tmp_path / "analytics.duckdb"))
    yield gw, tmp_path
    gw.close()
    reset_engine()


def _write_parquet(path, rows):
    con = duckdb.connect()
    con.execute(
        "CREATE TABLE t (cell_id VARCHAR, ts BIGINT, traffic DOUBLE)"
    )
    con.executemany("INSERT INTO t VALUES (?, ?, ?)", rows)
    p = str(path).replace("\\", "/")
    con.execute(f"COPY t TO '{p}' (FORMAT PARQUET)")
    con.close()


def test_full_then_upsert_is_idempotent(gateway):
    from upm_shared.enums import LoadMode
    from upm_shared.loadcmd import LoadCommand

    gw, tmp = gateway

    p1 = tmp / "run1.parquet"
    _write_parquet(p1, [("A", 1, 10.0), ("B", 1, 20.0)])
    res = gw.load(
        LoadCommand(run_id="r1", table="hybrid_cs_cell", landing_path=str(p1), load_mode=LoadMode.FULL)
    )
    assert res.row_count == 2
    assert res.table_version == 1

    # Upsert overlapping + new keys; replaying the same file must not duplicate.
    p2 = tmp / "run2.parquet"
    _write_parquet(p2, [("B", 1, 25.0), ("C", 2, 30.0)])
    cmd = LoadCommand(
        run_id="r2",
        table="hybrid_cs_cell",
        landing_path=str(p2),
        load_mode=LoadMode.UPSERT,
        key_columns=["cell_id", "ts"],
        watermark_value="2",
    )
    gw.load(cmd)
    assert gw.row_count("hybrid_cs_cell") == 3  # A, B(updated), C

    # Replay the exact same upsert => still 3 rows (idempotent).
    gw.load(cmd)
    assert gw.row_count("hybrid_cs_cell") == 3

    cols, rows = gw.execute_read(
        'SELECT "cell_id", "traffic" FROM "hybrid_cs_cell" WHERE "cell_id" = ?', ["B"]
    )
    assert rows == [{"cell_id": "B", "traffic": 25.0}]


def test_registry_updated(gateway):
    from upm_control_plane import session_scope
    from upm_control_plane.models import TableRegistry
    from upm_shared.enums import LoadMode
    from upm_shared.loadcmd import LoadCommand

    gw, tmp = gateway
    p = tmp / "r.parquet"
    _write_parquet(p, [("A", 1, 10.0)])
    gw.load(LoadCommand(run_id="r", table="t1", landing_path=str(p), load_mode=LoadMode.FULL))

    with session_scope() as s:
        reg = s.get(TableRegistry, "t1")
        assert reg.row_count == 1
        assert reg.last_load_status == "success"
        assert reg.table_version == 1
        assert "cell_id" in reg.schema_json
