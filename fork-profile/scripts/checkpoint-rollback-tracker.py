#!/usr/bin/env python3
"""
Checkpoint Rollback Tracker

Logs (memory_id, action_id, depends_on) dependency edges to lifecycle.db
table 'atp_checkpoints'. On rollback, identifies the minimum rollback set
for a given action_id by traversing dependency edges in reverse — no full
replay required.

Hypothesis: (memory_id, action_id) edge logging enables precise rollback
    to any prior state in O(depth) traversal rather than O(N) full replay.

GWT:
  Given: a sequence of recorded checkpoints with dependency edges,
  When:  get_rollback_set(action_id) is called,
  Then:  all transitively dependent action_ids are returned (not more, not less).

Kill test:
    cid  = record_checkpoint('m1', 'a1')
    cid2 = record_checkpoint('m2', 'a2', ['a1'])
    rs   = get_rollback_set('a2')
    assert 'a1' in rs

Schema:
    atp_checkpoints(
        id        INTEGER PRIMARY KEY,
        ts        TEXT,
        memory_id TEXT,
        action_id TEXT UNIQUE,
        depends_on TEXT,       -- JSON list of action_ids
        state_hash TEXT,
        rolled_back INTEGER DEFAULT 0
    )
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone, UTC
from pathlib import Path
from typing import Optional

# ── Paths ─────────────────────────────────────────────────────────────────────
HERMES_HOME  = Path(__file__).resolve().parents[3]
PROFILE_ROOT = HERMES_HOME / "profiles" / "fork"
DB_PATH      = PROFILE_ROOT / "cache" / "lifecycle.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS atp_checkpoints (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT    NOT NULL,
    memory_id   TEXT    NOT NULL,
    action_id   TEXT    NOT NULL,
    depends_on  TEXT    NOT NULL DEFAULT '[]',
    state_hash  TEXT    NOT NULL DEFAULT '',
    rolled_back INTEGER NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_atp_action
    ON atp_checkpoints(action_id);
"""

# ── DB helpers ────────────────────────────────────────────────────────────────
@contextmanager
def _connect(db_path: Path = DB_PATH):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute('PRAGMA journal_mode=WAL')
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(_SCHEMA)
        conn.commit()
        yield conn
    finally:
        conn.close()


def _hash(memory_id: str, action_id: str, depends_on: list[str]) -> str:
    key = json.dumps({"m": memory_id, "a": action_id, "d": sorted(depends_on)}, sort_keys=True)
    return hashlib.sha256(key.encode()).hexdigest()[:16]


# ── Public API ────────────────────────────────────────────────────────────────
def record_checkpoint(
    memory_id: str,
    action_id: str,
    depends_on: Optional[list[str]] = None,
    db_path: Path = DB_PATH,
) -> int:
    """
    Record a checkpoint edge. Returns the row id.
    If action_id already exists, updates depends_on and state_hash.
    """
    deps = depends_on or []
    ts   = datetime.now(UTC).isoformat()
    sh   = _hash(memory_id, action_id, deps)
    with _connect(db_path) as conn:
        conn.execute(
            """INSERT INTO atp_checkpoints (ts, memory_id, action_id, depends_on, state_hash)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(action_id) DO UPDATE SET
                   ts=excluded.ts, memory_id=excluded.memory_id,
                   depends_on=excluded.depends_on, state_hash=excluded.state_hash""",
            (ts, memory_id, action_id, json.dumps(deps), sh),
        )
        conn.commit()
        row = conn.execute(
            "SELECT id FROM atp_checkpoints WHERE action_id=?", (action_id,)
        ).fetchone()
        if row is None:
            raise RuntimeError(f"checkpoint for {action_id!r} not found after insert")
        return int(row["id"])


def get_ancestor_set(
    action_id: str,
    db_path: Path = DB_PATH,
) -> list[str]:
    """Return action_id plus all actions it transitively depends on (ancestors).
    Useful for determining what must have succeeded for this action to be valid.
    """
    with _connect(db_path) as conn:
        visited: set[str] = set()
        queue   = [action_id]
        while queue:
            cur = queue.pop()
            if cur in visited:
                continue
            visited.add(cur)
            row = conn.execute(
                "SELECT depends_on FROM atp_checkpoints WHERE action_id=?", (cur,)
            ).fetchone()
            if row:
                deps = json.loads(row["depends_on"])
                queue.extend(d for d in deps if d not in visited)
    return list(visited)


def get_rollback_set(
    action_id: str,
    db_path: Path = DB_PATH,
) -> list[str]:
    """Return action_id plus all actions that transitively depend on it (dependents).
    These are the actions that must be rolled back when rolling back action_id,
    because they built on a state that will no longer exist.
    Builds a reverse-edge index from the full checkpoint table, then BFS forward.
    """
    with _connect(db_path) as conn:
        # Build reverse adjacency: action_id -> list of actions that depend on it
        rows = conn.execute(
            "SELECT action_id, depends_on FROM atp_checkpoints WHERE rolled_back=0"
        ).fetchall()
        reverse: dict[str, list[str]] = {}
        for row in rows:
            for dep in json.loads(row["depends_on"]):
                reverse.setdefault(dep, []).append(row["action_id"])
        # BFS from action_id following forward (dependent) edges
        visited: set[str] = set()
        queue = [action_id]
        while queue:
            cur = queue.pop()
            if cur in visited:
                continue
            visited.add(cur)
            queue.extend(a for a in reverse.get(cur, []) if a not in visited)
    return list(visited)


