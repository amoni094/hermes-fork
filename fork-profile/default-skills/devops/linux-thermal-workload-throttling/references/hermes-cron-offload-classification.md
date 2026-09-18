# Hermes Cron Offload Classification (Sep 2026)

When evaluating Hermes cron jobs for offload to native systemd timers, apply this three-tier classification:

## Tier 1: Offloadable (safe to move to systemd timers)

Criteria: ALL of these must be true:
- `no_agent: true` in the cron job definition
- Script only does I/O checks (port probe, curl, pgrep, rfkill, pid kill) — no LLM calls
- Does not read or write `~/.hermes/state.db`
- Does not invoke the `hermes` binary
- Idempotent and stateless (running twice is safe)

Examples moved off Hermes cron — Sep 2026:
- `firecrawl-watchdog` (job 064999e8aff3): curl firecrawl:8000/health every 10m, auto-restart podman container
- `hindsight-watchdog` (job 6197789459d7): TCP port 9177 + HTTP health check every 5m
- `browser-orphan-watchdog` (job b9e48a4c500a): pgrep + kill stale Chrome/Node processes every 30m

## Tier 2: Must stay in Hermes (LLM or CLI dependency)

Criteria: ANY of these is true:
- Invokes an LLM (uses `hermes` binary, calls API, reads `state.db`)
- Needs hermes skill context or memory
- Writes to Hindsight, Graphiti, or skill library
- Uses `hermes sessions prune` or any hermes CLI subcommand
- Reads/writes `state.db` (SQLite lock risk if moved to root context)

Examples that stay:
- `hermes-chat-sync` — LLM synthesis
- `l1-extract` / `l1-promote` — state.db reads
- `session-auto-prune` — `hermes sessions prune` CLI; SQLite locking risk in root context
- `hermes-platform-watchdog` — config/API health checks using hermes binary
- All memory/GC jobs — LLM or state.db dependent

## Tier 3: No split of session-auto-prune

Specific rule: do NOT split session-auto-prune into two halves (LLM-free GC + LLM prune).
Rationale: the LLM-free parts (SQLite VACUUM, WAL checkpoint) are tiny (~2 lines) and the
risk of running them from root system-cleanup.sh while hermes holds a SQLite write lock
outweighs the token savings. Keep the whole job in Hermes user context.

## Systemd user unit placement

Offloaded jobs use user-context systemd timers, NOT system timers:
- Service files: `~/.config/systemd/user/<name>.service`
- Timer files: `~/.config/systemd/user/<name>.timer`
- Scripts: `~/.hermes/scripts/<name>.sh` or `~/.hermes/scripts/<name>.py`

This keeps them scoped to the user, avoids sudo requirements, and lets them access
user-space resources (podman, hermes venv, port 9177) without privilege escalation.

## Pausing the replaced Hermes cron job

After creating the systemd timer replacement, pause (do not delete) the Hermes cron job:
```python
cronjob_manage(action='pause', job_id='<id>')
```
Reason: pausing is reversible; deleting is not. If the systemd timer has a bug,
you can un-pause the original while diagnosing. Delete only after 7+ days of clean timer operation.

## Anti-duplication check

Before creating a systemd timer for a watchdog:
1. `ls /etc/systemd/system/ | grep <topic>` — check for existing system-level unit
2. `ls ~/.config/systemd/user/ | grep <topic>` — check for existing user-level unit
3. `hermes cron list | grep <topic>` — confirm the Hermes job you intend to replace

If a system-level service already handles the watchdog (e.g. `hermes-platform-watchdog`
for API/config health), do NOT create a duplicate user-level timer for the same concern.
