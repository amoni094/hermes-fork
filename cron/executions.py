"""Profile-local durable audit ledger for cron execution attempts.

The ledger records what is known about each attempt; it is not a retry queue. Interrupted attempts
become ``unknown`` only after their owner process is proved gone — a start-time reading that fails
to match the claim-time fingerprint is not proof of death. Terminal states are immutable.
"""

from __future__ import annotations

import json
import logging
import math
import os
import sqlite3
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone, UTC
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from hermes_constants import get_hermes_home
from hermes_time import now as _hermes_now
from cron.constants import CLAIM_TTL_INACTIVITY_HEADROOM
from hermes_cli.observability.shared_metrics_gateway import record_cron_finish

logger = logging.getLogger(__name__)


class StaleGenerationError(RuntimeError):
    """Chubby sequencer: reject a write whose generation is no longer current."""


# Optional test override. Production resolves the path at transaction time so dashboard operations
# that temporarily enter another profile cannot leak that profile's records into the import-time
# home.
EXECUTIONS_FILE: Optional[Path] = None
MAX_TERMINAL_EXECUTIONS = 1000
HANDOFF_ADOPTION_GRACE_SECONDS = 30.0
# Floor for the live-owner stale-claim bound (#115692); see _live_owner_stale_after_seconds.
LIVE_OWNER_STALE_CLAIM_FLOOR_SECONDS = 7200.0
_TERMINAL_STATES = ("completed", "failed", "unknown")
_lock = threading.RLock()
_PROCESS_ID = uuid.uuid4().hex
_LOCK_TTL_SECONDS = 300

def _hermes_home_base() -> Path:
    """Resolve the .hermes root even when HERMES_HOME points at a profile."""
    env = os.environ.get("HERMES_HOME", "").strip()
    p = Path(env).expanduser() if env else Path.home() / ".hermes"
    if p.name != ".hermes" and p.parent.name == "profiles":
        return p.parent.parent
    return p


HERMES_HOME = _hermes_home_base()
# ZooKeeper ephemeral-znode analogue (Hunt et al. 2010): presence == liveness.
LOCK_DIR: Path = HERMES_HOME / "profiles" / "fork" / "cron" / ".locks"


def _lock_dir() -> Path:
    """Resolve lock dir at call time so HERMES_HOME / EXECUTIONS_FILE redirects apply.

    Prefer the executions DB's parent (tests monkeypatch EXECUTIONS_FILE).
    Otherwise ``get_hermes_home()/cron/.locks`` — same tree as executions.db.
    """
    if EXECUTIONS_FILE:
        return Path(EXECUTIONS_FILE).parent / ".locks"
    try:
        from hermes_constants import get_hermes_home
        return Path(get_hermes_home()).resolve() / "cron" / ".locks"
    except Exception:
        return LOCK_DIR


def _lock_path(execution_id: str) -> Path:
    safe = str(execution_id).replace("/", "_").replace("\\", "_")
    return _lock_dir() / f"{safe}.lock"


def _parse_iso(stamp: str) -> datetime:
    dt = datetime.fromisoformat(str(stamp))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def create_execution_lock(execution_id: str, pid: int, started_at: str) -> Path:
    """Create an ephemeral lock file for a running execution (mkdir -p LOCK_DIR).

    JSON payload: {execution_id, pid, started_at, expires_at=started_at+300}.
    Analogous to a ZooKeeper ephemeral znode: the lock dies with the process.
    """
    _lock_dir().mkdir(parents=True, exist_ok=True)
    started_dt = _parse_iso(started_at)
    expires_at = (started_dt + timedelta(seconds=_LOCK_TTL_SECONDS)).isoformat()
    payload = {
        "execution_id": str(execution_id),
        "pid": int(pid),
        "started_at": started_at,
        "expires_at": expires_at,
    }
    dest = _lock_path(execution_id)
    tmp = dest.with_suffix(".lock.tmp")
    tmp.write_text(json.dumps(payload), encoding="utf-8")
    os.replace(str(tmp), str(dest))
    return dest


def release_execution_lock(execution_id: str) -> bool:
    """Delete LOCK_DIR/{execution_id}.lock if it exists. True iff deleted."""
    path = _lock_path(execution_id)
    if not path.exists():
        return False
    try:
        path.unlink()
        return True
    except OSError:
        return False


def is_lock_live(execution_id: str) -> bool:
    """True iff the lock file exists and its PID is still alive (os.kill(pid, 0))."""
    path = _lock_path(execution_id)
    if not path.is_file():
        return False
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        pid = int(data["pid"])
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # process exists but is not ours
    except OSError:
        return False


