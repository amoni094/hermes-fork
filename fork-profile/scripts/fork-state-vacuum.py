#!/usr/bin/env python3
"""fork-state-vacuum.py — Weekly VACUUM for the fork profile's state.db.

The default-profile state-wal-checkpoint cron hardcodes ~/.hermes/state.db and
does not touch the fork profile DB. Fork state.db runs journal_mode=delete
(no WAL), so it needs periodic VACUUM to reclaim freelist pages and prevent
unbounded growth.

Cron: 0 2 * * 0 (Sunday 02:00, no_agent=True)
"""
import os
import sqlite3
import sys
import pathlib

HERMES_HOME = pathlib.Path(os.environ.get("HERMES_HOME", pathlib.Path.home() / ".hermes"))
FORK_DB = HERMES_HOME / "profiles" / "fork" / "state.db"


def main() -> int:
    if not FORK_DB.exists():
        print(f"[fork-state-vacuum] {FORK_DB} not found — skipping")
        return 0

    size_before = FORK_DB.stat().st_size
    print(f"[fork-state-vacuum] VACUUM {FORK_DB} ({size_before / 1024 / 1024:.1f}MB)")

    try:
        con = sqlite3.connect(str(FORK_DB), timeout=10)
    except sqlite3.OperationalError as e:
        print(f"[fork-state-vacuum] ERROR: cannot open {FORK_DB}: {e}", file=sys.stderr)
        return 1
    try:
        jm = con.execute("PRAGMA journal_mode").fetchone()[0]
        fl = con.execute("PRAGMA freelist_count").fetchone()[0]
        av = con.execute("PRAGMA auto_vacuum").fetchone()[0]  # 0=none, 1=full, 2=incremental
        print(f"[fork-state-vacuum] journal_mode={jm}, freelist_pages={fl}, auto_vacuum={av}")

        # Enable incremental auto_vacuum if not already set (prevents unbounded growth)
        if av == 0:
            con.execute("PRAGMA auto_vacuum=INCREMENTAL")
            # auto_vacuum mode change requires VACUUM to take effect
            print("[fork-state-vacuum] Enabled PRAGMA auto_vacuum=INCREMENTAL")

        try:
            con.execute("VACUUM")
        except sqlite3.OperationalError as e:
            print(f"[fork-state-vacuum] ERROR: VACUUM failed (DB may be locked by gateway): {e}", file=sys.stderr)
            return 1
        fl_after = con.execute("PRAGMA freelist_count").fetchone()[0]
        print(f"[fork-state-vacuum] freelist after VACUUM: {fl_after}")
    finally:
        con.close()

    size_after = FORK_DB.stat().st_size
    saved = (size_before - size_after) / 1024 / 1024
    print(f"[fork-state-vacuum] Done. {size_after / 1024 / 1024:.1f}MB (saved {saved:.1f}MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
