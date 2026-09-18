#!/usr/bin/env python3
"""
Durable Run Ledger for Hermes agents.

Ported from Denuto `src/run_ledger/` (ADR-0010 pattern).

Implements:
  - CoordinationStore: conditional writes only (OCC — Kung & Robinson 1981)
  - ContentStore: content-addressed immutable objects (Merkle DAG pattern)
  - Clock: injected time source (testable/deterministic)
  - State machine with is_legal_transition() guards (Lamport crash-boundary)
  - RetryPolicy: exponential backoff with full jitter, explicit random.Random
  - DecisionAuditChain: append-only SHA-256 hash chain (tamper-evident audit log)

Theoretical foundations:
  - Conditional writes = Optimistic Concurrency Control (Kung & Robinson 1981)
  - Content addressing = Merkle DAG (same structure as git objects)
  - Hash chain = same structure as blockchain / certificate transparency logs.
    Modifying any event invalidates all subsequent hashes — tamper-evident.
  - Full-jitter backoff = Karn's algorithm

Stdlib-only. No external dependencies.

Usage:
    from run_ledger import (
        RunLedger, CoordinationStore, ContentStore, Clock,
        RetryPolicy, DecisionAuditChain, StateTransition,
    )

    clock = Clock()
    ledger = RunLedger(run_id="run_abc", clock=clock)
    ledger.transition("pending", "running")
    ledger.add_event("task_started", {"task": "analyze"})
    content_key = ledger.store_content("output text here")
    print(ledger.audit_chain.verify())
"""

from __future__ import annotations

import hashlib
import json
import random
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

DEFAULT_LEDGER_DIR = Path.home() / ".hermes" / "logs" / "run_ledger"

# Valid state transitions for a Hermes run
RUN_LEGAL_TRANSITIONS: dict[str, set[str]] = {
    "pending":      {"running", "cancelled"},
    "running":      {"completed", "failed", "cancelled"},
    "completed":    set(),   # terminal
    "failed":       {"running"},  # allow retry
    "cancelled":    set(),   # terminal
}


class Clock:
    """
    Injected time source. Replace with a fake in tests for deterministic timing.

    class FakeClock(Clock):
        def __init__(self, start=0.0): self._t = start
        def now(self) -> float: self._t += 0.001; return self._t
        def now_iso(self) -> str: return f"T+{self._t:.3f}"
    """
    def now(self) -> float:
        return time.time()

    def now_iso(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.now()))


@dataclass
class RetryPolicy:
    """
    Exponential backoff with full jitter (Karn's algorithm).
    Uses explicitly-passed rng (never module-global) for reproducibility.
    """
    max_attempts: int = 5
    base: float = 1.0
    cap: float = 32.0
    rng: random.Random = field(default_factory=random.Random)

    def sleep_duration(self, attempt: int) -> float:
        """Full-jitter: uniform in [0, min(cap, base * 2^attempt)]"""
        slot = min(self.cap, self.base * (2 ** attempt))
        return self.rng.uniform(0, slot)

    def should_retry(self, attempt: int) -> bool:
        return attempt < self.max_attempts


class ContentStore:
    """
    Content-addressed immutable object store.
    Write-once: storing the same content is idempotent.
    Key = SHA-256(content). Merkle DAG pattern.
    """

    def __init__(self, store_dir: Path | None = None) -> None:
        self._dir = store_dir or (DEFAULT_LEDGER_DIR / "content")
        self._dir.mkdir(parents=True, exist_ok=True)

    def put(self, content: str | bytes) -> str:
        """Store content. Returns content-address key (SHA-256 hex)."""
        if isinstance(content, str):
            content = content.encode("utf-8")
        key = hashlib.sha256(content).hexdigest()
        path = self._dir / key
        if not path.exists():
            path.write_bytes(content)
        return key

    def get(self, key: str) -> bytes | None:
        """Retrieve by key. Returns None if not found."""
        path = self._dir / key
        return path.read_bytes() if path.exists() else None

    def exists(self, key: str) -> bool:
        return (self._dir / key).exists()