def reap_stale_locks() -> list[str]:
    """Delete lock files whose PID is dead or whose expires_at has passed.

    Expired locks are reaped regardless of PID (TTL session expiry).
    Returns the list of reaped execution_ids.
    """
    reaped: list[str] = []
    lock_dir = _lock_dir()
    if not lock_dir.is_dir():
        return reaped
    now = datetime.now(UTC)
    for path in lock_dir.glob("*.lock"):
        execution_id = path.stem
        expired = False
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            execution_id = str(data.get("execution_id") or execution_id)
            exp = data.get("expires_at")
            if exp:
                exp_dt = _parse_iso(str(exp))
                if now >= exp_dt:
                    expired = True
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            expired = True
        if expired or not is_lock_live(execution_id):
            try:
                path.unlink(missing_ok=True)
                reaped.append(execution_id)
            except OSError:
                pass
    return reaped


def _safe_create_execution_lock(execution_id: str, pid: int, started_at: str) -> None:
    try:
        create_execution_lock(execution_id, pid, started_at)
    except Exception:
        logger.debug("create_execution_lock(%s) failed", execution_id, exc_info=True)


def _safe_release_execution_lock(execution_id: str) -> None:
    if not execution_id:
        return
    try:
        release_execution_lock(execution_id)
    except Exception:
        logger.debug("release_execution_lock(%s) failed", execution_id, exc_info=True)


# --- executions ledger --------------------------------------------------------------------------

def _connect() -> sqlite3.Connection:
    # Late imports: a scheduler daemon that outlives an on-disk upgrade already has the OLD
    # ``hermes_cli.sqlite_util`` / ``cron.jobs`` cached, so new names must be resolved at call time,
    # not at import time (the guarantee cron/ledger.py used to carry, see e24c8499).
    from cron.jobs import _ensure_cron_dir
    from hermes_cli.sqlite_util import open_db

    path = EXECUTIONS_FILE or (get_hermes_home().resolve() / "cron" / "executions.db")
    _ensure_cron_dir(path.parent)
    return open_db(path, db_label="cron/executions.db", synchronous_full=True, initialize=_initialize_schema)



def _compute_duration_s(started_at, finished_at) -> Optional[float]:
    """Wall-clock service time from ISO timestamps; None if either bound is missing."""
    if not started_at or not finished_at:
        return None
    try:
        delta = (_parse_iso(str(finished_at)) - _parse_iso(str(started_at))).total_seconds()
        return max(0.0, float(delta))
    except (TypeError, ValueError, OSError):
        return None


def _initialize_schema(conn: sqlite3.Connection) -> None:
    from hermes_cli.sqlite_util import add_column_if_missing

    conn.execute(
        """CREATE TABLE IF NOT EXISTS executions (
             id TEXT PRIMARY KEY,
             job_id TEXT NOT NULL,
             source TEXT NOT NULL,
             process_id TEXT NOT NULL,
             pid INTEGER NOT NULL,
             process_started_at INTEGER,
             status TEXT NOT NULL CHECK(status IN
               ('claimed','running','completed','failed','unknown')),
             handoff_pending INTEGER NOT NULL DEFAULT 0,
             handoff_started_at REAL,
             claimed_at TEXT NOT NULL,
             started_at TEXT,
             finished_at TEXT,
             error TEXT,
             generation INTEGER NOT NULL DEFAULT 0
           )"""
    )
    add_column_if_missing(
        conn, "executions", "handoff_pending",
        "handoff_pending INTEGER NOT NULL DEFAULT 0",
    )
    add_column_if_missing(
        conn, "executions", "handoff_started_at", "handoff_started_at REAL"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_executions_job_claimed "
        "ON executions(job_id, claimed_at DESC, id DESC)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_executions_status_claimed "
        "ON executions(status, claimed_at DESC, id DESC)"
    )
    add_column_if_missing(conn, "executions", "delivery_outcome", "delivery_outcome TEXT")
    add_column_if_missing(conn, "executions", "scheduled_instant", "scheduled_instant TEXT")
    add_column_if_missing(conn, "executions", "progress_at", "progress_at TEXT")
    add_column_if_missing(
        conn, "executions", "generation", "generation INTEGER NOT NULL DEFAULT 0"
    )
    add_column_if_missing(conn, "executions", "duration_s", "duration_s REAL")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_executions_occurrence "
        "ON executions(job_id, scheduled_instant) WHERE status='completed'"
    )


@contextmanager
def _transaction() -> Iterator[sqlite3.Connection]:
    from hermes_cli.sqlite_util import transaction

    with _lock, transaction(_connect()) as conn:
        yield conn


def _fetch(conn: sqlite3.Connection, execution_id: str) -> Optional[dict[str, Any]]:
    row = conn.execute("SELECT * FROM executions WHERE id=?", (execution_id,)).fetchone()
    return dict(row) if row is not None else None


