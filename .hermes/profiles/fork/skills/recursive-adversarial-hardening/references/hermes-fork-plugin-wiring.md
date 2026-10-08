# Hermes Fork Plugin Wiring: Common Pitfalls

Wiring failures discovered in the recursive audit protocol. Each item is a concrete
root cause with the correct fix pattern.

## Path Resolution

### `_hermes_root()` — strip profile suffix before resolving shared scripts

When a fork plugin resolves scripts in `~/.hermes/scripts/` (not fork-profile scripts),
it MUST strip the profile suffix from `HERMES_HOME`:

    def _hermes_root() -> Path:
        h = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
        # When running inside a fork profile, HERMES_HOME is already the profile root.
        # Strip profiles/<name> to get the true hermes root.
        parts = h.parts
        if len(parts) >= 2 and parts[-2] == "profiles":
            h = Path(*parts[:-2])
        return h

Use for: `jev_verify_fn.py`, `hermes-agent` binary, `memory-doob-decompose.py`,
any shared script that lives in `~/.hermes/` (not `profiles/fork/`).

Symptom when missing: plugin silently resolves to `profiles/fork/scripts/jev_verify_fn.py`
(non-existent) instead of `~/.hermes/scripts/jev_verify_fn.py`; cold audits surface this
as a WIRE finding (script path unresolvable).

## Configuration Reading

### `ctx.get_config()` not `getattr(ctx, 'config', {})`

PluginContext does NOT expose a `.config` attribute dict; `getattr(ctx, 'config', {})`
always returns `{}`. Always use the per-key API:

    value = ctx.get_config("plugins.entries.my-plugin.settings.my_key", default_value)

For each setting, issue a separate `get_config` call. The key path is:
`plugins.entries.<plugin-name>.settings.<setting-name>`.

Legacy fallback chain pattern:

    value = (
        ctx.get_config("plugins.entries.my-plugin.settings.my_key")
        or ctx.get_config("plugins.my_plugin.my_key")
        or DEFAULT_VALUE
    )

## Queue / State File Robustness

### Non-list JSON guard on queue reads

Any script that reads a queue JSON file and appends to it must guard against
non-list content (corruption, truncated write, wrong initial write):

    try:
        existing = json.loads(queue_path.read_text())
        if not isinstance(existing, list):
            existing = []
    except (json.JSONDecodeError, FileNotFoundError):
        existing = []

Without this guard, `existing + [new_item]` raises TypeError on dict/string content,
causing the job to abort without queuing.

### Atomic queue rewrite (always rewrite, never conditional append)

When cleaning stale items from a queue, always rewrite the entire queue in one
operation: filter old entries first, then append new if needed, then write once.
Conditional append logic ("write only if new item") leaves stale entries indefinitely.

    items = [x for x in existing if not is_stale(x)]
    if needs_new_item:
        items.append(new_item)
    queue_path.write_text(json.dumps(items))

## Architecture Documentation

### ARCHITECTURE.md as live truth for cold auditors

Cold audit subagents treat ARCHITECTURE.md as ground truth. A stale line like
`shadow_jev_evaluator: false` or `(NOT in plugins.enabled)` or `67 cron jobs` will
generate false HIGH findings in the next audit wave (WIRE-070 class).

Update ARCHITECTURE.md **in the same commit** as any:
- Plugin enabled/disabled via CLI
- Proposal state change (pending → approved → deployed)
- Cron job count change
- Shadow flag promotion
- GAP closed

Never leave a gap open in ARCHITECTURE.md when its fix was already deployed.

## H-I7 Compliance

Every plugin hook body must be wrapped in try/except, returning None on exception.
This applies to `pre_tool_call`, `post_tool_call`, `pre_llm_call`, `post_llm_call`.

    def pre_tool_call(self, ctx):
        try:
            # ... real logic ...
            return result
        except Exception:
            return None

A hook that raises will surface as an unhandled exception in the Hermes runtime
and will halt the session. The try/except is not optional even for "impossible" paths.
