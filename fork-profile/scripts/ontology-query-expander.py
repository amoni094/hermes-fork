#!/usr/bin/env python3
"""Self-ontology query expansion hook for Graphiti/Hindsight.

Given a search query string, generate an expanded query by:
  (1) extracting entity tokens (capitalised words, hyphenated terms, code-like tokens)
  (2) looking up synonyms from a small built-in ontology dict
  (3) appending matched synonyms to the query

Logs each expansion to SQLite table query_expansions in lifecycle.db.
Synthetic/in-memory fallback if DB ops fail. Stdlib only.
"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone, UTC
from pathlib import Path
from typing import Any

HERMES_HOME = Path(__file__).resolve().parents[3]
_env_home = os.environ.get("HERMES_HOME", "").strip()
if _env_home:
    _eh = Path(_env_home)
    # Unwrap if env already points at the fork profile root (cron sets it this way)
    _hh = str(_eh)
    if "profiles" in _hh and (_hh.endswith("fork") or _hh.endswith("fork/")):
        HERMES_HOME = _eh.parent.parent
    else:
        HERMES_HOME = _eh
PROFILE_ROOT = HERMES_HOME / "profiles" / "fork"
DB_PATH = PROFILE_ROOT / "cache" / "lifecycle.db"

# routing→bandit→linucb, memory→episodic→semantic→graphiti,
# skill→skill_view→SKILL.md, cron→scheduler→jobs.json,
# lifecycle→lifecycle.db→episode
ONTOLOGY: dict[str, list[str]] = {
    "routing": ["bandit", "linucb"],
    "bandit": ["routing", "linucb"],
    "linucb": ["routing", "bandit"],
    "memory": ["episodic", "semantic", "graphiti"],
    "episodic": ["memory", "semantic", "graphiti"],
    "semantic": ["memory", "episodic", "graphiti"],
    "graphiti": ["memory", "episodic", "semantic"],
    "skill": ["skill_view", "SKILL.md"],
    "skill_view": ["skill", "SKILL.md"],
    "skill.md": ["skill", "skill_view"],
    "cron": ["scheduler", "jobs.json"],
    "scheduler": ["cron", "jobs.json"],
    "jobs.json": ["cron", "scheduler"],
    "lifecycle": ["lifecycle.db", "episode"],
    "lifecycle.db": ["lifecycle", "episode"],
    "episode": ["lifecycle", "lifecycle.db"],
}

_CAP = re.compile(r"\b[A-Z][A-Za-z0-9_]*\b")
_HYPHEN = re.compile(r"\b[A-Za-z0-9]+(?:-[A-Za-z0-9]+)+\b")
_CODE = re.compile(
    r"\b[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_]+)+\b"
    r"|\b[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z0-9_.]+\b"
    r"|\b[a-z]+_[a-z0-9_]+\b"
    r"|\b[A-Z]{2,}[A-Za-z0-9_]*\b"
)
_WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*")

_FALLBACK_LOG: list[dict[str, Any]] = []
_FALLBACK_ID = 0

DDL = """
CREATE TABLE IF NOT EXISTS query_expansions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts TEXT NOT NULL,
    original_query TEXT NOT NULL,
    expanded_query TEXT NOT NULL,
    expansion_count INTEGER NOT NULL
)
"""


def extract_entity_tokens(query: str) -> list[str]:
    """Capitalised words, hyphenated terms, and code-like tokens."""
    if not query:
        return []
    found: list[str] = []
    seen: set[str] = set()
    for rx in (_CAP, _HYPHEN, _CODE):
        for m in rx.findall(query):
            key = m.lower()
            if key not in seen:
                seen.add(key)
                found.append(m)
    return found


def _lookup_keys(query: str) -> list[str]:
    keys: list[str] = []
    seen: set[str] = set()
    for tok in extract_entity_tokens(query) + _WORD.findall(query):
        k = tok.lower()
        if k not in seen:
            seen.add(k)
            keys.append(k)
    return keys


def expand_query(query: str) -> str:
    """Return query with ontology synonyms appended (deduped, order-preserving)."""
    if not query:
        return query
    qlow = query.lower()
    extras: list[str] = []
    extra_low: set[str] = set()
    for key in _lookup_keys(query):
        for syn in ONTOLOGY.get(key, []):
            sl = syn.lower()
            if sl in extra_low:
                continue
            if sl in qlow or syn in query:
                continue
            extras.append(syn)
            extra_low.add(sl)
    if not extras:
        return query
    return query + " " + " ".join(extras)


def _expansion_count(original: str, expanded: str) -> int:
    orig = set(original.lower().split())
    return sum(1 for w in expanded.split() if w.lower() not in orig)


def _connect() -> sqlite3.Connection | None:
    try:
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        con = sqlite3.connect(str(DB_PATH))
        con.execute('PRAGMA journal_mode=WAL')
        con.execute(DDL)
        con.commit()
        return con
    except Exception:
        return None


def log_expansion(original: str, expanded: str) -> dict:
    """Persist expansion to lifecycle.db; fall back to in-memory log."""
    global _FALLBACK_ID
    rec: dict[str, Any] = {
        "id": None,
        "ts": datetime.now(UTC).isoformat(),
        "original_query": original,
        "expanded_query": expanded,
        "expansion_count": _expansion_count(original, expanded),
    }
    con = _connect()
    if con is not None:
        try:
            cur = con.execute(
                "INSERT INTO query_expansions (ts, original_query, expanded_query, expansion_count) "
                "VALUES (?, ?, ?, ?)",
                (rec["ts"], rec["original_query"], rec["expanded_query"], rec["expansion_count"]),
            )
            con.commit()
            rec["id"] = int(cur.lastrowid)
            rec["backend"] = "sqlite"
            return rec
        except Exception:
            pass
        finally:
            try:
                con.close()
            except Exception:
                pass
    _FALLBACK_ID += 1
    rec["id"] = _FALLBACK_ID
    rec["backend"] = "memory"
    _FALLBACK_LOG.append(dict(rec))
    return rec


def _record_exists(rec: dict) -> bool:
    if rec.get("backend") == "memory":
        return any(x.get("id") == rec.get("id") for x in _FALLBACK_LOG)
    con = _connect()
    if con is None:
        return False
    try:
        row = con.execute(
            "SELECT id FROM query_expansions WHERE id = ?",
            (rec["id"],),
        ).fetchone()
        return row is not None
    except Exception:
        return False
    finally:
        try:
            con.close()
        except Exception:
            pass


def layer1_demo() -> None:
    # Redirect DB_PATH to :memory: equivalent (temp file) for isolation
    import tempfile
    global DB_PATH
    _saved_db = DB_PATH
    _tmp_db   = Path(tempfile.mktemp(suffix=".db"))
    DB_PATH   = _tmp_db
    try:
        q = "routing linucb latency"
        expanded = expand_query(q)
        assert len(expanded) > len(q), f"expected longer expansion, got {expanded!r}"
        assert "bandit" in expanded or "linucb" in expanded, expanded
        rec = log_expansion(q, expanded)
        assert rec.get("expanded_query") == expanded
        assert rec.get("original_query") == q
        assert rec.get("id") is not None
        assert _record_exists(rec), f"log_expansion did not persist: {rec}"
        # edge cases must not crash
        assert expand_query("") == ""
        _ = expand_query("x" * 10000)
        print(
            f"[layer1] PASS ontology-query-expander expanded={expanded!r} "
            f"id={rec['id']} backend={rec.get('backend')} (isolated temp db)"
        )
    finally:
        DB_PATH = _saved_db
        _tmp_db.unlink(missing_ok=True)
def main() -> None:
    pa = argparse.ArgumentParser(description="Ontology query expander")
    pa.add_argument("--layer1", action="store_true")
    pa.add_argument("--self-test", action="store_true")
    pa.add_argument("--query", default="", help="query string to expand")
    args = pa.parse_args()
    if args.layer1 or args.self_test:
        layer1_demo()
        return
    q = args.query
    if not q:
        print("usage: ontology-query-expander.py --query TEXT | --layer1", file=sys.stderr)
        sys.exit(2)
    expanded = expand_query(q)
    rec = log_expansion(q, expanded)
    print(expanded)
    print(f"[expand] count={rec['expansion_count']} backend={rec.get('backend')} id={rec['id']}")


if __name__ == "__main__":
    main()
