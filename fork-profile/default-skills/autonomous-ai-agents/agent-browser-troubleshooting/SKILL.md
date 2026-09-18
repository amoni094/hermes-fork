---
description: 'Use when: user reports browser is stuck, zombie, or agent-browser session desyncs from OS. Diagnose and fix
  stuck, orphaned, or zombie agent-browser headless Chrome processes.'
name: agent-browser-troubleshooting
provides: [browser_interact]
triggers:
  - User reports browser is stuck, frozen, or not responding during agent automation
  - A headless Chrome or Chromium process is zombie or orphaned from a previous agent session
  - browser_navigate or browser_snapshot hangs or returns stale content
related_skills:
  - computer-use
  - wayland-session-management
  - browser-agent-ops
---


# Agent-Browser Troubleshooting

## What this actually is

The Hermes browser tool (`browser_navigate`, `browser_click`, etc.) is backed by
`npx agent-browser`, which launches sandboxed (`bwrap`) headless Chrome sessions
under `/tmp/agent-browser-chrome-<uuid>` user-data-dirs. Each session is a small
process tree: main chrome -> zygote -> gpu-process -> network/storage utility ->
renderer(s). A single "hung session" can be 10+ OS processes.

When a user says "the browser is a zombie" they almost never mean a literal
Linux Z-state (defunct) process — check for that but expect zero. What they
mean is: the agent-browser daemon has lost track of a session (often because
it, or the wrapping terminal, was killed abruptly) while the underlying Chrome
process tree is still alive and consuming resources. `agent-browser session
list` can report "No active sessions" while dozens of real Chrome processes
sit there running. **Don't trust the daemon's session list as the source of
truth for whether processes are actually gone — always cross-check with `ps`.**

## Diagnosis

```bash
# Full picture: agent-browser chrome trees, bwrap sandboxes, unrelated lookalikes
ps -eo pid,ppid,stat,etime,cmd | grep -iE 'chrom|agent-browser|bwrap' | grep -v grep

# Literal zombies (rare, but check)
ps -eo pid,ppid,stat,cmd | awk '$3 ~ /Z/'

# What the daemon *thinks* is running (may lie after an abrupt external kill)
npx agent-browser session list

# Isolate just the orphaned session trees by their tmp profile dir naming
ps -eo pid,args | grep -oE 'agent-browser-chrome-[a-f0-9-]+' | sort -u
```

Do NOT assume every `chrom*` hit is agent-browser's fault. Common lookalikes
to rule out before touching anything:
- `chrome-headless-shell` under `/usr/local/share/playwright/...` — usually a
  separate service (e.g. a Firecrawl `playwright-service` container via
  conmon/podman). Different lifecycle, don't kill it as collateral.
- A real Flatpak Firefox/Chromium the user has open interactively (`bwrap ...
  -- firefox <url>` or `org.chromium.Chromium`) — that's their actual browser
  session, not a tool artifact.

Only the `agent-browser-chrome-<uuid>` user-data-dir naming convention marks a
process tree as belonging to the browser tool.

## Fix

```bash
# Graceful first — matches the whole tree via the user-data-dir substring
pkill -TERM -f 'agent-browser-chrome-'
sleep 3

# Escalate only on survivors
ps -eo pid,args | grep 'agent-browser-chrome-' | grep -v grep | wc -l
pkill -KILL -f 'agent-browser-chrome-'

# Clean up leftover empty tmp profile dirs (processes already gone)
rm -rf /tmp/agent-browser-chrome-*/
```

## Verification (don't skip this)

```bash
ps -eo pid,args | grep 'agent-browser-chrome-' | grep -v grep | wc -l   # expect 0
npx agent-browser session list                                          # "No active sessions"
ps -eo pid,ppid,stat,cmd | awk '$3 ~ /Z/'                               # expect empty
```

Report the actual before/after process counts to the user — "killed 122
orphaned processes across 10 stale sessions" is a real finding; "should be
fixed now" is not.

## Pitfalls

- `pkill -f 'agent-browser-chrome-'` returns exit code -15 (SIGTERM) for the
  *calling* pkill invocation in some shells — that's expected, not a failure.
  Re-run the ps count afterward to confirm.
