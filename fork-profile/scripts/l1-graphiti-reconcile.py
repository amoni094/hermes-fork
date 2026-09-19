#!/usr/bin/env python3
"""
l1-graphiti-reconcile.py — Scatter-gather reconciliation for the Hindsight → Graphiti write path.

Problem this solves (sweep 22 deferred item):
  l1-hindsight-promote runs l1-graphiti-write.py then truncates staging.md regardless of
  whether Graphiti writes succeeded. If Graphiti is down or a write fails, facts are lost
  from the graph permanently — there is no retry and no record of which facts are missing.

This script provides two modes:

  RECORD mode (called by l1-graphiti-write.py or its wrapper):
    After each fact write attempt, record the outcome in graphiti-state.db:
      - content_hash, episode_name, fact_text, source_type, written_at (or NULL), status
    Status: 'written' | 'failed' | 'pending'

  RECONCILE mode (called standalone or by l1-graphiti-periodic):
    Query graphiti-state.db for facts with status='failed' or status='pending'.
    Re-attempt writing them to Graphiti via l1-graphiti-write.py logic.
    On success: update status to 'written'.
    After 3 consecutive failures across runs: status → 'abandoned', log warning.

Usage:
  python3 l1-graphiti-reconcile.py reconcile          # retry all failed/pending facts
  python3 l1-graphiti-reconcile.py record <hash> <name> <status> [fact_text]
  python3 l1-graphiti-reconcile.py status             # print summary
  python3 l1-graphiti-reconcile.py prune              # remove written facts older than 14d

DB location: ~/.hermes/memory-facts/graphiti-state.db
"""
import os
import sys
import json
import sqlite3
import hashlib
import datetime
import pathlib
import time
import urllib.request
import urllib.error
import importlib.util

FACTS_DIR = pathlib.Path(os.environ.get("HERMES_HOME", str(pathlib.Path.home() / ".hermes"))) / "memory-facts"
DB_PATH = FACTS_DIR / "graphiti-state.db"
STAGING_PATH = FACTS_DIR / "staging.md"
GRAPHITI_BASE = "http://127.0.0.1:8765/mcp"
GROUP_ID = "hermes"
TIMEOUT = 60
MAX_FAILURES = 3  # abandon after this many consecutive full-run failures
PRUNE_DAYS = 14   # remove 'written' entries older than this

# TraceGrant: shared namespace policy enforcement (sweep 22)
# Shadow-wrapped (H1 fix): unguarded import crashed on missing file.
try:
    _tg_spec = importlib.util.spec_from_file_location(
        "l1_tracegrant", pathlib.Path(__file__).parent / "l1-tracegrant.py"
    )
    assert _tg_spec is not None
    _tg_mod = importlib.util.module_from_spec(_tg_spec)
    _tg_spec.loader.exec_module(_tg_mod)  # type: ignore[union-attr]
    tracegrant_check = _tg_mod.tracegrant_check
    tracegrant_log_grant = _tg_mod.tracegrant_log_grant
except Exception:
    def tracegrant_check(*_a, **_kw): return True    # fail-open stub
    def tracegrant_log_grant(*_a, **_kw): return None  # no-op stub

# ── Concurrency lockfile (prevents concurrent reconcile runs) ─────────────────
# H2 fix: replaced sys.exit() with module flag + atexit release (shadow compliance).
import fcntl as _fcntl
import atexit as _atexit
_RECONCILE_LOCK = '/tmp/l1-graphiti-reconcile.lock'
_RECONCILE_LOCK_HELD = False
try:
    _lock_fd = open(_RECONCILE_LOCK, 'w')
    _fcntl.flock(_lock_fd, _fcntl.LOCK_EX | _fcntl.LOCK_NB)
    _RECONCILE_LOCK_HELD = True
    def _release_reconcile_lock():
        try:
            _fcntl.flock(_lock_fd, _fcntl.LOCK_UN)
            _lock_fd.close()
        except Exception:
            pass
    _atexit.register(_release_reconcile_lock)
except BlockingIOError:
    print('l1-graphiti-reconcile: another instance running, skipping')
except Exception:
    pass  # shadow: non-blocking lock failure

# ── DB init ───────────────────────────────────────────────────────────────────

