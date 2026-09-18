# Full Rewrite Sync: Same-Day New Items (Worked Example)

This reference captures a concrete **full-rewrite** sync run that detected new durable work after an earlier same-day sync. Use it when you are deciding between timestamp-only refresh vs. content rewrite, and you find genuine new durable items.

## Scenario

**Date**: July 2, 2026, 19:11 AEST  
**Prior sync**: 18:10 AEST same day  
**Live-sync note state**: Current, accurate, frontmatter timestamp 2026-07-02 18:10 AEST, last visible body line 18:10 AEST  
**Daily note state**: Exists, already contains `## Hermes Chat Sync` block, mentions prior sync  
**Recent sessions**: 5 sessions in the last 1 hour (17:33–17:36 window) containing:
  - Session 17:34: **Session database cleanup + prune schedule fix** — DB VACUUM (1.1GB → 512MB), session-prune script enhanced, cron schedule changed 3am → every 4h
  - Sessions 17:33, 16:11, 14:07, 14:27: Nightly ops swarm, analysis worker, research work, agentmemory evaluation
**Hint files**: Stale (from July 1); not useful for same-day detection  
**New durable items**: YES — DB vacuum, session-prune enhancements, cron schedule change

## Decision tree walk-through

```
1. Read the current live-sync note and daily note first.
   ✓ Live-sync note: present, frontmatter 2026-07-02 18:10 AEST
   ✓ Daily note: present, contains sync block
   Both are continuity baselines; proceed.

2. Check timestamps.
   ✓ Both notes are recent (same day, within current sync window)
   ✓ Both appear current and curated
   Session history may have new signal; proceed to inspect.

3. Read 3 most recent sessions.
   ✓ Session 17:34: **Infrastructure fix** — DB vacuum, session-prune script, cron schedule change
      - Durable: DB state change (1.1GB → 512MB), new config (schedule), script enhancement
      - This is new since 18:10 sync
   ✓ Session 17:33: Kill inactive sessions — infrastructure maintenance
   ✓ Sessions 16:11, 14:07, 14:27: Nightly ops, kanban, agentmemory — already reflected in prior sync
   → **New durable items found** (session DB infrastructure work)

4. Decide.
   Current note state:  "Current + accurate"
   New durable items:   "YES — significant"
   Action from matrix:  "Rewrite live-sync note + patch daily note"
```

## Execution

### Step 1: Add new session section to live-sync note

The existing live-sync note has these sections:
- Hermes config upgrade passes 2 & 3 (2026-07-01)
- Hermes → Cowork port + review (2026-07-01)
- LLM routing optimization (2026-07-01)
- Session hygiene auto-prune (2026-07-01)  ← Prior session-related work
- News ingest pipeline (2026-07-02)

Insert the new section **after** the existing "Session hygiene auto-prune" section (which described the policy creation on 2026-07-01) and **before** "News ingest pipeline":

```markdown
### Session database cleanup + prune schedule fix (2026-07-02 17:34–17:36)

**Sonnet-4-6 diagnosed session accumulation root causes and fixed infrastructure.**

- **Root causes identified**:
  - Prune scheduled for `0 3 * * *` (3am) but Hermes wasn't running at 3am → cron window missed, sessions accumulated all day with no mid-day cleanup
  - DB had no VACUUM step → 657 MB of dead space (1.1 GB DB, only 512 MB of real data)
  - Subagent sessions had no retention rule (grey zone between 2-day cron limit and 7-day global limit)

- **Fixes applied**:
  - **DB VACUUM**: `1169 MB → 512 MB` reclaimed (one-time cleanup)
  - **session-prune.sh enhanced**:
    - Added `--source subagent --older-than 3` pass to capture subagent sessions older than 3 days
    - Added conditional VACUUM: runs when DB > 300 MB to keep size under control
  - **Cron schedule changed**: `0 3 * * *` → `every 240m` (every 4 hours)
    - Rationale: Tolerates Hermes being idle at any one 4h window without a full day of buildup
    - Next run ~21:37 tonight

- **Verified outcome**: Current session count and DB behavior now healthy. Sessions will stay well-controlled going forward.

- **Caveats**: This is the nightly ops session (last in the 17:33-17:36 window); the session-prune improvements fix the accumulation risk but the main issue (3am window miss) is architectural and may recur if Hermes is stopped/restarted near schedule windows. Monitor next 48h.
```

### Step 2: Update "Key Durable Themes" section

Add a new bullet to reflect the infrastructure resilience improvements:

```markdown
- **Session DB infrastructure now resilient**: DB VACUUM removes dead space (1.1GB → 512MB today), schedule change (3am → every 4h) eliminates missed-window risk, subagent sessions now covered by retention policy. Cron schedule change is backward-compatible; no service restart needed.
```

### Step 3: Update "Follow-Ups" section

Add new follow-up items related to the session-prune work:

```markdown
- Monitor session-prune with new 4h schedule: check that cron runs are actually firing every 4h (not missing windows like 3am did)
- Monitor DB vacuum effectiveness: if DB grows back to 1GB in next 2 weeks, increase VACUUM threshold or frequency
```

### Step 4: Update frontmatter and visible timestamp

```diff
- last_synced: 2026-07-02 18:10 AEST
+ last_synced: 2026-07-02 19:11 AEST
```

And separately:

```diff
- _Last synced: 2026-07-02 18:10 AEST._
+ _Last synced: 2026-07-02 19:11 AEST._
```

### Step 5: Update daily note

Replace the existing `## Hermes Chat Sync` block with new bullets that include the DB work:

```diff
- - [[Hermes Chat Live Sync]] — timestamp refreshed to 18:10 AEST
- - Nightly ops swarm completed: cron health all-pass, no new durable changes since 16:08 sync
+ - [[Hermes Chat Live Sync]] — synced 19:11 AEST
+ - Session DB cleanup: VACUUM completed (1.1GB → 512MB). Session-prune script enhanced + cron schedule fixed (3am → every 4h).
- Kanban swarm pattern spiked and documented as skill; idempotency key dedup working
- agentmemory evaluation completed; verdict: keep Hindsight, no action needed
```

### Step 6: Verify readback

After all edits, read both files to confirm:

**Live-sync note readback (lines 1–15)**:
```
---
title: Hermes Chat Live Sync
date: 2026-07-02
status: active
last_synced: 2026-07-02 19:11 AEST          ← Updated
scope: curated durable Hermes changes...
---

# Hermes Chat Live Sync

_Last synced: 2026-07-02 19:11 AEST._       ← Updated
```

**Live-sync note readback (session sections)**:
```
### Session hygiene + auto-prune implementation (2026-07-01...)
...Going forward: ...

### Session database cleanup + prune schedule fix (2026-07-02 17:34–17:36)  ← NEW

**Sonnet-4-6 diagnosed session accumulation root causes...
...Monitor next 48h.

### News ingest pipeline expansion...                    ← Existing section preserved
```

**Live-sync note readback (Key Durable Themes)**:
```
- **Session auto-pruning solves accumulation**: ...
- **Session DB infrastructure now resilient**: DB VACUUM removes dead space...
  ← NEW bullet added
- **Config export and sanitization now reusable**: ...
```

**Daily note readback**:
```
---
title: July 2, 2026
date: 2026-07-02
---

## Hermes Chat Sync

- [[Hermes Chat Live Sync]] — synced 19:11 AEST        ← Updated
- Session DB cleanup: VACUUM completed (1.1GB → 512MB)...  ← NEW bullet
- Kanban swarm pattern spiked...
- agentmemory evaluation completed...
```

✓ **Both notes updated correctly. Timestamps aligned. New content integrated.**

## Result

**Full-rewrite sync completed.**
- Live-sync note: Added new session section (infrastructure fixes), updated Key Durable Themes + Follow-Ups, refreshed both timestamps
- Daily note: Patched sync block in place, preserved other content, updated timestamp reference
- New durable items: DB vacuum, session-prune enhancements, cron schedule change — all captured
- Existing curated state: Preserved (config audit, Cowork port, routing optimization, news pipeline all stable)

**Return**: "Synced 19:11 AEST. New durable items: session DB cleanup (VACUUM 1.1GB→512MB), session-prune script enhanced, cron schedule changed (3am→every 4h). Content rewritten."

---

## Key learnings from this example

1. **Same-day iterative syncs are normal**: When an earlier sync completed on the same day, a new cron run may find genuinely new durable work. Do not assume "no new sessions" means "no new items" — read the sessions to distinguish signal from noise.

2. **Session clustering matters**: The 17:33–17:36 window contained 5 sessions, but only the 17:34 session was *new durable work*. The others (17:33, 16:11, 14:07, 14:27) were already known from the 18:10 sync. Filter correctly before deciding to rewrite.

3. **Full rewrite is not "brute rewrite"**: You preserve existing sections, add new ones cleanly, and update related sections (Themes, Follow-Ups) that reference the new work. Do not replace the entire note.

4. **Patch the daily note in place**: Extract the existing `## Hermes Chat Sync` block and replace only that section. Leave the rest of the daily note untouched.

5. **Update timestamps in both places**: When doing a full rewrite, update both frontmatter AND visible body timestamp. Verify they match after the patch.

6. **Verify section insertion**: When adding a new session section, insert it in chronological order (by session date) relative to existing sections. This maintains readability and prevents temporal drift.

7. **Capture caveats, not just wins**: The session-prune fix works, but there's an architectural risk (3am window miss) that may recur. Capture that caveat alongside the solution — it affects future monitoring strategy.

8. **Same-day efficiency**: A full rewrite after 1 hour of new infrastructure work is justified. Do not mistake "recent" for "new" — use the decision tree to gate the effort.

