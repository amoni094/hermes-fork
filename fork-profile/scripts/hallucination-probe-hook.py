#!/usr/bin/env python3
"""Hallucination probe hook — ground-truth dataset collector.

NOT a detector. After each tool result, logs lexical/structural features
to SQLite table hallucination_probe in lifecycle.db so a later
hallucination_detector.py can be trained against real traces.

Kill test:
    rec = probe_tool_result('s1','t1','web_search','The answer is 42. According to Wikipedia, ...')
    assert rec['self_citation_count'] >= 1
    assert rec['claim_count'] >= 1
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
from datetime import datetime, timezone, UTC
from pathlib import Path
from typing import Any, Optional

HERMES_HOME = Path(__file__).resolve().parents[3]
PROFILE_ROOT = HERMES_HOME / "profiles" / "fork"
DB_PATH = PROFILE_ROOT / "cache" / "lifecycle.db"

URL_RE = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
DATE_RE = re.compile(
    r"\b(?:(?:19|20)\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2})\b",
    re.IGNORECASE,
)
NUMBER_RE = re.compile(r"\d")
CITATION_RE = re.compile(r"\baccording to\b|\bbased on\b|\bas mentioned\b", re.IGNORECASE)
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS hallucination_probe (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    session_id TEXT NOT NULL,
    turn_id TEXT NOT NULL,
    tool_name TEXT NOT NULL,
    result_hash TEXT,
    result_length INTEGER,
    contains_url INTEGER,
    contains_date INTEGER,
    contains_number INTEGER,
    self_citation_count INTEGER,
    claim_count INTEGER
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


def _sentences(text: str) -> list[str]:
    raw = (text or "").strip()
    if not raw:
        return []
    parts = SENTENCE_SPLIT_RE.split(raw)
    return [p.strip() for p in parts if p.strip()]


def _is_claim(sentence: str) -> bool:
    s = sentence.strip()
    if not s:
        return False
    if NUMBER_RE.search(s) or DATE_RE.search(s) or URL_RE.search(s):
        return True
    if re.search(r"\b(is|was|are|were|has|have|had)\b", s, re.IGNORECASE) and s.endswith((".", "!", "?")):
        return True
    return False


def _features(result_text: str) -> dict[str, Any]:
    text = result_text if isinstance(result_text, str) else str(result_text or "")
    sents = _sentences(text)
    claims = [s for s in sents if _is_claim(s)]
    digest = hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()
    return {
        "result_hash": digest,
        "tool_result_hash": digest,
        "result_length": len(text),
        "contains_url": 1 if URL_RE.search(text) else 0,
        "contains_date": 1 if DATE_RE.search(text) else 0,
        "contains_number": 1 if NUMBER_RE.search(text) else 0,
        "self_citation_count": len(CITATION_RE.findall(text)),
        "claim_count": len(claims),
        "claim_sentences": claims,
    }


def probe_tool_result(
    session_id: str,
    turn_id: str,
    tool_name: str,
    result_text: str,
) -> dict[str, Any]:
    """Extract probe features and persist a hallucination_probe row."""
    ts = datetime.now(UTC).isoformat()
    feats = _features(result_text)
    rec: dict[str, Any] = {
        "ts": ts,
        "session_id": str(session_id),
        "turn_id": str(turn_id),
        "tool_name": str(tool_name),
        **feats,
        "db_fallback_memory": _using_memory,
    }
    try:
        conn = _get_conn()
        rec["db_fallback_memory"] = _using_memory
        cur = conn.execute(
            """
            INSERT INTO hallucination_probe (
                ts, session_id, turn_id, tool_name, result_hash, result_length,
                contains_url, contains_date, contains_number,
                self_citation_count, claim_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rec["ts"],
                rec["session_id"],
                rec["turn_id"],
                rec["tool_name"],
                rec["result_hash"],
                rec["result_length"],
                rec["contains_url"],
                rec["contains_date"],
                rec["contains_number"],
                rec["self_citation_count"],
                rec["claim_count"],
            ),
        )
        conn.commit()
        rec["id"] = int(cur.lastrowid or 0)
    except Exception as exc:
        rec["id"] = None
        rec["db_error"] = type(exc).__name__
    return rec


def get_probe_stats() -> dict[str, Any]:
    """Aggregate counters over hallucination_probe."""
    empty = {
        "n": 0,
        "avg_result_length": 0.0,
        "with_url": 0,
        "with_date": 0,
        "with_number": 0,
        "total_self_citations": 0,
        "total_claims": 0,
        "db_fallback_memory": _using_memory,
    }
    try:
        conn = _get_conn()
        empty["db_fallback_memory"] = _using_memory
        row = conn.execute(
            """
            SELECT
                COUNT(*),
                COALESCE(AVG(result_length), 0),
                COALESCE(SUM(contains_url), 0),
                COALESCE(SUM(contains_date), 0),
                COALESCE(SUM(contains_number), 0),
                COALESCE(SUM(self_citation_count), 0),
                COALESCE(SUM(claim_count), 0)
            FROM hallucination_probe
            """
        ).fetchone()
        if not row:
            return empty
        return {
            "n": int(row[0] or 0),
            "avg_result_length": float(row[1] or 0.0),
            "with_url": int(row[2] or 0),
            "with_date": int(row[3] or 0),
            "with_number": int(row[4] or 0),
            "total_self_citations": int(row[5] or 0),
            "total_claims": int(row[6] or 0),
            "db_fallback_memory": _using_memory,
        }
    except Exception as exc:
        empty["db_error"] = type(exc).__name__
        return empty


def layer1_demo() -> None:
    # Use an isolated in-memory DB so layer1 never writes to production lifecycle.db
    import sqlite3 as _sqlite3
    global _conn, _using_memory
    _saved_conn, _saved_mem = _conn, _using_memory
    _conn = _sqlite3.connect(":memory:")
    _using_memory = True
    _init_schema(_conn)
    try:
        rec = probe_tool_result(
            "s1",
            "t1",
            "web_search",
            "The answer is 42. According to Wikipedia, ...",
        )
        assert rec["self_citation_count"] >= 1, rec
        assert rec["claim_count"] >= 1, rec
        assert rec["contains_number"] == 1
        required = {
            "ts", "session_id", "turn_id", "tool_name", "result_hash",
            "result_length", "contains_url", "contains_date", "contains_number",
            "self_citation_count", "claim_count",
        }
        assert required.issubset(set(rec.keys())), f"missing fields: {required - set(rec.keys())}"
        # Verify None/empty input does not crash
        rec_empty = probe_tool_result("s1", "t2", "terminal", "")
        assert "ts" in rec_empty
        stats = get_probe_stats()
        assert isinstance(stats, dict)
        print(
            f"[layer1] PASS hallucination-probe-hook — "
            f"self_cit={rec['self_citation_count']} claims={rec['claim_count']} "
            f"backend=memory (isolated)"
        )
    finally:
        try: _conn.close()
        except Exception: pass
        _conn, _using_memory = _saved_conn, _saved_mem
def main() -> None:
    if "--layer1" in sys.argv:
        layer1_demo()
        return
    rec = probe_tool_result(
        "synthetic",
        "t0",
        "web_search",
        "The answer is 42. According to Wikipedia, water boils at 100 C.",
    )
    print(json.dumps({"record": rec, "stats": get_probe_stats()}, indent=2, default=str))


if __name__ == "__main__":
    main()
