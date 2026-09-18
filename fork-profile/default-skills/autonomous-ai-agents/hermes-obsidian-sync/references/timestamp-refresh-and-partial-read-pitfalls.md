# Timestamp refresh and partial-read pitfalls

Session-derived guidance for Hermes Obsidian sync runs.

## Use when
- Rewriting the live-sync note.
- Refreshing the visible timestamp after verification.
- Working from paginated note reads.

## Lessons
- The live-sync note can carry two visible timestamps: frontmatter `last_synced` and the body `_Last synced_` line. Refresh both after the final verification pass so they do not drift. If you patch only one timestamp location, immediately patch the other before finishing.
- If a note was last inspected with offset/limit pagination, re-read the full file before overwriting it. Partial reads are useful for inspection, but they are not a safe overwrite base.
- When the daily note is already current, keep it thin and stable unless genuinely new durable items appeared.
- If the daily note includes its own visible sync timestamp line, refresh it only when the completed sync time actually changed; do not churn the body just to chase the clock.
