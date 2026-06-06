"""`upm-scheduler sync` — push job_configs schedules into RedBeat."""

from __future__ import annotations

import argparse
import json


def cmd_sync(_args: argparse.Namespace) -> None:
    from upm_scheduler.sync import sync_schedules

    print(json.dumps(sync_schedules(), indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(prog="upm-scheduler")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("sync", help="sync job_configs -> RedBeat").set_defaults(func=cmd_sync)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
