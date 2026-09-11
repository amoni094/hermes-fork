# hermes-fork

Private fork of [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent).

## What's different

### 1. Adaptive compression plugin API (`feature/adaptive-compression-plugin-api`)

Three small, additive changes that expose live compression tuning to plugins:

**`agent/context_compressor.py`** — `ContextCompressor.set_compression_profile(profile, **kwargs)`

Allows plugins to adjust compression behaviour between turns without restart.
Built-in profiles: `"research"`, `"code"`, `"mixed"`. Custom dicts accepted
(merge with live state; unspecified keys unchanged). Unknown names warn and
are ignored (fail-open). Values are clamped to safe ranges; `_source` is a
log label only.

```python
compressor.set_compression_profile("research", _source="my-plugin")
# or custom:
compressor.set_compression_profile({"threshold_percent": 0.45, "protect_last_n": 15})
```

Safe to call from `pre_llm_call` hooks. Each compression pass re-reads the
attributes from scratch; mid-pass mutation is not safe (hooks fire between turns,
so this is never an issue in practice).

**`hermes_cli/plugins.py`** — `PluginContext.compressor` property

Always re-reads `agent.context_compressor` (no cached instance). PluginManager
holds the agent via weakref so a finished session can be GC'd.

```python
def on_pre_llm_call(ctx, agent=None, **kw):
    c = ctx.compressor  # live ContextCompressor or None
    if c:
        c.set_compression_profile("research")
```

**`agent/turn_context.py`** — `agent` kwarg in `pre_llm_call` hook

The live agent object is now passed to all `pre_llm_call` handlers, enabling
plugins to inspect or modify agent state between turns without global singletons.
The kwarg is ephemeral (not persisted). Shell-hook / webhook JSON extra strips
`agent` / `parent_agent` so serialization cannot dump the live object.
Idle compaction does **not** invoke `pre_llm_call`.

**`agent/agent_init.py`** — `PluginManager._agent` binding

Wires the agent into the plugin manager after compressor construction so
`ctx.compressor` resolves without importing agent internals from plugin code.

### 2. `plugins/user/lambda-tuner` — session-type adaptive compression

A plugin that classifies each session as `research`, `code`, or `mixed` from
accumulated user messages and applies the matching compression profile live.

- Uses the new `set_compression_profile()` API when available (this fork)
- Falls back to hint-file-only on vanilla Hermes (N+1 lag)
- Accumulates messages across turns; greeting/ack turns are filtered
- Locks classification on first confident non-mixed result, **or** after 3 turns
  even if still mixed; re-applies the locked profile on later turns (compressor rebuild)
- Session state is LRU-capped (64 sessions, 32 messages each)
- Writes `$HERMES_HOME/cache/last-session-type.json` (default `~/.hermes/cache/...`)
  for the launch wrapper; skips the write when type+lambda is unchanged
- Fail-open: errors are debug-logged, never raised
- Registers at the front of the `pre_llm_call` list so the profile is set before
  other hooks in the same wave that might read compression state

#### Profile defaults

| Profile    | threshold_percent | proactive_prune_tokens | protect_last_n |
|------------|:-----------------:|:----------------------:|:--------------:|
| `research` | 0.45              | 40 000                 | 15             |
| `code`     | 0.55              | 28 000                 | 25             |
| `mixed`    | 0.50              | 32 000                 | 20             |

Lower `threshold_percent` = earlier full compression. research < mixed < code.
`proactive_prune_tokens` is a trigger *floor* (higher = later cheap prune).

### 3. `hermes-session` launch wrapper

On this system the wrapper lives at `~/.local/bin/hermes-session` (not
`/usr/local/bin`). It reads the hint file and patches `rr_scorer_lambda` at
launch for session warm-up before the plugin fires on turn 1.

```
hermes-session [research|code|mixed|auto] [hermes args...]
HERMES_SESSION_TYPE=code hermes-session [hermes args...]
hermes-session --session-type research [hermes args...]
```

Lambda table: research=0.55, code=0.2, mixed=0.4.

## Syncing upstream

```bash
git fetch origin
git rebase origin/main
# resolve any conflicts, then force-push the feature branch.
# Prefer --force-with-lease over --force so a rewritten remote is not clobbered.
git push fork feature/adaptive-compression-plugin-api --force-with-lease
```

## Base

Forked from `45a6101f3` (v2026.9.7, 2026-09-11).
