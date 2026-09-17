# session-prune.sh — Canonical Script

Lives at `~/.hermes/scripts/session-prune.sh`. Registered as `no_agent=true` cron job `session-auto-prune`.

## Recommended schedule

`every 240m` (every 4 hours) — NOT `0 3 * * *`.

Rationale: Hermes is often not alive at 3am. A missed once-daily fire means a full day of accumulation.
An interval schedule guarantees cleanup fires within 4h of Hermes starting.

## Script (CORRECTED — includes `--source unknown`)

```bash
#!/bin/bash
# Prune stale Hermes sessions and reclaim DB space
# Cron sessions: 2-day retention
#   IMPORTANT: LLM-driven cron jobs register as source=unknown, NOT source=cron.
#   Always prune both to catch all cron-spawned sessions.
# Subagent sessions: 3-day retention
# All sessions: 7-day retention

hermes sessions prune --source cron --older-than 2 --yes 2>&1
hermes sessions prune --source unknown --older-than 2 --yes 2>&1
hermes sessions prune --source subagent --older-than 3 --yes 2>&1
hermes sessions prune --older-than 7 --yes 2>&1

# Reclaim freed pages (SQLite VACUUM); skip if DB < 300 MB to keep it cheap
DB="$HOME/.hermes/state.db"
DB_MB=$(du -m "$DB" | cut -f1)
if [ "$DB_MB" -gt 300 ]; then
  python3 -c "import sqlite3; c=sqlite3.connect('$DB'); c.execute('VACUUM'); c.close(); print('VACUUMed state.db (was ${DB_MB}MB)')"
fi
```

## Why `--source unknown` is mandatory

When a cron job has `no_agent=false` (LLM-driven), each run spawns a full agent session.
Those sessions are stored in the DB as `source=unknown` — NOT `source=cron`.
A prune that only targets `--source cron` silently skips all of them forever.

This was the root cause of a session explosion observed July 2026:
- `hourly-hermes-chat-sync` (60m interval, no_agent=false) had run 214 times
- Each run = 1 `source=unknown` session
- Both prune scripts were missing the `--source unknown` line
- Result: 300+ accumulated sessions within hours of a manual cleanup

Verify at any time:
```python
python3 -c "
import sqlite3
db = sqlite3.connect('/var/home/rainbow/.hermes/state.db')
rows = db.execute('SELECT source, COUNT(*) FROM sessions GROUP BY source').fetchall()
print(rows); db.close()
"
```
If `unknown` count is large, the prune script is missing the fix.

## Why four prune passes

| Pass | Source | Retention | Reason |
|------|--------|-----------|--------|
| 1 | cron | 2 days | no_agent=true cron sessions; may be empty |
| 2 | unknown | 2 days | no_agent=false (LLM-driven) cron sessions; accumulate fastest |
| 3 | subagent | 3 days | Delegation spawns many short sessions; 7d would bloat significantly |
| 4 | (all) | 7 days | Catch-all for CLI/telegram; matches typical session utility horizon |

## Second script: prune_sessions.sh

A second prune script (`~/.hermes/scripts/prune_sessions.sh`) is registered to the daily 2am cron job.
It also needs the `--source unknown` line. Canonical form:

```bash
#!/usr/bin/env bash
# NOTE: LLM-driven cron jobs are stored as source=unknown, not source=cron.
# Prune both to catch all cron-spawned sessions.
hermes sessions prune --source cron --older-than 3 --yes
hermes sessions prune --source unknown --older-than 3 --yes
hermes sessions prune --source cli --older-than 14 --yes
hermes sessions optimize
```

When patching one script, always audit the other.

## Cron job frequency guidance

LLM-driven cron jobs (no_agent=false) should run at the lowest frequency that meets the use case:
- Obsidian sync, memory sync, briefings: every 240m is sufficient, not every 60m
- 60m = 24 sessions/day = 48 live at any time under 2-day retention
- 240m = 6 sessions/day = 12 live at any time — 4x less noise

To slow down an existing job: `cronjob(action='update', job_id='<id>', schedule='every 240m')`

## Steady-state expectation

With chat-sync running every 240m (corrected from 60m):
- ~12 unknown sessions always present (2-day window)
- A few dozen CLI sessions (7-day window)
- Total: ~20-50 sessions is normal

300+ sessions = sign the `--source unknown` prune is missing OR a job runs too frequently.

## DB size diagnostic

```python
import sqlite3, datetime
conn = sqlite3.connect('/var/home/rainbow/.hermes/state.db')
cur = conn.cursor()
cur.execute('PRAGMA page_count')
pc = cur.fetchone()[0]
cur.execute('PRAGMA freelist_count')
fl = cur.fetchone()[0]
cur.execute('PRAGMA page_size')
ps = cur.fetchone()[0]
print(f'Total pages: {pc}, freelist (wasted): {fl}, page_size: {ps}')
print(f'Wasted: {fl*ps/1024/1024:.1f} MB out of {pc*ps/1024/1024:.1f} MB')
conn.close()
```

If `freelist_count / page_count > 0.3` (30%+ waste), run VACUUM immediately.
