"""Translate between the JobDefinition contract and the job_configs row (§8).

Lives in the control plane because it bridges the ORM model and the shared contract;
both the backend and the ingestion worker import it (avoids a backend<->ingestion cycle).
"""

from __future__ import annotations

from upm_shared.enums import LoadMode
from upm_shared.jobs import (
    JobDefinition,
    JobGuards,
    JobSource,
    Retention,
    Schedule,
    Watermark,
)

from upm_control_plane.models import JobConfig


def definition_to_kwargs(jd: JobDefinition, *, created_by: int | None = None) -> dict:
    return {
        "name": jd.name,
        "source_schema": jd.source.schema_name,
        "source_table": jd.source.table,
        "query_definition": jd.source.model_dump(by_alias=True, mode="json"),
        "target_table": jd.target_table,
        "schedule": jd.schedule.model_dump(mode="json"),
        "load_mode": jd.load_mode.value,
        "watermark_column": jd.watermark.column if jd.watermark else None,
        "key_columns": list(jd.key_columns),
        "retention": jd.retention.model_dump(mode="json"),
        "guards": jd.guards.model_dump(mode="json"),
        "is_enabled": jd.is_enabled,
    }


def row_to_definition(row: JobConfig) -> JobDefinition:
    source = JobSource.model_validate(row.query_definition)
    watermark = Watermark(column=row.watermark_column) if row.watermark_column else None
    return JobDefinition(
        name=row.name,
        source=source,
        target_table=row.target_table,
        schedule=Schedule.model_validate(row.schedule),
        load_mode=LoadMode(row.load_mode),
        watermark=watermark,
        key_columns=list(row.key_columns or []),
        retention=Retention.model_validate(row.retention) if row.retention else Retention(),
        guards=JobGuards.model_validate(row.guards) if row.guards else JobGuards(),
        is_enabled=row.is_enabled,
    )
