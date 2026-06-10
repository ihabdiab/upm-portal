"""Connection registry contracts (§4) + SQLAlchemy URL builder.

Passwords are never returned to clients (only `has_password`). The URL builder is used by
the backend (test connection) and the worker (extract) so they agree on driver mapping.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from upm_shared.enums import ConnectionKind

# Default ports per kind — used to prefill the form and to fall back when port is omitted.
DEFAULT_PORTS: dict[ConnectionKind, int] = {
    ConnectionKind.ORACLE: 1521,
    ConnectionKind.POSTGRESQL: 5432,
    ConnectionKind.MYSQL: 3306,
    ConnectionKind.MSSQL: 1433,
}

# SQLAlchemy driver per kind (all have wheels; portable in the Compose image).
_DRIVER: dict[ConnectionKind, str] = {
    ConnectionKind.ORACLE: "oracle+oracledb",
    ConnectionKind.POSTGRESQL: "postgresql+psycopg",
    ConnectionKind.MYSQL: "mysql+pymysql",
    ConnectionKind.MSSQL: "mssql+pymssql",
}


class ConnectionIn(BaseModel):
    name: str
    kind: ConnectionKind
    host: str | None = None
    port: int | None = None
    database: str | None = None  # Oracle: service name; others: db name
    username: str | None = None
    password: str | None = None
    extra: dict = Field(default_factory=dict)
    sqlalchemy_url: str | None = None  # for kind=generic (may embed credentials)


class ConnectionOut(BaseModel):
    id: int
    name: str
    kind: ConnectionKind
    host: str | None = None
    port: int | None = None
    database: str | None = None
    username: str | None = None
    has_password: bool = False
    extra: dict = Field(default_factory=dict)
    created_at: datetime | None = None


class ConnectionTestResult(BaseModel):
    ok: bool
    message: str
    latency_ms: int | None = None


def build_sqlalchemy_url(
    kind: ConnectionKind,
    *,
    host: str | None,
    port: int | None,
    database: str | None,
    username: str | None,
    password: str | None,
    extra: dict | None = None,
    generic_url: str | None = None,
) -> str:
    from urllib.parse import quote_plus

    if kind is ConnectionKind.GENERIC:
        if not generic_url:
            raise ValueError("generic connection requires a sqlalchemy_url")
        return generic_url

    driver = _DRIVER[kind]
    user = quote_plus(username or "")
    pw = quote_plus(password or "")
    auth = f"{user}:{pw}@" if user else ""
    p = port or DEFAULT_PORTS.get(kind)
    netloc = f"{host or 'localhost'}:{p}" if p else (host or "localhost")

    if kind is ConnectionKind.ORACLE:
        # Oracle service-name form.
        return f"{driver}://{auth}{netloc}/?service_name={database or ''}"
    return f"{driver}://{auth}{netloc}/{database or ''}"
