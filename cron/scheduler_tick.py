"""In-process tick admission and dispatch; job execution stays in scheduler.py."""

import concurrent.futures
import contextlib
import logging
import math
import time

from cron import store_health
from cron.constants import is_recurring

logger = logging.getLogger("cron.scheduler")


SITA_CUT_S = 45.0
_sita_pools = {}
_sita_pool_k = {}


def _predicted_s(job: dict) -> float:
    if not isinstance(job, dict):
        return 120.0
    hist = job.get("_ema_duration")
    if hist is not None:
        try:
            v = float(hist or 0.0)
            if v > 0:
                return v
        except (TypeError, ValueError):
            pass
    try:
        v = float(job.get("timeout") or job.get("timeout_seconds") or 120)
    except (TypeError, ValueError):
        v = 120.0
    return v if v > 0 else 120.0


def _edf_then_srpt(due_jobs):
    """EDF bands, SRPT within band. band = floor(log2(1+10*urgency))."""
    def _urgency(job: dict) -> float:
        try:
            from cron.jobs import _schedule_cadence_seconds
            lateness = max(0.0, float(job.get("last_dispatch", {}).get("lateness_seconds", 0.0) or 0.0))
            cadence = _schedule_cadence_seconds(job.get("schedule", {}))
            return lateness / cadence if cadence and cadence > 0 else 0.0
        except Exception:
            return 0.0

    def _key(job):
        u = _urgency(job)
        band = math.floor(math.log2(1.0 + 10.0 * max(0.0, u)))
        return (-band, _predicted_s(job))

    return sorted(due_jobs, key=_key)


def _get_sita_pool(kind: str, k: int):
    try:
        k = int(k or 1)
    except (TypeError, ValueError):
        k = 1
    k = max(1, k)
    pool = _sita_pools.get(kind)
    if pool is None or _sita_pool_k.get(kind) != k:
        if pool is not None:
            with contextlib.suppress(Exception):
                pool.shutdown(wait=False, cancel_futures=False)
        pool = concurrent.futures.ThreadPoolExecutor(
            max_workers=k, thread_name_prefix=f"cron-sita-{kind}"
        )
        _sita_pools[kind] = pool
        _sita_pool_k[kind] = k
    return pool



# Log the yield at most once per episode (reset when the skew changes) to avoid per-interval spam.
_YIELD_LOG_INTERVAL_SECONDS = 3600.0
_last_yield_log: dict[str, object] = {}


def _log_tick_yield_once(reason: str) -> None:
    """Log the yield at error level once per episode (skew signature)."""
    global _last_yield_log
    now = time.monotonic()
    last_reason = _last_yield_log.get("reason")
    last_at = _last_yield_log.get("at", 0.0)
    if last_reason != reason or (now - float(last_at)) >= _YIELD_LOG_INTERVAL_SECONDS:
        logger.error(
            "Cron tick yielded: this process is running stale code (%s) and a "
            "fresher gateway owns the runtime lock — jobs will fire from that "
            "process. Restart this one to reclaim its ticks.",
            reason)
    _last_yield_log = {"reason": reason, "at": now}


def tick(verbose=True, adapters=None, loop=None, sync=True, *, can_dispatch=None,
         headless: bool = False):
    from hermes_cli.backend_retirement import retirement

    # Hold admission through the entire scan/advance/submit handoff. A predicate alone races
    # prepare after the check but before a due job enters the running-job ledger.
    with retirement.work() as admitted:
        if not admitted:
            return 0
        return _tick_admitted(verbose, adapters, loop, sync, can_dispatch=can_dispatch,
                              headless=headless)


def _acquire_tick_lock_or_degrade(_sched):
    """The tick lock fd, or None when this tick must not run: another ticker holds the lock, or
    the store cannot be written (read-only/full/denied: the lock file cannot even be created), in
    which case the store is marked degraded and the MCP orphan sweep still runs."""
    lock_dir, lock_file = _sched._get_lock_paths()
    _sched._ensure_cron_dir(lock_dir)
    try:
        return _sched._acquire_tick_lock(lock_file)
    except OSError as exc:
        if exc.errno not in store_health.UNWRITABLE_ERRNOS:
            raise  # EMFILE/ENFILE etc. stay a FAILED tick (#87644)
        store_health.note_unwritable(exc, "tick lock unavailable", "lock", cron_dir=lock_dir)
        _sched._sweep_mcp_orphans()
        return None