def _read_generation(conn: sqlite3.Connection, execution_id: str) -> Optional[int]:
    """Return the Chubby generation for ``execution_id``, or None if the row is gone."""
    row = conn.execute(
        "SELECT generation FROM executions WHERE id=?",
        (execution_id,),
    ).fetchone()
    if row is None:
        return None
    try:
        val = row["generation"]
    except (KeyError, IndexError, TypeError):
        val = row[0]
    return int(val or 0)


def _require_generation(
    conn: sqlite3.Connection, execution_id: str, expected_gen: Optional[int]
) -> int:
    """SELECT current generation and reject a stale writer (Burrows 2006 §2.9).

    If ``expected_gen`` is None, the stored generation is the CAS predicate
    (same-process writers that did not capture dispatch-time gen).
    """
    stored = _read_generation(conn, execution_id)
    if stored is None:
        raise StaleGenerationError(f"execution {execution_id} does not exist")
    if expected_gen is not None and stored != int(expected_gen):
        raise StaleGenerationError(
            f"stale generation for {execution_id}: stored={stored} expected={expected_gen}"
        )
    return stored if expected_gen is None else int(expected_gen)


def _emit_execution_state(
    record: Optional[dict[str, Any]], *, delivery_outcome: Optional[str] = None
) -> None:
    """Project durable state to monitoring without affecting ledger behavior."""
    try:
        from agent.monitoring.cron_health import emit_execution_state

        emit_execution_state(record, delivery_outcome=delivery_outcome)
    except Exception:
        pass


def _process_start_time(pid: int) -> Optional[int]:
    try:
        from gateway.status import get_process_start_time
        return get_process_start_time(pid)
    except Exception:
        return None


def _owner_is_live(pid: int, started_at: Optional[int]) -> bool:
    try:
        from gateway.status import _pid_exists
        if not _pid_exists(pid):
            return False
    except Exception:
        return True  # fail safe: inability to prove death must not rewrite state
    if started_at is None:
        return pid == os.getpid()
    current = _process_start_time(pid)
    if current is None:
        return True  # cannot compare -> cannot prove death; a misread must not rewrite state
    # Drifted same-host readings (#117505) are not proof of death; a live misread is still
    # bounded by the stale-claim sweep below.
    from gateway.status import start_time_fingerprints_match
    return start_time_fingerprints_match(started_at, current)


def _live_owner_stale_after_seconds() -> Optional[float]:
    """Age past which a claimed/running row with a LIVE owner is treated as wedged.

    Derived from the existing knobs, never a bare wall-clock constant:
    ``max(3 × HERMES_CRON_TIMEOUT, cron script timeout, 7200)``. Returns ``None`` (never reclaim
    live owners — today's behaviour) when the inactivity timeout is 0/unlimited or not a finite
    positive number: with no bound to derive from, fail closed.
    """
    from cron.scheduler import _cron_inactivity_seconds
    from cron.scheduler_script import _get_script_timeout

    inactivity = float(_cron_inactivity_seconds())
    if not math.isfinite(inactivity) or inactivity <= 0:
        return None
    return max(
        inactivity * CLAIM_TTL_INACTIVITY_HEADROOM,
        float(_get_script_timeout()),
        LIVE_OWNER_STALE_CLAIM_FLOOR_SECONDS,
    )


def _claim_age_seconds(claimed_at: str) -> float:
    """Seconds since ``claimed_at`` (NOT NULL, always the aware ISO string from hermes_time.now)."""
    return (_hermes_now() - datetime.fromisoformat(claimed_at)).total_seconds()


def _stale_age_seconds(claimed_at: str, progress_at: Optional[str]) -> float:
    """Seconds since the owner last proved it was making progress.

    A wedged worker (#115692) stops stamping ``progress_at``; a long but healthy run keeps
    stamping it, so the derived stale bound measures silence, not run length. Rows written
    before the column existed have no stamp and fall back to claim age.
    """
    return _claim_age_seconds(progress_at or claimed_at)


def touch_execution_progress(execution_id: str) -> bool:
    """Stamp ``progress_at`` on a running attempt this process owns. Returns False when the row
    is no longer ours or no longer running (the caller treats that as informational only)."""
    now = _hermes_now().isoformat()
    with _transaction() as conn:
        cur = conn.execute(
            """UPDATE executions SET progress_at=?
               WHERE id=? AND status IN ('claimed','running') AND process_id=? AND pid=?""",
            (now, execution_id, _PROCESS_ID, os.getpid()),
        )
        return cur.rowcount == 1