def mark_rolled_back(
    action_ids: list[str],
    db_path: Path = DB_PATH,
) -> None:
    """Mark a list of action_ids as rolled_back=1."""
    with _connect(db_path) as conn:
        conn.executemany(
            "UPDATE atp_checkpoints SET rolled_back=1 WHERE action_id=?",
            [(aid,) for aid in action_ids],
        )
        conn.commit()


def get_checkpoint(action_id: str, db_path: Path = DB_PATH) -> Optional[dict]:
    """Fetch a single checkpoint by action_id."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM atp_checkpoints WHERE action_id=?", (action_id,)
        ).fetchone()
        if row is None:
            return None
        return dict(row)


def list_checkpoints(include_rolled_back: bool = False, db_path: Path = DB_PATH) -> list[dict]:
    """List all checkpoints, optionally excluding rolled-back ones."""
    with _connect(db_path) as conn:
        q = "SELECT * FROM atp_checkpoints"
        if not include_rolled_back:
            q += " WHERE rolled_back=0"
        q += " ORDER BY id"
        return [dict(r) for r in conn.execute(q).fetchall()]


# ── Layer1 demo ───────────────────────────────────────────────────────────────
def layer1_demo() -> None:
    import tempfile

    tmp_db = Path(tempfile.mktemp(suffix=".db"))
    try:
        # Record a chain: a1 ← a2 ← a3
        r1 = record_checkpoint("m1", "a1", db_path=tmp_db)
        r2 = record_checkpoint("m2", "a2", depends_on=["a1"], db_path=tmp_db)
        r3 = record_checkpoint("m3", "a3", depends_on=["a2"], db_path=tmp_db)
        assert r1 > 0 and r2 > 0 and r3 > 0, "row ids must be positive"

        # get_rollback_set(a1) = {a1, a2, a3}: rolling back a1 cascades to all dependents
        rs1 = get_rollback_set("a1", db_path=tmp_db)
        assert "a1" in rs1, f"a1 missing from own rollback set: {rs1}"
        assert "a2" in rs1, f"a2 must be in a1 rollback set: {rs1}"
        assert "a3" in rs1, f"a3 must be in a1 rollback set: {rs1}"

        # get_rollback_set(a3) = {a3}: nothing depends on a3
        rs3 = get_rollback_set("a3", db_path=tmp_db)
        assert rs3 == ["a3"], f"Expected only ['a3'], got {rs3}"

        # get_ancestor_set(a3) = {a1, a2, a3}: what a3 transitively needs
        as3 = get_ancestor_set("a3", db_path=tmp_db)
        assert "a1" in as3 and "a2" in as3 and "a3" in as3, f"ancestors of a3 wrong: {as3}"

        # mark_rolled_back
        mark_rolled_back(["a3"], db_path=tmp_db)
        cp = get_checkpoint("a3", db_path=tmp_db)
        assert cp["rolled_back"] == 1, "a3 should be rolled_back=1"

        # list_checkpoints excludes rolled-back by default
        active = list_checkpoints(include_rolled_back=False, db_path=tmp_db)
        assert not any(c["action_id"] == "a3" for c in active), "a3 should not appear in active list"

        # Branching: a4 depends on a1 only
        record_checkpoint("m4", "a4", depends_on=["a1"], db_path=tmp_db)
        # rollback a1 now cascades to a2 AND a4 (but not a3 - already rolled back)
        rs1b = get_rollback_set("a1", db_path=tmp_db)
        assert "a4" in rs1b, f"a4 should depend on a1: {rs1b}"
        assert "a2" in rs1b, f"a2 should depend on a1: {rs1b}"

        print(
            f"[layer1] PASS — rollback(a1)={sorted(rs1)}  rollback(a3)={rs3}  "
            f"ancestors(a3)={sorted(as3)}  active_count={len(active)}"
        )
    finally:
        tmp_db.unlink(missing_ok=True)


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    import argparse
    pa = argparse.ArgumentParser(description="Checkpoint Rollback Tracker")
    pa.add_argument("--layer1",   action="store_true")
    pa.add_argument("--list",     action="store_true", help="List active checkpoints")
    pa.add_argument("--rollback", metavar="ACTION_ID",  help="Show rollback set for action_id")
    pa.add_argument("--apply-rollback", metavar="ACTION_ID",
                    help="Mark rollback set as rolled_back=1")
    args = pa.parse_args()

    if args.layer1:
        layer1_demo()
        return

    if args.list:
        cps = list_checkpoints()
        print(f"Active checkpoints: {len(cps)}")
        for cp in cps:
            print(f"  [{cp['id']}] {cp['action_id']}  mem={cp['memory_id']}  deps={cp['depends_on']}")
        return

    if args.rollback:
        rs = get_rollback_set(args.rollback)
        print(f"Rollback set for {args.rollback}: {rs}")
        return

    if args.apply_rollback:
        rs = get_rollback_set(args.apply_rollback)
        mark_rolled_back(rs)
        print(f"Marked rolled_back: {rs}")
        return

    pa.print_help()


if __name__ == "__main__":
    main()
