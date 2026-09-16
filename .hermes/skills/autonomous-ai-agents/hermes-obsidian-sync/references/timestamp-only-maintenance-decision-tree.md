# Timestamp-Only Maintenance Decision Tree

When a cron sync run encounters an already-current live-sync note and daily note, avoid unnecessary session drilling and rewrites. Use this decision tree to determine whether to rewrite or refresh-only.

## Decision flow

1. **Read the current live-sync note and daily note first** (before browsing sessions or hint files).
   - These are the continuity baseline.
   - If both are already current and curated, subsequent session history is secondary context only.

2. **Check the live-sync note's frontmatter and visible timestamp**.
   - If both timestamps match and are recent (within the current sync window), the note is fresh.

3. **Read the 3 most recent sessions** (not all; aim for max 3-5 lines each).
   - **Filter out prior cron sync runs strictly** (they are maintenance context, not source material for new durable items).
   - When session_search returns crowded results, prioritize user/CLI sessions over cron-job sessions.
   - If the only recent sessions are cron sync runs, that signals "no new user work since last sync" → durable items have not appeared → Path A (timestamp-only refresh).
   - Look for: deployment changes, config state changes, integration additions, verified fixes.
   - If all recent sessions are either cron runs or routine activity refinement, check if they add anything new.

4. **Decision matrix**:

   | Current note state | New durable items found? | Action |
   |---|---|---|
   | Current + accurate | None | Timestamp refresh only (patch frontmatter + body line) |
   | Current + accurate | Yes, significant | Rewrite live-sync note + patch daily note |
   | Stale | N/A | Rewrite both |
   | Drifted | N/A | Rewrite both |

## Timestamp-refresh-only pattern

When no new durable items warrant content rewrite:
1. Patch the frontmatter `last_synced` field to current time.
2. Patch the visible body line `_Last synced: ...._` separately to match.
3. Leave the daily note untouched (unless it also has a visible timestamp line that needs refresh).
4. Re-read both files after patches to confirm alignment.
5. Report the result: "Timestamp refreshed to HH:MM AEST; content unchanged."

## Why this matters

- **Efficiency**: Timestamp-only maintenance takes ~5 seconds after readback. Full rewrite takes ~30 seconds and risks clobbering already-curated content if a new session was missed.
- **Stability**: The live-sync note content should not churn on every cron run. Rewrite only when genuinely new durable state appears.
- **Cron reliability**: Repeated cron runs on the same note should be idempotent; timestamp refresh is idempotent, full rewrites can introduce drift if concurrent writes happen.

## Pitfall: confusing "no new sessions" with "no new durable items"

A recent session may have produced tool output, test runs, or intermediate steps that don't constitute durable state. For example:
- A session that ran `git status` multiple times but made no actual commits → not durable.
- A session that tested a configuration change and then reverted it → not durable (unless the caveat is worth noting).
- A session that debugged an error and fixed it → durable is the fix, not the debug steps.

Read the session summary, not the full transcript, to distinguish signal from noise.
