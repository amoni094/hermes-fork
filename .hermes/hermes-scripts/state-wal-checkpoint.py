#!/usr/bin/env python3
"""
state-wal-checkpoint.py
Nightly SQLite WAL checkpoint + VACUUM for ~/.hermes/state.db.
Runs as --no-agent cron job. Replaced agent-job 462ef65ad091 (Sep 2026 audit).

Fix 2026-09-19: replaced PRAGMA incremental_vacuum (no-op when auto_vacuum=NONE)
with VACUUM. auto_vacuum=0 on this DB, so incremental_vacuum never freed a page.
VACUUM rewrites the DB file, reclaims all freelist pages, and resets freelist_count.
Prerequisite: no active readers/writers. Cron fires at 3:20am; safe window confirmed.
"""
import sqlite3
import os

db_path = os.path.expanduser("~/.hermes/state.db")
con = sqlite3.connect(db_path, timeout=30)
try:
    # WAL checkpoint first — flush WAL frames into the main DB before VACUUM
    r = con.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
    print(f"wal_checkpoint TRUNCATE: busy={r[0]} log={r[1]} ckpt={r[2]}")
    # Verify auto_vacuum mode for diagnostic purposes
    av = con.execute("PRAGMA auto_vacuum").fetchone()[0]
    print(f"auto_vacuum mode: {av} (0=NONE; incremental_vacuum would be no-op)")
    # VACUUM: rewrites the full DB, reclaims all dead pages regardless of auto_vacuum mode
    fl_before = con.execute("PRAGMA freelist_count").fetchone()[0]
    pc_before = con.execute("PRAGMA page_count").fetchone()[0]
    con.execute("VACUUM")
    fl_after = con.execute("PRAGMA freelist_count").fetchone()[0]
    pc_after = con.execute("PRAGMA page_count").fetchone()[0]
    freed_mb = (fl_before - fl_after) * 4096 / 1e6
    print(f"VACUUM: freelist {fl_before}->{fl_after}, pages {pc_before}->{pc_after}, freed ~{freed_mb:.1f}MB")
finally:
    con.close()
