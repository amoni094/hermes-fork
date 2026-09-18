# Single-Item Rewrite: Focused Fix (Worked Example)

This reference captures a **full-rewrite** sync that detected exactly one new durable item after an earlier same-day sync. Use this when the decision tree shows new content but the work is narrow and focused (e.g., one service fix, one config change, one script patch).

## Scenario

**Date**: July 4, 2026, 18:24 AEST  
**Prior sync**: 14:22 AEST same day (4 hours earlier)  
**Live-sync note state**: Current, accurate, frontmatter timestamp 2026-07-04 14:22 AEST, body timestamp 14:22 AEST  
**Daily note state**: Exists, contains `## Hermes Chat Sync` block with 5 durable clusters noted  
**Recent sessions**: 3 sessions in last 4 hours (17:40–18:03):
  - Session 18:03 UTC (6:04 PM): Web research on git forges (Codeberg, SourceHut, Radicle) — exploratory, no action items
  - Session 17:49 UTC (5:49 PM): **Hermes gateway + Graphiti MCP startup race condition fix** — real operational issue identified and fixed
  - Session 17:40 UTC (5:41 PM): Pharma AI deployment consultation — research/planning, no implementation
**Hint files**: Not checked (session search was sufficient)  
**New durable items**: YES — exactly one: systemd service ordering fix for hermes-gateway.service

## Decision tree walk-through

```
1. Read the current live-sync note and daily note first.
   ✓ Live-sync note: present, frontmatter 2026-07-04 14:22 AEST (4 hours old)
   ✓ Daily note: present, contains sync block with 5 clusters
   Both are continuity baselines; proceed.

2. Check timestamps.
   ✓ Live-sync note timestamp is recent but not current (4 hours old; OK for cron)
   ✓ Daily note is current (same day)
   Proceed to session inspection.

3. Read 3 most recent sessions.
   ✓ Session 18:03: Web research (Codeberg/SourceHut/Radicle) — exploratory, no action or config changes
      - Outcome quote: \"None of the three require immediate action or config changes\"
      - Durable: No
   ✓ Session 17:49: **Gateway/Graphiti startup race condition** — real issue found and fixed
      - Durable: YES — systemd service dependency added (After= and Wants= directives)
      - Fix location: /var/home/rainbow/.config/systemd/user/hermes-gateway.service
      - Impact: Guarantees Graphiti MCP is ready before gateway starts
   ✓ Session 17:40: Pharma deployment architecture — consultation/research, no code/config changes
      - Durable: No

4. Decide.
   Current note state:  \"Current + accurate\"
   New durable items:   \"YES — one focused item (systemd service fix)\"
   Action from matrix:  \"Rewrite live-sync note + patch daily note\"
```

## Execution

### Step 1: Add new session section

Insert a new section at the end of the \"Recent Sessions\" group (after document-layout-design skill work):

```markdown
### Hermes gateway + Graphiti MCP startup race condition fix (2026-07-04 17:49–17:51)

**Crash investigation by Sonnet-4-6; race condition found and fixed.**

- **What appeared to be crashes**: Two events clarified as normal/expected operations:
  - Exit 75 at 00:17 UTC — `EX_TEMPFAIL`, Hermes's own restart-after-update mechanism, not a crash
  - Gateway exit on SIGTERM — systemd shutdown, clean termination, not a crash
- **Real operational issue found**: hermes-gateway service was starting before graphiti-mcp.service was ready, causing the gateway to retry 3 times and give up. Graphiti would come up on its own but remain unavailable to the gateway until manual restart.
- **Fix applied to `/var/home/rainbow/.config/systemd/user/hermes-gateway.service`**:
  - Added `graphiti-mcp.service` to `After=` and `Wants=` directives (lines 3–4)
  - Now systemd enforces Graphiti startup before gateway attempts connection
  - Daemon reloaded; fix takes effect on next login
- **Outcome**: Graphiti MCP now available on every startup. No more silent unavailability window.
```

### Step 2: Add one bullet to \"Key Durable Themes\"

```markdown
- **Graphiti MCP availability is now guaranteed**: Gateway/MCP startup race condition eliminated via explicit systemd ordering. No more silent startup failures.
```

### Step 3: Add one follow-up item

Under \"Follow-Ups\":

```markdown
- **Monitor Graphiti MCP availability**: Verify next login that Graphiti comes up without manual restart and gateway connects successfully on first attempt
```

### Step 4: Update frontmatter and visible timestamps

Frontmatter:
```diff
- last_synced: 2026-07-04 14:22 AEST
+ last_synced: 2026-07-04 18:24 AEST
```