def _prune_unlocked(conn: sqlite3.Connection) -> None:
    conn.execute(
        """DELETE FROM executions WHERE id IN (
             SELECT id FROM executions
             WHERE status IN ('completed','failed','unknown')
             ORDER BY julianday(finished_at) DESC, finished_at DESC,
                      julianday(claimed_at) DESC, claimed_at DESC, id DESC LIMIT -1 OFFSET ?
           )""",
        (max(0, int(MAX_TERMINAL_EXECUTIONS)),),
    )


def create_execution(
    job_id: str, *, source: str, scheduled_instant: Optional[str] = None,
) -> dict[str, Any]:
    """Persist a claimed attempt before executor/provider dispatch."""
    from cron.occurrences import scheduled_instant as canonical_instant

    now = _hermes_now().isoformat()
    execution_id = uuid.uuid4().hex
    pid = os.getpid()
    with _transaction() as conn:
        conn.execute(
            """INSERT INTO executions
               (id, job_id, source, process_id, pid, process_started_at,
                status, claimed_at, scheduled_instant)
               VALUES (?, ?, ?, ?, ?, ?, 'claimed', ?, ?)""",
            (execution_id, str(job_id), str(source), _PROCESS_ID, pid,
             _process_start_time(pid), now, canonical_instant(scheduled_instant)),
        )
        record = _fetch(conn, execution_id)
    _emit_execution_state(record)
    return record  # type: ignore[return-value]


def set_execution_occurrence(execution_id: str, instant: Optional[str]) -> None:
    """Bind the store-claimed snapshot before a provider hands it to a worker."""
    from cron.occurrences import scheduled_instant

    with _transaction() as conn:
        cur = conn.execute(
            "UPDATE executions SET scheduled_instant=? WHERE id=? AND status='claimed' "
            "AND handoff_pending=0 AND process_id=? AND pid=?",
            (scheduled_instant(instant), execution_id, _PROCESS_ID, os.getpid()),
        )
        if cur.rowcount != 1:
            raise RuntimeError("Cron occurrence could not be bound before dispatch")


def mark_execution_handoff_pending(execution_id: str) -> Optional[dict[str, Any]]:
    """Fence restart recovery while an external worker is adopting a claim."""
    with _transaction() as conn:
        cur = conn.execute(
            """UPDATE executions
               SET handoff_pending=1, handoff_started_at=?
               WHERE id=? AND status='claimed'
                 AND process_id=? AND pid=?""",
            (time.time(), execution_id, _PROCESS_ID, os.getpid()),
        )
        if cur.rowcount != 1:
            return None
        record = _fetch(conn, execution_id)
    _emit_execution_state(record)
    return record


def adopt_claimed_execution(execution_id: str) -> Optional[dict[str, Any]]:
    """Atomically transfer and start an attempt in its worker process.

    The dispatching gateway creates the row before spawning a restart-safe
    worker.  Adoption is the single ``claimed`` → ``running`` gate: only the
    winner may acknowledge ownership or run side effects.
    """
    pid = os.getpid()
    process_started_at = _process_start_time(pid)
    now = _hermes_now().isoformat()
    with _transaction() as conn:
        stored_gen = _read_generation(conn, execution_id)
        if stored_gen is None:
            return None
        cur = conn.execute(
            """UPDATE executions
               SET process_id=?, pid=?, process_started_at=?,
                   status='running', started_at=?, handoff_pending=0,
                   handoff_started_at=NULL, generation = generation + 1
               WHERE id=? AND status='claimed' AND handoff_pending=1
                 AND generation=?""",
            (_PROCESS_ID, pid, process_started_at, now, execution_id, stored_gen),
        )
        if cur.rowcount != 1:
            return None
        record = _fetch(conn, execution_id)
    _emit_execution_state(record)
    if record is not None:
        _safe_create_execution_lock(
            execution_id, pid, record.get("started_at") or now,
        )
    return record


def mark_execution_running(execution_id: str) -> Optional[dict[str, Any]]:
    """Transition one claimed attempt to running exactly once."""
    now = _hermes_now().isoformat()
    with _transaction() as conn:
        stored_gen = _read_generation(conn, execution_id)
        if stored_gen is None:
            return None
        cur = conn.execute(
            """UPDATE executions
               SET status='running', started_at=?, handoff_pending=0,
                   handoff_started_at=NULL, generation = generation + 1
               WHERE id=? AND status='claimed' AND handoff_pending=0
                 AND process_id=? AND pid=? AND generation=?""",
            (now, execution_id, _PROCESS_ID, os.getpid(), stored_gen),
        )
        if cur.rowcount != 1:
            return None
        record = _fetch(conn, execution_id)
    _emit_execution_state(record)
    if record is not None:
        _safe_create_execution_lock(
            execution_id, os.getpid(), record.get("started_at") or now,
        )
    return record