def get_db() -> sqlite3.Connection:
    FACTS_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS graphiti_writes (
            content_hash    TEXT PRIMARY KEY,
            episode_name    TEXT NOT NULL,
            fact_text       TEXT NOT NULL,
            source_type     TEXT NOT NULL DEFAULT 'internal',
            volatility_class TEXT NOT NULL DEFAULT 'stable',
            memory_namespace TEXT NOT NULL DEFAULT 'record',
            entities        TEXT NOT NULL DEFAULT '[]',   -- JSON array
            anchors         TEXT NOT NULL DEFAULT '[]',   -- JSON array
            status          TEXT NOT NULL DEFAULT 'pending',  -- pending|written|failed|abandoned
            failure_count   INTEGER NOT NULL DEFAULT 0,
            first_seen_at   TEXT NOT NULL,
            written_at      TEXT,
            last_attempt_at TEXT
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_status ON graphiti_writes(status)
    """)
    conn.commit()
    return conn


# ── MCP transport (mirrors l1-graphiti-write.py) ──────────────────────────────

HEADERS_BASE = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}


def mcp_request(session_id: str, method: str, params: dict) -> dict:
    payload = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
    headers = dict(HEADERS_BASE)
    if session_id:
        headers["mcp-session-id"] = session_id
    data = json.dumps(payload).encode()
    req = urllib.request.Request(GRAPHITI_BASE, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read().decode()
        for line in raw.splitlines():
            if line.startswith("data: "):
                return json.loads(line[6:])
        return json.loads(raw)


def initialize_session() -> str:
    payload = {
        "jsonrpc": "2.0", "id": 0, "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "l1-graphiti-reconcile", "version": "1.0"},
        },
    }
    headers = dict(HEADERS_BASE)
    data = json.dumps(payload).encode()
    req = urllib.request.Request(GRAPHITI_BASE, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        session_id = resp.headers.get("mcp-session-id", "")
        if not session_id:
            raise RuntimeError("No mcp-session-id from Graphiti initialize")
        resp.read()
    return session_id


def write_episode(session_id: str, row: sqlite3.Row) -> bool:
    """Attempt to write one fact row to Graphiti. Returns True on success."""
    now = datetime.datetime.now(datetime.timezone.utc)
    source_tag = f"[source_type={row['source_type']}]"
    as_of_tag = f"[as_of={now.strftime('%Y-%m-%dT%H:%MZ')}]"
    vc_tag = f"[vc={row['volatility_class']}]"
    ns_tag = f"[ns={row['memory_namespace']}]"

    entities = json.loads(row['entities'] or '[]')
    anchors = json.loads(row['anchors'] or '[]')
    if entities:
        entity_parts = ", ".join(f"{e['type']}:{e['name']}" for e in entities)
        entity_hint = f"[entities: {entity_parts}] "
    else:
        entity_hint = ""
    anchor_hint = f"[anchors: {', '.join(anchors)}] " if anchors else ""

    episode_body = (
        f"{source_tag} {as_of_tag} {vc_tag} {ns_tag} "
        f"{entity_hint}{anchor_hint}{row['fact_text']}"
    )

    def _do_write() -> bool:
        resp = mcp_request(session_id, "tools/call", {
            "name": "add_memory",
            "arguments": {
                "episode_body": episode_body,
                "group_id": GROUP_ID,
                "name": row['episode_name'],
            },
        })
        result = resp.get("result", {})
        if isinstance(result, dict):
            content = result.get("content", [])
            if content and isinstance(content, list):
                text = content[0].get("text", "")
                return "queued" in text.lower() or "success" in text.lower()
        return False

    # Use retry-budget-guard if available
    try:
        guard_path = str(pathlib.Path(__file__).parent / "retry-budget-guard.py")
        spec = importlib.util.spec_from_file_location("retry_budget_guard", guard_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return mod.with_retry(_do_write, classify_fn=mod.classify_http_error,
                              label=f"graphiti-reconcile:{row['episode_name'][:30]}")
    except Exception:
        try:
            return _do_write()
        except Exception as e:
            print(f"  [reconcile] write failed for {row['episode_name']}: {e}", file=sys.stderr)
            return False


# ── Staging parser (minimal, mirrors l1-graphiti-write.py) ────────────────────

import re

TIMESTAMP_RE = re.compile(
    r"^\s*-\s*\[[\dT:Z\-+]+\]\s*(?:\[score=\d+\]\s*)?(?:\[type=(\w+)\]\s*)?(?:\[source=(\w+)\]\s*)?"
)
ENTITIES_RE = re.compile(r'\[entities:\s*([^\]]+)\]')
VC_RE = re.compile(r'\[vc=(stable|volatile|ephemeral)\]')
NS_RE = re.compile(r'\[ns=(profile|event|record)\]')
ANCHORS_RE = re.compile(r'\[anchors:\s*([^\]]+)\]')
SOURCE_TYPES = {"internal", "cron", "external", "subagent"}


def parse_staging_to_rows(path: pathlib.Path) -> list[dict]:
    """Parse staging.md into fact dicts suitable for DB insertion."""
    rows = []
    if not path.exists() or path.stat().st_size == 0:
        return rows
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line.startswith("-"):
            continue
        m = TIMESTAMP_RE.match(line)
        if not m:
            continue
        inline_source = m.group(2)
        source_type = inline_source if inline_source in SOURCE_TYPES else "internal"
        text = TIMESTAMP_RE.sub("", line).strip()

        entities_raw = []
        em = ENTITIES_RE.search(text)
        if em:
            for part in em.group(1).split(","):
                part = part.strip()
                if ":" in part:
                    etype, _, ename = part.partition(":")
                    entities_raw.append({"type": etype.strip(), "name": ename.strip()})
        text = ENTITIES_RE.sub("", text).strip()

        vc_m = VC_RE.search(text)
        volatility_class = vc_m.group(1) if vc_m else "stable"
        ns_m = NS_RE.search(text)
        memory_namespace = ns_m.group(1) if ns_m else "record"
        anc_m = ANCHORS_RE.search(text)
        anchors_raw = [a.strip() for a in anc_m.group(1).split(",")] if anc_m else []

        text = VC_RE.sub("", text).strip()
        text = NS_RE.sub("", text).strip()
        text = ANCHORS_RE.sub("", text).strip()

        if not text:
            continue

        content_hash = hashlib.sha256(text[:200].encode()).hexdigest()[:12]
        i = len(rows)
        episode_name = f"l1-{m.group(1) or 'fact'}-{content_hash}-{i:03d}"

        rows.append({
            "content_hash": content_hash,
            "episode_name": episode_name,
            "fact_text": text,
            "source_type": source_type,
            "volatility_class": volatility_class,
            "memory_namespace": memory_namespace,
            "entities": json.dumps(entities_raw),
            "anchors": json.dumps(anchors_raw),
        })
    return rows


# ── Mode: record ─────────────────────────────────────────────────────────────

def cmd_record(args: list[str]):
    """
    Record the outcome of a Graphiti write attempt.
    Usage: record <content_hash> <episode_name> <status> [fact_text]
    """
    if len(args) < 3:
        print("Usage: record <content_hash> <episode_name> <status> [fact_text]", file=sys.stderr)
        sys.exit(1)

    content_hash, episode_name, status = args[0], args[1], args[2]
    fact_text = args[3] if len(args) > 3 else ""
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    conn = get_db()
    existing = conn.execute(
        "SELECT * FROM graphiti_writes WHERE content_hash = ?", (content_hash,)
    ).fetchone()

    if status == "written":
        if existing:
            conn.execute(
                "UPDATE graphiti_writes SET status='written', written_at=?, last_attempt_at=? "
                "WHERE content_hash=?",
                (now, now, content_hash)
            )
        else:
            conn.execute(
                "INSERT INTO graphiti_writes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (content_hash, episode_name, fact_text, "internal", "stable", "record",
                 "[]", "[]", "written", 0, now, now, now)
            )
    elif status == "failed":
        if existing:
            new_count = (existing["failure_count"] or 0) + 1
            new_status = "abandoned" if new_count >= MAX_FAILURES else "failed"
            conn.execute(
                "UPDATE graphiti_writes SET status=?, failure_count=?, last_attempt_at=? "
                "WHERE content_hash=?",
                (new_status, new_count, now, content_hash)
            )
            if new_status == "abandoned":
                print(f"[reconcile] WARN: fact {content_hash} abandoned after {new_count} failures")
        else:
            conn.execute(
                "INSERT INTO graphiti_writes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (content_hash, episode_name, fact_text, "internal", "stable", "record",
                 "[]", "[]", "failed", 1, now, None, now)
            )
    elif status == "pending":
        if not existing:
            conn.execute(
                "INSERT INTO graphiti_writes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (content_hash, episode_name, fact_text, "internal", "stable", "record",
                 "[]", "[]", "pending", 0, now, None, None)
            )
    conn.commit()
    conn.close()


# ── Mode: reconcile ───────────────────────────────────────────────────────────

def cmd_reconcile():
    """Retry all failed/pending facts from graphiti-state.db."""
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM graphiti_writes WHERE status IN ('failed', 'pending') "
        "ORDER BY first_seen_at ASC"
    ).fetchall()

    if not rows:
        # Also check staging.md for any facts not yet registered
        staging_rows = parse_staging_to_rows(STAGING_PATH)
        new_rows = []
        for r in staging_rows:
            existing = conn.execute(
                "SELECT content_hash FROM graphiti_writes WHERE content_hash=?",
                (r["content_hash"],)
            ).fetchone()
            if not existing:
                now = datetime.datetime.now(datetime.timezone.utc).isoformat()
                conn.execute(
                    "INSERT INTO graphiti_writes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (r["content_hash"], r["episode_name"], r["fact_text"],
                     r["source_type"], r["volatility_class"], r["memory_namespace"],
                     r["entities"], r["anchors"], "pending", 0, now, None, None)
                )
                new_rows.append(r)
        conn.commit()
        if new_rows:
            print(f"[reconcile] Registered {len(new_rows)} untracked staging facts as pending")
            rows = conn.execute(
                "SELECT * FROM graphiti_writes WHERE status='pending'"
            ).fetchall()
        else:
            print("[reconcile] No failed or pending facts — nothing to reconcile")
            conn.close()
            return

    print(f"[reconcile] Attempting to reconcile {len(rows)} fact(s) ...")

    try:
        session_id = initialize_session()
    except Exception as e:
        print(f"[reconcile] ERROR: Graphiti unreachable: {e}", file=sys.stderr)
        conn.close()
        sys.exit(1)

    # TraceGrant: log grant for this reconcile run
    grant_id = tracegrant_log_grant("l1-graphiti-reconcile", "internal")
    if grant_id:
        print(f"[tracegrant] grant={grant_id} caller=l1-graphiti-reconcile", file=sys.stderr)

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    recovered = 0
    still_failed = 0

    for row in rows:
        # TraceGrant: enforce namespace policy before retry write
        ns = row["memory_namespace"] if row["memory_namespace"] else "record"
        src = row["source_type"] if row["source_type"] else "internal"
        if not tracegrant_check(src, ns, fact_id=row["content_hash"]):
            still_failed += 1
            continue
        ok = write_episode(session_id, row)
        if ok:
            conn.execute(
                "UPDATE graphiti_writes SET status='written', written_at=?, last_attempt_at=? "
                "WHERE content_hash=?",
                (now, now, row["content_hash"])
            )
            recovered += 1
            print(f"  recovered: {row['fact_text'][:60]}...")
        else:
            new_count = (row["failure_count"] or 0) + 1
            new_status = "abandoned" if new_count >= MAX_FAILURES else "failed"
            conn.execute(
                "UPDATE graphiti_writes SET status=?, failure_count=?, last_attempt_at=? "
                "WHERE content_hash=?",
                (new_status, new_count, now, row["content_hash"])
            )
            still_failed += 1
            if new_status == "abandoned":
                print(f"  ABANDONED (>{MAX_FAILURES} failures): {row['fact_text'][:60]}",
                      file=sys.stderr)
        time.sleep(0.3)

    conn.commit()
    conn.close()

    print(f"[reconcile] Done: {recovered} recovered, {still_failed} still failed")
    if still_failed > 0:
        sys.exit(1)


# ── Mode: register_staging ────────────────────────────────────────────────────

def cmd_register_staging():
    """
    Parse staging.md and register all facts as 'pending' in graphiti-state.db
    (if not already present). Call this BEFORE truncating staging.md so we have
    a durable record of what needs to reach Graphiti.
    """
    rows = parse_staging_to_rows(STAGING_PATH)
    if not rows:
        print("[reconcile] staging.md empty — nothing to register")
        return

    conn = get_db()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    registered = 0
    for r in rows:
        existing = conn.execute(
            "SELECT content_hash FROM graphiti_writes WHERE content_hash=?",
            (r["content_hash"],)
        ).fetchone()
        if not existing:
            conn.execute(
                "INSERT INTO graphiti_writes VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (r["content_hash"], r["episode_name"], r["fact_text"],
                 r["source_type"], r["volatility_class"], r["memory_namespace"],
                 r["entities"], r["anchors"], "pending", 0, now, None, None)
            )
            registered += 1
    conn.commit()
    conn.close()
    print(f"[reconcile] Registered {registered} new pending facts from staging.md "
          f"({len(rows) - registered} already tracked)")


# ── Mode: mark_written ────────────────────────────────────────────────────────

def cmd_mark_written_from_output(script_output: str):
    """
    Parse l1-graphiti-write.py stdout and mark matching facts as written or failed.
    Called after l1-graphiti-write.py runs.
    Lines like: '  queued: [fact] ...' → written
    Lines like: '  [graphiti] WARNING: failed to write ...' → failed
    """
    conn = get_db()
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    written = 0
    failed = 0

    for line in script_output.splitlines():
        if "queued:" in line.lower():
            # Extract fact text fragment and find matching row by content
            frag = line.split("queued:")[-1].strip().rstrip("...").strip()[:60]
            rows = conn.execute(
                "SELECT content_hash FROM graphiti_writes "
                "WHERE status IN ('pending','failed') AND fact_text LIKE ? LIMIT 1",
                (f"{frag}%",)
            ).fetchone()
            if rows:
                conn.execute(
                    "UPDATE graphiti_writes SET status='written', written_at=?, last_attempt_at=? "
                    "WHERE content_hash=?",
                    (now, now, rows["content_hash"])
                )
                written += 1
        elif "failed to write" in line.lower() or "warning:" in line.lower():
            frag = line.split("failed to write")[-1].strip().strip("'\"")[:30]
            rows = conn.execute(
                "SELECT content_hash, failure_count FROM graphiti_writes "
                "WHERE status IN ('pending','failed') AND episode_name LIKE ? LIMIT 1",
                (f"%{frag}%",)
            ).fetchone()
            if rows:
                new_count = (rows["failure_count"] or 0) + 1
                new_status = "abandoned" if new_count >= MAX_FAILURES else "failed"
                conn.execute(
                    "UPDATE graphiti_writes SET status=?, failure_count=?, last_attempt_at=? "
                    "WHERE content_hash=?",
                    (new_status, new_count, now, rows["content_hash"])
                )
                failed += 1

    conn.commit()
    conn.close()
    print(f"[reconcile] Marked {written} written, {failed} failed from script output")


# ── Mode: status ──────────────────────────────────────────────────────────────

def cmd_status():
    conn = get_db()
    rows = conn.execute(
        "SELECT status, COUNT(*) as n FROM graphiti_writes GROUP BY status"
    ).fetchall()
    print("[graphiti-state.db] summary:")
    for r in rows:
        print(f"  {r['status']}: {r['n']}")
    pending = conn.execute(
        "SELECT * FROM graphiti_writes WHERE status IN ('failed','pending') LIMIT 5"
    ).fetchall()
    if pending:
        print("\nTop pending/failed:")
        for r in pending:
            print(f"  [{r['status']}] fc={r['failure_count']} {r['fact_text'][:60]}...")
    conn.close()


# ── Mode: prune ───────────────────────────────────────────────────────────────

def cmd_prune():
    cutoff = (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(days=PRUNE_DAYS)
    ).isoformat()
    conn = get_db()
    r = conn.execute(
        "DELETE FROM graphiti_writes WHERE status='written' AND written_at < ?",
        (cutoff,)
    )
    conn.commit()
    print(f"[reconcile] Pruned {r.rowcount} written entries older than {PRUNE_DAYS}d")
    conn.close()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    # H2 fix: skip execution if lock was not acquired (another instance is running)
    if not _RECONCILE_LOCK_HELD:
        return
    args = sys.argv[1:]
    cmd = args[0] if args else "reconcile"

    if cmd == "reconcile":
        cmd_reconcile()
    elif cmd == "register":
        cmd_register_staging()
    elif cmd == "record":
        cmd_record(args[1:])
    elif cmd == "mark-written":
        # read script output from stdin
        cmd_mark_written_from_output(sys.stdin.read())
    elif cmd == "status":
        cmd_status()
    elif cmd == "prune":
        cmd_prune()
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        print("Commands: reconcile | register | record | mark-written | status | prune",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()