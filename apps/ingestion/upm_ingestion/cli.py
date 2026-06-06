"""Standalone ingestion CLI (mostly for debugging a worker host)."""

from __future__ import annotations

import argparse
import json
import os

from upm_ingestion.orchestrator import resolve_job_id, run_job_inline


def cmd_run(args: argparse.Namespace) -> None:
    from upm_dataplane import get_gateway

    gw = get_gateway()
    try:
        result = run_job_inline(resolve_job_id(args.job), gateway=gw)
    finally:
        gw.close()
    print(json.dumps(result, indent=2, default=str))


def cmd_enqueue(args: argparse.Namespace) -> None:
    import redis as redislib

    from upm_ingestion.orchestrator import extract_and_enqueue

    client = redislib.from_url(os.environ.get("UPM_REDIS_URL", "redis://localhost:6379/0"))
    result = extract_and_enqueue(resolve_job_id(args.job), client)
    print(json.dumps(result, indent=2, default=str))


def main() -> None:
    parser = argparse.ArgumentParser(prog="upm-ingest")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="extract + load inline through the Gateway (dev)")
    run.add_argument("job")
    run.set_defaults(func=cmd_run)

    enq = sub.add_parser("enqueue", help="extract + push a LoadCommand to Redis (worker path)")
    enq.add_argument("job")
    enq.set_defaults(func=cmd_enqueue)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