def _advance_or_drop_recurring(_sched, due_jobs: list) -> list:
    """Persist the recurring jobs' advance before any runs; when the store refuses it, drop them
    (no durable advance -> a crash mid-run would re-fire them, so skipping is the at-most-once
    side). One-shots still go through their own fire claim."""
    try:
        _sched.advance_next_runs([job["id"] for job in due_jobs])
        return due_jobs
    except OSError as exc:
        skipped = [j for j in due_jobs if is_recurring(j)]
        store_health.note_unwritable(exc, f"skipped {len(skipped)} recurring job(s)", "advance", skipped)
        return [j for j in due_jobs if not is_recurring(j)]


def _pre_dispatch_housekeeping(_sched, headless: bool) -> None:
    """Admission reconcile, legacy upgrade drain and dead-owner reap, run under the tick lock
    before due jobs are read."""
    from cron.scheduler_authority import reconcile_pending
    if headless:
        reconcile_pending(allow_connect=False)
    else:
        reconcile_pending()
    # Upgrade drain for the retired CLI lane's records: never let it stop due jobs below.
    try:
        from cron.bot_chat_legacy import drain_legacy_pending
        drain_legacy_pending()
    except Exception as _legacy_exc:
        _sched.logger.warning("Legacy Bot Chat pending drain failed: %s", _legacy_exc, exc_info=True)
    _sched._maybe_reap_dead_owners()


