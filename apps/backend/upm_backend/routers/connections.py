"""Connection registry (§4) — Airflow-like saved RDBMS connections.

Credentials are encrypted at rest (control_plane.crypto) and never returned. Test runs a
lightweight probe. Builders (job:author) manage connections to use them as job sources.
"""

from __future__ import annotations

import time

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from upm_control_plane.crypto import decrypt, encrypt
from upm_control_plane.models import Connection
from upm_shared.connections import (
    ConnectionIn,
    ConnectionOut,
    ConnectionTestResult,
    build_sqlalchemy_url,
)
from upm_shared.enums import ConnectionKind

from upm_backend.audit import record_audit
from upm_backend.db import get_session
from upm_backend.deps import UserContext, require_cap

router = APIRouter(tags=["connections"], prefix="/connections")

# Oracle needs FROM DUAL; everyone else accepts a bare SELECT 1.
_PROBE = {ConnectionKind.ORACLE: "SELECT 1 FROM DUAL"}


def _out(c: Connection) -> ConnectionOut:
    return ConnectionOut(
        id=c.id, name=c.name, kind=ConnectionKind(c.kind), host=c.host, port=c.port,
        database=c.database, username=c.username,
        has_password=bool(c.encrypted_password or c.encrypted_url), extra=c.extra or {},
        created_at=c.created_at,
    )


def _url_for(c: Connection) -> str:
    return build_sqlalchemy_url(
        ConnectionKind(c.kind), host=c.host, port=c.port, database=c.database,
        username=c.username, password=decrypt(c.encrypted_password),
        extra=c.extra, generic_url=decrypt(c.encrypted_url),
    )


def _url_for_in(body: ConnectionIn) -> str:
    return build_sqlalchemy_url(
        body.kind, host=body.host, port=body.port, database=body.database,
        username=body.username, password=body.password, extra=body.extra,
        generic_url=body.sqlalchemy_url,
    )


def _run_probe(url: str, kind: ConnectionKind) -> ConnectionTestResult:
    from sqlalchemy import create_engine, text

    started = time.time()
    try:
        engine = create_engine(url, connect_args={}, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text(_PROBE.get(kind, "SELECT 1")))
        engine.dispose()
    except Exception as e:  # noqa: BLE001 - report any driver/network error to the user
        return ConnectionTestResult(ok=False, message=str(e)[:500])
    return ConnectionTestResult(
        ok=True, message="connection ok", latency_ms=int((time.time() - started) * 1000)
    )


@router.get("", response_model=list[ConnectionOut])
def list_connections(
    _: UserContext = Depends(require_cap("job:author")),
    session: Session = Depends(get_session),
) -> list[ConnectionOut]:
    return [_out(c) for c in session.query(Connection).order_by(Connection.name).all()]


@router.post("", response_model=ConnectionOut, status_code=status.HTTP_201_CREATED)
def create_connection(
    body: ConnectionIn,
    ctx: UserContext = Depends(require_cap("job:author")),
    session: Session = Depends(get_session),
) -> ConnectionOut:
    if session.query(Connection).filter(Connection.name == body.name).first():
        raise HTTPException(status.HTTP_409_CONFLICT, "connection name already exists")
    c = Connection(
        name=body.name, kind=body.kind.value, host=body.host, port=body.port,
        database=body.database, username=body.username,
        encrypted_password=encrypt(body.password),
        encrypted_url=encrypt(body.sqlalchemy_url),
        extra=body.extra or {}, created_by=ctx.user.id,
    )
    session.add(c)
    session.flush()
    record_audit(session, actor_id=ctx.user.id, action="create", entity_type="connection",
                 entity_id=c.id)
    return _out(c)


@router.post("/test", response_model=ConnectionTestResult)
def test_unsaved(
    body: ConnectionIn,
    _: UserContext = Depends(require_cap("job:author")),
) -> ConnectionTestResult:
    try:
        url = _url_for_in(body)
    except ValueError as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(e))
    return _run_probe(url, body.kind)


@router.get("/{conn_id}", response_model=ConnectionOut)
def get_connection(
    conn_id: int,
    _: UserContext = Depends(require_cap("job:author")),
    session: Session = Depends(get_session),
) -> ConnectionOut:
    c = session.get(Connection, conn_id)
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "connection not found")
    return _out(c)


@router.put("/{conn_id}", response_model=ConnectionOut)
def update_connection(
    conn_id: int,
    body: ConnectionIn,
    ctx: UserContext = Depends(require_cap("job:author")),
    session: Session = Depends(get_session),
) -> ConnectionOut:
    c = session.get(Connection, conn_id)
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "connection not found")
    c.name, c.kind = body.name, body.kind.value
    c.host, c.port, c.database, c.username = body.host, body.port, body.database, body.username
    c.extra = body.extra or {}
    # Only replace secrets when a new value is supplied (blank = keep existing).
    if body.password is not None:
        c.encrypted_password = encrypt(body.password)
    if body.sqlalchemy_url is not None:
        c.encrypted_url = encrypt(body.sqlalchemy_url)
    record_audit(session, actor_id=ctx.user.id, action="update", entity_type="connection",
                 entity_id=c.id)
    return _out(c)


@router.delete("/{conn_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_connection(
    conn_id: int,
    ctx: UserContext = Depends(require_cap("job:author")),
    session: Session = Depends(get_session),
) -> None:
    c = session.get(Connection, conn_id)
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "connection not found")
    record_audit(session, actor_id=ctx.user.id, action="delete", entity_type="connection",
                 entity_id=c.id)
    session.delete(c)


@router.post("/{conn_id}/test", response_model=ConnectionTestResult)
def test_saved(
    conn_id: int,
    _: UserContext = Depends(require_cap("job:author")),
    session: Session = Depends(get_session),
) -> ConnectionTestResult:
    c = session.get(Connection, conn_id)
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "connection not found")
    return _run_probe(_url_for(c), ConnectionKind(c.kind))


@router.get("/{conn_id}/tables")
def list_tables(
    conn_id: int,
    schema: str | None = None,
    _: UserContext = Depends(require_cap("job:author")),
    session: Session = Depends(get_session),
) -> dict:
    from sqlalchemy import create_engine, inspect

    c = session.get(Connection, conn_id)
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "connection not found")
    try:
        engine = create_engine(_url_for(c))
        insp = inspect(engine)
        schemas = insp.get_schema_names()
        tables = insp.get_table_names(schema=schema)
        engine.dispose()
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"introspection failed: {e}")
    return {"schemas": schemas, "tables": tables}


@router.post("/{conn_id}/infer")
def infer_table(
    conn_id: int,
    body: dict,
    _: UserContext = Depends(require_cap("job:author")),
    session: Session = Depends(get_session),
) -> dict:
    from upm_ingestion.inference import infer_connection

    c = session.get(Connection, conn_id)
    if c is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "connection not found")
    try:
        schema = infer_connection(
            _url_for(c), table=body.get("table"), schema=body.get("schema"),
            sql=body.get("sql"),
        )
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"inference failed: {e}")
    return schema.model_dump()
