# Session cleanup checks

Use these checks when `hermes sessions list` is not enough to separate live sessions from stale rows.

## CLI checks

- `hermes sessions prune --help`
- `hermes sessions delete --help`
- `hermes sessions list`
- `hermes sessions stats`

## SQLite inspection targets

Query `~/.hermes/state.db`, table `sessions`.

Useful columns:
- `id`
- `source`
- `started_at`
- `ended_at`
- `title`
- `message_count`
- `tool_call_count`
- `archived`

Primary filter for open rows:
- `WHERE ended_at IS NULL`

Useful interpretation:
- newest untitled `cli` row with `message_count = 0` may be the current live shell
- old `tui`/`cli` rows with `message_count = 0` are usually safe stale-session candidates
- low-count sessions with 1-2 messages should be read before deletion
- cron rows need extra care; verify against active jobs or current process state

## Deletion pattern

Prefer explicit deletions:
- `hermes sessions delete <id> --yes`

Use CLI deletion when the stale count is small (<10).
Use bulk Python close (see below) when there are 10+ stale rows — looping the CLI 80 times is slow and fragile.

## Bulk close via Python (for 10+ stale rows)

When there's a backlog of cron sessions that the runtime never stamped with `ended_at`:

```python
import sqlite3, time
conn = sqlite3.connect('/var/home/rainbow/.hermes/state.db')
now = time.time()

# Close specific stale CLI sessions by ID list
cli_stale = ['id1', 'id2', 'id3']
placeholders = ','.join('?' * len(cli_stale))
conn.execute(f'UPDATE sessions SET ended_at = ? WHERE id IN ({placeholders})', [now] + cli_stale)
print(f'Closed {conn.execute("SELECT changes()").fetchone()[0]} stale CLI sessions')

# Close ALL completed cron sessions that were never stamped
conn.execute("UPDATE sessions SET ended_at = ? WHERE source = 'cron' AND ended_at IS NULL", [now])
print(f'Closed {conn.execute("SELECT changes()").fetchone()[0]} stale cron sessions')

conn.commit()
conn.close()
```

Safe to use: `ended_at` is a close-timestamp only. Hermes reads it but does not write back
to these rows once a session ends. Direct DB write is safe for bulk-close.

Note: `sqlite3` CLI binary is not available on this system (Fedora Silverblue).
Use `python3 -c "import sqlite3 ..."` — Python's built-in sqlite3 module is always present.

## Post-delete verification

```python
import sqlite3
conn = sqlite3.connect('/var/home/rainbow/.hermes/state.db')
rows = conn.execute(
    "SELECT id, source, title, message_count FROM sessions WHERE ended_at IS NULL ORDER BY started_at DESC"
).fetchall()
print(f'Open sessions remaining: {len(rows)}')
for r in rows:
    print(f'  {r[0]}  source={r[1]}  msgs={r[3]}  title={r[2]}')
conn.close()
```

Then also rerun `hermes sessions stats` and confirm only the current session or genuinely
live background sessions remain.

## Lesson captured

The reliable cleanup pattern is:
1. inventory via CLI (`hermes sessions list`, `hermes sessions stats`)
2. inspect `state.db` for `ended_at IS NULL`
3. read borderline low-count sessions
4. delete by ID (CLI for small counts, Python bulk-close for large backlogs)
5. verify in both CLI and SQLite
