# Daily note bootstrap and timestamp sync

Use this when the current daily note does not yet exist or when a cron run must refresh the visible timestamp after final verification.

## Rules

- Resolve the current local date/time first and use that exact runtime value for the daily-note filename and visible timestamps.
- If today's daily note file is missing, create a minimal note containing only the `## Hermes Chat Sync` block rather than skipping the update.
- When the live-sync note is drafted before the final verification pass, refresh the visible `last_synced` line to the actual completion time so the note body and frontmatter do not drift.
- If the daily-note sync block includes its own visible timestamp line, refresh that line too after readback verification.
- Read back the written files after the write/patch and treat that readback as the primary verification source.