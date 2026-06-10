"""Schema inference engine (§1.2).

CSV inference leans on DuckDB's battle-tested sniffer (delimiter/header/type detection)
via sniff_csv + read_csv_auto. Connection inference uses SQLAlchemy reflection. Inferred
schema is returned for user review/correction before the final load.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import duckdb
from upm_shared.inference import InferredColumn, InferredSchema


def _q(path: str) -> str:
    return str(path).replace("\\", "/").replace("'", "''")


def _jsonable(v):
    if isinstance(v, datetime | date):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    return v


def infer_csv(path: str, *, sample_rows: int = 20) -> InferredSchema:
    p = _q(path)
    con = duckdb.connect()
    warnings: list[str] = []
    delimiter = None
    has_header = None
    try:
        try:
            sniff = con.execute(f"FROM sniff_csv('{p}')").fetchone()
            cols = con.execute(f"FROM sniff_csv('{p}')").description
            sniff_map = dict(zip([c[0] for c in cols], sniff, strict=False))
            delimiter = sniff_map.get("Delimiter")
            has_header = sniff_map.get("HasHeader")
        except Exception as e:  # noqa: BLE001 - sniff is best-effort
            warnings.append(f"sniff_csv failed, using auto defaults: {e}")

        described = con.execute(f"DESCRIBE SELECT * FROM read_csv_auto('{p}')").fetchall()
        columns = [
            InferredColumn(name=row[0], type=str(row[1]), nullable=(str(row[2]).upper() != "NO"))
            for row in described
        ]

        sample = con.execute(
            f"SELECT * FROM read_csv_auto('{p}') LIMIT {int(sample_rows)}"
        )
        names = [d[0] for d in sample.description]
        rows = [
            {n: _jsonable(v) for n, v in zip(names, r, strict=False)}
            for r in sample.fetchall()
        ]
        try:
            row_estimate = int(
                con.execute(f"SELECT count(*) FROM read_csv_auto('{p}')").fetchone()[0]
            )
        except Exception:  # noqa: BLE001
            row_estimate = None
    finally:
        con.close()

    if not columns:
        warnings.append("no columns detected")
    return InferredSchema(
        columns=columns,
        delimiter=delimiter,
        has_header=has_header,
        row_estimate=row_estimate,
        sample_rows=rows,
        warnings=warnings,
    )


def infer_connection(
    url: str, *, table: str | None = None, schema: str | None = None, sql: str | None = None,
    sample_rows: int = 20,
) -> InferredSchema:
    from sqlalchemy import create_engine, inspect, text

    engine = create_engine(url)
    warnings: list[str] = []
    try:
        if sql:
            with engine.connect() as conn:
                result = conn.execute(text(sql))
                names = list(result.keys())
                rows = [
                    {n: _jsonable(v) for n, v in zip(names, r, strict=False)}
                    for r in result.fetchmany(sample_rows)
                ]
            columns = [InferredColumn(name=n, type="VARCHAR") for n in names]
            warnings.append("types from a raw query are reported as VARCHAR; verify before load")
            return InferredSchema(columns=columns, sample_rows=rows, warnings=warnings)

        if not table:
            raise ValueError("connection inference requires a table or sql")
        insp = inspect(engine)
        cols = insp.get_columns(table, schema=schema)
        columns = [
            InferredColumn(name=c["name"], type=str(c["type"]), nullable=bool(c.get("nullable", True)))
            for c in cols
        ]
        ident = f"{schema + '.' if schema else ''}{table}"
        with engine.connect() as conn:
            result = conn.execute(text(f"SELECT * FROM {ident}"))
            names = list(result.keys())
            rows = [
                {n: _jsonable(v) for n, v in zip(names, r, strict=False)}
                for r in result.fetchmany(sample_rows)
            ]
        return InferredSchema(columns=columns, sample_rows=rows, warnings=warnings)
    finally:
        engine.dispose()
