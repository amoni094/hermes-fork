#!/bin/bash
# Prune stale Hermes sessions and reclaim DB space
# Cron sessions: 2-day retention (they accumulate hourly)
#   NOTE: LLM-driven cron jobs are stored as source=unknown, not source=cron.
#   Prune both to catch all cron-spawned sessions.
# Subagent sessions: 3-day retention
# All sessions: 7-day retention
# Runs every 4h so missed 3am fire doesn't cause all-day accumulation

hermes sessions prune --source cron --older-than 2 --yes 2>&1
hermes sessions prune --source unknown --older-than 2 --yes 2>&1
hermes sessions prune --source subagent --older-than 3 --yes 2>&1
hermes sessions prune --older-than 7 --yes 2>&1

# GC stale working-memory files (>48h, not linked to any active session)
WM_DIR="${HERMES_HOME:-$HOME/.hermes}/cache/working-memory"
if [ -d "$WM_DIR" ]; then
  WM_DELETED=$(find "$WM_DIR" -name '*.json' -mtime +2 2>/dev/null | wc -l)
  find "$WM_DIR" -name '*.json' -mtime +2 -delete 2>/dev/null
  echo "WM GC: removed ${WM_DELETED} stale working-memory files older than 48h"
fi

# Reclaim freed pages (SQLite VACUUM); skip if DB < 300 MB to keep it cheap
DB="${HERMES_HOME:-$HOME/.hermes}/state.db"
DB_MB=$(du -m "$DB" | cut -f1)
if [ "$DB_MB" -gt 300 ]; then
  python3 -c "import sqlite3; c=sqlite3.connect('$DB'); c.execute('VACUUM'); c.close(); print('VACUUMed state.db (was ${DB_MB}MB)')"
fi
