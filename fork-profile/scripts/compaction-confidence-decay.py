#!/usr/bin/env python3
"""compaction-confidence-decay.py — Anderson (1994) RIF confidence decay.

Facts in compaction_gate_facts compete for retrieval slots. Older facts
whose token overlap with newer same-session facts is high have confidence
decayed so HINDSIGHT CONTEXT is not dominated by stale, superseded facts.

Usage:
  HERMES_HOME=... python3 compaction-confidence-decay.py
  HERMES_HOME=... python3 compaction-confidence-decay.py --self-test
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DECAY_FACTOR = 0.85
JACCARD_THRESHOLD = 0.5
MIN_CONFIDENCE = 0.05
TOKEN_RE = re.compile(r"[a-z0-9]+")
SQLITE_TIMEOUT = 10.0


def _hermes_home() -> Path:
    raw = os.environ.get("HERMES_HOME")
    return Path(raw) if raw else Path.home() / ".hermes"


def _profile_root() -> Path:
    hh = _hermes_home()
    if hh.name == "fork":
        return hh
    return hh / "profiles" / "fork"


def db_path() -> Path:
    hh = _hermes_home()
    path = hh / "state.db"
    if hh.name != "fork":
        path = hh / "profiles" / "fork" / "state.db"
    return path


def _cache_dir() -> Path:
    return _profile_root() / "cache"


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def word_tokens(text: str) -> set[str]:
    return set(TOKEN_RE.findall((text or "").lower()))


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / float(len(union))


def _open_db(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=SQLITE_TIMEOUT)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS compaction_gate_facts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  TEXT    NOT NULL,
            topic       TEXT    NOT NULL DEFAULT '',
            fact_text   TEXT    NOT NULL,
            confidence  REAL    NOT NULL DEFAULT 1.0,
            created_at  REAL    NOT NULL,
            dedup_hash  TEXT    NOT NULL UNIQUE
        )
        """
    )
    cols = {row[1] for row in conn.execute("PRAGMA table_info(compaction_gate_facts)")}
    if "last_decay_at" not in cols:
        conn.execute("ALTER TABLE compaction_gate_facts ADD COLUMN last_decay_at REAL")


def decay_session_facts(facts: list[dict[str, Any]]) -> list[tuple[int, float, float]]:
    """Return (id, old_conf, new_conf) for facts whose confidence should change.

    facts must be sorted oldest-first. Decay applies only vs NEWER facts.
    """
    updates: list[tuple[int, float, float]] = []
    tokenized = [word_tokens(str(f.get("fact_text") or "")) for f in facts]
    n = len(facts)
    for i in range(n):
        older = facts[i]
        older_toks = tokenized[i]
        competitors = 0
        for j in range(i + 1, n):
            sim = jaccard(older_toks, tokenized[j])
            if sim >= JACCARD_THRESHOLD:
                competitors += 1
        if competitors <= 0:
            continue
        try:
            old_conf = float(older.get("confidence") if older.get("confidence") is not None else 1.0)
        except (TypeError, ValueError):
            old_conf = 1.0
        new_conf = old_conf * (DECAY_FACTOR ** competitors)
        new_conf = max(MIN_CONFIDENCE, new_conf)
        if new_conf != old_conf:
            updates.append((int(older["id"]), old_conf, new_conf))
    return updates


def apply_decay(conn: sqlite3.Connection) -> dict[str, Any]:
    _ensure_schema(conn)
    rows = conn.execute(
        "SELECT id, session_id, fact_text, confidence, created_at "
        "FROM compaction_gate_facts ORDER BY session_id, created_at ASC, id ASC"
    ).fetchall()
    by_session: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        rec = dict(row)
        by_session.setdefault(str(rec["session_id"]), []).append(rec)

    now = time.time()
    facts_processed = len(rows)
    decayed: list[tuple[int, float, float]] = []
    for session_facts in by_session.values():
        decayed.extend(decay_session_facts(session_facts))

    for fact_id, _old, new_conf in decayed:
        conn.execute(
            "UPDATE compaction_gate_facts SET confidence=?, last_decay_at=? WHERE id=?",
            (new_conf, now, fact_id),
        )

    deltas = [old - new for _i, old, new in decayed]
    avg_decay = (sum(deltas) / float(len(deltas))) if deltas else 0.0
    return {
        "facts_processed": facts_processed,
        "facts_decayed": len(decayed),
        "avg_decay": avg_decay,
    }


