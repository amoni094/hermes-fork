# Timestamp-Only Maintenance: Worked Example

This reference captures a concrete timestamp-only maintenance sync run. Use it when you are unsure whether to rewrite the live-sync note or just refresh its timestamp.

## Scenario

**Date**: July 2, 2026, 16:08 AEST  
**Prior sync**: 15:07 AEST same day  
**Live-sync note state**: Current, accurate, frontmatter timestamp 2026-07-02 15:07 AEST  
**Daily note state**: Exists, already contains `## Hermes Chat Sync` block linking to live-sync note, states "No new durable changes since prior sync (15:07 AEST)"  
**Recent sessions**: One research/exploration session at 14:28 AEST (Reddit browsing); no configuration, cron, or workflow changes  
**Hint files**: No dirty-path entries since prior sync; file-event log tail shows activity ending ~24 hours prior

## Decision tree walk-through

```
1. Read the current live-sync note and daily note first.
   ✓ Live-sync note: present, frontmatter shows 2026-07-02 15:07 AEST
   ✓ Daily note: present, contains sync block, references live-sync note
   Both are continuity baselines; proceed.

2. Check timestamps.
   ✓ Both notes are recent (within current sync window, same day)
   ✓ Both appear current and curated
   Session history is secondary context only.

3. Read 3 most recent sessions.
   ✓ Session 1 (14:28): Reddit research exploration
      - No configuration changes, cron edits, or integration wiring
      - Transient exploration, not durable
   ✓ No other sessions in last 24 hours besides prior cron sync runs
   → No new durable items found

4. Decide.
   Current note state:  "Current + accurate"
   New durable items:   "None"
   Action from matrix:  "Timestamp refresh only"
```

## Execution

**Step 1: Patch frontmatter timestamp**

```diff
- last_synced: 2026-07-02 15:07 AEST
+ last_synced: 2026-07-02 16:08 AEST
```

**Step 2: Patch visible body timestamp**

(After frontmatter patch, re-read and verify the visible line separately)

```diff
- _Last synced: 2026-07-02 15:07 AEST._
+ _Last synced: 2026-07-02 16:08 AEST._
```

**Step 3: Verify readback**

After both patches, re-read the first 15 lines of the live-sync note:

```
---
title: Hermes Chat Live Sync
date: 2026-07-02
status: active
last_synced: 2026-07-02 16:08 AEST          ← Matches current time
scope: curated durable Hermes changes and verified results from the last 24 hours
---

# Hermes Chat Live Sync

_Last synced: 2026-07-02 16:08 AEST._       ← Matches current time
```

✓ **Both timestamps align to current sync time.**

**Step 4: Leave daily note unchanged**

The daily note is already correct:
- Contains `## Hermes Chat Sync` block
- References `[[Hermes Chat Live Sync]]`
- Notes "No new durable changes since prior sync (15:07 AEST)"
- Has no visible timestamp line of its own

→ Do not patch the daily note. Its state is current.

## Result

**Timestamp-only maintenance completed.**
- Live-sync note frontmatter and body both updated to 2026-07-02 16:08 AEST
- Daily note left stable (already correct)
- No new durable content found; existing curated state preserved
- Sync signals Hermes ran today without content churn

**Return**: "Timestamp refreshed to 16:08 AEST; no new durable changes. Content stable."

---

## Key learnings from this example

1. **Read existing notes first**: Do not assume a prior report or context summary counts as reading. Read the actual files.

2. **Recognize transient sessions**: A research/exploration session that produces no configuration, cron, integration, or workflow changes is not durable. Exclude it from the rewrite decision.

3. **Patch both locations**: When updating timestamps, patch frontmatter AND visible body separately. Do not assume one edit also updated the other. Always re-read to confirm.

4. **Daily note stability rule**: If the daily note is already correct (sync block present, reference correct, state accurate) and has no visible timestamp line, leave it untouched. The live-sync note carries the freshness signal.

5. **Efficiency**: Timestamp-only refresh takes ~2–3 minutes (read, patch, verify, report). Full rewrite would take ~20 minutes and risk clobbering already-curated content. The decision tree saves time and reduces churn.

6. **Same-day chaining**: When a prior sync already ran earlier the same day and found nothing new, the decision matrix says "timestamp refresh only" — do not re-run session discovery just because wall-clock time passed. Rely on the daily note block to signal whether another cron run happened.