def finish_execution(
    execution_id: str, *, success: bool, error: Optional[str] = None,
    delivery_outcome: Optional[str] = None,
    expected_generation: Optional[int] = None,
) -> Optional[dict[str, Any]]:
    """Write a terminal result once; terminal attempts cannot be rewritten.

    Only the owning process may finish its attempt; receipt recovery for a departed owner
    settles through ``recover_receipted_execution``.

    ``expected_generation`` is the Chubby sequencer value captured at dispatch. A
    mismatch raises ``StaleGenerationError`` so a slow duplicate cannot clobber a
    newer completion.
    """
    now = _hermes_now().isoformat()
    status = "completed" if success else "failed"
    detail = None if success else (str(error) if error else "unknown failure")
    with _transaction() as conn:
        owner = (_PROCESS_ID, os.getpid())
        stored_gen = _read_generation(conn, execution_id)
        if stored_gen is None:
            if expected_generation is not None:
                raise StaleGenerationError(f"execution {execution_id} does not exist")
            return None
        if expected_generation is not None and stored_gen != int(expected_generation):
            raise StaleGenerationError(
                f"stale generation for {execution_id}: "
                f"stored={stored_gen} expected={expected_generation}"
            )
        cas_gen = stored_gen if expected_generation is None else int(expected_generation)
        started_row = conn.execute(
            "SELECT started_at FROM executions WHERE id=?",
            (execution_id,),
        ).fetchone()
        started_at = started_row["started_at"] if started_row else None
        duration_s = _compute_duration_s(started_at, now)
        cur = conn.execute(
            """UPDATE executions
               SET status=?, finished_at=?, error=?, handoff_pending=0,
                   handoff_started_at=NULL, delivery_outcome=?,
                   duration_s=?,
                   generation = generation + 1
               WHERE id=? AND status IN ('claimed','running')
                 AND process_id=? AND pid=? AND generation=?""",
            (status, now, detail, delivery_outcome, duration_s, execution_id, *owner, cas_gen),
        )
        if cur.rowcount != 1:
            return None
        _prune_unlocked(conn)
        record = _fetch(conn, execution_id)
    _emit_execution_state(record, delivery_outcome=delivery_outcome)
    record_cron_finish(record, delivery_outcome)
    _safe_release_execution_lock(execution_id)
    return record


def recover_receipted_execution(execution_id, job_id, *, success, error=None, delivery_outcome=None):
    """Settle a verified canonical receipt after owner loss, including its unknown audit row.

    Terminal verdicts stay immutable. A live firer still owns its bookkeeping
    (``execution_owner_live``).
    """
    now = _hermes_now().isoformat()
    with _transaction() as conn:
        row = _recoverable_row(conn, execution_id, job_id)
        if row is None or _row_owner_live(row):
            return None
        cas_gen = _require_generation(conn, execution_id, None)
        started_row = conn.execute(
            "SELECT started_at FROM executions WHERE id=?",
            (execution_id,),
        ).fetchone()
        started_at = started_row["started_at"] if started_row else None
        duration_s = _compute_duration_s(started_at, now)
        conn.execute(
            """UPDATE executions SET status=?, finished_at=?, error=?, handoff_pending=0,
               handoff_started_at=NULL, delivery_outcome=?, duration_s=?, generation = generation + 1
               WHERE id=? AND generation=?""",
            ('completed' if success else 'failed', now, None if success else (str(error) if error else 'unknown failure'),
             delivery_outcome, duration_s, execution_id, cas_gen))
        _prune_unlocked(conn)
        record = _fetch(conn, execution_id)
    _emit_execution_state(record, delivery_outcome=delivery_outcome)
    record_cron_finish(record, delivery_outcome)
    _safe_release_execution_lock(execution_id)
    return record


def _recoverable_row(conn, execution_id, job_id):
    return conn.execute(
        """SELECT status, process_id, pid, process_started_at FROM executions
           WHERE id=? AND job_id=? AND status IN ('claimed','running','unknown')""",
        (str(execution_id), str(job_id))).fetchone()


def _row_owner_live(row) -> bool:
    if row['process_id'] == _PROCESS_ID:
        # The in-gateway ticker fires on pool threads: a claimed/running row of THIS process is
        # still in flight here. Only an unknown row was given up by its own firer.
        return row['status'] != 'unknown'
    return _owner_is_live(int(row['pid']), row['process_started_at'])


def execution_owner_live(execution_id: str, job_id: str) -> bool:
    """True while the attempt's own firer (this process included) can still finish it, so receipt
    recovery must not act for it: no output re-save, no job mark, no ledger write."""
    with _transaction() as conn:
        row = _recoverable_row(conn, execution_id, job_id)
    return row is not None and _row_owner_live(row)


