#!/usr/bin/env python3
"""
memory-provenance.py — Provenance edge store for dependency-guided rollback.

Records (memory_id → action_id) edges so that when a memory is invalidated,
its downstream action dependencies can be identified and flagged as potentially stale.

Based on:
  arXiv:2608.10502 — Dependency-Guided Rollback Repair (Aug 2026)
  Key insight: deleting a poisoned/stale memory without tracing its downstream
  action dependencies leaves propagated claims active. This store enables
  dependency-aware invalidation.

Schema:
  provenance_edges: memory_id → action_id, timestamp, context (what the memory was used for)
  invalidation_log: when a memory is superseded, log what action_ids are now stale

Usage:
  python3 memory-provenance.py write --memory-id <id> --action-id <id> [--context "..."]
  python3 memory-provenance.py invalidate --memory-id <id>
  python3 memory-provenance.py query --memory-id <id>
  python3 memory-provenance.py stale                    # list all stale action_ids

Callable as a module: from memory_provenance import write_edge, invalidate_memory, stale_actions
"""
import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

FACTS_DIR = Path.home() / ".hermes" / "memory-facts"
PROVENANCE_DB = FACTS_DIR / "provenance.db"


def _init_db(conn: sqlite3.Connection):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS provenance_edges (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_id       TEXT NOT NULL,
            action_id       TEXT NOT NULL,
            ts              TEXT NOT NULL,
            context         TEXT,
            UNIQUE(memory_id, action_id)
        );
        CREATE INDEX IF NOT EXISTS idx_prov_memory ON provenance_edges(memory_id);
        CREATE INDEX IF NOT EXISTS idx_prov_action ON provenance_edges(action_id);

        CREATE TABLE IF NOT EXISTS invalidation_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            memory_id       TEXT NOT NULL,
            ts              TEXT NOT NULL,
            reason          TEXT,
            stale_action_ids TEXT   -- JSON array of action_ids that used this memory
        );
        CREATE INDEX IF NOT EXISTS idx_inv_memory ON invalidation_log(memory_id);
    """)


def write_edge(memory_id: str, action_id: str, context: str = "") -> bool:
    """Record that action_id used memory_id as a premise. Idempotent."""
    FACTS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with sqlite3.connect(str(PROVENANCE_DB)) as conn:
            _init_db(conn)
            ts = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT OR IGNORE INTO provenance_edges (memory_id, action_id, ts, context) VALUES (?,?,?,?)",
                (memory_id, action_id, ts, context),
            )
        return True
    except Exception as e:
        print(f"[memory-provenance] write_edge error: {e}", file=sys.stderr)
        return False


def invalidate_memory(memory_id: str, reason: str = "") -> list[str]:
    """Mark memory_id as invalidated. Returns list of stale action_ids that used it."""
    FACTS_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with sqlite3.connect(str(PROVENANCE_DB)) as conn:
            _init_db(conn)
            rows = conn.execute(
                "SELECT action_id FROM provenance_edges WHERE memory_id=?",
                (memory_id,),
            ).fetchall()
            stale_ids = [r[0] for r in rows]
            ts = datetime.now(timezone.utc).isoformat()
            conn.execute(
                "INSERT INTO invalidation_log (memory_id, ts, reason, stale_action_ids) VALUES (?,?,?,?)",
                (memory_id, ts, reason, json.dumps(stale_ids)),
            )
        return stale_ids
    except Exception as e:
        print(f"[memory-provenance] invalidate_memory error: {e}", file=sys.stderr)
        return []


def stale_actions() -> list[dict]:
    """Return all action_ids that have been marked stale by an invalidation."""
    if not PROVENANCE_DB.exists():
        return []
    try:
        with sqlite3.connect(str(PROVENANCE_DB)) as conn:
            _init_db(conn)
            rows = conn.execute(
                "SELECT memory_id, ts, reason, stale_action_ids FROM invalidation_log ORDER BY ts DESC"
            ).fetchall()
            result = []
            for r in rows:
                ids = json.loads(r[3]) if r[3] else []
                for aid in ids:
                    result.append({"memory_id": r[0], "action_id": aid, "ts": r[1], "reason": r[2]})
            return result
    except Exception as e:
        print(f"[memory-provenance] stale_actions error: {e}", file=sys.stderr)
        return []


def query_edges(memory_id: str) -> list[dict]:
    """Return all action_ids that used the given memory_id."""
    if not PROVENANCE_DB.exists():
        return []
    try:
        with sqlite3.connect(str(PROVENANCE_DB)) as conn:
            _init_db(conn)
            rows = conn.execute(
                "SELECT action_id, ts, context FROM provenance_edges WHERE memory_id=? ORDER BY ts",
                (memory_id,),
            ).fetchall()
            return [{"action_id": r[0], "ts": r[1], "context": r[2]} for r in rows]
    except Exception as e:
        print(f"[memory-provenance] query_edges error: {e}", file=sys.stderr)
        return []


def main():
    p = argparse.ArgumentParser(description="Provenance edge store for dependency-guided rollback")
    sub = p.add_subparsers(dest="cmd")

    w = sub.add_parser("write", help="Record memory_id → action_id edge")
    w.add_argument("--memory-id", required=True)
    w.add_argument("--action-id", required=True)
    w.add_argument("--context", default="")

    inv = sub.add_parser("invalidate", help="Mark a memory as invalidated, return stale action_ids")
    inv.add_argument("--memory-id", required=True)
    inv.add_argument("--reason", default="")

    q = sub.add_parser("query", help="Show action_ids that used a memory")
    q.add_argument("--memory-id", required=True)

    sub.add_parser("stale", help="List all stale action_ids from invalidations")

    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        sys.exit(2)

    if args.cmd == "write":
        ok = write_edge(args.memory_id, args.action_id, args.context)
        print("OK" if ok else "FAILED")
    elif args.cmd == "invalidate":
        stale = invalidate_memory(args.memory_id, args.reason)
        print(json.dumps({"stale_action_ids": stale}, indent=2))
    elif args.cmd == "query":
        edges = query_edges(args.memory_id)
        print(json.dumps(edges, indent=2))
    elif args.cmd == "stale":
        items = stale_actions()
        print(json.dumps(items, indent=2))


# === Beta-Binomial Trust Posterior (Gelman BDA3 Ch 2) ===
# Model source reliability as Beta distribution. Update with recall outcomes.
import json as _json_bda
from pathlib import Path as _Path_bda

import os as _os_mp
_hermes_base_mp = _Path_bda(_os_mp.environ.get("HERMES_HOME", str(_Path_bda.home() / ".hermes")))
_hermes_profile_mp = _os_mp.environ.get("HERMES_PROFILE", "")
_hermes_root_mp = (_hermes_base_mp / "profiles" / _hermes_profile_mp) if _hermes_profile_mp and "profiles" not in str(_hermes_base_mp) else _hermes_base_mp
_TRUST_POST_PATH = _hermes_root_mp / "cache" / "trust-posterior.json"
_TRUST_WEIGHTS_STATIC = {'internal': 1.0, 'cron': 0.85, 'external': 0.70}

def _load_trust_posteriors():
    try:
        if _TRUST_POST_PATH.exists():
            return _json_bda.loads(_TRUST_POST_PATH.read_text())
    except Exception:
        pass
    return {s: {'alpha': 2.0, 'beta': 1.0} for s in _TRUST_WEIGHTS_STATIC}

def update_trust_posterior(source, reward):
    try:
        state = _load_trust_posteriors()
        if source not in state:
            state[source] = {'alpha': 2.0, 'beta': 1.0}
        state[source]['alpha'] += float(reward)
        state[source]['beta'] += float(1.0 - reward)
        _TRUST_POST_PATH.parent.mkdir(parents=True, exist_ok=True)
        # L8 fix: atomic write via tmp+rename to prevent Beta posterior corruption
        _tp_tmp = _TRUST_POST_PATH.with_suffix('.tmp')
        _tp_tmp.write_text(_json_bda.dumps(state, indent=2))
        _tp_tmp.rename(_TRUST_POST_PATH)
    except Exception:
        pass

def get_trust_weight(source):
    try:
        state = _load_trust_posteriors()
        if source in state:
            a, b = state[source]['alpha'], state[source]['beta']
            return a / (a + b)
    except Exception:
        pass
    return _TRUST_WEIGHTS_STATIC.get(source, 0.7)


if __name__ == "__main__":
    main()
