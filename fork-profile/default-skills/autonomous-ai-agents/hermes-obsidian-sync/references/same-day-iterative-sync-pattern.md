# Same-Day Iterative Sync Pattern

**When:** A cron sync run completes (timestamp-refresh only, no new durable items). Within the same day, new durable work occurs (config changes, feature integrations, verified deployments), triggering another sync run before the next calendar day.

**Scenario:** The 2026-07-02 sync illustrates this:
1. **10:20 AM cron sync**: Live-sync note refreshed to 10:19 AEST. Daily note created with "no new changes" block.
2. **10:24–11:20 AM user session**: News API research + integration work completes. GNews, HN Algolia, yfinance successfully integrated into `news_feed_ingest.py`. Reference docs created. Pipeline metrics verified (165 articles/22+ source-groups).
3. **11:21 AM cron sync** (this run): Detected new durable items in session history. Partial rewrite needed.

**Decision tree adjustments for same-day chaining:**

| Prior sync state | New session signal | Action |
|---|---|---|
| Timestamp-only refresh (no new items) | None within same day | Leave as-is; next sync adds timestamp if still current |
| Timestamp-only refresh (no new items) | New durable work detected before EOD | Partial rewrite: add new session section + timestamp refresh |
| Timestamp-only refresh (no new items) | User requests immediate sync | Treat as explicit delegation; full rewrite if work is substantial |

**Implementation pattern:**

1. When checking for durable items on same day as prior refresh:
   - Read current live-sync note + daily note (continuity baseline).
   - Check session history for work *after* prior sync timestamp (not just "today").
   - Filter: exclude cron maintenance sessions and transient activity; keep verified integrations, config changes, deployments.
2. If new durable items found:
   - Add new "### Session Name (HH:MM–HH:MM)" section in Recent Sessions.
   - Update Follow-Ups if needed.
   - Refresh both frontmatter and body timestamps to current time.
   - Update daily note sync block to mention the new item (3–5 bullets, no detail spill).
3. If nothing new:
   - Keep timestamp from prior run; do not refresh.
   - (Optional: return `[SILENT]` if caller accepts silent-delivery; otherwise report as timestamp-maintained).

**Pitfall: mistaking "multiple cron runs per day" for "session spam"**

Same-day chaining is normal and expected when:
- Morning cron sync (discovers yesterday's work)
- Afternoon user session (new integration/config work)
- Evening cron sync (discovers afternoon work)

This is not a sign of over-syncing; it is correct behavior when durable items genuinely appear between cron runs. The decision tree filters transient noise; multiple runs per day on meaningful changes are healthy.

**Pitfall: forgetting to update the daily note when rewriting the live-sync**

The daily note sync block is the user-facing visibility signal. If you rewrite the live-sync note due to new durable items discovered same-day, also patch the daily note's `## Hermes Chat Sync` section. Keep it thin (3–5 bullets) but mention the new item so the daily note does not show stale wording from the prior sync.

**Verification:**

After a same-day partial rewrite:
- Read back the live-sync note: new section present, timestamps aligned.
- Read back the daily note: sync block mentions the new work (not just timestamp).
- Confirm no contradictions between the two (live-sync should have detail; daily note should have thin bullets).
