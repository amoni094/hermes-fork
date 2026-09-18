# Cron Sync Full Rewrite Pattern (Scheduled Tasks)

When `hermes-obsidian-sync` runs as a **scheduled cron job** (not user-triggered), use this pattern to determine when a full rewrite is appropriate vs. when timestamp-only maintenance suffices.

## Trigger

A cron sync job fires on a regular schedule (e.g., daily at 10:54 AM AEST). The user is not actively present at that moment. The question is: should the sync rewrite the live-sync note with new durable items from the prior 24 hours, or should it perform only timestamp-only maintenance?

## Decision

**Mandatory use of the decision tree** (`references/timestamp-only-maintenance-decision-tree.md`):

1. Read the current live-sync note and daily note first.
2. Check: does the live-sync note already contain accurate information about the durable state from the last 24 hours?
   - If yes → the decision tree output is **timestamp-only refresh**.
   - If no (new durable work occurred, or notes are stale/drifted) → the decision tree output is **full rewrite**.

The decision tree is the authoritative gate. Do not skip it or make assumptions based on "a cron job ran" or "no user asked for it."

## Real-world example: July 9, 2026, 10:54 AM AEST

**Setup:**
- Cron job configured to run daily at 10:54 AM AEST.
- Job runs unattended; no active user.
- Live-sync note was last updated July 8, 17:14 PM (yesterday afternoon).

**Decision tree execution:**
1. Read live-sync note: Last synced July 8, 17:14 PM. Contains session cleanup + stalled-session investigation.
2. Read daily note: 2026-07-08.md exists, contains that same sync block.
3. Read 2026-07-09.md: Does not exist yet (today's date).
4. Browse recent sessions: Found two new substantive sessions from July 8 evening (19:24–19:56 PM):
   - officecli skill created and installed (July 8, 19:25 PM)
   - NAB framework consolidation completed with all 14 findings integrated (July 8, 19:55 PM)
5. **Decision tree verdict:** Live-sync note is stale (from yesterday afternoon, doesn't mention July 8 evening work). New durable items found. → **Path B: Full Rewrite.**

**Execution:**
- Rewrote live-sync note with both July 8 sessions.
- Created today's daily note (2026-07-09.md) with a thin sync block.
- Verified readback.
- Reported the rewrite (not silent, because new durable state was significant).

## Pitfalls

- **Do not assume "it's a cron job" means "only timestamps."** Every cron run consults the decision tree. If new durable work appeared since the last sync, a full rewrite is mandatory.
- **Do not skip the decision tree because "nothing will change."** The decision tree exists precisely to discover what you don't expect.
- **Do not confuse "user not present" with "no durable changes."** Session history and durable files are the source of truth, not the user's moment-to-moment presence.
- **Do not suppress a rewrite because the last session was a cron/maintenance session itself.** If durable state changed, report it; if it didn't, only refresh timestamps.

## Connection to parent skill

This pattern is part of the mandatory step 3 in `hermes-obsidian-sync`: **MANDATORY CHECKPOINT — Consult the decision tree.**

The decision tree is language-agnostic about whether the sync was user-triggered or cron-scheduled. Both types of invocation follow the same gate.