Body timestamp:
```diff
- _Last synced: 2026-07-04 14:22 AEST._
+ _Last synced: 2026-07-04 18:24 AEST._
```

### Step 5: Update daily note

Replace the sync block:

```diff
- - [[Hermes Chat Live Sync]] — synced 10:00 AEST (5 durable clusters from 2026-07-03 to 2026-07-04)
+ - [[Hermes Chat Live Sync]] — synced 18:24 AEST (6 durable clusters from 2026-07-03 to 2026-07-04)
  - **Fable-5 Pass 5 audit**: obsidian-weekly-review cron fixed...
  - **Medical-research-analysis v1.3.0**: 14 CRITICAL+HIGH patches...
  - **Messaging consent skill**: verified, no action needed
  - **Architecture documentation**: hermes-config and hermes-to-cowork-port READMEs...
  - **Document-layout-design skill v1.0**: created with recursive adversarial review...
+ - **Graphiti MCP startup fix**: hermes-gateway.service now depends on graphiti-mcp.service via systemd ordering; eliminates startup race condition...
```

### Step 6: Verify readback

**Live-sync frontmatter**:
```
last_synced: 2026-07-04 18:24 AEST      ← Refreshed ✓
```

**Live-sync body**:
```
_Last synced: 2026-07-04 18:24 AEST._   ← Refreshed ✓
```

**Live-sync new section**:
```
### Hermes gateway + Graphiti MCP startup race condition fix (2026-07-04 17:49–17:51)

**Crash investigation by Sonnet-4-6; race condition found and fixed.**

- **What appeared to be crashes**: ...
...
- **Outcome**: Graphiti MCP now available on every startup. No more silent unavailability window.
```

✓ **Section present and complete.**

**Live-sync Key Durable Themes**:
```
- **Graphiti MCP availability is now guaranteed**: Gateway/MCP startup race condition...
```

✓ **Bullet added.**

**Daily note**:
```
- [[Hermes Chat Live Sync]] — synced 18:24 AEST (6 durable clusters from 2026-07-03 to 2026-07-04)
  - **Fable-5 Pass 5 audit**: obsidian-weekly-review cron fixed...
  - ...
  - **Graphiti MCP startup fix**: hermes-gateway.service now depends on graphiti-mcp.service...
```

✓ **Cluster count incremented from 5 to 6. New bullet present. Timestamp updated.**

## Result

**Full-rewrite sync completed.**
- Live-sync note: Added one new session section (Graphiti MCP startup fix), added one bullet to Themes, added one follow-up, refreshed both timestamps
- Daily note: Patched sync block in place, updated cluster count and sync timestamp, added single new bullet
- New durable item: Systemd service ordering fix — captured with impact statement (\"no more silent unavailability\")
- Existing curated state: All 5 prior clusters preserved unchanged

**Return**: \"Synced 18:24 AEST. New durable item: hermes-gateway.service now depends on graphiti-mcp.service via systemd ordering; eliminates startup race condition. Content rewritten.\"

---

## Key learnings from this example

1. **Single-item rewrites are valid**: Not every rewrite has multiple items. One real fix is enough to justify a full rewrite (vs. timestamp-only refresh). The decision tree gates this correctly.

2. **Minimal invasiveness**: When only one item is new, the rewrite touches only:
   - One new section in \"Recent Sessions\"
   - One new bullet in \"Key Durable Themes\"
   - One new follow-up item
   - Both timestamps (frontmatter + body)
   - Daily note: cluster count increment + one new bullet
   
   This is surgical. Not all content rewrites are large.

3. **Avoid conflating \"recent\" and \"durable\"**: Sessions 18:03 and 17:40 were recent (within last 4h) but produced zero durable items. Session 17:49 was the only one worth capturing. This is why the decision tree requires you to read sessions, not just count them.

4. **Fix impact matters more than lines changed**: The Graphiti startup fix is 2 directives added to one systemd file, but the impact is \"no more silent unavailability on every login.\" Capture the impact statement alongside the fix.

5. **Verify section insertion**: The new Graphiti section was inserted *after* document-layout-design (the prior session work) to maintain chronological order. Do not append at the end if earlier sections are out of order.

6. **Daily-note granularity**: The new bullet was a single concise line in the daily note, not a paragraph. The daily note stays thin and skimmable, even when adding new items.

7. **Follow-up is a promise**: The new follow-up (\"Monitor Graphiti MCP availability next login\") is something that will be checked in the next session or manual verification. Capture it so it does not disappear.

8. **Same-day 4-hour gap is common**: Cron runs every 4 hours are standard. A gap between 14:22 and 18:24 is normal. Do not assume \"old timestamp\" means \"stale note\" — check the actual content state.
