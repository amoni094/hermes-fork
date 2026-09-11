# hermes-fork

Private fork of [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent).

## What's different

### 1. Adaptive compression plugin API (`feature/adaptive-compression-plugin-api`)

Three small, additive changes that expose live compression tuning to plugins:

**`agent/context_compressor.py`** — `ContextCompressor.set_compression_profile(profile, **kwargs)`

Allows plugins to adjust compression behaviour between turns without restart.
Built-in profiles: `"research"`, `"code"`, `"mixed"`, `"entropy-adaptive"`. Custom dicts accepted
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

A plugin that classifies each session as `research`, `code`, `mixed`, or
`entropy-adaptive` from accumulated user messages and applies the matching
compression profile live.

- Uses the new `set_compression_profile()` API when available (this fork)
- Falls back to hint-file-only on vanilla Hermes (N+1 lag)
- Accumulates messages across turns; greeting/ack turns are filtered
- Locks classification on first confident non-mixed result, **or** after 3 turns
  even if still mixed; re-applies the locked profile on later turns (compressor rebuild)
- Session state is LRU-capped (64 sessions, 32 messages each)
- Writes `$HERMES_HOME/cache/last-session-type.json` (default `~/.hermes/cache/...`)
  for the launch wrapper; skips the write when type+lambda is unchanged
- Fail-open: errors are debug-logged, never raised
- Hooks: `pre_llm_call` (classify + live profile + hint intent), `on_session_start`
  (apply hint `intent` → `compressor.current_intent`), `pre_compress` (re-apply
  before a full compression pass), `on_session_end` (drop LRU/`_fired`)
- Registers at the front of the `pre_llm_call` list so the profile is set before
  other hooks in the same wave that might read compression state

#### Profile defaults

| Profile    | threshold_percent | proactive_prune_tokens | protect_last_n |
|------------|:-----------------:|:----------------------:|:--------------:|
| `research` | 0.45              | 40 000                 | 15             |
| `code`     | 0.55              | 28 000                 | 25             |
| `mixed`    | 0.50              | 32 000                 | 20             |
| `entropy-adaptive` | R(D) from message entropy (placeholder 0.50) | 32 000 | 20 |

Lower `threshold_percent` = earlier full compression. research < mixed < code.
`proactive_prune_tokens` is a trigger *floor* (higher = later cheap prune).
`entropy-adaptive` is not a fixed percent — Shannon R(D) proxy; fail-open to mixed.

### 3. `hermes-session` launch wrapper

On this system the wrapper lives at `~/.local/bin/hermes-session` (not
`/usr/local/bin`). It reads the hint file and patches `rr_scorer_lambda` at
launch for session warm-up before the plugin fires on turn 1.

```
hermes-session [research|code|mixed|auto] [hermes args...]
HERMES_SESSION_TYPE=code hermes-session [hermes args...]
hermes-session --session-type research [hermes args...]
```

Lambda table: research=0.55, code=0.2, mixed=0.4, entropy-adaptive=0.4.

New flags:

```
hermes-session --entropy-adaptive [hermes args...]
hermes-session --intent 'implement feature X' research
hermes-session --no-hint          # skip hint file; start mixed
hermes-session --dry-run          # print profile+lambda; do not exec
```

`--entropy-adaptive` sets `HERMES_SESSION_TYPE=entropy-adaptive` and writes
`profile: entropy-adaptive` into the hint file. `--intent` adds an `intent`
string to the hint JSON so lambda-tuner can set `compressor.current_intent`.
Missing `expires_at` in the hint is treated as expired (`hint.get('expires_at', 0)`).

## Predicates

`plugins/user/lambda-tuner/predicates.py` exposes boolean helpers other plugins
can import to gate behavior without re-implementing the classifier. They read
the in-process `_fired` dict:

```
{session_id: {"type": str, "confidence": float, "ts": float}}
```

```python
# Import from the loaded plugin package (directory slug is lambda-tuner).
from hermes_plugins.<slug>.predicates import (
    is_research_session,
    is_code_session,
    is_high_confidence,
    session_type,
)
```

Also re-exported from `plugins/user/lambda-tuner/__init__.py`. All predicates
fail-open (unknown session → `False` / `None`).

## Intent instrumentation (future: intent-conditioned compression)

`ContextCompressor.current_intent` is an optional string describing what the
user is trying to do this session (e.g. `"implement feature X"`). When set,
intent-conditioned offload / RR scoring can keep spans that match the intent
and demote unrelated tool results more aggressively.

