"""Real-data ingestion helpers (§2, §8): load the CS sample CSV through the same CSV
ingestion path the UI uses, then build a dashboard over the real KPIs.

This dogfoods Option B end-to-end and replaces the synthetic dummy data with the actual
circuit-switched cell dataset.
"""

from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy.orm import Session
from upm_control_plane.models import Dashboard, JobConfig, TableRegistry, Upload
from upm_ingestion.inference import infer_csv
from upm_shared.enums import LoadMode, SourceKind
from upm_shared.jobs import JobDefinition, JobSource, Schedule

from upm_backend.jobmap import definition_to_kwargs


def create_csv_job(
    session: Session,
    *,
    path: str,
    table: str,
    job_name: str | None = None,
    columns: list[str] | None = None,
    load_mode: LoadMode = LoadMode.FULL,
    key_columns: list[str] | None = None,
    created_by: int | None = None,
) -> int:
    """Register an Upload (pointing at an existing file) + a CSV job. Returns job id."""
    abspath = str(Path(path).resolve())
    if not Path(abspath).exists():
        raise FileNotFoundError(abspath)

    inferred = infer_csv(abspath)
    upload_id = str(uuid.uuid4())
    session.add(
        Upload(
            id=upload_id,
            original_filename=Path(abspath).name,
            stored_path=abspath,
            kind="csv",
            delimiter=inferred.delimiter,
            has_header=bool(inferred.has_header) if inferred.has_header is not None else True,
            row_estimate=inferred.row_estimate,
            inferred_schema=inferred.model_dump(),
            suggested_table=table,
            created_by=created_by,
        )
    )
    session.flush()

    jd = JobDefinition(
        name=job_name or f"load_{table}",
        source=JobSource(kind=SourceKind.CSV, upload_id=upload_id, columns=columns or []),
        target_table=table,
        schedule=Schedule(every="1d"),
        load_mode=load_mode,
        key_columns=key_columns or [],
    )
    row = session.query(JobConfig).filter(JobConfig.name == jd.name).one_or_none()
    if row is None:
        row = JobConfig(**definition_to_kwargs(jd, created_by=created_by), created_by=created_by)
        session.add(row)
        session.flush()
    else:
        for k, v in definition_to_kwargs(jd, created_by=created_by).items():
            setattr(row, k, v)
    if session.get(TableRegistry, table) is None:
        session.add(TableRegistry(table_name=table, source_job_id=row.id, is_visible=False))
    return row.id


def _cs_dashboard_def(table: str) -> dict:
    """Aggregation-first dashboard for the real CS snapshot (single date/hour, many cells)."""
    src = {"table": table}
    return {
        "version": 1,
        "layout": {"cols": 12, "rowHeight": 40},
        "widgets": [
            {
                "id": "kpi_traffic_3g", "type": "kpi", "title": "Total CS traffic (3G)",
                "source": src,
                "query": {"table": table,
                          "aggregations": [{"fn": "sum", "col": "TRAFFIC_3G", "as": "value"}]},
                "viz": {"value": "value", "unit": "Erl", "precision": 0},
                "grid": {"x": 0, "y": 0, "w": 3, "h": 3},
            },
            {
                "id": "kpi_calls_3g", "type": "kpi", "title": "Total calls (3G)",
                "source": src,
                "query": {"table": table,
                          "aggregations": [{"fn": "sum", "col": "TOTAL_CALLS_3G", "as": "value"}]},
                "viz": {"value": "value", "precision": 0},
                "grid": {"x": 3, "y": 0, "w": 3, "h": 3},
            },
            {
                "id": "pie_tech", "type": "pie", "title": "Cells by technology",
                "source": src,
                "query": {"table": table, "aggregations": [{"fn": "count", "as": "value"}],
                          "groupBy": ["TECHNOLOGY"], "sort": [{"col": "TECHNOLOGY", "dir": "asc"}]},
                "viz": {"x": "TECHNOLOGY", "y": "value"},
                "grid": {"x": 6, "y": 0, "w": 6, "h": 6},
            },
            {
                "id": "bar_traffic_region", "type": "bar", "title": "CS traffic (3G) by region",
                "source": src,
                "query": {"table": table,
                          "aggregations": [{"fn": "sum", "col": "TRAFFIC_3G", "as": "traffic"}],
                          "groupBy": ["REGION"], "sort": [{"col": "REGION", "dir": "asc"}]},
                "viz": {"x": "REGION", "y": "traffic"},
                "grid": {"x": 0, "y": 3, "w": 6, "h": 6},
            },
            {
                "id": "bar_drops_region", "type": "bar", "title": "Call drops (3G) by region",
                "source": src,
                "query": {"table": table,
                          "aggregations": [{"fn": "sum", "col": "DROP_NUM_3G", "as": "drops"}],
                          "groupBy": ["REGION"], "sort": [{"col": "REGION", "dir": "asc"}]},
                "viz": {"x": "REGION", "y": "drops"},
                "grid": {"x": 6, "y": 6, "w": 6, "h": 6},
            },
            {
                "id": "tbl_governorate", "type": "table", "title": "Traffic & drops by governorate",
                "source": src,
                "query": {"table": table,
                          "aggregations": [
                              {"fn": "sum", "col": "TRAFFIC_3G", "as": "traffic"},
                              {"fn": "sum", "col": "DROP_NUM_3G", "as": "drops"},
                          ],
                          "groupBy": ["GOVERNORATE"],
                          "sort": [{"col": "traffic", "dir": "desc"}], "limit": 25},
                "viz": {},
                "grid": {"x": 0, "y": 9, "w": 12, "h": 7},
            },
        ],
    }


def build_cs_dashboard(session: Session, project_id: int, created_by: int, table: str) -> int:
    name = "CS Cell KPIs (real data)"
    dash = (
        session.query(Dashboard)
        .filter(Dashboard.project_id == project_id, Dashboard.name == name)
        .one_or_none()
    )
    definition = _cs_dashboard_def(table)
    if dash is None:
        dash = Dashboard(project_id=project_id, name=name, definition=definition,
                         version=1, created_by=created_by)
        session.add(dash)
        session.flush()
    else:
        dash.definition = definition
    return dash.id
