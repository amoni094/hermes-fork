# Hindsight Daemon Recovery — Missing API Key

## Symptoms
- `hindsight_recall` / `hindsight_retain` return: `Failed to search memory: Failed to start daemon for profile 'hermes'`
- `~/.hermes/logs/hindsight-embed.log` shows: `ValueError: LLM API key is required. Set HINDSIGHT_API_LLM_API_KEY environment variable.`
- `~/.hindsight/profiles/hermes.log` shows the same ValueError on every attempt

## Root cause
The Hindsight embedded daemon reads `HINDSIGHT_LLM_API_KEY` from `~/.hermes/.env` and
writes it to `~/.hindsight/profiles/hermes.env` as `HINDSIGHT_API_LLM_API_KEY`.
The daemon process is started with that profile env — NOT with the parent process env.
Setting `llm_provider: anthropic` in `~/.hermes/hindsight/config.json` does NOT cause
it to fall back to `ANTHROPIC_API_KEY`. The dedicated key must be set explicitly.

## Permanent fix (survives restarts)

```bash
echo 'HINDSIGHT_LLM_API_KEY=<same value as ANTHROPIC_API_KEY>' >> ~/.hermes/.env
```

The plugin reads this on next session start and rebuilds the profile env automatically.

## Mid-session recovery (no Hermes restart needed)

Step 1 — patch `~/.hermes/.env` (permanent fix, as above).

Step 2 — patch the profile env directly so the current session can start the daemon:

```python
import pathlib

KEY = "<your anthropic api key>"
path = pathlib.Path('/var/home/rainbow/.hindsight/profiles/hermes.env')
lines = path.read_text().splitlines(keepends=True)
new_lines = [
    f'HINDSIGHT_API_LLM_API_KEY={KEY}\n'
    if l.startswith('HINDSIGHT_API_LLM_API_KEY=') else l
    for l in lines
]
path.write_text(''.join(new_lines))
print("done")
```

Step 3 — trigger the daemon (it will time out in the foreground but continues in background):

```python
from hindsight_embed.daemon_embed_manager import DaemonEmbedManager
mgr = DaemonEmbedManager()
profile_config = mgr._profile_manager.load_profile_config('hermes')
try:
    mgr.ensure_running(profile_config, 'hermes')
except Exception:
    pass  # timeout is expected; daemon still starts
```

Step 4 — wait ~30s, then verify:

```bash
ss -tlnp | grep 9177              # should show hindsight-api listening
tail -5 ~/.hindsight/profiles/hermes.log  # should end with: Application startup complete.
```

Step 5 — test recall (from this session's tool):
```
hindsight_recall(query="test")
```

## Diagnosing key presence

```python
import pathlib
path = pathlib.Path('/var/home/rainbow/.hindsight/profiles/hermes.env')
for line in path.read_text().splitlines():
    k, _, v = line.strip().partition('=')
    print(f'{k}={"[set]" if v.strip() else "[EMPTY]"}')
```

`HINDSIGHT_API_LLM_API_KEY=[EMPTY]` confirms the missing key.

## Key paths
- `~/.hermes/.env` — source of `HINDSIGHT_LLM_API_KEY`
- `~/.hermes/hindsight/config.json` — provider config (`llm_provider`, `llm_model`)
- `~/.hindsight/profiles/hermes.env` — runtime env written by plugin, read by daemon subprocess
- `~/.hermes/logs/hindsight-embed.log` — plugin-side log (daemon manager output)
- `~/.hindsight/profiles/hermes.log` — daemon-side log (uvicorn/API process output)
- Port 9177 — Hindsight embedded daemon HTTP port (profile: hermes)

## Key env var mapping
| What you set | Where | What the daemon sees |
|---|---|---|
| `HINDSIGHT_LLM_API_KEY` | `~/.hermes/.env` | → plugin reads and writes `HINDSIGHT_API_LLM_API_KEY` to profile env |
| `ANTHROPIC_API_KEY` | `~/.hermes/.env` | NOT forwarded to daemon — insufficient alone |
| `HINDSIGHT_API_LLM_API_KEY` | `~/.hindsight/profiles/hermes.env` | ✓ daemon reads directly |
