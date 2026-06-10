"""Schema inference contracts (§1.2). Inferred schema is shown to the user for
review/correction before the final load, and stored for later use in job building.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class InferredColumn(BaseModel):
    name: str
    type: str            # DuckDB type name (BIGINT, DOUBLE, VARCHAR, TIMESTAMP, BOOLEAN...)
    nullable: bool = True
    include: bool = True  # user can deselect columns before load


class InferredSchema(BaseModel):
    columns: list[InferredColumn] = Field(default_factory=list)
    delimiter: str | None = None
    has_header: bool | None = None
    row_estimate: int | None = None
    sample_rows: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class UploadOut(BaseModel):
    id: str
    original_filename: str
    suggested_table: str
    schema_: InferredSchema = Field(alias="schema")
    created_at: Any | None = None

    model_config = {"populate_by_name": True}
