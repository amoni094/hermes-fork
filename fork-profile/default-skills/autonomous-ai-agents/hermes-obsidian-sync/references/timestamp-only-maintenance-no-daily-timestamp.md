# Timestamp-Only Maintenance: Daily Note Without Visible Timestamp

**Scenario**: A cron sync run finds no new durable items, both live-sync and daily notes are current and well-curated, but the daily note has no `- Last synced: ...` line (only a link bullet + 2-4 short content bullets).

**Decision**: Path A (timestamp-only refresh). Apply the refresh to the live-sync note only; leave the daily note completely untouched.

## Concrete Example: July 18, 2026, 18:47 AEST

**Session history**:
- Last sync: July 18, 03:42 UTC (morning)
- Most recent substantive work: July 18, 13:27 UTC (AI Agent Efficiency Research)
- Time now: July 18, 18:47 AEST (15 hours after last sync)

**Current state of live-sync note**:
```
---
last_synced: 2026-07-18T03:42:02Z
scope: Curated Hermes chat activity...
---

# Hermes Chat Live Sync

_Last synced: 2026-07-18 03:42 UTC_

## Recent Sessions
[AI Agent Efficiency Research session fully captured; 40+ papers, 6 implementations, detailed durable state]
```

**Current state of daily note** (`2026-07-18.md`):
```
## Hermes Chat Sync

- See [[Hermes Chat Live Sync]] for curated recent Hermes activity
- **AI Agent Efficiency Research**: Multilingual sweep...40+ papers verified. Research index updated.
- **Implementations completed**: nesy.py CodingVerifier, skillopt_score.py...
- **Pending**: PreAct state-machine skill, Selective Persistent Memory pattern...
```

**Key observations**:
1. Daily note has NO visible timestamp line (no `- Last synced: ...`)
2. Daily note content is accurate and up-to-date (4 concise bullets)
3. Live-sync note exposes visible timestamp in the body
4. No new durable changes since the morning sync

**Action taken**:
1. Patched live-sync frontmatter: `last_synced: 2026-07-18T03:42:02Z` → `2026-07-18T08:47:12Z`
2. Patched live-sync visible line: `_Last synced: 2026-07-18 03:42 UTC_` → `_Last synced: 2026-07-18 18:47 AEST_`
3. **Left daily note untouched** (no patches applied)

**Verification**:
```
Live-sync note readback (lines 2, 9):
  Line 2: last_synced: 2026-07-18T08:47:12Z ✓
  Line 9: _Last synced: 2026-07-18 18:47 AEST_ ✓
  
Daily note readback:
  Unchanged from prior state (4 bullet sync block intact) ✓
```

## Why this pattern matters

- **Separating concerns**: Live-sync note is the curated repository; daily note is the quick-reference summary. They don't need synchronized timestamps.
- **Reducing noise**: Daily notes that already have 2-4 concise bullets don't benefit from an added timestamp line — it adds visual clutter without added value.
- **Timestamp signal location**: The live-sync note's timestamp is the primary "sync was successful" signal. The daily note's link to it is enough; the daily note doesn't need to redundantly repeat the timestamp.
- **Consistency with the skill**: The skill's Path A section explicitly says "leave it unchanged unless it has its own visible timestamp line that needs refresh." This example follows that rule strictly.

## Pitfall: Don't add timestamps where they don't belong

A common mistake: "The live-sync note was refreshed, so let me also add a timestamp line to the daily note for consistency."

**Don't do this.** The skill lists two independent text locations for a reason: they evolve independently. The daily note's content updates when new durable items appear (Path B rewrite). The daily note's timestamp would update only if that note itself had originally exposed a visible timestamp. Introducing a timestamp line into a note that previously had none creates false consistency and makes future sync runs more error-prone (now you have two timestamp locations to track even when they should move independently).

**Rule**: Keep the daily note structure stable. If it never had a visible timestamp, don't add one during maintenance runs.