def _tick_admitted(
    verbose: bool = True, adapters=None, loop=None, sync: bool = True, *, can_dispatch=None,
    headless: bool = False):
    """Check and run all due jobs. File-locked so only one tick runs at a time (gateway ticker vs
    standalone daemon / manual tick). ``can_dispatch``: optional gate; false leaves due jobs for the
    next allowed tick. ``headless``: the tick runs outside any gateway (system crontab, ``hermes
    cron tick``) and must refuse agent jobs rather than spawn one. Returns the number of jobs
    executed (0 if another tick holds the lock)."""
    from cron import scheduler as _sched

    # ZooKeeper ephemeral-znode reap: drop locks whose PID died or TTL expired
    # so a crashed run cannot block the next fire of the same job.
    try:
        from cron.executions import reap_stale_locks
        reap_stale_locks()
    except Exception:
        logger.debug("ephemeral execution lock reap failed", exc_info=True)

    # Stale-code yield gate — BEFORE the lock race. A process whose checkout was updated under it
    # serves mixed sys.modules (jobs die on ImportErrors); if a fresher gateway holds the runtime
    # lock, ITS ticker dispatches. With no fresh holder (desktop-standalone) the tick proceeds.
    _skew = _sched._should_yield_tick_to_fresh_gateway()
    if _skew is not None:
        _log_tick_yield_once(f"boot={_skew[0]} disk={_skew[1]}")
        raise _sched.CronTickYielded(_skew[0], _skew[1])

    lock_fd = _acquire_tick_lock_or_degrade(_sched)
    if lock_fd is None:
        return 0

    try:
        # `hermes pause` ESTOP: skip dispatch, never touch in-flight runs; check_paused logs once.
        with contextlib.suppress(ImportError):
            from agent.estop import check_paused as _estop_check_paused
            if _estop_check_paused("cron", _sched.logger):
                return 0

        if can_dispatch is not None and not can_dispatch():
            _sched.logger.debug("Cron dispatch paused while gateway drains existing work")
            return 0

        _pre_dispatch_housekeeping(_sched, headless)
        # Periodic worktree GC (6h, threaded) — the only sweep gateway-only boxes get.
        try:
            _sched._maybe_run_worktree_maintenance()
        except Exception as _wt_exc:
            _sched.logger.debug("Worktree maintenance dispatch failed: %s", _wt_exc)

        due_jobs = _sched.get_due_jobs()
        _sched._sweep_stale_inflight_for_tick(due_jobs)
        if headless:
            from cron.scheduler_gateway_gate import refuse_agent_jobs_without_gateway
            due_jobs = refuse_agent_jobs_without_gateway(due_jobs)

        if not due_jobs:
            # Idle tick: skip config load + pool setup, but still reap crashed jobs' MCP orphans.
            if verbose:
                # Idle tick: skip config load + pool partitioning entirely (#33612 — the gateway ticker
                # calls tick(verbose=False) every 60s, so idle ticks previously fell through to
                # load_config()). Still run the post-tick MCP orphan sweep: main intentionally sweeps on
                # idle ticks so orphaned stdio children from crashed jobs are reaped even when nothing is
                # due.
                _sched.logger.info("%s - No jobs due", _sched._hermes_now().strftime('%H:%M:%S'))
            store_health.recheck_idle()
            _sched._sweep_mcp_orphans()
            return 0

        if store_health.dispatch_blocked(due_jobs):
            # Known-unwritable store, re-probed at most once a minute: every advance/claim would
            # fail, so skip them (the skip is recorded) and keep the tick's housekeeping alive.
            _sched._sweep_mcp_orphans()
            return 0

        if verbose:
            _sched.logger.info("%s - %s job(s) due", _sched._hermes_now().strftime('%H:%M:%S'), len(due_jobs))

        # Advance next_run_at for recurring jobs FIRST, under the lock, before any execution
        # (at-most-once). Re-advancing running jobs keeps the grace window alive; mark_job_run
        # overwrites it on completion. Composes with the claim-time advance in claim_job_for_fire.
        due_jobs = _advance_or_drop_recurring(_sched, due_jobs)
        if not due_jobs:
            _sched._sweep_mcp_orphans()
            return 0

        # EDF bands then SRPT within band (Harchol-Balter size-aware).
        due_jobs = _edf_then_srpt(due_jobs)

        _max_workers = _sched._resolve_max_parallel_workers(due_jobs)
        if verbose:
            _sched.logger.info(
                "Running %d job(s) in parallel (max_workers=%s)",
                len(due_jobs),
                _max_workers if _max_workers else "unbounded")

        def _process_job(job: dict) -> bool:
            return _sched._process_due_job(job, adapters, loop, verbose)

        # Harchol-Balter Ch 24: do not rebalance pools to equal rho
        # SITA: never steal a short-pool slot for a long job (defeats isolation).
        short_jobs = [j for j in due_jobs if _predicted_s(j) < SITA_CUT_S]
        long_jobs = [j for j in due_jobs if _predicted_s(j) >= SITA_CUT_S]
        R_s = sum(_predicted_s(j) for j in short_jobs) / 60.0
        R_l = sum(_predicted_s(j) for j in long_jobs) / 60.0
        k_s = _sched._square_root_k(R_s, beta=1.0, k_min=1, k_max=12)
        k_l = _sched._square_root_k(R_l, beta=1.0, k_min=1, k_max=8)
        if _max_workers:
            # cap total, but do not rebalance long->short when short is idle
            total = k_s + k_l
            if total > _max_workers:
                scale = _max_workers / float(total)
                k_s = max(1 if short_jobs else 0, math.floor(k_s * scale) or (1 if short_jobs else 0))
                k_l = max(1 if long_jobs else 0, _max_workers - k_s)
        short_pool = _get_sita_pool("short", max(1, k_s)) if short_jobs else None
        long_pool = _get_sita_pool("long", max(1, k_l)) if long_jobs else None
        logger.info(
            "SITA dispatch short=%d k_s=%s long=%d k_l=%s cut=%.1f",
            len(short_jobs), k_s, len(long_jobs), k_l, SITA_CUT_S,
        )

        _results: list = []
        _all_futures: list = []
        for job in due_jobs:
            # Skip if a prior execution still holds a live ephemeral lock
            # (Hunt 2010: presence of the znode == owner still alive).
            try:
                from cron.executions import is_lock_live, live_inflight_execution
                execution_id = job.get("execution_id")
                if not execution_id:
                    inflight = live_inflight_execution(job["id"])
                    if inflight:
                        execution_id = inflight.get("id")
                if execution_id and is_lock_live(str(execution_id)):
                    logger.info(
                        "Job '%s' already running (live execution lock) — skipping",
                        job.get("name", job["id"]))
                    continue
            except Exception:
                logger.debug("execution lock check failed", exc_info=True)
            size = _predicted_s(job)
            pool = short_pool if size < SITA_CUT_S else long_pool
            if pool is None:
                pool = short_pool or long_pool or _sched._get_parallel_pool(_max_workers)
            fut = _sched._submit_with_guard(job, pool, _process_job)
            if fut is None:
                continue
            _all_futures.append(fut)
            if not sync:
                _results.append(True)  # optimistically counted

        if sync:
            for f in concurrent.futures.as_completed(_all_futures):
                try:
                    _results.append(f.result())
                except Exception as exc:
                    _sched.logger.error("Cron job future failed: %s", exc)
                    _results.append(False)
            _sched._sweep_mcp_orphans()
            return sum(_results)

        _sched._sweep_mcp_orphans_when_all_done(_all_futures)
        return sum(_results)
    finally:
        _sched._release_tick_lock(lock_fd)
