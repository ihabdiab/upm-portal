"""upm-dataplane — the DuckDB Gateway.

The ONE process-local owner of the DuckDB file. Serializes writes (staging -> atomic
swap), fans out read-only queries, and keeps `table_registry` (freshness) in lockstep.
In the MVP this runs in-process inside the backend; the interface is unchanged when it is
later lifted into a standalone single-instance service (ADR-002).
"""

from upm_dataplane.gateway import DuckDBGateway, get_gateway, reset_gateway

__all__ = ["DuckDBGateway", "get_gateway", "reset_gateway"]