def settle_delivery_outcome(execution_id: str, outcome: str) -> bool:
    """Replace a terminal attempt's ``queued`` delivery outcome with the drain's real one.

    The only post-terminal rewrite the ledger allows: the attempt's status is untouched and
    only a ``queued`` handoff can settle, so a replay or a late caller is a no-op.
    """
    with _transaction() as conn:
        cur = conn.execute(
            """UPDATE executions SET delivery_outcome=?
               WHERE id=? AND delivery_outcome='queued'
                 AND status IN ('completed','failed','unknown')""",
            (outcome, execution_id),
        )
    return cur.rowcount == 1


_OWNER_GONE_REASON = (
    "Scheduler restarted after this execution's owner exited before a durable "
    "terminal state; whether side effects ran is unknown."
)
_OWNER_WEDGED_REASON = (
    "Owner process is still alive but the claim outlived the derived stale bound; "
    "treated as wedged (#115692). The process was not terminated; whether side effects "
    "ran is unknown."
)


def settle_unstarted_execution(execution_id: str, job_id: str, error: str) -> None:
    """Close the receipt of a run that never started: a ``claimed`` row never resolves. Best-effort
    so a ledger write cannot mask the failure the caller logs or re-raises."""
    try:
        finish_execution(execution_id, success=False, error=error)
    except (sqlite3.Error, OSError, StaleGenerationError) as record_err:
        logger.error("Job '%s': failed to close execution receipt %s (%s): %s",
                     job_id, execution_id, error, record_err)


def recover_interrupted_executions() -> int:
    """Mark abandoned attempts unknown without scheduling retries: rows whose owner is provably
    dead, plus rows whose live owner holds a claim older than the derived stale bound (the
    process is not killed)."""
    now = _hermes_now().isoformat()
    changed = 0
    recovered: list[dict[str, Any]] = []
    # Derived on the first live-owned row only: the bound reads config, and the idle gateway
    # tick must stay config-free (tests/cron/test_idle_tick_config_skip.py).
    stale_after: Optional[float] = None
    stale_after_resolved = False
    with _transaction() as conn:
        rows = conn.execute(
            """SELECT id, status, process_id, pid, process_started_at,
                      handoff_pending, handoff_started_at, claimed_at, progress_at,
                      generation, started_at
               FROM executions
               WHERE status IN ('claimed','running')"""
        ).fetchall()
        for row in rows:
            if row["process_id"] == _PROCESS_ID:
                continue
            reason = _OWNER_GONE_REASON
            if _owner_is_live(int(row["pid"]), row["process_started_at"]):
                # A live owner is normally a legitimately running job. A worker permanently
                # deadlocked (e.g. futex_wait behind a route/proxy flip, #115692) also passes
                # this check, so a claim SILENT for longer than the derived bound is treated
                # as wedged and released — the external-worker wait loop polls this ledger
                # for a terminal status, so the job can fire again. Silence is measured from
                # the owner's last ``progress_at`` stamp (the run monitor refreshes it while
                # the agent is active), so a healthy multi-hour run is never reclaimed while
                # it is still working. The wedged worker PROCESS is NOT terminated here
                # (leaked until host restart); rows owned by this process (process_id ==
                # _PROCESS_ID, in-process runs) are skipped above and remain out of scope.
                if not stale_after_resolved:
                    stale_after = _live_owner_stale_after_seconds()
                    stale_after_resolved = True
                if (
                    stale_after is None
                    or _stale_age_seconds(row["claimed_at"], row["progress_at"]) <= stale_after
                ):
                    continue
                reason = _OWNER_WEDGED_REASON
            handoff_started_at = row["handoff_started_at"]
            if (
                row["handoff_pending"]
                and handoff_started_at is not None
                and time.time() - float(handoff_started_at)
                < HANDOFF_ADOPTION_GRACE_SECONDS
            ):
                continue
            # The SELECT ran outside a write transaction and the liveness probe takes time: the
            # owner may have stamped progress since, so act only on the snapshot that was judged.
            try:
                cas_gen = _require_generation(
                    conn, row["id"], int(row["generation"] or 0)
                )
            except StaleGenerationError:
                continue
            duration_s = _compute_duration_s(row["started_at"], now)
            cur = conn.execute(
                """UPDATE executions
                   SET status='unknown', finished_at=?, error=?,
                       handoff_pending=0, handoff_started_at=NULL,
                       duration_s=?,
                       generation = generation + 1
                   WHERE id=? AND status=? AND process_id=? AND pid=?
                     AND handoff_pending=?
                     AND handoff_started_at IS ?
                     AND generation=?
                     AND claimed_at=? AND progress_at IS ?""",
                (now, reason, duration_s, row["id"], row["status"], row["process_id"], row["pid"],
                 row["handoff_pending"], row["handoff_started_at"], cas_gen,
                 row["claimed_at"], row["progress_at"]),
            )
            changed += cur.rowcount
            if cur.rowcount:
                record = _fetch(conn, row["id"])
                if record is not None:
                    recovered.append(record)
        if changed:
            _prune_unlocked(conn)
    for record in recovered:
        _emit_execution_state(record)
        _safe_release_execution_lock(str(record.get("id") or ""))
    return changed