How it gets set:

1. `hermes-session --intent '...'` writes `"intent"` into
   `$HERMES_HOME/cache/last-session-type.json`.
2. lambda-tuner reads the hint on `on_session_start` / first `pre_llm_call`
   and, if the value is a non-empty string and the agent is available, sets
   `agent.context_compressor.current_intent` (fail-open).
3. Classifier rewrites of the hint preserve an existing `intent` field so the
   wrapper-provided string is not lost after lock-in.

Empty or missing `intent` is ignored. The attribute is set even if the
compressor has not declared it yet (Domain A); consumers should `getattr`.

**Task Complexity Scoring**

> Known limitation: `DEFAULT_SCORER.update_recent()` accumulates a single 2000-token vocabulary across all sessions in a long-running gateway process. Novelty scores for session N reflect session N-1's vocabulary. This is intentional for single-session CLI use but may bias novelty in persistent gateways. Mitigation: instantiate a per-session `TaskComplexityScorer()` if isolation is required.

lambda-tuner scores accumulated user text (length, code density, ambiguity, constraints, multistep, tool hints, questions, novelty) after classification lock.
High complexity (>0.7) raises `protect_last_n` by 5 (cap 40); low complexity (<0.3) lowers `proactive_prune_tokens` by 8000 (floor 8000).
`session_complexity(sid)` reads the locked score from `_fired`.

## Multi-agent diversity (pre_agent_exchange hook)

`invoke_hook_for_exchange` fires `pre_agent_exchange` with `agent_results`, `parent_session_id`, and `exchange_round` so plugins can diversify Best-of-N samples before parent aggregation (arXiv:2608.11065); hooks may mutate the list in place and the helper fail-opens.
`PluginContext.filter_duplicate_results` keeps the first of each near-duplicate cluster using `difflib.SequenceMatcher` (default key `content`, threshold 0.85).
Callers that skip the hook still get the original `agent_results` unchanged.

## Tool result compaction (MDL)

`ToolResultCompactor` in lambda-tuner applies a head+tail MDL cut to oversized tool payloads, inserting an omitted-char marker instead of shipping the full dump.
`PluginContext.compact_tool_result` lazily imports the compactor and only runs it when `predicates.session_type(session_id) == 'research'`.
`DEFAULT_COMPACTOR` is the shared instance exported from `plugins/user/lambda-tuner/complexity.py`.

**AEP Floor (informational)**

The AEP information floor (`should_compress_info` gating) is gated on `_turn_clock > protect_last_n` to avoid inflated estimates early in sessions. In practice once gated, `floor ≈ protect_last_n × 64 ≈ 1280 tokens`, which is well below the compress threshold (~40K+). The floor is therefore a no-op in normal operation. It provides a hard safety valve only for very small context windows (<2K tokens) where threshold-based compression might otherwise destroy all information. This is intentional — the entropy-adaptive *profile* (dynamic threshold) is the primary theory-grounded mechanism; the AEP floor is a belt-and-suspenders guard.

**Entropy-adaptive profile**

Use `--entropy-adaptive` (or `HERMES_SESSION_TYPE=entropy-adaptive`) when
session type is not known up front and compression should follow message
entropy rather than a research/code prior:

- Wrapper warm-up lambda is `0.4` (same as mixed) so launch is safe.
- Hint `type`/`profile` is `entropy-adaptive` for Domain A's named profile.
- Do **not** use it for a session that is already clearly code or research —
  those named profiles protect causal chains (code) or dump stale web results
  (research) more predictably.
- The classifier may still lock research/code/mixed after enough user turns;
  entropy-adaptive is a launch prior, not a lock that overrides classify.

## Compression scheduling (entropy-delta gate)

If Shannon entropy rate has not moved by 0.15 bits/token since the last successful compression and more than 3 ChronoMem turns have elapsed, `should_compress_info` skips with reason `low_entropy_delta` (another pass will not help).
`_last_compress_entropy` / `_last_compress_clock` update only after a successful `compress()` and reset in `bind_session_state` (`/new`).
A never-compressed clock (`_last_compress_clock == 0`) does not skip the first compression.

## RR scoring (Kolmogorov proxy)

`MessageImportanceScorer.compressibility` is a zlib ratio (lower = more compressible = less unique). `ContextCompressor.rr_score` is `0.6 * importance + 0.4 * compressibility` and is the eviction key in `importance_biased_prune`.
`_pre_compress_checkpoint` logs `avg_rr_score` over the last 20 messages.

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
