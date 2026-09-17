# Timestamp-Only Refresh — Timezone Pattern (July 2026)

## Runtime context
- **Cron execution**: 2026-07-23T21:44:04+10:00 (AEST, Australian Eastern Standard Time)
- **Frontmatter timestamp**: ISO-8601 UTC (2026-07-23T11:44:04Z)
- **Visible body timestamp**: Human-readable AEST (2026-07-23 21:44 AEST)

## Why both locations matter

The frontmatter `last_synced` is machine-read and ISO-8601 strict (UTC, always).
The visible body `_Last synced: ..._` is human-facing and uses the local vault timezone (AEST).

**They drift if only one is patched.** On the next sync run:
- If frontmatter was patched but body wasn't: the body shows stale time, confusing whether sync actually ran
- If body was patched but frontmatter wasn't: programmatic readers (e.g., decision tree helpers, other tooling) see stale UTC time

Both patches must happen in the same run, even if it's a timestamp-only maintenance refresh with no new durable content.

## Patch sequence

1. Resolve runtime date/time first: `date --iso-8601=seconds` (captures both local and UTC offset)
2. Read existing notes before any decision
3. Apply decision tree
4. If Path A (timestamp-only refresh):
   - Calculate two forms:
     - **ISO-8601 UTC**: `2026-07-23T11:44:04Z`
     - **Human AEST**: `2026-07-23 21:44 AEST`
   - Patch frontmatter `last_synced: 2026-07-23T11:44:04Z`
   - Patch visible body `_Last synced: 2026-07-23 21:44 AEST_` (separate patch call, independent location)
5. Verify both via readback

## Worked example

**Runtime**: `date --iso-8601=seconds` → `2026-07-23T21:44:04+10:00`

Extract:
- UTC: `2026-07-23T11:44:04Z` (subtract 10 hours from local wall-clock, append Z)
- AEST: `2026-07-23 21:44 AEST` (use local wall-clock, add timezone label)

Apply patches in separate calls:
```
patch(
  path=.../Hermes Chat Live Sync.md,
  old_string='last_synced: 2026-07-23T17:41:57Z',
  new_string='last_synced: 2026-07-23T11:44:04Z'
)

patch(
  path=.../Hermes Chat Live Sync.md,
  old_string='_Last synced: 2026-07-23 17:41 AEST_',
  new_string='_Last synced: 2026-07-23 21:44 AEST_'
)
```

Readback both to confirm:
- Frontmatter: `last_synced: 2026-07-23T11:44:04Z` ✓
- Body: `_Last synced: 2026-07-23 21:44 AEST_` ✓

## Pitfall: don't assume date arithmetic is correct

Timezones are tricky. Instead of calculating "UTC = local - 10", use the runtime `date` output which includes the offset (+10:00), then map directly:
- Keep the date + time digits, add Z for UTC form
- Use the local wall-clock time + append the zone label (AEST) for human form

If you re-calculate the hour offset, you risk off-by-one errors when DST transitions occur or when running at edge times (e.g., 23:50 local → 13:50 UTC next day).

**Don't**: `local_time - hours_offset = utc_time`
**Do**: Use the output of `date --iso-8601=seconds` directly, extract the (+HH:MM) offset, and map it.
