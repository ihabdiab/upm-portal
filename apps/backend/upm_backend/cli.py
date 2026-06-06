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


def main() -> None:
    parser = argparse.ArgumentParser(prog="upm", description="UPM platform CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="create tables + seed RBAC").set_defaults(func=cmd_init_db)
    sub.add_parser("seed", help="seed demo users/project/jobs/dashboard").set_defaults(func=cmd_seed)

    run = sub.add_parser("run-job", help="extract+load a job inline (dev)")
    run.add_argument("job", help="job name or id")
    run.set_defaults(func=cmd_run_job)

    sub.add_parser("demo", help="init + seed + load both demo jobs").set_defaults(func=cmd_demo)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
