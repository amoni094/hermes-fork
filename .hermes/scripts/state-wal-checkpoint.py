#!/usr/bin/env python3
"""
state-wal-checkpoint.py
Nightly SQLite WAL checkpoint + incremental vacuum for ~/.hermes/state.db.
Runs as --no-agent cron job. Replaced agent-job 462ef65ad091 (Sep 2026 audit).
"""
import sqlite3
import os

db_path = os.path.expanduser("~/.hermes/state.db")
con = sqlite3.connect(db_path, timeout=30)
try:
    r = con.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
    print(f"wal_checkpoint TRUNCATE: busy={r[0]} log={r[1]} ckpt={r[2]}")
    con.execute("PRAGMA incremental_vacuum")
    # Note: PRAGMA auto-commits in SQLite; explicit commit is harmless redundancy.
    print("incremental_vacuum: done")
finally:
    con.close()
