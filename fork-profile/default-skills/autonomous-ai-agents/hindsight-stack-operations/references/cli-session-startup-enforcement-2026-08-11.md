# CLI Session Startup Enforcement — 2026-08-11

## Context
Daemon was down since ~2026-08-08 (3 days). Lock file was stale zero-byte.
No port 9177 listener. daemon.log tail was hours old from the prior active session.
Goal: ensure hindsight starts at every new CLI session and auto-recovers if broken.

## What was tried / what worked

### Gateway hooks (session:start) — DOES NOT cover CLI
`hermes hooks list` showed no hooks configured. Docs confirm: gateway hooks fire only
for gateway sessions (Telegram/Discord/Slack/WhatsApp). CLI sessions (`hermes chat`) do
not emit `session:start`. Shell hooks require `hooks:` config block + per-command consent.

### AGENTS.md startup rule — CORRECT MECHANISM FOR CLI
The agent reads AGENTS.md at the start of every session (it's injected as project context).
Adding a mandatory startup section with explicit steps = the agent checks/fixes hindsight
before doing anything else. No hook infrastructure needed.

### Embedding keys: config.json vs hermes.env
- `~/.hermes/hindsight/config.json` had the HINDSIGHT_API_EMBEDDINGS_* keys already (from a prior session)
- `~/.hindsight/profiles/hermes.env` was missing them (4 keys only)
- Root cause: `_build_embedded_profile_env()` in plugin/__init__.py regenerates hermes.env
  from a hardcoded whitelist — EMBEDDINGS keys are not in it, even if present in config.json
- Attempted to append to hermes.env via execute_code — succeeded, but plugin overwrote on restart
- Confirmed config.json has the keys; daemon used them via a different code path (not hermes.env)
  when the daemon was already running from a prior session that had them in memory

### Recovery sequence that actually worked (2026-08-11)
1. `pkill -f 'hindsight-api' 2>/dev/null` — clear zombie
2. `rm -f ~/.hindsight/profiles/hermes.lock` — remove stale lock
3. Called `hindsight_recall(query="hindsight daemon startup")` — plugin detected dead daemon,
   started fresh process, embedding config loaded from config.json
4. Verified: `curl -sf http://127.0.0.1:9177/health` → `{"status":"healthy","database":"connected"}`
5. `hindsight_recall` returned 51 results — fully operational

## Key architectural facts confirmed

- Daemon starts LAZILY on first hindsight tool call in a Hermes session
- Plugin checks lock file on start; stale lock = daemon not started (bug: lock not cleaned on crash)
- `_build_embedded_profile_env()` whitelist does not forward HINDSIGHT_API_EMBEDDINGS_* keys
- BUT: config.json is the durable config; if daemon was last started with correct env, embedding
  config may survive across sessions via the running process (not via hermes.env at restart)
- Do NOT manually invoke `hindsight-api` binary from inside a Hermes session — let the plugin do it

## Files modified this session
- `~/AGENTS.md` — added "Session startup (mandatory)" section with step-by-step
- `~/.hermes/scripts/hindsight-ensure.sh` — diagnostic script for non-session callers (cron etc.)
- `~/.hermes/hindsight/config.json` — embedding keys already present, not changed
- `~/.hindsight/profiles/hermes.env` — attempted to add EMBEDDINGS keys (plugin overwrote on restart;
  keys are in config.json which is the canonical source)
