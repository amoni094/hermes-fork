"""Harel Statechart-inspired execution state machine guard for cron transitions.

Theory: Harel (1987) Statecharts extend finite automata with hierarchy (AND/OR
states), history, and broadcast events. For cron executions, the key insight is
that state transitions should be *validated against a transition table*, not
just checked inline at each call site. This prevents illegal transitions (e.g.,
claimed→completed without going through running, or completed→running).

Chubby (Burrows 2006) §2.9 fail-over: when a master fails, it must reconstruct
in-memory state from durable records. The epoch number mechanism prevents stale
packets from a dead master from modifying the new master's state. Applied here:
each execution has a "generation" counter that increments on every valid
transition. A transition attempt carrying a stale generation is rejected.

This module provides:
  1. A formal transition table (the statechart)
  2. Transition guard functions that enforce legal arcs
  3. Generation-counter validation (Chubby-style sequencer)
  4. A validator that can audit existing rows in executions.db for illegal states

Usage:
  python3 execution-state-machine.py --audit
  python3 execution-state-machine.py --validate claimed running  (exit 0=valid, 1=invalid)
  python3 execution-state-machine.py --self-test
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import sys
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("execution-state-machine")

HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes" / "profiles" / "fork"))


def _resolve_executions_db() -> Path:
    """Prefer the active profile cron DB; do not silently audit ~/.hermes/cron/.

    Order: HERMES_EXECUTIONS_DB override, HERMES_HOME/cron/executions.db if
    present, then HERMES_HOME_ROOT/cron/executions.db.
    """
    override = os.environ.get("HERMES_EXECUTIONS_DB", "").strip()
    if override:
        return Path(override)
    profile_db = HERMES_HOME / "cron" / "executions.db"
    if profile_db.exists():
        return profile_db
    root = Path(os.environ.get("HERMES_HOME_ROOT", Path.home() / ".hermes"))
    return root / "cron" / "executions.db"


EXECUTIONS_DB = _resolve_executions_db()

# ---------------------------------------------------------------------------
# Harel Statechart: formal transition table
# ---------------------------------------------------------------------------
# States: claimed, running, completed, failed, unknown, missed, cancelled
# Terminal states: completed, failed, unknown, missed, cancelled
#   (immutable — no outbound arcs)
#
# Scheduler-only terminals (not illegal / not unknown):
#   missed    — cron window skipped (host asleep, catch-up dropped, etc.)
#   cancelled — job cancelled before or during a run
#
# Statechart hierarchy:
#   ACTIVE (superstate)
#   ├── claimed  (initial)
#   │   ├── handoff_pending=False → running  (mark_execution_running)
#   │   └── handoff_pending=True  → running  (adopt_claimed_execution)
#   └── running
#       ├── success → completed
#       ├── error   → failed
#       └── orphan  → unknown   (stale-claim reaper)
#   TERMINAL (superstate, history=deep, no exit)
#   ├── completed
#   ├── failed
#   ├── unknown
#   ├── missed
#   └── cancelled

# Each arc: (from_state, to_state) → {description, conditions}
_VALID_ARCS: dict[tuple[str, str], dict] = {
    ("claimed", "running"): {
        "description": "Job started executing (normal path or handoff adoption)",
        "conditions": ["process_id matches or handoff_pending=True"],
    },
    ("claimed", "failed"): {
        "description": "Job failed before starting (pre-run validation failure)",
        "conditions": ["process_id matches"],
    },
    ("claimed", "unknown"): {
        "description": "Claim orphaned — owner process died without transitioning",
        "conditions": ["stale-claim reaper: owner not live OR claim age > threshold"],
    },
    ("running", "completed"): {
        "description": "Job completed successfully",
        "conditions": ["process_id matches OR handoff owner matches"],
    },
    ("running", "failed"): {
        "description": "Job failed with an error",
        "conditions": ["process_id matches OR handoff owner matches"],
    },
    ("running", "unknown"): {
        "description": "Running claim orphaned — owner died mid-execution",
        "conditions": ["stale-claim reaper: owner not live AND stale_age > threshold"],
    },
    # Illegal re-claims: terminal states have NO outbound arcs
    # This is enforced by the absence of any arc FROM a terminal state
}

_TERMINAL_STATES = frozenset({"completed", "failed", "unknown", "missed", "cancelled"})
_ALL_STATES = frozenset({"claimed", "running", "completed", "failed", "unknown", "missed", "cancelled"})


def is_valid_transition(from_state: str, to_state: str) -> bool:
    """Return True if the state arc (from_state, to_state) is permitted."""
    if from_state not in _ALL_STATES or to_state not in _ALL_STATES:
        return False
    # Terminal states are immutable — no outbound arcs (Harel: absorbing superstates)
    if from_state in _TERMINAL_STATES:
        return False
    return (from_state, to_state) in _VALID_ARCS


def assert_valid_transition(from_state: str, to_state: str) -> None:
    """Raise ValueError if the transition is illegal."""
    if not is_valid_transition(from_state, to_state):
        arc = (from_state, to_state)
        if from_state in _TERMINAL_STATES:
            raise ValueError(
                f"Illegal transition {arc}: {from_state!r} is a terminal state "
                f"(completed/failed/unknown cannot transition to any other state)"
            )
        valid = [str(a) for a in _VALID_ARCS if a[0] == from_state]
        raise ValueError(
            f"Illegal transition {arc}. Valid arcs from {from_state!r}: {valid}"
        )


def validate_transition_sequence(states: list[str]) -> list[dict]:
    """Validate a sequence of states. Returns list of violations (empty = valid)."""
    violations = []
    for i in range(len(states) - 1):
        from_s, to_s = states[i], states[i + 1]
        if not is_valid_transition(from_s, to_s):
            violations.append({
                "index": i,
                "from": from_s,
                "to": to_s,
                "legal": False,
                "reason": f"No arc ({from_s}→{to_s}) in statechart",
            })
    return violations


# ---------------------------------------------------------------------------
# Generation counter (Chubby-style sequencer for stale-write rejection)
# ---------------------------------------------------------------------------
# Stored in executions.db as 'generation INTEGER DEFAULT 0'
# Incremented on every valid transition. A transition attempt with the wrong
# generation is a stale write from a prior owner process (like a Chubby
# delayed packet from before fail-over).

def _get_db_connection() -> Optional[sqlite3.Connection]:
    """Connect to executions.db with WAL mode."""
    if not EXECUTIONS_DB.exists():
        return None
    conn = sqlite3.connect(str(EXECUTIONS_DB), timeout=5.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def assert_fresh_generation(current, expected) -> None:
    """Chubby sequencer: reject stale or NULL generation vs the caller's epoch."""
    if expected is None:
        return
    if current is None:
        raise ValueError("NULL generation (Chubby sequencer: missing epoch)")
    try:
        cur_i = int(current)
        exp_i = int(expected)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid generation current={current!r} expected={expected!r}") from exc
    if cur_i != exp_i:
        raise ValueError(f"stale generation {cur_i} != expected {exp_i}")


