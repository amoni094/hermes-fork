"""Cron admission control using Liu & Layland (1973) utilisation bounds.

Theory: Liu & Layland (1973) proved that for a set of periodic tasks on a
uniprocessor, the utilisation U = Σ(C_i/T_i) is the key schedulability criterion:
  - EDF (optimal): feasible iff U <= 1.0
  - Rate Monotonic (fixed priority, optimal): feasible iff U <= n*(2^(1/n)-1)
    which converges to ln(2) ≈ 0.6931 as n→∞

For hermes-fork cron jobs:
  C_i = job timeout (execution time bound, worst case)
  T_i = job cadence (period = scheduled interval in seconds)
  U   = Σ(C_i/T_i) = total CPU fraction consumed by periodic jobs

If U > 1.0, some jobs will always miss their deadlines (EDF can't help).
If U > ln2, RM priority assignment may cause missed deadlines.

This module:
  1. Reads jobs.json and computes per-job utilisation contributions
  2. Checks against EDF and RM bounds
  3. Reports which jobs contribute most (candidates for timeout reduction or
     cadence increase)
  4. Can be called before adding a new job (admission test)

Note on C_i estimation: We use job timeout as C_i (worst case). If timeout is
not set, we use a configurable default (DEFAULT_TIMEOUT_SECONDS). Jobs with
no periodic schedule (one-shots, event-triggered) are excluded.

Usage:
  python3 cron-admission-control.py            # audit current jobs
  python3 cron-admission-control.py --new-job --timeout 60 --cadence 86400
  python3 cron-admission-control.py --self-test
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import os
import re
import sys
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("cron-admission-control")

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes" / "profiles" / "fork"))
JOBS_FILE = HERMES_HOME / "cron" / "jobs.json"
REPORT_FILE = HERMES_HOME / "omni" / "cron-admission-report.json"

# Default C_i when timeout not specified (seconds)
DEFAULT_TIMEOUT_SECONDS = 300.0

# Liu-Layland RM bound (converges to ln2 ≈ 0.6931)
RM_BOUND_ASYMPTOTIC = math.log(2)  # 0.6931...


def rm_bound(n: int) -> float:
    """Exact Liu-Layland RM bound: n*(2^(1/n) - 1). Equals ln2 as n→∞."""
    if n <= 0:
        return 0.0
    return n * (2 ** (1.0 / n) - 1)


# ---------------------------------------------------------------------------
# Cron expression → period in seconds
# ---------------------------------------------------------------------------

def _parse_cron_cadence(expr: str) -> Optional[float]:
    """Parse a cron expression and return the period in seconds.

    Only handles simple cases (all fields are specific values or *).
    Returns None for complex expressions (multiple values, ranges, steps with non-standard).
    """
    if not expr:
        return None
    parts = expr.strip().split()
    if len(parts) != 5:
        return None
    minute, hour, dom, month, dow = parts

    # Detect period by finding the most frequent field
    # Common patterns:
    #   * * * * *     → every minute (60s)
    #   */5 * * * *   → every 5 minutes (300s)
    #   0 * * * *     → every hour (3600s)
    #   0 H * * *     → every day (86400s)
    #   0 H * * 0     → every week (604800s)
    #   0 H 1 * *     → every month (~2592000s)

    def _is_star(f): return f == "*"
    def _is_step(f): return f.startswith("*/")
    def _step_val(f): return int(f[2:]) if _is_step(f) else None

    if _is_star(minute) and _is_star(hour) and _is_star(dom) and _is_star(month) and _is_star(dow):
        return 60.0  # every minute
    if _is_step(minute) and _is_star(hour) and _is_star(dom) and _is_star(month) and _is_star(dow):
        sv = _step_val(minute)
        return sv * 60.0 if sv is not None else None
    if not _is_star(minute) and _is_star(hour) and _is_star(dom) and _is_star(month) and _is_star(dow):
        return 3600.0  # hourly
    if not _is_star(minute) and not _is_star(hour) and _is_star(dom) and _is_star(month) and _is_star(dow):
        return 86400.0  # daily
    if not _is_star(minute) and not _is_star(hour) and _is_star(dom) and _is_star(month) and not _is_star(dow):
        return 604800.0  # weekly
    if not _is_star(minute) and not _is_star(hour) and not _is_star(dom) and _is_star(month) and _is_star(dow):
        return 2592000.0  # monthly (approx 30 days)
    return None  # cannot determine


def _job_cadence_seconds(job: dict) -> Optional[float]:
    """Extract cadence in seconds from a job dict."""
    schedule = job.get("schedule", {})
    if not isinstance(schedule, dict):
        return None
    kind = schedule.get("kind", "")
    if kind == "interval":
        return float(schedule.get("seconds", 0)) or None
    if kind == "cron":
        return _parse_cron_cadence(schedule.get("expr", ""))
    return None


def _job_timeout_seconds(job: dict) -> float:
    """Get job timeout as C_i. Falls back to DEFAULT_TIMEOUT_SECONDS."""
    t = job.get("timeout")
    if t is not None:
        try:
            return float(t)
        except (TypeError, ValueError):
            pass
    return DEFAULT_TIMEOUT_SECONDS


# ---------------------------------------------------------------------------
# Utilisation computation
# ---------------------------------------------------------------------------

def compute_utilisation(jobs: list[dict]) -> dict:
    """Compute utilisation report for a list of jobs.

    Returns:
      total_u: float — total utilisation
      edf_bound: 1.0
      rm_bound_n: float — exact RM bound for n periodic tasks
      n_periodic: int — number of periodic jobs included
      n_excluded: int — one-shots / unknown cadence jobs excluded
      status: 'OK_EDF' | 'WARN_RM' | 'OVERLOADED'
      jobs: list of per-job dicts with {id, name, timeout_s, cadence_s, utilisation}
      top_contributors: top 5 by utilisation
    """
    per_job = []
    excluded = 0

    for job in jobs:
        if not isinstance(job, dict):
            continue
        schedule = job.get("schedule", {})
        if not isinstance(schedule, dict):
            excluded += 1
            continue
        # Exclude one-shots (no kind or kind=once)
        kind = schedule.get("kind", "")
        if kind in ("", "once", "agent"):
            excluded += 1
            continue

        cadence = _job_cadence_seconds(job)
        if cadence is None or cadence <= 0:
            excluded += 1
            continue

        timeout = _job_timeout_seconds(job)
        u = timeout / cadence

        per_job.append({
            "id": job.get("id", "?"),
            "name": job.get("name", "?"),
            "timeout_s": timeout,
            "cadence_s": cadence,
            "utilisation": round(u, 6),
        })

    n = len(per_job)
    total_u = sum(j["utilisation"] for j in per_job)
    rm_b = rm_bound(n) if n > 0 else 0.0

    if total_u <= rm_b:
        status = "OK_EDF_AND_RM"
    elif total_u <= 1.0:
        status = "WARN_RM_ONLY"  # EDF is fine but RM may miss deadlines
    else:
        status = "OVERLOADED"

    top = sorted(per_job, key=lambda x: x["utilisation"], reverse=True)[:5]

    # Zilberstein (1996) VOI-based priority: when overloaded, prioritize jobs with
    # lowest quality_score (most stale) — they have highest value of computation.
    # quality_score read from lifecycle.db if available; default to 0.5 (mid quality).
    quality_ordered = None
    if status == "OVERLOADED":
        try:
            import sqlite3 as _sql3, os as _os
            _db_candidates = [
                _os.path.expanduser("~/.hermes/profiles/fork/memory-facts/lifecycle.db"),
                _os.path.expanduser("~/.hermes/memory-facts/lifecycle.db"),
            ]
            _db_path = next((p for p in _db_candidates if _os.path.exists(p)), None)
            if _db_path:
                with _sql3.connect(_db_path, timeout=3.0) as _lc:
                    _qrows = {r[0]: r[1] for r in _lc.execute(
                        "SELECT source, quality_score FROM fact_lifecycle WHERE quality_score IS NOT NULL"
                    ).fetchall()}
                for j in per_job:
                    j["quality_score"] = _qrows.get(j["name"], 0.5)
            else:
                for j in per_job:
                    j["quality_score"] = 0.5
        except Exception:
            for j in per_job:
                j.setdefault("quality_score", 0.5)
        # Sort: lowest quality_score first = highest priority (most stale = most valuable to run)
        quality_ordered = sorted(per_job, key=lambda x: x.get("quality_score", 0.5))

    return {
        "total_utilisation": round(total_u, 6),
        "edf_bound": 1.0,
        "rm_bound": round(rm_b, 6),
        "rm_bound_asymptotic": round(RM_BOUND_ASYMPTOTIC, 6),
        "n_periodic": n,
        "n_excluded": excluded,
        "status": status,
        "jobs": per_job,
        "top_contributors": top,
        "quality_priority_order": quality_ordered,  # Zilberstein VOI ordering (None if not overloaded)
    }


def admit_new_job(existing_jobs: list[dict], timeout_s: float, cadence_s: float,
                  name: str = "new-job", policy: str = "edf") -> dict:
    """Test if adding a new job with given timeout+cadence is admissible.

    policy: 'edf' (check U <= 1.0) or 'rm' (check U <= rm_bound)
    """
    synthetic = {
        "id": "__new__",
        "name": name,
        "schedule": {"kind": "cron", "expr": "0 0 * * *"},  # placeholder
        "timeout": timeout_s,
    }
    # Override cadence directly
    all_jobs = list(existing_jobs) + [synthetic]
    report = compute_utilisation(all_jobs)

    # Override cadence for the synthetic job
    new_u = timeout_s / cadence_s if cadence_s > 0 else 0.0
    report["proposed_job"] = {
        "name": name,
        "timeout_s": timeout_s,
        "cadence_s": cadence_s,
        "utilisation": round(new_u, 6),
    }

    # Recompute with correct cadence
    base = compute_utilisation(existing_jobs)
    total_with_new = base["total_utilisation"] + new_u
    rm_b = rm_bound(base["n_periodic"] + 1)

    if policy == "rm":
        admitted = total_with_new <= rm_b
    else:
        admitted = total_with_new <= 1.0

    report["admitted"] = admitted
    report["total_with_new"] = round(total_with_new, 6)
    report["policy"] = policy
    report["admission_bound"] = rm_b if policy == "rm" else 1.0

    return report


def load_jobs() -> list[dict]:
    try:
        data = json.loads(JOBS_FILE.read_text())
        return data if isinstance(data, list) else data.get("jobs", [])
    except Exception as exc:
        logger.error("Failed to load %s: %s", JOBS_FILE, exc)
        return []


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Cron admission control (Liu-Layland bounds)")
    parser.add_argument("--new-job", action="store_true", help="Test adding a new job")
    parser.add_argument("--timeout", type=float, help="New job timeout in seconds")
    parser.add_argument("--cadence", type=float, help="New job period in seconds")
    parser.add_argument("--name", default="proposed-job", help="New job name")
    parser.add_argument("--policy", choices=["edf", "rm"], default="edf",
                        help="Admission policy: edf (U<=1) or rm (U<=ln2)")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        # Test rm_bound
        assert abs(rm_bound(1) - 1.0) < 1e-9, "RM bound for n=1 should be 1.0"
        assert abs(rm_bound(2) - (2*(2**0.5 - 1))) < 1e-9, f"RM bound n=2 failed: {rm_bound(2)}"
        # rm_bound(n) approaches ln2 from above as n→∞
        assert RM_BOUND_ASYMPTOTIC < rm_bound(100) < RM_BOUND_ASYMPTOTIC + 0.01, \
            f"RM bound should approach ln2 from above: {rm_bound(100):.6f}"

        # Test cadence parsing
        assert _parse_cron_cadence("0 2 * * *") == 86400.0, "Daily parse failed"
        assert _parse_cron_cadence("0 5 * * 0") == 604800.0, "Weekly parse failed"
        assert _parse_cron_cadence("0 * * * *") == 3600.0, "Hourly parse failed"

        # Test utilisation
        jobs = [
            {"schedule": {"kind": "cron", "expr": "0 * * * *"}, "timeout": 60, "name": "j1"},
            {"schedule": {"kind": "cron", "expr": "0 0 * * *"}, "timeout": 300, "name": "j2"},
        ]
        report = compute_utilisation(jobs)
        # j1: 60/3600 = 0.0167; j2: 300/86400 = 0.00347; total ≈ 0.0201
        assert report["total_utilisation"] < 0.1, f"Utilisation too high: {report['total_utilisation']}"
        assert report["status"] == "OK_EDF_AND_RM", f"Expected OK, got {report['status']}"

        print(f"self-test OK: rm_bound(1)={rm_bound(1):.4f}, "
              f"rm_bound(inf)≈{RM_BOUND_ASYMPTOTIC:.4f}, "
              f"test_util={report['total_utilisation']:.6f} ({report['status']})")
        return 0

    jobs = load_jobs()

    if args.new_job:
        if not args.timeout or not args.cadence:
            print("--new-job requires --timeout and --cadence", file=sys.stderr)
            return 2
        report = admit_new_job(jobs, args.timeout, args.cadence, args.name, args.policy)
    else:
        report = compute_utilisation(jobs)

    # Save report
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_FILE.write_text(json.dumps(report, indent=2))

    print(json.dumps({
        k: report[k] for k in [
            "total_utilisation", "edf_bound", "rm_bound", "n_periodic",
            "n_excluded", "status", "top_contributors",
        ] + (["admitted", "total_with_new"] if args.new_job else [])
    }, indent=2))

    return 1 if report.get("status") == "OVERLOADED" else 0


if __name__ == "__main__":
    sys.exit(main())
