#!/usr/bin/env python3
"""Data collection hook for Self-GC retry.

Scans lifecycle.db for session records and measures:
  (1) count of sessions with > 50 tool calls (large sessions)
  (2) total tool_call rows
  (3) per-session token_estimate (tool_call count * 200)
  (4) candidates for fold/mask/prune (token_estimate > 8000)

Logs to cache/session-gc-probe.json.
Provides get_gc_candidates() -> list[dict].
Synthetic/in-memory fallback throughout. Stdlib only.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import time
from datetime import datetime, timezone, UTC
from pathlib import Path
from typing import Any

HERMES_HOME = Path(__file__).resolve().parents[3]
_env_home = os.environ.get("HERMES_HOME", "").strip()
if _env_home:
    _eh = Path(_env_home)
    _hh = str(_eh)
    if "profiles" in _hh and (_hh.endswith("fork") or _hh.endswith("fork/")):
        HERMES_HOME = _eh.parent.parent
    else:
        HERMES_HOME = _eh
PROFILE_ROOT = HERMES_HOME / "profiles" / "fork"
DB_PATH = PROFILE_ROOT / "cache" / "lifecycle.db"
REPORT_PATH = PROFILE_ROOT / "cache" / "session-gc-probe.json"

LARGE_CALLS = 50
TOKEN_PER_CALL = 200
GC_TOKEN_THRESHOLD = 8000  # => tool_call_count > 40

_SAFE_IDENT = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_")
_SYNTHETIC: list[dict[str, Any]] = []

DDL_SESSIONS = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    tool_call_count INTEGER,
    created_at TEXT
)
"""
DDL_TOOL_CALLS = """
CREATE TABLE IF NOT EXISTS tool_calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    ts TEXT
)
"""


def _ident_ok(name: str) -> bool:
    return bool(name) and all(c in _SAFE_IDENT for c in name)


def _atomic_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2))
    os.replace(tmp, path)


def _connect(rw: bool = True) -> sqlite3.Connection | None:
    try:
        if rw:
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            con = sqlite3.connect(str(DB_PATH))
            con.execute('PRAGMA journal_mode=WAL')
            try:
                con.execute(DDL_SESSIONS)
                con.execute(DDL_TOOL_CALLS)
                con.commit()
            except Exception:
                pass
            return con
        if not DB_PATH.exists():
            return None
        return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    except Exception:
        return None


