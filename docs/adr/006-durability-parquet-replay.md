# ADR-006 — Durability: Parquet replay + scheduled EXPORT

**Status:** Accepted

## Decision
Retain landing Parquet for N days (default 30) as a replay log; rebuild any table — or the whole
store — from Parquet **without Oracle**. Additionally take periodic `EXPORT DATABASE` snapshots.

## Why
The analytics store is the system of record for the read path; it must survive a WAN/Oracle
outage and be recoverable locally. Rebuilding from Parquet is exactly the recovery needed when
Oracle is unreachable.

## Trade-off / revisit
Disk for retained Parquet + snapshots. See the [recovery runbook](../runbook-recovery.md).
