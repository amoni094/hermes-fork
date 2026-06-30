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

Prefer explicit deletion when the task is "inactive sessions" rather than "everything older than N days".

## Post-delete verification

After deleting:
1. rerun `hermes sessions stats`
2. rerun the SQLite open-session query
3. confirm only the current session or genuinely live background sessions remain

## Lesson captured

The reliable cleanup pattern is:
1. inventory via CLI
2. inspect `state.db` for `ended_at IS NULL`
3. read borderline low-count sessions
4. delete by ID
5. verify in both CLI and SQLite