- Don't kill by bare `chrome` or `chromium` pattern — too broad, catches the
  user's real browser and unrelated containerized services (Firecrawl
  playwright, etc.).
- Session state files/socket dirs under `/tmp/agent-browser-*` can also go
  stale; if cleanup doesn't fully resolve repeated recurrences, check
  `~/.hermes/hermes-agent/tools/browser_tool.py` and `browser_supervisor.py`
  for the socket-dir and idle-timeout logic (`AGENT_BROWSER_SOCKET_DIR`,
  `AGENT_BROWSER_IDLE_TIMEOUT_MS`).
- This is an operational cleanup pattern, not evidence the browser tool is
  broken — don't record "browser tool is unreliable" anywhere; record the fix.
- Same-control thrash / multi-field form burn / extract re-injection is NOT
  a zombie process problem — use `browser-agent-ops` (loop guard + multi-act).

## browser_navigate times out cold (Silverblue / Wayland / Flatpak environments)

**Symptom:** `browser_navigate` always returns "Command timed out after 120 seconds / The browser
daemon may still be starting, or Chromium may be missing system libraries." — even though
agent-browser and Playwright Chromium are installed and the daemon starts fine manually.

**Root cause (confirmed July 2026):** `hermes_subprocess_env(inherit_credentials=False)` strips
ALL env vars not on its explicit allowlist before passing them to the agent-browser subprocess.
This means `AGENT_BROWSER_EXECUTABLE_PATH` and `AGENT_BROWSER_ARGS` set in `.env` or the process
environment are silently dropped. The daemon can't find Chromium and hangs indefinitely.

On Fedora Silverblue (Flatpak Chromium), the additional issue is `_needs_chromium_sandbox_bypass()`
returning False (no root, no Docker, no AppArmor file at `/proc/sys/kernel/apparmor_restrict_unprivileged_userns`),
so `--no-sandbox` is never auto-injected. The Flatpak bwrap sandbox requires it explicitly.

**Diagnosis:**
```bash
# Confirm the daemon starts manually with explicit env
AGENT_BROWSER_EXECUTABLE_PATH=~/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome \
  AGENT_BROWSER_ARGS="--no-sandbox,--disable-setuid-sandbox,--disable-dev-shm-usage" \
  timeout 20 npx agent-browser open "https://example.com" 2>&1
# Should print: ✓ Example Domain — if this works, root cause is env stripping

# Confirm what Playwright Chromium path is available
ls ~/.cache/ms-playwright/chromium-*/chrome-linux64/chrome 2>/dev/null
```

**Fix (two steps):**

Step 1 — Set both keys in `config.yaml` via Python (patch tool and `hermes config set`
both reject these as unknown keys; direct Python write works):
```python
import yaml
path = '/var/home/rainbow/.hermes/config.yaml'
with open(path) as f:
    cfg = yaml.safe_load(f)
cfg.setdefault('browser', {})['executable_path'] = \
    '/var/home/rainbow/.cache/ms-playwright/chromium-1223/chrome-linux64/chrome'
cfg['browser']['args'] = '--no-sandbox,--disable-setuid-sandbox,--disable-dev-shm-usage'
with open(path, 'w') as f:
    yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True)
```

Step 2 — Patch `browser_tool.py` to re-inject these from config after the env strip.
Add the block below immediately after `browser_env = _build_browser_env()` and before
`browser_env["PATH"] = ...` (search for "AGENT_BROWSER_SOCKET_DIR" to find the insertion point):
```python
        # Inject browser.executable_path and browser.args from config.yaml into
        # the subprocess env (they are stripped by hermes_subprocess_env, so we
        # re-add them here if the user configured them).
        from hermes_cli.config import read_raw_config as _read_raw_config
        _bcfg = (_read_raw_config() or {}).get("browser", {})
        _exec_path = _bcfg.get("executable_path", "").strip() if isinstance(_bcfg, dict) else ""
        if _exec_path and "AGENT_BROWSER_EXECUTABLE_PATH" not in browser_env:
            browser_env["AGENT_BROWSER_EXECUTABLE_PATH"] = _exec_path
        _browser_args = _bcfg.get("args", "").strip() if isinstance(_bcfg, dict) else ""
        if _browser_args and "AGENT_BROWSER_ARGS" not in browser_env:
            browser_env["AGENT_BROWSER_ARGS"] = _browser_args
```

