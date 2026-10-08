#!/usr/bin/env python3
"""
l1-tracegrant.py — Shared TraceGrant namespace policy + grant log for the l1 memory pipeline.

Imported by: l1-promote.py, l1-graphiti-write.py, l1-graphiti-reconcile.py

TraceGrant (sweep 22, arXiv:2608.07952 PSE trust tier extension):
  Enforces which source_types may write to which memory namespaces.
  Logs a grant row per pipeline run for audit and rollback tracing.
  Violations are fail-closed: write is blocked and logged to stderr.

Sweep 24 additions (arXiv:2608.23547 — anomaly baseline integrity + AIREP decision records):
  - taint_path field: tracks provenance chain for each grant (which caller chain produced it)
  - decision_hash: SHA-256 of (caller, source_type, allowed_ns, granted_at) for tamper detection
  - tracegrant_verify(): validate decision_hash integrity of recent grants
  AIREP (Audit Integrity for Records of Evidence in Pipelines, arXiv:2608.23547):
    Signed decision records allow anomaly baselines to be validated for drift — if a grant's
    hash doesn't match, either the DB was tampered with or the policy changed without a
    corresponding schema migration. Baseline drift (policy change without hash update) is a
    known vector for slowly eroding security controls.

Usage:
    from l1_tracegrant import NAMESPACE_POLICY, tracegrant_check, tracegrant_log_grant, tracegrant_revoke, tracegrant_audit, tracegrant_verify
"""
from __future__ import annotations

import json
import os
import sys
import uuid
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import sqlite3

# --------------------------------------------------------------------------- #
# Policy table
# --------------------------------------------------------------------------- #
# Which namespaces each source_type may write to.
# external = scraped/web/injected content — never touches profile namespace.
# agent    = subagent-produced facts — can write events and records, not user identity.
# cron     = autonomous cron output — same as agent.
# internal = session-authored facts by the primary model — full access.
NAMESPACE_POLICY: dict[str, set[str]] = {
    "internal": {"profile", "event", "record"},
    "agent":    {"event", "record"},
    "cron":     {"event", "record"},
    "external": {"record"},
}
_DEFAULT_ALLOWED_NS: set[str] = {"record"}  # fail-safe for unknown source types

# --------------------------------------------------------------------------- #
# DB path resolution
# --------------------------------------------------------------------------- #
HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
LIFECYCLE_DB = HERMES_HOME / "memory-facts" / "lifecycle.db"


def _get_db_path() -> Path:
    """Allow override via LIFECYCLE_DB env var for tests."""
    return Path(os.environ.get("L1_LIFECYCLE_DB", str(LIFECYCLE_DB)))


def _ensure_grants_schema(conn: sqlite3.Connection) -> None:
    """Create grants table and grant_id column on fact_lifecycle if missing."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tracegrant_grants (
            grant_id     TEXT PRIMARY KEY,
            session_id   TEXT NOT NULL DEFAULT '',
            caller       TEXT NOT NULL,
            source_type  TEXT NOT NULL,
            allowed_ns   TEXT NOT NULL,   -- JSON list
            granted_at   TEXT NOT NULL,
            revoked      INTEGER NOT NULL DEFAULT 0,
            revoked_at   TEXT,
            taint_path   TEXT NOT NULL DEFAULT '',  -- sweep 24: provenance chain
            decision_hash TEXT NOT NULL DEFAULT '' -- sweep 24: AIREP tamper-detection hash
        );
        CREATE INDEX IF NOT EXISTS idx_tgg_caller ON tracegrant_grants(caller);
        CREATE INDEX IF NOT EXISTS idx_tgg_source ON tracegrant_grants(source_type);
    """)
    # Idempotently add grant_id column to fact_lifecycle if it exists
    try:
        conn.execute("ALTER TABLE fact_lifecycle ADD COLUMN grant_id TEXT NOT NULL DEFAULT ''")
    except sqlite3.OperationalError:
        pass  # column already exists
    # Idempotently add sweep 24 columns to tracegrant_grants
    for col, definition in [
        ("taint_path", "TEXT NOT NULL DEFAULT ''"),
        ("decision_hash", "TEXT NOT NULL DEFAULT ''"),
    ]:
        try:
            conn.execute(f"ALTER TABLE tracegrant_grants ADD COLUMN {col} {definition}")
        except sqlite3.OperationalError:
            pass  # already exists


