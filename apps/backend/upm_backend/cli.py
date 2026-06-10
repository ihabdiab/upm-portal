"""`upm` CLI — init DB, seed the demo, run a job inline, or run the whole demo pipeline.

In dev these all run in one process that owns DuckDB, so they are safe to use while the
API server is stopped. Start the API afterwards to read the loaded data.
"""

from __future__ import annotations

import argparse
import json

from upm_backend.config import get_settings
from upm_backend.runtime import apply_runtime_env


def _init_schema() -> None:
    from upm_control_plane import session_scope
    from upm_control_plane.bootstrap import init_db, seed_rbac

    init_db()
    with session_scope() as session:
        seed_rbac(session)


def cmd_init_db(_args: argparse.Namespace) -> None:
    apply_runtime_env(get_settings())
    _init_schema()
    print("control plane initialized + RBAC seeded")


def cmd_seed(_args: argparse.Namespace) -> None:
    apply_runtime_env(get_settings())
    _init_schema()
    from upm_control_plane import session_scope

    from upm_backend.seed import seed_demo

    with session_scope() as session:
        info = seed_demo(session)
    print(json.dumps(info, indent=2))


def cmd_run_job(args: argparse.Namespace) -> None:
    apply_runtime_env(get_settings())
    from upm_dataplane import get_gateway
    from upm_ingestion.orchestrator import resolve_job_id, run_job_inline

    gw = get_gateway()
    try:
        result = run_job_inline(resolve_job_id(args.job), gateway=gw)
    finally:
        gw.close()
    print(json.dumps(result, indent=2, default=str))


def cmd_demo(_args: argparse.Namespace) -> None:
    apply_runtime_env(get_settings())
    _init_schema()
    from upm_control_plane import session_scope
    from upm_dataplane import get_gateway
    from upm_ingestion.orchestrator import resolve_job_id, run_job_inline

    from upm_backend.seed import seed_demo

    with session_scope() as session:
        info = seed_demo(session)

    gw = get_gateway()
    try:
        for name in info["jobs"]:
            result = run_job_inline(resolve_job_id(name), gateway=gw)
            print(f"  loaded {name}: {result['rows_written']} rows -> {result['table']}")
    finally:
        gw.close()

    print("\nDemo ready. Start the API and log in:")
    for u in info["users"]:
        print(f"  {u['role']:8} {u['email']} / {u['password']}")


def cmd_load_csv(args: argparse.Namespace) -> None:
    """Ingest a CSV file end-to-end via the CSV source (upload record + job + inline run)."""
    apply_runtime_env(get_settings())
    _init_schema()
    from upm_control_plane import session_scope
    from upm_dataplane import get_gateway
    from upm_ingestion.orchestrator import run_job_inline

    from upm_backend.realdata import create_csv_job

    with session_scope() as session:
        job_id = create_csv_job(
            session, path=args.path, table=args.table, job_name=args.name
        )
    gw = get_gateway()
    try:
        result = run_job_inline(job_id, gateway=gw)
    finally:
        gw.close()
    print(json.dumps(result, indent=2, default=str))


def cmd_cs_demo(args: argparse.Namespace) -> None:
    """Real-data demo: users/project + ingest the CS sample CSV + build a CS dashboard."""
    apply_runtime_env(get_settings())
    _init_schema()
    from upm_control_plane import session_scope
    from upm_dataplane import get_gateway
    from upm_ingestion.orchestrator import run_job_inline

    from upm_backend.realdata import build_cs_dashboard, create_csv_job
    from upm_backend.seed import seed_users_and_project

    with session_scope() as session:
        users, project = seed_users_and_project(session)
        admin_id = users["admin@upm.com"].id
        job_id = create_csv_job(
            session, path=args.path, table=args.table, job_name="load_cs_cell",
            created_by=admin_id,
        )
        build_cs_dashboard(session, project.id, admin_id, args.table)

    gw = get_gateway()
    try:
        result = run_job_inline(job_id, gateway=gw)
    finally:
        gw.close()
    print(f"loaded {result['rows_written']} rows -> {result['table']} (v{result['table_version']})")
    print("Real-CS dashboard built. Start the API and log in as admin@upm.com / admin12345")


def main() -> None:
    parser = argparse.ArgumentParser(prog="upm", description="UPM platform CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="create tables + seed RBAC").set_defaults(func=cmd_init_db)
    sub.add_parser("seed", help="seed demo users/project/jobs/dashboard").set_defaults(func=cmd_seed)

    run = sub.add_parser("run-job", help="extract+load a job inline (dev)")
    run.add_argument("job", help="job name or id")
    run.set_defaults(func=cmd_run_job)

    sub.add_parser("demo", help="init + seed + load both synthetic demo jobs").set_defaults(
        func=cmd_demo
    )

    lc = sub.add_parser("load-csv", help="ingest a CSV file (upload + job + run) inline")
    lc.add_argument("path", help="path to the CSV file")
    lc.add_argument("table", help="target DuckDB table name")
    lc.add_argument("--name", default=None, help="job name (default load_<table>)")
    lc.set_defaults(func=cmd_load_csv)

    cs = sub.add_parser("cs-demo", help="real-data demo: ingest the CS sample CSV + dashboard")
    cs.add_argument(
        "--path",
        default="oracle-sample-data/CS+and+PS+cell+samples/CS_CELL_SAMPLE.csv",
        help="path to CS_CELL_SAMPLE.csv",
    )
    cs.add_argument("--table", default="cs_cell")
    cs.set_defaults(func=cmd_cs_demo)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