class CoordinationStore:
    """
    Coordination state store with CONDITIONAL WRITES ONLY.

    No unconditional writes. This is Optimistic Concurrency Control (OCC):
    all writes either create-if-absent or update-if-current-matches.

    Backed by a JSONL file for durability.
    """

    def __init__(self, store_path: Path | None = None) -> None:
        self._path = store_path or (DEFAULT_LEDGER_DIR / "coordination.json")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._data: dict[str, Any] = {}
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text())
            except (json.JSONDecodeError, OSError):
                self._data = {}

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._data, indent=2))

    def put_if_absent(self, key: str, value: Any) -> bool:
        """Write only if key doesn't exist. Returns True if written."""
        with self._lock:
            if key in self._data:
                return False
            self._data[key] = value
            self._save()
            return True

    def update_if(self, key: str, expected: Any, new_value: Any) -> bool:
        """Update only if current value matches expected. Returns True if updated."""
        with self._lock:
            if self._data.get(key) != expected:
                return False
            self._data[key] = new_value
            self._save()
            return True

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def read_all(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._data)


class DecisionAuditChain:
    """
    Append-only SHA-256 hash chain for tamper-evident audit log.

    Same structure as blockchain / certificate transparency logs.
    Modifying any event invalidates all subsequent hashes.

    Should be used for skill version auditing and run audit trails.
    """

    def __init__(self, chain_path: Path | None = None) -> None:
        self._path = chain_path or (DEFAULT_LEDGER_DIR / "audit_chain.jsonl")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._prev_hash = "0" * 64  # genesis hash
        # Replay existing chain to restore _prev_hash for append continuity
        if self._path.exists():
            try:
                with self._path.open("r", encoding="utf-8") as _f:
                    for _line in _f:
                        _line = _line.strip()
                        if not _line:
                            continue
                        try:
                            _entry = json.loads(_line)
                            if "event_hash" in _entry:
                                self._prev_hash = _entry["event_hash"]
                        except json.JSONDecodeError:
                            pass
            except OSError:
                pass

    def _compute_event_hash(self, payload_hash: str) -> str:
        combined = f"{self._prev_hash}:{payload_hash}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def append(self, event_type: str, payload: dict[str, Any], clock: Clock | None = None) -> str:
        """
        Append an event. Returns the event hash.
        Thread-safe.
        """
        clk = clock or Clock()
        with self._lock:
            payload_str = json.dumps(payload, sort_keys=True)
            payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()
            event_hash = self._compute_event_hash(payload_hash)
            entry = {
                "event_type": event_type,
                "ts": clk.now_iso(),
                "payload_hash": payload_hash,
                "event_hash": event_hash,
                "prev_hash": self._prev_hash,
                "payload": payload,
            }
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
            self._prev_hash = event_hash
            return event_hash

    def verify(self) -> bool:
        """
        Verify the entire chain. Returns True if unmodified.
        Any tampering → subsequent hashes won't match.
        """
        if not self._path.exists():
            return True
        prev = "0" * 64
        with self._path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    return False
                if entry.get("prev_hash") != prev:
                    return False
                payload_str = json.dumps(entry["payload"], sort_keys=True)
                payload_hash = hashlib.sha256(payload_str.encode()).hexdigest()
                if payload_hash != entry.get("payload_hash"):
                    return False
                combined = f"{prev}:{payload_hash}"
                expected_event_hash = hashlib.sha256(combined.encode()).hexdigest()
                if expected_event_hash != entry.get("event_hash"):
                    return False
                prev = entry["event_hash"]
        return True


