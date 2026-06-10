from upm_shared.connections import build_sqlalchemy_url
from upm_shared.enums import ConnectionKind


def test_crypto_roundtrip(monkeypatch):
    monkeypatch.setenv("UPM_SECRET_KEY", "unit-test-key")
    from upm_control_plane.crypto import decrypt, encrypt, reset_cache

    reset_cache()
    token = encrypt("hunter2")
    assert token != "hunter2"
    assert decrypt(token) == "hunter2"
    assert encrypt(None) is None and decrypt(None) is None
    reset_cache()


def test_build_url_postgres():
    url = build_sqlalchemy_url(
        ConnectionKind.POSTGRESQL, host="db", port=5432, database="kpi",
        username="u", password="p@ss/word", extra={},
    )
    assert url.startswith("postgresql+psycopg://u:")
    assert "@db:5432/kpi" in url
    # password special chars must be percent-encoded
    assert "p%40ss%2Fword" in url


def test_build_url_oracle_service_name():
    url = build_sqlalchemy_url(
        ConnectionKind.ORACLE, host="ora", port=1521, database="ORCLPDB1",
        username="ro", password="x", extra={},
    )
    assert url.startswith("oracle+oracledb://ro:x@ora:1521/?service_name=ORCLPDB1")


def test_build_url_generic_passthrough():
    raw = "duckdb:///:memory:"
    url = build_sqlalchemy_url(
        ConnectionKind.GENERIC, host=None, port=None, database=None,
        username=None, password=None, generic_url=raw,
    )
    assert url == raw
