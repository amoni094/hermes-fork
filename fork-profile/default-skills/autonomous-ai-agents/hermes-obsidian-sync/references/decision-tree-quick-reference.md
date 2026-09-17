# Decision Tree Quick Reference

## Three-Path Decision Logic

After reading the live-sync note and today's daily note, ask **three quick questions**:

### 1. Are both notes recent **and** accurate?
   - Live-sync `last_synced` within ~8 hours? ✓
   - Daily note exists and reflects the current durable state? ✓
   - No new sessions found since last sync timestamp? ✓
   - → **PATH A: Timestamp-Only Refresh** (jump to verification, patch timestamps, done)

### 2. Are notes stale, drifted, or missing?
   - Live-sync `last_synced` >8 hours ago? ✓
   - Daily note doesn't exist yet? ✓
   - New sessions found in last 24 hours with durable work? ✓
   - → **PATH B: Full Rewrite** (inspect sessions, rewrite live-sync, create/patch daily note)

### 3. No new content AND caller allows silent delivery?
   - No new durable items detected? ✓
   - Cron job explicitly accepts `[SILENT]` suppression? ✓
   - → **PATH C: Silent Suppression** (return `[SILENT]`, no files touched)

## Default Behavior

If in doubt → **PATH A** (timestamp-only refresh). It is always safe and signals "sync completed successfully at this time." The timestamp proves the run executed even if no new durable items were found.

## Session-Search Quick Heuristic

- **Cron-dominated results** (e.g., five cron jobs in last 24h): Treat as maintenance context; focus on user or non-cron substantive sessions
- **Recent session >100KB**: Use `grep` on the temp file to extract high-signal keywords (`write_file`, `patch`, `skill`, `config`, `cron`, feature names) before attempting full read
- **Same-day multiple syncs**: After an earlier sync, look for new durable work **after** that sync's timestamp; avoid re-reporting the same settled items

## Verification Checklist

- ✅ Read back the live-sync note frontmatter `last_synced` field (should match the completed sync time)
- ✅ Read back the visible body `_Last synced: ..._` line (must match frontmatter)
- ✅ Read back today's daily note (should exist, should have sync block with link)
- ✅ If any timestamp line still shows old time after patching, patch it again immediately — do not defer to next run

**Pitfall**: Frontmatter and visible-body timestamps are independent text locations. Patching one does not auto-update the other. Always patch both and verify readback.