class RunLedger:
    """
    Durable run ledger combining all crash-boundary patterns.

    - CoordinationStore for state transitions (conditional writes)
    - ContentStore for output artifacts (content-addressed)
    - DecisionAuditChain for tamper-evident audit log
    - Injected Clock for deterministic testing
    """

    def __init__(
        self,
        run_id: str,
        clock: Clock | None = None,
        ledger_dir: Path | None = None,
        legal_transitions: dict[str, set[str]] | None = None,
    ) -> None:
        self.run_id = run_id
        self._clock = clock or Clock()
        base = ledger_dir or DEFAULT_LEDGER_DIR
        self._coord = CoordinationStore(base / f"{run_id}_coord.json")
        self._content = ContentStore(base / "content")
        self._audit = DecisionAuditChain(base / f"{run_id}_audit.jsonl")
        self._legal = legal_transitions or RUN_LEGAL_TRANSITIONS

        # Initialize state (put_if_absent: no-op on re-attach; genesis only written once)
        is_new = self._coord.put_if_absent("state", "pending")
        self._coord.put_if_absent("run_id", run_id)
        self._coord.put_if_absent("created_at", self._clock.now_iso())
        if is_new:
            # New run: write genesis event (only once)
            self._audit.append("run_created", {"run_id": run_id}, self._clock)

    @property
    def state(self) -> str:
        return self._coord.get("state", "pending")

    def transition(self, to_state: str) -> bool:
        """
        Transition to a new state. RAISES on illegal transition.
        Uses conditional write (OCC) — safe under concurrent access.
        """
        from_state = self.state
        if to_state not in self._legal.get(from_state, set()):
            raise ValueError(
                f"Illegal state transition: {from_state!r} → {to_state!r} "
                f"for run {self.run_id!r}. "
                f"Legal from {from_state!r}: {self._legal.get(from_state, set())!r}"
            )
        ok = self._coord.update_if("state", from_state, to_state)
        if ok:
            self._audit.append(
                "state_transition",
                {"run_id": self.run_id, "from": from_state, "to": to_state},
                self._clock,
            )
        return ok

    def add_event(self, event_type: str, payload: dict[str, Any]) -> str:
        """Add a custom event to the audit chain. Returns event hash."""
        return self._audit.append(event_type, {"run_id": self.run_id, **payload}, self._clock)

    def store_content(self, content: str | bytes) -> str:
        """Store content artifact. Returns content-address key."""
        key = self._content.put(content)
        self._audit.append("content_stored", {"run_id": self.run_id, "content_key": key}, self._clock)
        return key

    def get_content(self, key: str) -> bytes | None:
        return self._content.get(key)

    def verify_audit(self) -> bool:
        """Verify the audit chain for this run. Returns True if unmodified."""
        return self._audit.verify()

    def summary(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "state": self.state,
            "audit_valid": self.verify_audit(),
            **self._coord.read_all(),
        }


# ── CLI entry point ───────────────────────────────────────────────────────────

def _cmd_create(args) -> int:
    """CLI: create a new run entry (pending → running)."""
    import sys as _sys
    run_id = args.run_id
    goal = args.goal
    try:
        ledger = RunLedger(run_id)
        # Record goal as a custom event
        ledger.add_event("goal_set", {"goal": goal})
        # Transition immediately to running
        ledger.transition("running")
        summary = ledger.summary()
        summary["goal"] = goal
        print(json.dumps(summary, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=_sys.stderr)
        return 1


def _cmd_complete(args) -> int:
    """CLI: mark a run as completed."""
    import sys as _sys
    run_id = args.run_id
    try:
        ledger = RunLedger(run_id)
        ledger.transition("completed")
        print(json.dumps(ledger.summary(), indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=_sys.stderr)
        return 1


def _cmd_fail(args) -> int:
    """CLI: mark a run as failed with a reason."""
    import sys as _sys
    run_id = args.run_id
    reason = args.reason
    try:
        ledger = RunLedger(run_id)
        ledger.add_event("failure_reason", {"reason": reason})
        ledger.transition("failed")
        print(json.dumps(ledger.summary(), indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=_sys.stderr)
        return 1


def _cmd_status(args) -> int:
    """CLI: show status summary of a run."""
    import sys as _sys
    run_id = args.run_id
    try:
        ledger = RunLedger(run_id)
        print(json.dumps(ledger.summary(), indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=_sys.stderr)
        return 1


def main() -> int:
    import argparse as _argparse
    import sys as _sys

    parser = _argparse.ArgumentParser(
        description="Run Ledger CLI — durable run tracking with OCC and audit chain"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # create
    p_create = sub.add_parser("create", help="Create and start a new run")
    p_create.add_argument("run_id", help="Unique run identifier (e.g. job-001)")
    p_create.add_argument("goal", help="Human-readable goal description")
    p_create.set_defaults(func=_cmd_create)

    # complete
    p_complete = sub.add_parser("complete", help="Mark a run as completed")
    p_complete.add_argument("run_id", help="Run identifier to complete")
    p_complete.set_defaults(func=_cmd_complete)

    # fail
    p_fail = sub.add_parser("fail", help="Mark a run as failed with a reason")
    p_fail.add_argument("run_id", help="Run identifier to fail")
    p_fail.add_argument("reason", help="Failure reason string")
    p_fail.set_defaults(func=_cmd_fail)

    # status
    p_status = sub.add_parser("status", help="Show current status of a run")
    p_status.add_argument("run_id", help="Run identifier to query")
    p_status.set_defaults(func=_cmd_status)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(main())