def terminalize_dead_owner(execution_id: str, *, reason: str) -> bool:
    """Record one attempt as ``unknown`` with a cause this process actually observed.

    ``recover_interrupted_executions`` sweeps every attempt whose owner is provably
    dead, and knows nothing but that absence — so all it can write is
    ``_OWNER_GONE_REASON``, which asserts a scheduler restart. A waiter that held the
    worker's ``Popen`` knows more: the owner was that external worker, and it exited
    with a known status. Without this, a manual run whose worker dies is filed as
    "Scheduler restarted ..." (a restart that never happened) and, because the sweep
    leaves the row terminal, the waiter reports success and never records the run —
    the job's ``fire_claim`` then blocks the next manual fire for the whole lease
    (#128509).

    The attempt stays ``unknown``, not ``failed``: whether side effects ran is still
    unknown. Only the CAUSE becomes truthful. Returns False — leaving the caller to
    fall back to the generic sweep — when the row is absent, already terminal, owned by
    this process, inside the handoff adoption grace, or owned by a live process: a
    worker that is still running must never be terminalized out from under itself.
    """
    now = _hermes_now().isoformat()
    with _transaction() as conn:
        row = conn.execute(
            """SELECT id, status, process_id, pid, process_started_at,
                      handoff_pending, handoff_started_at, generation
               FROM executions WHERE id=?""",
            (execution_id,),
        ).fetchone()
        if row is None or row["status"] not in ("claimed", "running"):
            return False
        if row["process_id"] == _PROCESS_ID:
            return False
        if _owner_is_live(int(row["pid"]), row["process_started_at"]):
            return False
        handoff_started_at = row["handoff_started_at"]
        if (
            row["handoff_pending"]
            and handoff_started_at is not None
            and time.time() - float(handoff_started_at) < HANDOFF_ADOPTION_GRACE_SECONDS
        ):
            return False
        try:
            cas_gen = _require_generation(conn, execution_id, int(row["generation"] or 0))
        except StaleGenerationError:
            return False
        cur = conn.execute(
            """UPDATE executions
               SET status='unknown', finished_at=?, error=?,
                   handoff_pending=0, handoff_started_at=NULL,
                   generation = generation + 1
               WHERE id=? AND status=? AND process_id=? AND pid=? AND generation=?""",
            (now, reason, row["id"], row["status"], row["process_id"], row["pid"], cas_gen),
        )
        if cur.rowcount != 1:
            return False
        record = _fetch(conn, execution_id)
        _prune_unlocked(conn)
    _emit_execution_state(record)
    _safe_release_execution_lock(execution_id)
    return True


def give_up_execution(execution_id: str, *, reason: str) -> bool:
    """The firer itself gave up on its in-flight attempt (``CronExecutionUnknown``): record it
    ``unknown`` now, owner-fenced to this process, instead of leaving it ``running`` until a
    restart's dead-owner sweep. Receipt recovery never acts for a same-process running row, so
    the owner's later terminal receipt can settle it only once it is marked given up."""
    now = _hermes_now().isoformat()
    with _transaction() as conn:
        stored_gen = _read_generation(conn, str(execution_id))
        if stored_gen is None:
            return False
        cur = conn.execute(
            """UPDATE executions SET status='unknown', finished_at=?, error=?,
                   handoff_pending=0, handoff_started_at=NULL,
                   generation = generation + 1
               WHERE id=? AND status IN ('claimed','running') AND process_id=? AND pid=?
                 AND generation=?""",
            (now, reason, str(execution_id), _PROCESS_ID, os.getpid(), stored_gen))
        if cur.rowcount != 1:
            return False
        record = _fetch(conn, str(execution_id))
        _prune_unlocked(conn)
    _emit_execution_state(record)
    _safe_release_execution_lock(str(execution_id))
    return True