def next_generation(current) -> int:
    """Increment generation after a valid transition. NULL/garbage → 1."""
    try:
        return int(current or 0) + 1
    except (TypeError, ValueError):
        return 1


def ensure_generation_column() -> bool:
    """Add generation column to executions table if missing. Returns True if added."""
    conn = _get_db_connection()
    if conn is None:
        logger.warning("executions.db not found at %s", EXECUTIONS_DB)
        return False
    try:
        with conn:
            # Check if column exists
            cols = [row[1] for row in conn.execute("PRAGMA table_info(executions)").fetchall()]
            if "generation" in cols:
                logger.info("generation column already present")
                return False
            conn.execute("ALTER TABLE executions ADD COLUMN generation INTEGER NOT NULL DEFAULT 0")
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_executions_generation "
                "ON executions(job_id, generation)"
            )
            logger.info("Added generation column + index to executions table")
            return True
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Audit: find rows in executions.db with invalid status values
# ---------------------------------------------------------------------------

def audit_executions() -> dict:
    """Scan executions.db for rows with invalid or suspicious state.

    Checks:
      1. status not in known states (schema violation). Known includes scheduler
         terminals 'missed' (window skipped) and 'cancelled'.
      2. Rows where finished_at IS NULL but status IS terminal (inconsistency)
      3. Rows where started_at IS NULL but status='completed' (skipped running)
    """
    conn = _get_db_connection()
    if conn is None:
        return {"error": f"executions.db not found at {EXECUTIONS_DB}", "findings": [], "db": str(EXECUTIONS_DB)}

    findings = []
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(executions)")]
        has_generation = "generation" in cols
        if not has_generation:
            findings.append({
                "id": None,
                "job_id": None,
                "issue": (
                    f"generation column missing on {EXECUTIONS_DB} — "
                    "Chubby sequencer is advisory-only until --ensure-generation"
                ),
                "severity": "HIGH",
            })

        select_cols = "id, job_id, status, claimed_at, started_at, finished_at, pid"
        if has_generation:
            select_cols += ", generation"
        rows = conn.execute(
            f"SELECT {select_cols} "
            "FROM executions ORDER BY claimed_at DESC LIMIT 500"
        ).fetchall()

        for row in rows:
            row = dict(row)
            status = (row.get("status") or "").strip()

            if has_generation and row.get("generation") is None:
                findings.append({
                    "id": row["id"],
                    "job_id": row["job_id"],
                    "issue": "NULL generation (sequencer cannot reject stale writes)",
                    "severity": "HIGH",
                })

            # Check 1: unknown status
            if status not in _ALL_STATES:
                findings.append({
                    "id": row["id"],
                    "job_id": row["job_id"],
                    "issue": f"Unknown status: {status!r}",
                    "severity": "HIGH",
                })

            # Check 2: terminal without finished_at
            if status in _TERMINAL_STATES and not row.get("finished_at"):
                findings.append({
                    "id": row["id"],
                    "job_id": row["job_id"],
                    "issue": f"Terminal status {status!r} with NULL finished_at",
                    "severity": "MEDIUM",
                })

            # Check 3: completed without ever running
            if status == "completed" and not row.get("started_at"):
                findings.append({
                    "id": row["id"],
                    "job_id": row["job_id"],
                    "issue": "Status=completed but started_at is NULL (skipped running state)",
                    "severity": "MEDIUM",
                })

        total = conn.execute("SELECT COUNT(*) FROM executions").fetchone()[0]
        summary = {
            "db": str(EXECUTIONS_DB),
            "has_generation": has_generation,
            "total_rows_scanned": len(rows),
            "total_rows_in_db": total,
            "findings_count": len(findings),
            "findings": findings,
        }
        return summary
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Harel statechart guard for cron execution state machine"
    )
    parser.add_argument("--validate", nargs=2, metavar=("FROM", "TO"),
                        help="Check if a transition is valid")
    parser.add_argument("--audit", action="store_true",
                        help="Audit executions.db for illegal states")
    parser.add_argument("--ensure-generation", action="store_true",
                        help="Add generation column to executions.db if missing")
    parser.add_argument("--print-arcs", action="store_true",
                        help="Print the full statechart transition table")
    parser.add_argument("--self-test", action="store_true",
                        help="Run module smoke tests")
    args = parser.parse_args()

    if args.self_test:
        # Test valid transitions
        assert is_valid_transition("claimed", "running"), "claimed→running should be valid"
        assert is_valid_transition("running", "completed"), "running→completed should be valid"
        assert not is_valid_transition("completed", "running"), "completed→running is illegal"
        assert not is_valid_transition("failed", "completed"), "failed→completed is illegal"
        assert not is_valid_transition("claimed", "completed"), "claimed→completed is illegal (skip running)"
        # Scheduler terminals: missed/cancelled are known valid statuses, not unknown
        assert "missed" in _ALL_STATES and "missed" in _TERMINAL_STATES
        assert "cancelled" in _ALL_STATES and "cancelled" in _TERMINAL_STATES
        assert not is_valid_transition("missed", "running"), "missed is terminal"
        assert not is_valid_transition("cancelled", "claimed"), "cancelled is terminal"
        # Test sequence validation
        violations = validate_transition_sequence(["claimed", "running", "completed"])
        assert violations == [], f"Valid sequence had violations: {violations}"
        bad_violations = validate_transition_sequence(["claimed", "completed"])
        assert len(bad_violations) == 1, "Expected 1 violation for claimed→completed skip"
        assert_fresh_generation(3, 3)
        try:
            assert_fresh_generation(None, 1)
            raise AssertionError("NULL generation should raise")
        except ValueError:
            pass
        try:
            assert_fresh_generation(2, 3)
            raise AssertionError("stale generation should raise")
        except ValueError:
            pass
        assert next_generation(None) == 1
        assert next_generation(4) == 5
        print("self-test OK: all statechart assertions passed")
        return 0

    if args.print_arcs:
        print("Execution state machine arcs:")
        for (from_s, to_s), info in sorted(_VALID_ARCS.items()):
            print(f"  {from_s} → {to_s}: {info['description']}")
        print(f"\nTerminal states (no outbound arcs): {sorted(_TERMINAL_STATES)}")
        return 0

    if args.validate:
        from_s, to_s = args.validate
        valid = is_valid_transition(from_s, to_s)
        arc_info = _VALID_ARCS.get((from_s, to_s), {})
        result = {
            "from": from_s,
            "to": to_s,
            "valid": valid,
            "description": arc_info.get("description", "N/A — illegal arc"),
            "conditions": arc_info.get("conditions", []),
        }
        print(json.dumps(result, indent=2))
        return 0 if valid else 1

    if args.ensure_generation:
        added = ensure_generation_column()
        print("generation column added" if added else "generation column already present")
        return 0

    if args.audit:
        report = audit_executions()
        print(json.dumps(report, indent=2))
        # Exit 1 only for HIGH illegal-state findings. Scheduler statuses such as
        # 'missed' are known terminals; MEDIUM inconsistencies are advisory.
        high = [
            f for f in report.get("findings") or []
            if str(f.get("severity", "")).upper() == "HIGH"
        ]
        return 1 if high else 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
