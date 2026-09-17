# Config Audit Pitfalls Addendum (Aug 2026)

These pitfalls were discovered during the Aug 2026 live runtime audit and should be
incorporated into the main SKILL.md Pitfalls section at next edit opportunity.

## MCP args must be a YAML list, not a JSON string (CRITICAL)

The `mcp_servers.<name>.args` field in config.yaml must be a proper YAML list:
```yaml
mcp_servers:
  stealth-browser-mcp:
    args:
      - /path/to/server.py    # CORRECT
```
Not a JSON string:
```yaml
    args: '["/path/to/server.py"]'  # BROKEN
```

`mcp_config.py` line 240: `cmd_args = list(preset.get("args") or [])`.
`list()` on a string yields individual characters, not arguments.
A YAML-string-encoded JSON list PASSES yaml.safe_load() silently — the only way to
catch it is `type(server_cfg["args"])` at runtime.

**Audit step:** When reviewing config.yaml, grep for any `args:` field under
`mcp_servers` that is a quoted scalar rather than a YAML sequence. Every `args` value
must start with the next line indented with `- `.

**Confirmed Aug 2026:** stealth-browser-mcp.args was stored as a JSON string.
Server worked only because stealth-browser-mcp.sh hardcoded the correct args independently.

## Same-interval cron jobs cannot guarantee pipeline ordering (CRITICAL)

Two jobs that must run in sequence MUST NOT share the same interval value.
Their `next_run_at` offset equals only their creation-time offset (seconds).
Any scheduler restart, slow run, or manual trigger destroys this.

**Confirmed Aug 2026:** l1-extract and l1-promote both at `interval: 180m`,
only 3.942885s apart. If l1-extract takes > 4 seconds, promote fires during extract.

**Fix direction:** Give the downstream job a longer interval (e.g. extract=180m,
promote=210m) so the offset is structurally enforced. Or implement a lock file:
```bash
# l1-promote.py header check:
lockfile = Path("~/.hermes/.l1-extract-lock").expanduser()
if lockfile.exists():
    sys.exit(0)  # extract still running, skip this cycle
```

## Cron output dead-drop — no watcher reads cron/output/

`no_agent=True` script jobs write to `~/.hermes/cron/output/<job-id>/YYYY-MM-DD.md`.
Nothing reads that directory automatically.

`hermes-mutation-gate-watch.sh` watches `integrations/hermes-agent-self-evolution/output/`
— a completely different path. Any analysis job (drift audit, memory staleness, skill
quality scan) that produces findings will silently accumulate them unread.

**Audit step:** For every `no_agent=True` cron job, ask: "Is there a downstream consumer
of its output?" If not, either:
1. Add a downstream agent job that reads and acts on the output directory, OR
2. Route findings to a path that an existing watcher monitors, OR
3. Accept that the job is a manual-pull resource (document this explicitly)

## Script header / cron config mismatch

`l1-extract.py` header says `no_agent=False, every 30m`.
Live cron: `no_agent=True, every 180m`.

Scripts that assume agent context (tool calls, session access) but run as `no_agent=True`
will silently produce incomplete/wrong output. Script headers drift when config changes.

**Audit step:** For any cron-backing script, compare its header's claimed mode and
schedule against the actual cron job entry. The cron job is authoritative at runtime.
