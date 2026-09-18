# Daily-Note Bootstrap Logic

When a cron sync run encounters a missing daily note, deciding whether to create one is driven by visibility and continuity, not content volume.

## Rule

**Always create the daily note, even on timestamp-only or no-durable-changes runs.**

The daily note serves as a timestamp signal that "Hermes ran today." An observer looking at the vault on 2026-07-02 should be able to see whether Hermes ran on 2026-07-01 by checking for the existence of `memory/2026-07-01.md`. If no durable items appeared, the note can be minimal, but it should exist.

## Pattern examples

### Timestamp-only refresh, minimal case (no new durable items, no transient context)
```markdown
## Hermes Chat Sync

- [[Hermes Chat Live Sync]]
- No new durable changes since prior sync (July 15)
- Last synced: 2026-07-16 10:40 UTC
```

**Why:** Three lines only:
1. Link to live-sync note (de-duplication — don't repeat full durable state here)
2. Explicit "no new items" statement (prevents ambiguity: did the sync run or not?)
3. Timestamp for verification (confirms the sync completed at this specific time)

Use this when no new items and no transient context warrants mentioning.

### Timestamp-only refresh, no new durable items (with transient context)
```markdown
# 2026-07-01

## Hermes Chat Sync

- [[Hermes Chat Live Sync]]
- No new durable configuration or workflow changes since 2026-06-30 sync
- Policy dashboard spun up (transient activity)
```

**Why:** Future sessions can see at a glance that:
1. Hermes did run on 2026-07-01 (the note exists)
2. No operational changes were made that day (explicit "no new durable" bullet)
3. The dashboard was running (context for anyone reviewing daily patterns)

Use this when transient/diagnostic activity warrants noting but no durable changes appeared.

### Major sync run, many items found
```markdown
# 2026-07-01

## Hermes Chat Sync

- [[Hermes Chat Live Sync]]
- Config veto rules: 6 new hard-block rules added, 3 new warn rules
- Fable-5 threat-model extension completed (4 upstream adversarial patterns, 1 regex fix)
- Free-tier LLM integration: Groq, Cerebras, Gemini provisioned + routing matrix updated
```

**Why:** Same visibility signal, but with substantive items anchoring the day's work.

## Exception case: Silent suppression

If the cron caller explicitly set `silent_delivery: true` AND genuinely no new durable items appeared, you may return `[SILENT]` instead of creating the daily-note stub.

But if ANY durable items were found, always create the note even if silent delivery is enabled — the note is the permanent record, not the delivery output.

## Pitfall: confusing "nothing to report" with "nothing to create"

A timestamp-only refresh is still a run that happened. Create the note. A future session asking "did Hermes run on the 15th?" should get a clear yes/no answer from the vault, not have to puzzle through whether the missing note means "didn't run" or "ran but found nothing."

## Integration with live-sync note rewrite

When the daily note is minimal (no new durable items), the live-sync note still carries the full durable state from recent sessions. They are not mirrors of each other:

- **Live-sync note** — comprehensive durable state + themes, not limited by "what was new today"
- **Daily note** — thin visibility + the most pressing new items from today (or explicit "no new items" if applicable)

Do not skip creating the daily note just because the live-sync note wasn't rewritten. They serve different purposes: vault continuity vs. curated durable summary.