def _table_names(con: sqlite3.Connection) -> set[str]:
    try:
        return {
            r[0]
            for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    except Exception:
        return set()


def _col_names(con: sqlite3.Connection, table: str) -> list[str]:
    if not _ident_ok(table):
        return []
    try:
        return [c[1] for c in con.execute(f'PRAGMA table_info("{table}")').fetchall()]
    except Exception:
        return []


def _load_from_db() -> list[dict[str, Any]]:
    con = _connect(rw=False)
    if con is None:
        return []
    sessions: dict[str, int] = {}
    total_rows_seen = 0
    try:
        tables = _table_names(con)
        if "tool_calls" in tables:
            cols = {c.lower() for c in _col_names(con, "tool_calls")}
            sid_col = "session_id" if "session_id" in cols else None
            if sid_col is None:
                for cand in ("session", "sid", "conversation_id"):
                    if cand in cols:
                        sid_col = cand
                        break
            if sid_col and _ident_ok(sid_col):
                try:
                    rows = con.execute(
                        f'SELECT "{sid_col}", COUNT(*) FROM tool_calls '
                        f'GROUP BY "{sid_col}"'
                    ).fetchall()
                    for sid, n in rows:
                        if sid is None:
                            continue
                        sessions[str(sid)] = sessions.get(str(sid), 0) + int(n)
                    total_rows_seen = sum(sessions.values())
                except Exception:
                    pass
        if "sessions" in tables:
            cols = {c.lower(): c for c in _col_names(con, "sessions")}
            sid_col = cols.get("session_id") or cols.get("id") or cols.get("sid")
            count_col = (
                cols.get("tool_call_count")
                or cols.get("n_tool_calls")
                or cols.get("tool_calls")
            )
            if sid_col and _ident_ok(sid_col):
                try:
                    if count_col and _ident_ok(count_col):
                        rows = con.execute(
                            f'SELECT "{sid_col}", "{count_col}" FROM sessions'
                        ).fetchall()
                        for sid, n in rows:
                            if sid is None:
                                continue
                            key = str(sid)
                            dbn = int(n or 0)
                            sessions[key] = max(sessions.get(key, 0), dbn)
                    else:
                        rows = con.execute(f'SELECT "{sid_col}" FROM sessions').fetchall()
                        for (sid,) in rows:
                            if sid is None:
                                continue
                            sessions.setdefault(str(sid), 0)
                except Exception:
                    pass
        _ = total_rows_seen
        return [
            {
                "session_id": sid,
                "tool_call_count": n,
                "token_estimate": n * TOKEN_PER_CALL,
            }
            for sid, n in sessions.items()
        ]
    except Exception:
        return []
    finally:
        try:
            con.close()
        except Exception:
            pass


def _merge_sessions() -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for rec in _load_from_db() + list(_SYNTHETIC):
        sid = str(rec.get("session_id", ""))
        if not sid:
            continue
        n = int(rec.get("tool_call_count") or 0)
        prev = by_id.get(sid)
        if prev is None or n > int(prev.get("tool_call_count") or 0):
            by_id[sid] = {
                "session_id": sid,
                "tool_call_count": n,
                "token_estimate": n * TOKEN_PER_CALL,
            }
    return list(by_id.values())


def get_gc_candidates() -> list[dict]:
    """Sessions whose token_estimate exceeds the fold/mask/prune threshold."""
    out = []
    for rec in _merge_sessions():
        if rec["token_estimate"] > GC_TOKEN_THRESHOLD:
            out.append(dict(rec))
    out.sort(key=lambda r: r["token_estimate"], reverse=True)
    return out


def inject_synthetic_session(session_id: str, tool_call_count: int) -> dict:
    """Insert a synthetic session into DB, with in-memory fallback."""
    rec = {
        "session_id": str(session_id),
        "tool_call_count": int(tool_call_count),
        "token_estimate": int(tool_call_count) * TOKEN_PER_CALL,
    }
    con = _connect(rw=True)
    if con is not None:
        try:
            con.execute(DDL_SESSIONS)
            con.execute(DDL_TOOL_CALLS)
            con.execute(
                "INSERT OR REPLACE INTO sessions (session_id, tool_call_count, created_at) "
                "VALUES (?, ?, ?)",
                (rec["session_id"], rec["tool_call_count"], datetime.now(UTC).isoformat()),
            )
            # Keep tool_calls in sync (bounded insert)
            n = rec["tool_call_count"]
            existing = con.execute(
                "SELECT COUNT(*) FROM tool_calls WHERE session_id = ?",
                (rec["session_id"],),
            ).fetchone()[0]
            missing = max(0, n - int(existing or 0))
            ts = datetime.now(UTC).isoformat()
            con.executemany(
                "INSERT INTO tool_calls (session_id, ts) VALUES (?, ?)",
                [(rec["session_id"], ts)] * missing,
            )
            con.commit()
            rec["backend"] = "sqlite"
            return rec
        except Exception:
            pass
        finally:
            try:
                con.close()
            except Exception:
                pass
    rec["backend"] = "memory"
    _SYNTHETIC.append(dict(rec))
    return rec


def run_probe() -> dict[str, Any]:
    sessions = _merge_sessions()
    total_tool_calls = sum(int(s["tool_call_count"]) for s in sessions)
    large = [s for s in sessions if s["tool_call_count"] > LARGE_CALLS]
    candidates = get_gc_candidates()
    if not sessions:
        rec = "NO_SESSIONS"
    elif candidates:
        rec = "GC_RETRY"
    else:
        rec = "NO_GC"
    result: dict[str, Any] = {
        "ts": datetime.now(UTC).isoformat(),
        "total_sessions": len(sessions),
        "large_sessions": len(large),
        "total_tool_calls": total_tool_calls,
        "gc_candidates": candidates,
        "recommendation": rec,
    }
    try:
        _atomic_json(REPORT_PATH, result)
        result["report_path"] = str(REPORT_PATH)
    except Exception:
        result["report_path"] = None
    return result


def layer1_demo() -> None:
    result = run_probe()
    assert "total_sessions" in result, result
    assert isinstance(result["gc_candidates"], list), result
    assert "large_sessions" in result
    assert "total_tool_calls" in result
    assert "ts" in result
    sid = f"synth-gc-{int(time.time() * 1000)}"
    try:
        injected = inject_synthetic_session(sid, 60)
        assert injected["token_estimate"] == 60 * TOKEN_PER_CALL
        result2 = run_probe()
        ids = {c["session_id"] for c in result2["gc_candidates"]}
        assert sid in ids, f"injected session missing from candidates: {result2}"
        assert result2["large_sessions"] >= 1
        print(
            f"[layer1] PASS session-gc-probe sessions={result2['total_sessions']} "
            f"large={result2['large_sessions']} candidates={len(result2['gc_candidates'])} "
            f"injected={sid}"
        )
    finally:
        # Clean up synthetic session from production DB so layer1 does not pollute telemetry
        con = _connect(rw=True)
        if con is not None:
            try:
                con.execute("DELETE FROM sessions WHERE session_id=?", (sid,))
                con.execute("DELETE FROM tool_calls WHERE session_id=?", (sid,))
                con.commit()
            except Exception:
                pass
            finally:
                try: con.close()
                except Exception: pass
        # Also clean synthetic in-memory fallback
        global _SYNTHETIC
        _SYNTHETIC = [s for s in _SYNTHETIC if s.get("session_id") != sid]


def main() -> None:
    pa = argparse.ArgumentParser(description="Session GC probe")
    pa.add_argument("--layer1", action="store_true")
    pa.add_argument("--self-test", action="store_true")
    args = pa.parse_args()
    if args.layer1 or args.self_test:
        layer1_demo()
        return
    result = run_probe()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
