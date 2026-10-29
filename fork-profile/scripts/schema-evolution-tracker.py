#!/usr/bin/env python3
"""
schema-evolution-tracker.py — Track and migrate lifecycle.db schema over time.

Based on:
  Curino et al. 2008 "PRIMA: Managing and Querying Transaction-Time Databases
  under Schema Evolution" (VLDB 2008): databases change over time; schema
  versions must be tracked so queries can be answered against any historical
  version, and migrations must be idempotent and monotonic.

  Liu & Layland 1973 EDF principle applied: schema migrations run in priority
  order (blocking migrations first, additive-only last) with idempotency
  guarantees so partial runs are safe.

What this script does:
  1. Reads the current schema_version from lifecycle.db (if tracked).
  2. Applies any pending additive-only migrations in version order.
  3. Records each migration in a schema_migrations audit table with
     applied_at, version, description, and checksum.
  4. Never drops columns or changes column types (PRIMA additive principle:
     schema evolution is monotone — new columns/tables only, never deletions,
     so old queries remain valid against the current schema).

Usage:
  python3 schema-evolution-tracker.py [--dry-run] [--verbose]
  python3 schema-evolution-tracker.py --status

Cron: run weekly or on hermes startup (before any script that uses lifecycle.db).
"""

import argparse
import hashlib
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

_base = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
_profile = os.environ.get("HERMES_PROFILE", "")
_HERMES_HOME = (_base / "profiles" / _profile) if _profile and "profiles" not in str(_base) else _base
LIFECYCLE_DB = _HERMES_HOME / "memory-facts" / "lifecycle.db"
AUDIT_LOG = _HERMES_HOME / "memory-facts" / "schema-migrations.jsonl"

CURRENT_VERSION = 4  # increment when adding new migrations below


