# ADR-004 — Scheduler: Celery + Redis, schedules in the DB via RedBeat

**Status:** Accepted

## Decision
Celery workers + Celery Beat with the RedBeat scheduler. Schedules are derived from
`job_configs` rows (config-as-data) and stored in Redis — **no DAG files**.

## Why
Reuses production Celery experience; gives retries/backoff/DLQ and a worker pool for free;
RedBeat lets schedules be edited at runtime without redeploys.

## Rejected
Airflow (heavy; DAG-file model contradicts config-as-data). APScheduler (single-process; weak
distributed retry/DLQ).

## Trade-off
You operate a beat + worker. Acceptable. `apps/scheduler` syncs `job_configs` → RedBeat entries.
