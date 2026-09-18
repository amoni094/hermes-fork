# Cron Job Session Hygiene Pattern

Use this when documenting Hermes cron jobs that run repeatedly and leave session/history artifacts, and you need to report both the job's function AND its housekeeping/retention policy.

## Context

Repeated cron jobs (e.g., hourly sync, daily briefings) accumulate session records in the Hermes SQLite store. Without a retention policy, these sessions grow indefinitely and make session browsing and querying slower over time. The pattern here separates job **execution** (what it does) from its **hygiene footprint** (how much history it leaves behind).

## Session lifecycle example: hourly-hermes-chat-sync

**Job frequency**: Every hour  
**Retention policy**: Cron sessions kept for 2 days (48 sessions max); automatic cleanup via daily prune script

**Pattern components**:

1. **Primary cron job** (`hourly-hermes-chat-sync`):
   - Runs every hour
   - Executes the sync logic
   - Leaves a session record in the store each run

2. **Hygiene script** (`~/.hermes/scripts/session-prune.sh`):
   - Two-tier retention:
     - Cron sessions >2 days old → delete (keeps recent job history for debugging)
     - All sessions >7 days old → delete (user sessions cap at 1 week)
   - Idempotent: safe to run repeatedly
   - Can be invoked manually or via a separate cron job

3. **Hygiene cron job** (`session-auto-prune`):
   - Runs daily (e.g., at 3am)
   - Invokes the prune script
   - Keeps session store lean without manual intervention

## Reporting in sync notes

When a cron job's hygiene implementation is durable/notable, record:
- **Job name**: What it does, how often
- **Current retention policy**: Max session age, any two-tier thresholds
- **Implementation**: Script path, cleanup job name/schedule
- **Verification**: How you confirmed it works (ad-hoc test, cron log check, schema check)
- **Benefit**: Storage footprint, query speed impact, debugging value preserved

Example:

```
### Session hygiene + auto-prune implementation

- **Problem**: Cron job accumulating indefinitely; 863 old sessions pruned
- **Solution**:
  - `sessions.retention_days`: 90 → 7 in config.yaml
  - `~/.hermes/scripts/session-prune.sh`: two-tier prune (cron 2d, all 7d)
  - Cron job `session-auto-prune` (ID `1ea1d2459f51`): runs daily at 3am
  - Verification: 5-check ad-hoc test passed
- **Result**: Cron history capped at ~48 sessions, user sessions at 7d. Store stays lean.
```

## When to record this pattern in sync notes

Include this when:
- A cron job's hygiene policy is newly established or changed
- A pruning/cleanup action was taken (delete old sessions, consolidate logs, etc.)
- The retention policy differs from the Hermes default
- The cleanup logic is non-obvious (two-tier policy, special exemptions, etc.)

Do NOT include if:
- The cron job runs once and cleans up after itself (no session accumulation)
- Retention is the Hermes default and unchanged
- The cleanup is internal to the job and not visible to future syncs

## Design notes

**Why two-tier retention?**
- Keep 2 days of cron job sessions for debugging recent runs (e.g., "did the 3am sync fail?")
- But cap all sessions at 7 days so old user sessions don't linger indefinitely
- Balances operational debugging value against storage footprint

**Why a separate hygiene job?**
- Keeps the primary job's logic focused (sync the content, not cleanup)
- Cleanup runs on its own schedule (can be adjusted without touching the primary job)
- Allows manual execution of the cleanup script if a one-off prune is needed

**Verify the policy is working**:
- Check `hermes sessions list` — should not grow unbounded
- Check `hermes cron history session-auto-prune` — verify the cleanup script is running  <!-- why: 'hermes cron log' is not a valid subcommand; 'history' is the correct command -->
- Spot-check old sessions are gone: `hermes sessions stats` shows store size over time
