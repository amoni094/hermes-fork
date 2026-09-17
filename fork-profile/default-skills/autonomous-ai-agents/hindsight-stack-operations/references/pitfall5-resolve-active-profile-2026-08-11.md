# Pitfall 5: resolve_active_profile() returns empty string (2026-08-11)

## What happened

Called `hindsight_recall` from a Hermes turn. Tool returned:
```
{"error": "Failed to search memory: Failed to start daemon for profile 'hermes'"}
```

Investigated via Python:
```python
from hindsight_embed.daemon_client import resolve_active_profile, ensure_daemon_running
profile = resolve_active_profile()
print(repr(profile))  # → ''
ensure_daemon_running(config=profile, profile=profile)
# TypeError: 'str' object is not a mapping
# Starting daemon for profile: ''
```

## Root cause

`resolve_active_profile()` reads a Hermes-set env var. When Hermes is running but the
daemon is not yet started (cold session), or when called from a subagent/cron without
the parent env, the function returns `''` (empty string), not `None`. The caller
`ensure_daemon_running(config, profile)` receives `config=''` and tries to do
`{**profile_config, **config}` — crash because `''` is not a mapping.

## Fix

Pass profile explicitly, never via `resolve_active_profile()`:
```python
from hindsight_embed.daemon_client import ensure_daemon_running, is_daemon_running

profile = "hermes"   # must match profile name in ~/.hermes/config.yaml memory.bank
config = {
    "llm_api_key": "<value of HINDSIGHT_LLM_API_KEY in ~/.hermes/.env>",
    "llm_provider": "anthropic",
    "llm_model": "claude-haiku-4-5",
}
if not is_daemon_running(profile):
    ensure_daemon_running(config=config, profile=profile)
```

## Additional finding: HindsightEmbedded() hangs in foreground turns

Calling `HindsightEmbedded(profile="hermes")` as a context manager in a Hermes turn
(not background) timed out at 180s. The constructor starts the daemon synchronously,
which involves multiple API round-trips. **Do not call in a foreground Hermes turn.**

Use the REST API when daemon is already known-running:
```bash
curl -s -X POST http://127.0.0.1:9177/v1/default/banks/hermes/memories/recall \
  -H "Content-Type: application/json" \
  -d '{"query": "your query", "top_k": 10}'
```

## Fallback: session DB SQLite

When Hindsight is unavailable, the session DB is the reliable fallback for link/URL recovery.
See session-db-url-recall pattern in hermes-session-hygiene references.

Key query pattern:
```python
import sqlite3, re, json, datetime

db = sqlite3.connect('/var/home/rainbow/.hermes/state.db')

# Get sessions after a timestamp
cutoff_ts = datetime.datetime(2026, 8, 10, 2, 33, 0).timestamp()   # adjust for AEST offset
sessions = db.execute(
    'SELECT id, title, started_at FROM sessions WHERE started_at >= ? AND archived = 0',
    (cutoff_ts,)
).fetchall()

url_re = re.compile(r'https?://[^\s\'"<>\]\)]+')
all_urls = {}

for sid, title, ts in sessions:
    msgs = db.execute(
        'SELECT content FROM messages WHERE session_id = ? AND active = 1', (sid,)
    ).fetchall()
    for (content,) in msgs:
        text = content or ''
        if text.startswith('['):
            try:
                parts = json.loads(text)
                text = ' '.join(p.get('text','') if isinstance(p,dict) else str(p) for p in parts)
            except: pass
        for url in url_re.findall(text):
            url = url.rstrip('.,;:\'")')
            if url not in all_urls:
                all_urls[url] = title or sid[:20]
```

Note: `timestamps in state.db are Unix epoch floats in UTC`. Convert AEST to UTC by subtracting
10 hours (UTC+10 → UTC = -10h = -36000 seconds).
