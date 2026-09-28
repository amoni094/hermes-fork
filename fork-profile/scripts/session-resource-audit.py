#!/usr/bin/env python3
"""
session-resource-audit.py — Runtime-acquired resource authorization audit
arXiv:2609.14744 — Runtime Authorization for Resources Acquired by AI Agents

Checks that all resources acquired during a session (tools called, subagents spawned,
cron jobs created) have explicit expiry or renewal records in lifecycle.db.

Unaudited resources = acquired without expiry = authorization drift risk.

Usage: python3 session-resource-audit.py [--session-id SESSION_ID]
Output: ~/.hermes/profiles/fork/logs/session-resource-audit.jsonl
"""
import argparse
import datetime
import json
import os
import sqlite3
from pathlib import Path

_HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
LIFECYCLE_DB = _HERMES_HOME / "memory-facts/lifecycle.db"
CRON_JOBS = _HERMES_HOME / "profiles/fork/cron/jobs.json"
EXEC_LOG = _HERMES_HOME / "profiles/fork/logs/exec-integrity.jsonl"
AUDIT_LOG = _HERMES_HOME / "profiles/fork/logs/session-resource-audit.jsonl"
AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)


def _now_iso() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"


def _load_cron_jobs() -> list[dict]:
    if not CRON_JOBS.exists():
        return []
    try:
        data = json.loads(CRON_JOBS.read_text())
        jobs = data if isinstance(data, list) else data.get("jobs", [])
        return [j for j in jobs if j]
    except Exception:
        return []


def _load_tracegrant_grants(session_id: str | None) -> list[dict]:
    """Query tracegrant_grants from lifecycle.db for grants without expiry."""
    if not LIFECYCLE_DB.exists():
        return []
    grants = []
    try:
        conn = sqlite3.connect(str(LIFECYCLE_DB))
        conn.execute("PRAGMA journal_mode=WAL")  # F09: shared db needs WAL
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        # Check columns available
        cursor.execute("PRAGMA table_info(tracegrant_grants)")
        cols = {row[1] for row in cursor.fetchall()}
        if not cols:
            return []
        # Build query based on available columns
        where = ""
        params: list = []
        if "session_id" in cols and session_id:
            where = "WHERE session_id = ?"
            params.append(session_id)
        cursor.execute(f"SELECT * FROM tracegrant_grants {where} LIMIT 500", params)
        rows = cursor.fetchall()
        for row in rows:
            g = dict(row)
            grants.append(g)
        conn.close()
    except Exception:
        pass
    return grants


def _load_exec_log_tools(session_id: str | None) -> list[dict]:
    """Read exec-integrity.jsonl for tool calls in this session."""
    if not EXEC_LOG.exists():
        return []
    tools = []
    try:
        with EXEC_LOG.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    # F10: filter by session_id when provided so cross-session tool
                    # calls are not audited as belonging to this session
                    if session_id and rec.get("session_id") and rec["session_id"] != session_id:
                        continue
                    tools.append(rec)
                except json.JSONDecodeError:
                    pass
    except OSError:
        pass
    return tools


def _check_grant_expiry(grant: dict) -> bool:
    """Return True if grant has no expiry or expiry is None/empty."""
    for key in ("expires_at", "expiry", "ttl", "expires"):
        val = grant.get(key)
        if val is not None and str(val).strip():
            return False  # has expiry
    return True  # no expiry found


def main() -> int:
    parser = argparse.ArgumentParser(description="Session resource audit")
    parser.add_argument("--session-id", default=None, help="Audit specific session")
    args = parser.parse_args()
    session_id = args.session_id or os.environ.get("HERMES_SESSION_ID")

    ts = _now_iso()
    flagged = []

    # 1. Check tracegrant_grants for grants without expiry
    grants = _load_tracegrant_grants(session_id)
    for grant in grants:
        if _check_grant_expiry(grant):
            flagged.append({
                "resource_type": "tracegrant",
                "resource_id": str(grant.get("grant_id", grant.get("id", "?"))),
                "session_id": str(grant.get("session_id", session_id or "unknown")),
                "acquired_at": str(grant.get("created_at", grant.get("ts", "?"))),
                "issue": "no expiry record",
            })

    # 2. Check cron jobs — flag any with no TTL or end_date
    cron_jobs = _load_cron_jobs()
    for job in cron_jobs:
        job_id = job.get("id", "?")
        has_expiry = any(
            job.get(k) for k in ("end_date", "expires_at", "ttl", "max_runs", "run_once")
        )
        if not has_expiry:
            flagged.append({
                "resource_type": "cron_job",
                "resource_id": str(job_id),
                "session_id": session_id or "unknown",
                "acquired_at": str(job.get("created_at", "?")),
                "issue": "cron job has no end_date, ttl, or max_runs — perpetual resource",
            })

    # 3. Tool calls from exec log — flag any without call_id
    tools = _load_exec_log_tools(session_id)
    for tool in tools:
        if not tool.get("call_id"):
            flagged.append({
                "resource_type": "tool_call",
                "resource_id": tool.get("tool_name", "?"),
                "session_id": session_id or "unknown",
                "acquired_at": tool.get("ts", "?"),
                "issue": "tool call has no call_id — not traceable",
            })

    status = "warn" if flagged else "ok"
    record = {
        "ts": ts,
        "session_id": session_id or "unknown",
        "grants_checked": len(grants),
        "cron_jobs_checked": len(cron_jobs),
        "tool_calls_checked": len(tools),
        "flagged_count": len(flagged),
        "flagged": flagged[:50],  # cap
        "status": status,
    }
    with AUDIT_LOG.open("a") as f:
        f.write(json.dumps(record) + "\n")

    if flagged:
        print(f"session-resource-audit: {len(flagged)} unaudited resources "
              f"({len(grants)} grants, {len(cron_jobs)} cron, {len(tools)} tools checked)")

    return len(flagged)


if __name__ == "__main__":
    import sys
    sys.exit(1 if main() else 0)