Note: there are TWO `_build_browser_env()` call sites in `browser_tool.py` — ideally patch both
(search for `browser_env = _build_browser_env()` to find them, they're at line ~1050 and ~2380).
In practice, the ~2380 site covers standard browser_navigate usage. The ~1050 site covers
Camofox/cloud routing — if browser tools still misbehave after patching ~2380, check ~1050 too.

**Verify:**
```bash
# After the patch, confirm config reads correctly
python3 -c "
import sys; sys.path.insert(0, '/var/home/rainbow/.hermes/hermes-agent')
from hermes_cli.config import read_raw_config
cfg = read_raw_config() or {}; b = cfg.get('browser', {})
print('executable_path:', b.get('executable_path'))
print('args:', b.get('args'))
"
# Then test browser_navigate in a new session (the fix requires restart — module caching)
```

**Platform context:**
- Playwright Chromium lives at `~/.cache/ms-playwright/chromium-<build>/chrome-linux64/chrome`
- Flatpak Chromium at `~/.local/bin/chromium` is a bwrap wrapper — it launches `open` but
  hangs indefinitely because the bwrap sandbox inside the Hermes terminal session doesn't have
  the right display context. Use Playwright Chromium (headless, no Wayland dependency) instead.
- The agent-browser daemon listens on `127.0.0.1:<port>` (visible via `ss -tlnp`). Subsequent
  `npx agent-browser` commands connect to the existing daemon — they don't relaunch Chrome.
- `hermes computer-use doctor` correctly reports cua-driver health but does NOT diagnose
  agent-browser env-stripping — they are separate subsystems.

## If this recurs frequently

Consider a lightweight watchdog: periodic `pgrep -f agent-browser-chrome- |
wc -l` with an alert threshold, run via cron, rather than manually diagnosing
each time. Only add this if the user asks for it — a one-off cleanup does not
need a standing cron job.

## Building the watchdog, once asked for

Don't re-implement the pkill logic above in the watchdog script. Hermes
already ships a tested orphan reaper —
`tools/browser_tool.py::_reap_orphaned_browser_sessions()`, covered by
`tests/tools/test_browser_orphan_reaper.py` — that stays in sync with
whatever socket-dir/idle-timeout rules the tool itself uses to define
"orphaned." Call that function from the watchdog instead of hand-rolling
process matching a second time:

```bash
#!/usr/bin/env bash
# ~/.hermes/scripts/browser_orphan_watchdog.sh
cd /var/home/rainbow/.hermes/hermes-agent || exit 1
./venv/bin/python3 -c "
import sys, os
sys.path.insert(0, os.getcwd())
from tools.browser_tool import _reap_orphaned_browser_sessions
result = _reap_orphaned_browser_sessions()
if result:
    print(result)
"
```

Register it as a script-only cron job (no LLM tokens, silent when clean):

```
cronjob(action='create', name='browser-orphan-watchdog',
        schedule='every 30m', no_agent=True,
        script='browser_orphan_watchdog.sh', deliver='local')
```

Key points:
- `no_agent=True` + a script that prints nothing on a clean run means the
  watchdog is truly silent day-to-day — it only produces output (and only
  then triggers a delivery) when it actually reaps something. Don't make the
  script chatty ("no orphans found") or every tick becomes a notification.
- Relative `script=` paths resolve under `~/.hermes/scripts/`; write the
  script there directly rather than passing an absolute path if you want it
  to follow the profile.
- This is local-only delivery unless the user wants alerts pushed to a
  connected messaging platform (`deliver='telegram'`/`'all'`) — a CLI-only
  profile will never see watchdog output surface back into the terminal
  session that created it.
- Test the reaper import/call once by hand before trusting the cron
  schedule — confirms the function signature and that it runs clean (0
  orphans, no exception) in the actual venv the cron job will use.
