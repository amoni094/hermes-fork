#!/usr/bin/env python3
"""Memory coherence probe hook.

Data collection for memory-prime-spawn-orchestrator. Logs per-session-turn
joint coherence of episodic / semantic / procedural counts to lifecycle.db
table memory_coherence_log.

joint_coherence = min(ep, sem, proc) / max(max(ep, sem, proc), 1)
spawn_candidate = 1 if score < 0.4

Kill test:
    rec = log_coherence('s1','t1',10,2,1)
    assert rec['joint_coherence_score'] < 0.5
    assert should_spawn('s1') in (True, False)
"""

from __future__ import annotations

import json
import sqlite3
import sys
from datetime import datetime, timezone, UTC
from pathlib import Path
from typing import Any, Optional

HERMES_HOME = Path(__file__).resolve().parents[3]
PROFILE_ROOT = HERMES_HOME / "profiles" / "fork"
DB_PATH = PROFILE_ROOT / "cache" / "lifecycle.db"

SPAWN_THRESHOLD = 0.4

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS memory_coherence_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    session_id TEXT NOT NULL,
    turn_id TEXT NOT NULL,
    episodic_count INTEGER,
    semantic_count INTEGER,
    procedural_count INTEGER,
    joint_coherence_score REAL,
    spawn_candidate INTEGER
)
"""

_conn: Optional[sqlite3.Connection] = None
_using_memory = False


def _init_schema(conn: sqlite3.Connection) -> None:
    conn.execute(SCHEMA_SQL)
    conn.commit()


def _get_conn() -> sqlite3.Connection:
    global _conn, _using_memory
    if _conn is not None:
        return _conn
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(DB_PATH), timeout=5)
        conn.execute('PRAGMA journal_mode=WAL')
        _init_schema(conn)
        _conn = conn
        _using_memory = False
        return _conn
    except Exception:
        conn = sqlite3.connect(":memory:")
        _init_schema(conn)
        _conn = conn
        _using_memory = True
        return _conn


def joint_coherence(episodic_count: int, semantic_count: int, procedural_count: int) -> float:
    ep = max(0, int(episodic_count or 0))
    se = max(0, int(semantic_count or 0))
    pr = max(0, int(procedural_count or 0))
    # Edge case: all counts zero = memory not yet populated, not imbalanced.
    # Return 1.0 (fully coherent / insufficient data) to suppress premature spawn.
    if ep == 0 and se == 0 and pr == 0:
        return 1.0
    numer = min(ep, se, pr)
    denom = max(max(ep, se, pr), 1)
    return float(numer) / float(denom)


def log_coherence(
    session_id: str,
    turn_id: str,
    episodic_count: int,
    semantic_count: int,
    procedural_count: int,
) -> dict[str, Any]:
    score = joint_coherence(episodic_count, semantic_count, procedural_count)
    rec: dict[str, Any] = {
        "ts": datetime.now(UTC).isoformat(),
        "session_id": str(session_id),
        "turn_id": str(turn_id),
        "episodic_count": int(episodic_count or 0),
        "semantic_count": int(semantic_count or 0),
        "procedural_count": int(procedural_count or 0),
        "joint_coherence_score": score,
        "spawn_candidate": 1 if score < SPAWN_THRESHOLD else 0,
        "db_fallback_memory": _using_memory,
    }
    try:
        conn = _get_conn()
        rec["db_fallback_memory"] = _using_memory
        cur = conn.execute(
            """
            INSERT INTO memory_coherence_log (
                ts, session_id, turn_id, episodic_count, semantic_count,
                procedural_count, joint_coherence_score, spawn_candidate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rec["ts"],
                rec["session_id"],
                rec["turn_id"],
                rec["episodic_count"],
                rec["semantic_count"],
                rec["procedural_count"],
                rec["joint_coherence_score"],
                rec["spawn_candidate"],
            ),
        )
        conn.commit()
        rec["id"] = int(cur.lastrowid or 0)
    except Exception as exc:
        rec["id"] = None
        rec["db_error"] = type(exc).__name__
    return rec


def get_coherence_trend(session_id: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        conn = _get_conn()
        cur = conn.execute(
            """
            SELECT id, ts, session_id, turn_id, episodic_count, semantic_count,
                   procedural_count, joint_coherence_score, spawn_candidate
            FROM memory_coherence_log
            WHERE session_id = ?
            ORDER BY id ASC
            """,
            (str(session_id),),
        )
        cols = [
            "id",
            "ts",
            "session_id",
            "turn_id",
            "episodic_count",
            "semantic_count",
            "procedural_count",
            "joint_coherence_score",
            "spawn_candidate",
        ]
        for tup in cur.fetchall():
            rec = dict(zip(cols, tup))
            rec["joint_coherence_score"] = float(rec["joint_coherence_score"] or 0.0)
            rows.append(rec)
        return rows
    except Exception:
        return rows


def should_spawn(session_id: str) -> bool:
    """True if the last 3 turns' mean joint_coherence is below 0.4."""
    try:
        trend = get_coherence_trend(session_id)
        if len(trend) < 3:
            return False
        last3 = trend[-3:]
        mean = sum(float(r["joint_coherence_score"]) for r in last3) / 3.0
        return mean < SPAWN_THRESHOLD
    except Exception:
        return False


def layer1_demo() -> None:
    # Use isolated in-memory DB — never write to production lifecycle.db
    import sqlite3 as _sqlite3
    global _conn, _using_memory
    _saved_conn, _saved_mem = _conn, _using_memory
    _conn = _sqlite3.connect(":memory:")
    _using_memory = True
    _init_schema(_conn)
    try:
        rec = log_coherence("s1", "t1", 10, 2, 1)
        assert rec["joint_coherence_score"] < 0.5, rec
        assert rec["joint_coherence_score"] == 1.0 / 10.0
        assert rec["spawn_candidate"] == 1
        assert should_spawn("s1") in (True, False)

        sid = "layer1-low-coherence"
        for i, counts in enumerate(((12, 1, 1), (9, 2, 1), (15, 1, 0), (8, 1, 1)), start=1):
            log_coherence(sid, f"t{i}", *counts)

        trend = get_coherence_trend(sid)
        assert len(trend) >= 3, trend
        assert should_spawn(sid) is True

        sid_ok = "layer1-balanced"
        for i in range(1, 4):
            log_coherence(sid_ok, f"t{i}", 5, 5, 5)
        assert should_spawn(sid_ok) is False
        balanced = joint_coherence(5, 5, 5)
        assert balanced == 1.0

        assert joint_coherence(0, 0, 0) == 1.0  # all-zero = insufficient data, no spawn
        print(
            f"[layer1] PASS — kill_score={rec['joint_coherence_score']:.3f} "
            f"spawn_low={should_spawn(sid)} spawn_ok={should_spawn(sid_ok)} "
            f"trend_n={len(trend)} backend=memory (isolated)"
        )
    finally:
        try: _conn.close()
        except Exception: pass
        _conn, _using_memory = _saved_conn, _saved_mem
def main() -> None:
    if "--layer1" in sys.argv:
        layer1_demo()
        return
    rec = log_coherence("synthetic", "t0", 4, 4, 3)
    print(
        json.dumps(
            {
                "record": rec,
                "trend": get_coherence_trend("synthetic"),
                "should_spawn": should_spawn("synthetic"),
            },
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