def _open_db(path: Path = LIFECYCLE_DB) -> sqlite3.Connection:
    """Open lifecycle.db with WAL + concurrent-read-safe pragmas (SQLite WAL paper)."""
    conn = sqlite3.connect(str(path), timeout=10.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA wal_autocheckpoint=100")
    conn.row_factory = sqlite3.Row
    return conn


# ---------------------------------------------------------------------------
# Migration registry
# Each entry: (version, description, sql_statements)
# PRIMA principle: all migrations are additive only (CREATE TABLE IF NOT EXISTS,
# ADD COLUMN — never DROP, RENAME without alias, or change column type).
# ---------------------------------------------------------------------------
MIGRATIONS: list[tuple[int, str, list[str]]] = [
    (
        1,
        "baseline: schema_migrations audit table",
        [
            """CREATE TABLE IF NOT EXISTS schema_migrations (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                version       INTEGER NOT NULL UNIQUE,
                description   TEXT NOT NULL,
                applied_at    TEXT NOT NULL DEFAULT (datetime('now','utc')),
                checksum      TEXT NOT NULL,
                duration_ms   REAL
            )"""
        ],
    ),
    (
        2,
        "fact_lifecycle: add quality_score column if missing",
        [
            # quality_score was added in sweep 24 but may be absent in older DBs
            "ALTER TABLE fact_lifecycle ADD COLUMN quality_score REAL DEFAULT NULL",
        ],
    ),
    (
        3,
        "fact_lifecycle: add inhibition_weight column for Anderson 1994 RIF model",
        [
            # Retrieval-induced forgetting (Anderson et al. 1994): competing memories
            # in the same domain are inhibited in proportion to the practised item's
            # strength. inhibition_weight tracks how much this fact suppresses others.
            "ALTER TABLE fact_lifecycle ADD COLUMN inhibition_weight REAL DEFAULT 0.0",
            # competitor_of references the memory_id of the practised item that inhibits this fact
            "ALTER TABLE fact_lifecycle ADD COLUMN competitor_of TEXT DEFAULT NULL",
        ],
    ),
    (
        4,
        "fact_lifecycle: add strength column for SAM associative memory model",
        [
            # Raaijmakers & Shiffrin 1981 SAM: memory items have associative strength
            # that decays with time since last retrieval and grows with each access.
            # strength = base activation; initialised from access_count at migration time.
            "ALTER TABLE fact_lifecycle ADD COLUMN strength REAL DEFAULT 0.0",
            # Create an index on strength for fast top-K retrieval
            "CREATE INDEX IF NOT EXISTS idx_fact_lifecycle_strength ON fact_lifecycle(strength DESC)",
            # Create an index on domain + access_count for inhibition grouping
            "CREATE INDEX IF NOT EXISTS idx_fact_lifecycle_domain_access ON fact_lifecycle(fact_type, access_count DESC)",
        ],
    ),
]


def _checksum(stmts: list[str]) -> str:
    return hashlib.sha256("\n".join(stmts).encode()).hexdigest()[:16]


def _get_applied_versions(conn: sqlite3.Connection) -> set[int]:
    try:
        rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
        return {r["version"] for r in rows}
    except sqlite3.OperationalError:
        return set()


def _apply_migration(
    conn: sqlite3.Connection,
    version: int,
    description: str,
    stmts: list[str],
    *,
    dry_run: bool = False,
    verbose: bool = False,
) -> bool:
    """Apply a single migration. Returns True if applied, False if skipped."""
    import time

    chk = _checksum(stmts)
    t0 = time.monotonic()
    applied = 0
    for stmt in stmts:
        if verbose:
            print(f"  [v{version}] {stmt[:80]}...")
        if not dry_run:
            try:
                conn.execute(stmt)
                applied += 1
            except sqlite3.OperationalError as e:
                # Column already exists is OK (idempotent ADD COLUMN)
                if "duplicate column" in str(e).lower() or "already exists" in str(e).lower():
                    if verbose:
                        print(f"  [v{version}] skipped (already exists): {e}")
                else:
                    raise
    if not dry_run and applied > 0:
        ms = (time.monotonic() - t0) * 1000
        conn.execute(
            "INSERT OR IGNORE INTO schema_migrations (version, description, checksum, duration_ms) VALUES (?,?,?,?)",
            (version, description, chk, round(ms, 2)),
        )
        conn.commit()
        _append_audit(version, description, chk)
    return not dry_run and applied >= 0


def _append_audit(version: int, description: str, checksum: str) -> None:
    entry = {
        "version": version,
        "description": description,
        "checksum": checksum,
        "applied_at": datetime.now(timezone.utc).isoformat(),
    }
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def run_migrations(*, dry_run: bool = False, verbose: bool = False) -> int:
    """Apply all pending migrations. Returns count of migrations applied."""
    if not LIFECYCLE_DB.exists():
        print("[schema-evolution] lifecycle.db does not exist — nothing to migrate.")
        return 0

    conn = _open_db()
    # Bootstrap: schema_migrations table itself is migration v1
    # Apply v1 unconditionally first (CREATE TABLE IF NOT EXISTS is idempotent)
    for version, description, stmts in MIGRATIONS:
        if version == 1:
            for stmt in stmts:
                conn.execute(stmt)
            conn.commit()
            break

    applied_versions = _get_applied_versions(conn)
    count = 0
    for version, description, stmts in MIGRATIONS:
        if version in applied_versions:
            if verbose:
                print(f"[schema-evolution] v{version} already applied — skip")
            continue
        print(f"[schema-evolution] applying v{version}: {description}")
        if _apply_migration(conn, version, description, stmts, dry_run=dry_run, verbose=verbose):
            count += 1
            print(f"[schema-evolution] v{version} OK")

    # After migrations: backfill strength from access_count for existing rows
    if not dry_run and 4 in {v for v, _, _ in MIGRATIONS} and 4 not in applied_versions:
        try:
            # SAM strength initialisation: strength = log1p(access_count) normalised
            conn.execute(
                "UPDATE fact_lifecycle SET strength = MIN(1.0, 0.1 * log(1 + COALESCE(access_count, 0))) WHERE strength = 0.0 AND COALESCE(access_count, 0) > 0"
            )
            conn.commit()
            if verbose:
                print("[schema-evolution] backfilled strength column from access_count")
        except Exception as e:
            print(f"[schema-evolution] strength backfill skipped: {e}", file=sys.stderr)

    conn.close()
    return count


def show_status() -> None:
    if not LIFECYCLE_DB.exists():
        print("lifecycle.db not found")
        return
    conn = _open_db()
    applied = _get_applied_versions(conn)
    print(f"lifecycle.db: {LIFECYCLE_DB}")
    print(f"Schema migrations: {len(applied)}/{len(MIGRATIONS)} applied")
    for version, description, stmts in MIGRATIONS:
        status = "✓" if version in applied else "PENDING"
        print(f"  v{version} [{status}]: {description}")
    try:
        rows = conn.execute(
            "SELECT version, applied_at, duration_ms FROM schema_migrations ORDER BY version"
        ).fetchall()
        if rows:
            print("\nApplied history:")
            for r in rows:
                print(f"  v{r['version']} at {r['applied_at']} ({r['duration_ms']:.1f}ms)")
    except Exception:
        pass
    conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="lifecycle.db schema evolution tracker")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be applied without running")
    parser.add_argument("--verbose", "-v", action="store_true")
    parser.add_argument("--status", action="store_true", help="Show migration status and exit")
    args = parser.parse_args()

    if args.status:
        show_status()
        return

    n = run_migrations(dry_run=args.dry_run, verbose=args.verbose)
    if n:
        print(f"[schema-evolution] Applied {n} migration(s).")
    else:
        print("[schema-evolution] No pending migrations.")


if __name__ == "__main__":
    main()
