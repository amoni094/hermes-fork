# hermes-fork

Private fork of [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent).

## What's different

### 1. Adaptive compression plugin API (`feature/adaptive-compression-plugin-api`)

Three small, additive changes that expose live compression tuning to plugins:

**`agent/context_compressor.py`** — `ContextCompressor.set_compression_profile(profile)`

Allows plugins to adjust compression behaviour between turns without restart.
Built-in profiles: `"research"`, `"code"`, `"mixed"`. Custom dicts accepted.

```python
compressor.set_compression_profile("research", _source="my-plugin")
# or custom:
compressor.set_compression_profile({"threshold_percent": 0.45, "protect_last_n": 15})
```

Safe to call from `pre_llm_call` hooks. Each compression pass re-reads the
attributes from scratch; mid-pass mutation is not safe (hooks fire between turns,
so this is never an issue in practice).

**`hermes_cli/plugins.py`** — `PluginContext.compressor` property

```python
def on_pre_llm_call(ctx, agent=None, **kw):
    c = ctx.compressor  # live ContextCompressor or None
    if c:
        c.set_compression_profile("research")
```

**`agent/turn_context.py`** — `agent` kwarg in `pre_llm_call` hook

The live agent object is now passed to all `pre_llm_call` handlers, enabling
plugins to inspect or modify agent state between turns without global singletons.

**`agent/agent_init.py`** — `PluginManager._agent` binding

Wires the agent into the plugin manager after compressor construction so
`ctx.compressor` resolves without importing agent internals from plugin code.

### 2. `plugins/user/lambda-tuner` — session-type adaptive compression

A plugin that classifies each session as `research`, `code`, or `mixed` from
accumulated user messages and applies the matching compression profile live.

- Uses the new `set_compression_profile()` API when available (this fork)
- Falls back to hint-file-only on vanilla Hermes (N+1 lag)
- Accumulates messages across turns; greeting/ack turns are filtered
- Locks classification on first confident non-mixed result
- Writes `~/.hermes/cache/last-session-type.json` for the launch wrapper
- Fail-open: errors are debug-logged, never raised

#### Profile defaults

| Profile    | threshold_percent | proactive_prune_tokens | protect_last_n |
|------------|:-----------------:|:----------------------:|:--------------:|
| `research` | 0.45              | 40 000                 | 15             |
| `code`     | 0.55              | 28 000                 | 25             |
| `mixed`    | 0.50              | 32 000                 | 20             |

### 3. `hermes-session` launch wrapper

`/usr/local/bin/hermes-session` (or `~/.local/bin/hermes-session`) reads the
hint file and patches `rr_scorer_lambda` at launch for session warm-up before
the plugin fires on turn 1. Supports `--session-type research|code|mixed` and
`HERMES_SESSION_TYPE` env override.

## Syncing upstream

```bash
git fetch origin
git rebase origin/main
# resolve any conflicts, then force-push feature branch
git push fork feature/adaptive-compression-plugin-api --force-with-lease
```

## Base

Forked from `45a6101f3` (v2026.9.7, 2026-09-11).
