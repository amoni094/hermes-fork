#!/usr/bin/env python3
"""memory-auto-improvement.py — session-log review → proposed memory/skill patches.

Reviews recent session JSONL + state.db messages + error logs and proposes
small, reviewable patches: stale rule updates, new gotchas, procedure promotions.
NEVER auto-applies skill or memory writes. Cache JSON only.
stale_rule proposals emit only when a matching on-disk skill or memory exists.

Usage:
  python3 memory-auto-improvement.py
  python3 memory-auto-improvement.py --days 7
  python3 memory-auto-improvement.py --self-test
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone, UTC
from pathlib import Path

_raw_home = Path(os.environ.get('HERMES_HOME', str(Path.home() / '.hermes')))
_hermes_profile = os.environ.get('HERMES_PROFILE', '')
if _raw_home.parent.name == 'profiles':
    _hermes_base = _raw_home.parent.parent
    _hermes_root = _raw_home
    if not _hermes_profile:
        _hermes_profile = _raw_home.name
else:
    _hermes_base = _raw_home
    _hermes_root = (_hermes_base / 'profiles' / _hermes_profile) if _hermes_profile else _hermes_base

GOTCHA_RE = re.compile(r"\b(never|always|do not|don't|gotcha|pitfall|must not)\b", re.IGNORECASE)
ERROR_RE = re.compile(r"\b(error|exception|traceback|failed|fail_open)\b", re.IGNORECASE)
PROCEDURE_RE = re.compile(r"\b(procedure|runbook|playbook|workflow|whenever you)\b", re.IGNORECASE)
SKILL_RE = re.compile(r"\b([a-z][a-z0-9-]{3,40}-[a-z0-9-]{2,40})\b")
MAX_PROPOSALS = 24
MAX_SNIPPET = 240


def _cache_dir() -> Path:
    override = os.environ.get("UE_CACHE_DIR", "").strip()
    p = Path(override) if override else (_hermes_root / "cache")
    try:
        p.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return p


def _atomic_write(path: Path, obj) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(obj, indent=2, default=str), encoding="utf-8")
        os.replace(tmp, path)
    except Exception:
        pass


def _snip(text: str) -> str:
    s = " ".join(str(text or "").split())
    if len(s) > MAX_SNIPPET:
        return s[: MAX_SNIPPET - 3] + "..."
    return s


def _iter_jsonl(path: Path):
    try:
        if not path.exists():
            return
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                s = line.strip()
                if not s:
                    continue
                if not s.startswith("{"):
                    continue
                try:
                    obj = json.loads(s)
                except json.JSONDecodeError:
                    continue
                if isinstance(obj, dict):
                    yield obj
    except Exception:
        return


def _text_of(obj: dict) -> str:
    for k in ("content", "text", "message", "error", "result"):
        v = obj.get(k)
        if isinstance(v, str) and v.strip():
            return v
        if isinstance(v, list):
            parts = []
            for item in v:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    t = item.get("text") or item.get("content") or ""
                    if t:
                        parts.append(str(t))
            if parts:
                return "\n".join(parts)
    return ""


def _session_files():
    override = os.environ.get("HERMES_SESSIONS_DIR", "").strip()
    if override:
        d = Path(override)
        return sorted(d.glob("*.jsonl")) if d.is_dir() else []
    seen = set()
    out = []
    for d in (
        _hermes_root / "sessions",
        _hermes_base / "sessions",
        _hermes_root / "session",
    ):
        try:
            if not d.is_dir():
                continue
            for p in d.glob("*.jsonl"):
                key = str(p.resolve()) if p.exists() else str(p)
                if key in seen:
                    continue
                seen.add(key)
                out.append(p)
        except Exception:
            continue
    return sorted(out)


def _log_files():
    override = os.environ.get("HERMES_LOGS_DIR", "").strip()
    if override:
        d = Path(override)
        if not d.is_dir():
            return []
        try:
            return sorted(p for p in d.glob("*.log") if p.is_file())
        except Exception:
            return []
    out = []
    seen = set()
    names = ("errors.log", "agent.log", "gateway.log", "hermes.log")
    for logs in (_hermes_root / "logs", _hermes_base / "logs"):
        try:
            if not logs.is_dir():
                continue
            for name in names:
                p = logs / name
                if p.is_file():
                    key = str(p.resolve())
                    if key not in seen:
                        seen.add(key)
                        out.append(p)
        except Exception:
            continue
    return out


def _mtime_ok(path: Path, cutoff: float) -> bool:
    try:
        return path.stat().st_mtime >= cutoff
    except Exception:
        return False


def _state_db_path() -> Path | None:
    override = os.environ.get("HERMES_STATE_DB", "").strip()
    if override:
        p = Path(override)
        return p if p.is_file() else None
    # Isolated jsonl-only runs (self-test / HERMES_SESSIONS_DIR) must not
    # read the live DB unless HERMES_STATE_DB is set.
    if os.environ.get("HERMES_SESSIONS_DIR", "").strip():
        return None
    for p in (_hermes_root / "state.db", _hermes_base / "state.db"):
        try:
            if p.is_file():
                return p
        except Exception:
            continue
    return None


def _iter_state_db_messages(cutoff: float):
    path = _state_db_path()
    if path is None:
        return
    try:
        uri = path.resolve().as_posix()
        con = None
        for qs in ("mode=ro", "mode=ro&immutable=1"):
            try:
                con = sqlite3.connect(f"file:{uri}?{qs}", uri=True, timeout=2.0)
                break
            except sqlite3.OperationalError:
                con = None
                continue
        if con is None:
            return
        try:
            con.execute("PRAGMA query_only=ON")
            cur = con.execute(
                """
                SELECT session_id, content, timestamp
                FROM messages
                WHERE IFNULL(timestamp, 0) >= ?
                  AND IFNULL(active, 1) = 1
                  AND content IS NOT NULL
                  AND content != ''
                """,
                (cutoff,),
            )
            for session_id, content, ts in cur:
                yield str(session_id or ""), str(content or ""), float(ts or 0.0)
        finally:
            con.close()
    except Exception:
        return


def _list_skill_names() -> set[str]:
    names: set[str] = set()
    dirs = []
    env = os.environ.get("HERMES_SKILLS_DIR", "").strip()
    if env:
        dirs.append(Path(env))
    else:
        dirs.extend((_hermes_root / "skills", _hermes_base / "skills"))
    for d in dirs:
        try:
            if not d.is_dir():
                continue
            for p in d.rglob("SKILL.md"):
                names.add(p.parent.name.lower())
        except Exception:
            continue
    return names


def _list_memory_stems() -> set[str]:
    stems: set[str] = set()
    dirs = []
    env = os.environ.get("HERMES_MEMORIES_DIR", "").strip()
    if env:
        dirs.append(Path(env))
    else:
        dirs.extend((_hermes_root / "memories", _hermes_base / "memories"))
    for d in dirs:
        try:
            if not d.is_dir():
                continue
            for p in d.glob("*.md"):
                stem = p.stem.lower()
                if stem:
                    stems.add(stem)
        except Exception:
            continue
    return stems


_GENERIC_MEMORY_STEMS = frozenset({"memory", "user", "soul", "notes", "todo", "readme", "index", "log"})


def _matching_target(snippet: str, skills: set[str], memories: set[str]) -> str | None:
    text = (snippet or "").lower()
    if not text:
        return None
    for name in skills:
        if name and len(name) >= 6 and re.search(r"(?i)\b" + re.escape(name) + r"\b", text):
            return f"skill:{name}"
    for stem in memories:
        if not stem or stem in _GENERIC_MEMORY_STEMS or len(stem) < 6:
            continue
        if re.search(r"(?i)\b" + re.escape(stem) + r"\b", text):
            return f"memory:{stem}"
    return None


def _ingest_text(text: str, error_counter: Counter, gotcha_hits: list, procedure_hits: list, skill_counter: Counter) -> None:
    if not text:
        return
    if ERROR_RE.search(text):
        error_counter[_snip(text)[:120]] += 1
    if GOTCHA_RE.search(text):
        gotcha_hits.append(_snip(text))
    if PROCEDURE_RE.search(text):
        procedure_hits.append(_snip(text))
    for m in SKILL_RE.findall(text.lower()):
        skill_counter[m] += 1


def review(days: int = 7) -> dict:
    try:
        now = datetime.now(UTC)
        try:
            days_n = max(0, int(days))
        except (TypeError, ValueError):
            days_n = 7
        cutoff = (now - timedelta(days=days_n)).timestamp()
        error_counter = Counter()
        gotcha_hits = []
        procedure_hits = []
        skill_counter = Counter()
        n_sessions = 0
        n_events = 0
        n_logs = 0
        jsonl_stems = set()
        for path in _session_files():
            if not _mtime_ok(path, cutoff):
                continue
            n_sessions += 1
            jsonl_stems.add(path.stem)
            for obj in _iter_jsonl(path):
                n_events += 1
                _ingest_text(_text_of(obj), error_counter, gotcha_hits, procedure_hits, skill_counter)
        state_db_queried = False
        n_state_sessions = 0
        db_path = _state_db_path()
        if db_path is not None:
            state_db_queried = True
            state_sessions = set()
            for sid, content, _ts in _iter_state_db_messages(cutoff):
                if sid:
                    state_sessions.add(sid)
                n_events += 1
                text = content
                stripped = text.lstrip()
                if stripped.startswith("{"):
                    try:
                        obj = json.loads(text)
                    except json.JSONDecodeError:
                        obj = None
                    if isinstance(obj, dict):
                        extracted = _text_of(obj)
                        if extracted:
                            text = extracted
                _ingest_text(text, error_counter, gotcha_hits, procedure_hits, skill_counter)
            n_state_sessions = len(state_sessions)
            n_sessions = n_sessions + len(state_sessions - jsonl_stems)
        for path in _log_files():
            if not _mtime_ok(path, cutoff):
                continue
            try:
                if not path.is_file():
                    continue
                data = path.read_text(encoding="utf-8", errors="replace")[-80000:]
            except Exception:
                continue
            n_logs += 1
            for line in data.splitlines():
                if ERROR_RE.search(line):
                    error_counter[_snip(line)[:120]] += 1
        proposals = []
        skills = _list_skill_names()
        memories = _list_memory_stems()
        for snippet, count in error_counter.most_common(8):
            if count < 2:
                continue
            target = _matching_target(snippet, skills, memories)
            if not target:
                continue
            proposals.append({
                "kind": "stale_rule",
                "title": "Recurring error pattern",
                "evidence": snippet,
                "count": count,
                "target": target,
                "action": "Update the matching memory/skill rule so this failure is skipped or retried.",
            })
        seen = set()
        for hit in gotcha_hits:
            key = hit[:80]
            if key in seen:
                continue
            seen.add(key)
            proposals.append({
                "kind": "gotcha",
                "title": "New gotcha candidate",
                "evidence": hit,
                "count": 1,
                "action": "Add a one-line gotcha to the relevant skill if the constraint is durable.",
            })
            if len(proposals) >= MAX_PROPOSALS:
                break
        for hit in procedure_hits[:6]:
            proposals.append({
                "kind": "procedure_promotion",
                "title": "Procedure promotion candidate",
                "evidence": hit,
                "count": 1,
                "action": "If this workflow repeated across sessions, promote it to a short skill procedure.",
            })
        rec = {
            "ok": True,
            "applied": False,
            "n_sessions": n_sessions,
            "n_events": n_events,
            "n_logs": n_logs,
            "n_state_sessions": n_state_sessions,
            "state_db_queried": state_db_queried,
            "n_proposals": len(proposals[:MAX_PROPOSALS]),
            "top_skills": skill_counter.most_common(8),
            "proposals": proposals[:MAX_PROPOSALS],
            "ts": now.isoformat(),
            "days": days_n,
        }
        _atomic_write(_cache_dir() / "memory-auto-improvement.json", rec)
        return rec
    except Exception as exc:
        return {"ok": False, "applied": False, "n_proposals": 0, "proposals": [], "fail_open": str(exc)}


def self_test() -> int:
    import tempfile
    import time
    td = Path(tempfile.mkdtemp(prefix="mai-"))
    sess = td / "sessions"
    logs = td / "logs"
    cache = td / "cache"
    skill = td / "skills" / "blocked-file-guard"
    sess.mkdir(); logs.mkdir(); cache.mkdir(); skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("# blocked-file-guard\nnever write the blocked file\n", encoding="utf-8")
    (sess / "s1.jsonl").write_text(
        json.dumps({"content": "ERROR: blocked-file-guard never write to the blocked file"}) + "\n"
        + json.dumps({"content": "ERROR: blocked-file-guard never write to the blocked file"}) + "\n"
        + json.dumps({"content": "Whenever you install a service, enable linger."}) + "\n"
        + "not-json\n"
        + "{bad\n",
        encoding="utf-8",
    )
    (logs / "errors.log").write_text("traceback: boom\n", encoding="utf-8")
    env_keys = (
        "HERMES_SESSIONS_DIR", "HERMES_LOGS_DIR", "UE_CACHE_DIR",
        "HERMES_SKILLS_DIR", "HERMES_MEMORIES_DIR", "HERMES_STATE_DB",
    )
    old = {k: os.environ.get(k) for k in env_keys}

    def _restore() -> None:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    os.environ["HERMES_SESSIONS_DIR"] = str(sess)
    os.environ["HERMES_LOGS_DIR"] = str(logs)
    os.environ["UE_CACHE_DIR"] = str(cache)
    os.environ["HERMES_SKILLS_DIR"] = str(td / "skills")
    rec = review(days=30)
    kinds = {p["kind"] for p in rec["proposals"]}
    assert rec["ok"] is True
    assert rec["applied"] is False
    assert rec["n_sessions"] == 1
    assert rec["state_db_queried"] is False
    assert "stale_rule" in kinds
    assert any(p.get("target") == "skill:blocked-file-guard" for p in rec["proposals"] if p["kind"] == "stale_rule")
    assert "gotcha" in kinds
    assert "procedure_promotion" in kinds

    db = td / "state.db"
    con = sqlite3.connect(str(db))
    con.execute(
        "CREATE TABLE messages (id INTEGER PRIMARY KEY, session_id TEXT, role TEXT, "
        "content TEXT, timestamp REAL, active INTEGER)"
    )
    now = time.time()
    con.executemany(
        "INSERT INTO messages(session_id, role, content, timestamp, active) VALUES (?,?,?,?,1)",
        [
            ("db-sess-1", "user", "ERROR: blocked-file-guard never write to the blocked file", now),
            ("db-sess-1", "assistant", "ERROR: blocked-file-guard never write to the blocked file", now),
            ("db-sess-2", "user", "Whenever you run the blocked-file-guard workflow, check linger.", now),
        ],
    )
    con.commit()
    con.close()
    os.environ["HERMES_SESSIONS_DIR"] = str(td / "missing-jsonl")
    os.environ["HERMES_LOGS_DIR"] = str(td / "missing-logs")
    os.environ["HERMES_STATE_DB"] = str(db)
    merged = review(days=30)
    assert merged["state_db_queried"] is True
    assert merged["n_state_sessions"] == 2
    assert merged["n_sessions"] == 2
    assert any(p["kind"] == "stale_rule" for p in merged["proposals"])

    os.environ.pop("HERMES_STATE_DB", None)
    os.environ["HERMES_SESSIONS_DIR"] = str(td / "missing")
    os.environ["HERMES_LOGS_DIR"] = str(td / "missing-logs")
    empty = review(days=7)
    _restore()
    assert empty["n_proposals"] == 0
    assert empty["ok"] is True
    assert empty["state_db_queried"] is False
    print("PASS memory-auto-improvement self-test")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--days", type=int, default=7)
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    try:
        rec = review(days=args.days)
        print(json.dumps(rec, indent=2, default=str))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "applied": False, "proposals": [], "fail_open": str(exc)}))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
