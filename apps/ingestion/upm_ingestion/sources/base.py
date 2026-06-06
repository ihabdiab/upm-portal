"""Source abstraction. A Source extracts a watermarked delta to a Parquet file and can
return a bounded preview. Oracle is the real one; Synthetic backs the no-Oracle path."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from upm_shared.jobs import JobDefinition


@dataclass
class ExtractResult:
    landing_path: str
    rows_read: int
    new_watermark: str | None
    columns: list[str]


class Source(Protocol):
    def extract(
        self,
        job: JobDefinition,
        *,
        watermark_value: str | None,
        landing_path: str,
        row_cap: int,
    ) -> ExtractResult: ...

    def preview(self, job: JobDefinition, *, n: int = 20) -> list[dict]: ...