def _compute_decision_hash(caller: str, source_type: str, allowed_ns: list[str], granted_at: str) -> str:
    """
    Sweep 24 (AIREP, arXiv:2608.23547): SHA-256 of canonical grant fields.
    Used to detect tampered or drifted grant records at audit time.
    """
    canonical = json.dumps({
        "caller": caller,
        "source_type": source_type,
        "allowed_ns": sorted(allowed_ns),
        "granted_at": granted_at,
    }, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()[:32]  # first 32 hex chars = 128 bits


# --------------------------------------------------------------------------- #
# Core functions
# --------------------------------------------------------------------------- #

def tracegrant_check(source_type: str, memory_namespace: str, fact_id: str = "") -> bool:
    """
    Return True iff source_type is allowed to write to memory_namespace.
    Logs a violation message to stderr on False.
    """
    allowed = NAMESPACE_POLICY.get(source_type, _DEFAULT_ALLOWED_NS)
    if memory_namespace in allowed:
        return True
    print(
        f"[tracegrant] VIOLATION blocked: source_type={source_type!r} "
        f"may not write to namespace={memory_namespace!r}"
        + (f" fact_id={fact_id}" if fact_id else ""),
        file=sys.stderr,
    )
    return False


def tracegrant_log_grant(
    caller: str,
    source_type: str,
    session_id: str = "",
    taint_path: str = "",  # sweep 24: provenance chain, e.g. "l1-extract→l1-promote"
) -> str:
    """
    Log a capability grant for this pipeline run. Returns the grant_id.
    Call once per script invocation before writing any facts.

    Sweep 24: taint_path records the full caller chain for provenance tracking.
    decision_hash is computed and stored for AIREP audit integrity (arXiv:2608.23547).
    """
    grant_id = f"grant-{uuid.uuid4().hex[:12]}"
    allowed_ns = sorted(NAMESPACE_POLICY.get(source_type, _DEFAULT_ALLOWED_NS))
    now_ts = datetime.now(timezone.utc).isoformat()
    dhash = _compute_decision_hash(caller, source_type, allowed_ns, now_ts)
    db = _get_db_path()
    try:
        db.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(db)) as conn:
            _ensure_grants_schema(conn)
            conn.execute(
                """
                INSERT INTO tracegrant_grants
                    (grant_id, session_id, caller, source_type, allowed_ns, granted_at, taint_path, decision_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (grant_id, session_id, caller, source_type, json.dumps(allowed_ns), now_ts, taint_path, dhash),
            )
            conn.commit()
    except Exception as e:
        print(f"[tracegrant] grant log error: {e}", file=sys.stderr)
    return grant_id


def tracegrant_revoke(grant_id: str) -> bool:
    """Mark a grant as revoked. Returns True on success."""
    now_ts = datetime.now(timezone.utc).isoformat()
    db = _get_db_path()
    try:
        with sqlite3.connect(str(db)) as conn:
            _ensure_grants_schema(conn)
            conn.execute(
                "UPDATE tracegrant_grants SET revoked=1, revoked_at=? WHERE grant_id=?",
                (now_ts, grant_id),
            )
            conn.commit()
        return True
    except Exception as e:
        print(f"[tracegrant] revoke error for {grant_id}: {e}", file=sys.stderr)
        return False


def tracegrant_audit(
    namespace: str | None = None,
    since: str | None = None,
) -> list[dict]:
    """
    Audit query: return grants (and violation summary) for a namespace or time window.

    Args:
        namespace: filter to grants whose allowed_ns includes this namespace (None = all)
        since: ISO timestamp lower bound on granted_at (None = all time)

    Returns list of grant dicts with keys:
        grant_id, caller, source_type, allowed_ns (list), granted_at, revoked
    """
    db = _get_db_path()
    results: list[dict] = []
    try:
        with sqlite3.connect(str(db)) as conn:
            conn.row_factory = sqlite3.Row
            _ensure_grants_schema(conn)
            query = "SELECT * FROM tracegrant_grants"
            params: list = []
            if since:
                query += " WHERE granted_at >= ?"
                params.append(since)
            query += " ORDER BY granted_at DESC"
            rows = conn.execute(query, params).fetchall()
            for row in rows:
                allowed = json.loads(row["allowed_ns"])
                if namespace and namespace not in allowed:
                    continue
                results.append({
                    "grant_id":    row["grant_id"],
                    "session_id":  row["session_id"],
                    "caller":      row["caller"],
                    "source_type": row["source_type"],
                    "allowed_ns":  allowed,
                    "granted_at":  row["granted_at"],
                    "revoked":     bool(row["revoked"]),
                    "revoked_at":  row["revoked_at"],
                })
    except Exception as e:
        print(f"[tracegrant] audit error: {e}", file=sys.stderr)
    return results


def tracegrant_verify(since: str | None = None) -> dict:
    """
    Sweep 24 (AIREP, arXiv:2608.23547): Verify decision_hash integrity of recent grants.

    Re-computes expected hash for each grant and compares to stored value.
    Mismatches indicate either DB tampering or policy change without schema migration.

    Returns:
        {
            "total": int,
            "verified": int,     # hashes matched
            "tampered": int,     # hashes mismatched
            "no_hash": int,      # pre-sweep-24 grants with empty decision_hash
            "tampered_grants": [{"grant_id": ..., "caller": ..., "granted_at": ...}, ...]
        }
    """
    db = _get_db_path()
    result: dict = {"total": 0, "verified": 0, "tampered": 0, "no_hash": 0, "tampered_grants": []}
    try:
        with sqlite3.connect(str(db)) as conn:
            conn.row_factory = sqlite3.Row
            _ensure_grants_schema(conn)
            query = "SELECT * FROM tracegrant_grants"
            params: list = []
            if since:
                query += " WHERE granted_at >= ?"
                params.append(since)
            rows = conn.execute(query, params).fetchall()
            for row in rows:
                result["total"] += 1
                stored_hash = row["decision_hash"] or ""
                if not stored_hash:
                    result["no_hash"] += 1
                    continue
                allowed_ns = json.loads(row["allowed_ns"] or "[]")
                expected = _compute_decision_hash(
                    row["caller"], row["source_type"], allowed_ns, row["granted_at"]
                )
                if stored_hash == expected:
                    result["verified"] += 1
                else:
                    result["tampered"] += 1
                    result["tampered_grants"].append({
                        "grant_id": row["grant_id"],
                        "caller": row["caller"],
                        "source_type": row["source_type"],
                        "granted_at": row["granted_at"],
                        "stored_hash": stored_hash,
                        "expected_hash": expected,
                    })
                    print(
                        f"[tracegrant] INTEGRITY VIOLATION: grant {row['grant_id']} "
                        f"hash mismatch (caller={row['caller']}, granted_at={row['granted_at']})",
                        file=sys.stderr,
                    )
    except Exception as e:
        print(f"[tracegrant] verify error: {e}", file=sys.stderr)
    return result


def main(argv: list[str] | None = None) -> int:
    """Minimal CLI: check / audit / verify / grant."""
    import argparse
    parser = argparse.ArgumentParser(description="TraceGrant namespace policy (sweep 22/24)")
    sub = parser.add_subparsers(dest="cmd")

    check = sub.add_parser("check", help="Check source_type vs namespace")
    check.add_argument("--source-type", required=True)
    check.add_argument("--namespace", required=True)
    check.add_argument("--fact-id", default="")

    grant = sub.add_parser("grant", help="Log a capability grant")
    grant.add_argument("--caller", required=True)
    grant.add_argument("--source-type", required=True)
    grant.add_argument("--session", default="")
    grant.add_argument("--taint-path", default="")

    audit = sub.add_parser("audit", help="List grants")
    audit.add_argument("--namespace", default=None)
    audit.add_argument("--since", default=None)

    verify = sub.add_parser("verify", help="AIREP hash integrity check")
    verify.add_argument("--since", default=None)

    args = parser.parse_args(argv)
    if args.cmd == "check":
        ok = tracegrant_check(args.source_type, args.namespace, args.fact_id)
        print(json.dumps({"allowed": ok, "source_type": args.source_type, "namespace": args.namespace}))
        return 0 if ok else 1
    if args.cmd == "grant":
        gid = tracegrant_log_grant(args.caller, args.source_type, args.session, args.taint_path)
        print(json.dumps({"grant_id": gid}))
        return 0
    if args.cmd == "audit":
        rows = tracegrant_audit(namespace=args.namespace, since=args.since)
        print(json.dumps(rows, indent=2))
        return 0
    if args.cmd == "verify":
        result = tracegrant_verify(since=args.since)
        print(json.dumps(result, indent=2))
        return 1 if result.get("tampered") else 0
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())

