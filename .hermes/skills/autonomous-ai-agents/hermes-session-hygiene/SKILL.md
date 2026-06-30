---
name: hermes-session-hygiene
description: Clean up inactive Hermes sessions safely by distinguishing live sessions from stale/open rows, deleting specific inactive sessions, and verifying the session store afterward.
version: 1.0.0
author: Hermes Agent
created_by: agent
license: MIT
platforms: [linux, macos]
metadata:
  hermes:
    tags: [hermes, sessions, cleanup, sqlite, cli, hygiene]
---

# Hermes Session Hygiene

Use this when the user asks to clean up, prune, or inspect Hermes sessions, especially when `hermes sessions list` shows blank, inactive, or obviously stale entries.

This is a narrow session-cleanup skill. If the problem is broader context bloat inside the current live conversation, load `hermes-context-hygiene` instead. If you are deciding where prior continuity should be retrieved from, load `hermes-memory-surface-selection`.

## Triggers

- "clean up inactive sessions"
- "prune old Hermes sessions"
- "why do I have so many empty sessions?"
- "which sessions are still open?"
- "delete stale CLI/TUI sessions but keep the live one"

## Goals

1. Preserve the active session the user is currently using.
2. Remove stale open sessions with low or zero value.
3. Prefer explicit deletion of identified session IDs over broad pruning when recency matters.
4. Verify the result in both the CLI view and the SQLite session store.

## Workflow

1. Check Hermes session commands first.
   - Use `hermes sessions prune --help` to confirm broad-prune options.
   - Use `hermes sessions delete --help` to confirm targeted deletion syntax.

2. Inspect current session inventory.
   - Run `hermes sessions list` to see recent titles, last-active timestamps, and IDs.
   - Run `hermes sessions stats` to capture the before-state.

3. Distinguish live processes from stale session rows.
   - Check running Hermes processes separately; do not assume every open session row is still active.
   - The active CLI session usually appears as the newest open `cli` session.

4. Inspect the SQLite store when the CLI list is ambiguous.
   - Query `~/.hermes/state.db` table `sessions` for rows with `ended_at IS NULL`.
   - Review `id`, `source`, `started_at`, `title`, and `message_count`.
   - Stale candidates are often old `cli`/`tui` rows with `message_count = 0` or tiny counts and no active matching process.

5. Read borderline sessions before deleting.
   - If a session has a small nonzero message count, inspect it before deletion rather than guessing.
   - Keep sessions that are current, user-meaningful, or clearly tied to still-running work.

6. Delete explicitly by session ID.
   - Use `hermes sessions delete <session_id> --yes` for each stale inactive session.
   - Prefer this over `prune --older-than` when the user asked for inactive sessions rather than merely old ones.

7. Verify after deletion.
   - Recheck `hermes sessions stats`.
   - Requery `state.db` for remaining `ended_at IS NULL` rows.
   - Confirm that only the actual live current session remains, or explain any remaining cron/live sessions.

## Decision Rules

- Keep the current session, even if it is untitled or has `message_count = 0`.
- Treat cron sessions separately from CLI/TUI cleanup; they may still be valid if tied to active jobs.
- If a cron session is clearly stale and not still running, it can be deleted, but verify more carefully than for empty CLI/TUI rows.
- Empty untitled sessions are strong deletion candidates when they are not the current live session.

## Verification Checklist

- `hermes sessions list` still shows the current session.
- `hermes sessions stats` reflects a reduced total.
- SQLite `sessions` query shows only genuinely live open sessions.
- No claim of success without post-delete verification.

## Pitfalls

- Do not use age alone as the definition of inactive; a recent row can still be stale, and an older row may still matter.
- Do not delete the newest open CLI session just because it has zero messages; that is often the current shell session.
- Do not assume blank titles mean worthless sessions; inspect low-count sessions if there is any doubt.
- Do not stop after `hermes sessions list`; the SQLite store is the tie-breaker when open-session state is unclear.

## References

- `references/session-cleanup-checks.md` — compact SQLite queries and deletion heuristics used during a real cleanup pass.
