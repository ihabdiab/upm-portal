"""Redis load-command consumer (prod). Runs inside the backend — the sole DuckDB owner.

Workers push LoadCommands; this single-threaded consumer applies them serially through
the Gateway, completing the matching `job_runs` row. Keeping the consumer here (not in a
worker) is what preserves the one-writer invariant (§9.1).
"""

from __future__ import annotations

import logging
import threading
from datetime import UTC, datetime

from upm_control_plane import session_scope
from upm_control_plane.models import JobRun
from upm_shared.constants import LOAD_QUEUE
from upm_shared.loadcmd import LoadCommand

log = logging.getLogger("upm.loadconsumer")


class LoadConsumer:
    def __init__(self, gateway, redis_client) -> None:
        self._gw = gateway
        self._r = redis_client
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._loop, name="load-consumer", daemon=True)
        self._thread.start()
        log.info("load consumer started on queue %s", LOAD_QUEUE)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                item = self._r.brpop(LOAD_QUEUE, timeout=1)
            except Exception:  # noqa: BLE001 - transient redis errors shouldn't kill the loop
                log.exception("redis brpop failed")
                continue
            if not item:
                continue
            _, raw = item
            try:
                cmd = LoadCommand.model_validate_json(raw)
            except Exception:  # noqa: BLE001
                log.exception("bad load command: %s", raw)
                continue
            self._apply(cmd)

    def _apply(self, cmd: LoadCommand) -> None:
        try:
            result = self._gw.load(cmd)
            self._complete_run(cmd, rows_written=result.rows_written, ok=True)
            log.info("loaded %s v%s (%s rows)", cmd.table, result.table_version, result.row_count)
        except Exception as e:  # noqa: BLE001
            log.exception("load failed for %s", cmd.table)
            self._complete_run(cmd, rows_written=0, ok=False, error=str(e))

    @staticmethod
    def _complete_run(cmd: LoadCommand, *, rows_written: int, ok: bool, error: str | None = None):
        if not (cmd.run_id and cmd.run_id.isdigit()):
            return
        with session_scope() as session:
            run = session.get(JobRun, int(cmd.run_id))
            if run is None:
                return
            run.status = "success" if ok else "failed"
            run.finished_at = datetime.now(UTC)
            run.rows_written = rows_written
            if error:
                run.error = error