def run(path: Path | None = None, write_stats: bool = True) -> dict[str, Any]:
    db = path if path is not None else db_path()
    conn = _open_db(db)
    try:
        conn.execute("BEGIN")
        stats = apply_decay(conn)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    payload = {
        "ts": datetime.now(UTC).isoformat(),
        "facts_processed": stats["facts_processed"],
        "facts_decayed": stats["facts_decayed"],
        "avg_decay": stats["avg_decay"],
        "db_path": str(db),
    }
    if write_stats:
        _atomic_write_json(_cache_dir() / "compaction-decay-stats.json", payload)
    return payload


def _self_test() -> int:
    import tempfile

    overlapping_a = (
        "compaction gate stores facts about rate distortion thresholds "
        "and hindsight context ranking"
    )
    overlapping_b = (
        "compaction gate stores facts about rate distortion thresholds "
        "and hindsight context ranking plus mdl scoring"
    )
    unique = "banana muffin recipe with extra chocolate chips and clay soil tomatoes"

    assert jaccard(word_tokens(overlapping_a), word_tokens(overlapping_b)) >= 0.5
    assert jaccard(word_tokens(overlapping_a), word_tokens(unique)) < 0.5

    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "state.db"
        conn = _open_db(db)
        _ensure_schema(conn)
        session = "self-test-decay"
        now = time.time()
        rows = [
            (session, "decision", overlapping_a, 1.0, now - 30.0, "hash-overlap-old"),
            (session, "decision", overlapping_b, 1.0, now - 10.0, "hash-overlap-new"),
            (session, "eval_result", unique, 1.0, now - 5.0, "hash-unique"),
        ]
        conn.executemany(
            "INSERT INTO compaction_gate_facts"
            "(session_id, topic, fact_text, confidence, created_at, dedup_hash) "
            "VALUES (?,?,?,?,?,?)",
            rows,
        )
        conn.commit()
        conn.close()

        stats = run(path=db, write_stats=False)
        assert stats["facts_processed"] == 3, stats
        assert stats["facts_decayed"] >= 1, stats

        conn = _open_db(db)
        by_hash = {
            r["dedup_hash"]: r
            for r in conn.execute(
                "SELECT dedup_hash, confidence, last_decay_at FROM compaction_gate_facts"
            )
        }
        cols = {row[1] for row in conn.execute("PRAGMA table_info(compaction_gate_facts)")}
        conn.close()

        assert "last_decay_at" in cols
        old_conf = float(by_hash["hash-overlap-old"]["confidence"])
        new_conf = float(by_hash["hash-overlap-new"]["confidence"])
        uniq_conf = float(by_hash["hash-unique"]["confidence"])
        assert old_conf < 1.0, old_conf
        assert new_conf == 1.0, new_conf
        assert uniq_conf == 1.0, uniq_conf
        assert old_conf >= MIN_CONFIDENCE
        pair_min = min(old_conf, new_conf)
        assert pair_min < 1.0

        # Empty DB is a no-op.
        empty = Path(tmp) / "empty.db"
        empty_stats = run(path=empty, write_stats=False)
        assert empty_stats["facts_processed"] == 0
        assert empty_stats["facts_decayed"] == 0

    print(
        "[self-test] PASS compaction-confidence-decay "
        f"old={old_conf:.4f} new={new_conf:.4f} unique={uniq_conf:.4f} "
        f"decayed={stats['facts_decayed']}"
    )
    return 0


def main() -> int:
    if "--self-test" in sys.argv:
        return _self_test()
    try:
        payload = run()
        print(json.dumps(payload, indent=2))
        return 0
    except Exception as exc:
        print(f"compaction-confidence-decay: {exc}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