def list_executions(
    *, job_id: Optional[str] = None, limit: int = 50, before_claimed_at: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Return indexed, newest-first execution history with cursor pagination."""
    clauses: list[str] = []
    params: list[Any] = []
    if job_id is not None:
        clauses.append("job_id=?")
        params.append(str(job_id))
    if before_claimed_at is not None:
        # Same (instant, text) key as the ORDER BY, so a page never skips or repeats a row.
        clauses.append("(julianday(claimed_at), claimed_at) < (julianday(?), ?)")
        params.extend([str(before_claimed_at)] * 2)
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    params.append(max(1, min(int(limit), 500)))
    # Stamps carry the local offset, which changes at DST and on a timezone change, so text order
    # is not time order. julianday() compares instants (ms); the text breaks same-ms ties.
    with _transaction() as conn:
        rows = conn.execute(
            "SELECT * FROM executions" + where
            + " ORDER BY julianday(claimed_at) DESC, claimed_at DESC, id DESC LIMIT ?",
            params,
        ).fetchall()
    return [dict(row) for row in rows]


def get_execution(execution_id: str) -> Optional[dict[str, Any]]:
    """Return one exact execution attempt, or ``None`` when it is absent."""
    with _transaction() as conn:
        row = conn.execute(
            "SELECT * FROM executions WHERE id=?",
            (str(execution_id),),
        ).fetchone()
    return dict(row) if row is not None else None


def latest_execution(job_id: str) -> Optional[dict[str, Any]]:
    rows = list_executions(job_id=job_id, limit=1)
    return rows[0] if rows else None


def live_inflight_execution(job_id: str) -> Optional[dict[str, Any]]:
    """The job's latest attempt while it is still claimed/running under a LIVE owner, else ``None``.

    This is scheduler OWNERSHIP, not recent activity: a run inside a long tool call writes no
    heartbeat yet stays owned, while a run whose process died (watchdog kill, crash) does not.
    Read-only — unlike ``recover_interrupted_executions`` it never rewrites a row.
    """
    record = latest_execution(job_id)
    if not record or record.get("status") not in ("claimed", "running"):
        return None
    if not _owner_is_live(int(record["pid"]), record.get("process_started_at")):
        return None
    return record


def latest_executions(job_ids: list[str]) -> dict[str, dict[str, Any]]:
    """Load latest execution for many jobs in one query."""
    clean = [str(job_id) for job_id in dict.fromkeys(job_ids) if job_id]
    if not clean:
        return {}
    placeholders = ",".join("?" for _ in clean)
    # One windowed sort: a per-row correlated ORDER BY julianday() cannot use the index and
    # grows quadratically with history (~90 ms at 1000 rows).
    with _transaction() as conn:
        rows = conn.execute(
            f"""SELECT e.* FROM executions e WHERE e.id IN (
                  SELECT id FROM (
                    SELECT id, ROW_NUMBER() OVER (
                             PARTITION BY job_id
                             ORDER BY julianday(claimed_at) DESC, claimed_at DESC, id DESC
                           ) AS rn
                    FROM executions WHERE job_id IN ({placeholders}))
                  WHERE rn=1)""",
            clean,
        ).fetchall()
    return {row["job_id"]: dict(row) for row in rows}


def _self_test() -> None:
    """Chubby sequencer: wrong gen rejected; correct gen bumps 0 -> 1."""
    import tempfile

    global EXECUTIONS_FILE
    prev = EXECUTIONS_FILE
    tmp = tempfile.TemporaryDirectory(prefix="executions-gen-")
    try:
        EXECUTIONS_FILE = Path(tmp.name) / "executions.db"
        rec = create_execution("self-test-job", source="self-test")
        eid = rec["id"]
        gen0 = int(rec.get("generation") or 0)
        if gen0 != 0:
            raise AssertionError(f"new execution generation must be 0, got {gen0}")
        raised = False
        try:
            finish_execution(eid, success=True, expected_generation=gen0 + 1)
        except StaleGenerationError:
            raised = True
        if not raised:
            raise AssertionError("wrong generation must raise StaleGenerationError")
        still = get_execution(eid)
        if still is None or still.get("status") != "claimed":
            raise AssertionError("stale write must not change status")
        if int(still.get("generation") or 0) != 0:
            raise AssertionError("stale write must not bump generation")
        rec2 = finish_execution(eid, success=True, expected_generation=gen0)
        if rec2 is None:
            raise AssertionError("correct generation must succeed")
        if int(rec2.get("generation") or 0) != 1:
            raise AssertionError(f"generation must be 1 after CAS, got {rec2.get('generation')}")
        rec3 = get_execution(eid)
        if rec3 is None or int(rec3.get("generation") or 0) != 1:
            raise AssertionError("persisted generation must be 1")
        print("self-test ok: StaleGenerationError on wrong gen; generation=1 after CAS")
    finally:
        EXECUTIONS_FILE = prev
        tmp.cleanup()


if __name__ == "__main__":
    import sys

    if "--self-test" in sys.argv:
        _self_test()
    else:
        print("usage: python3 -m cron.executions --self-test", file=sys.stderr)
        raise SystemExit(2)
