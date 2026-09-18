---
name: hermes-reasoning-layer-engineering
description: "Use when extending Hermes reasoning effort or verbosity."
tags: [hermes, reasoning, fork, plugin, adaptive]
related_skills: [hermes-fork, hermes-lambda-tuner, adaptive-agent-reasoning]
---

# Hermes Reasoning Layer Engineering

Engineering reference for adding adaptive reasoning effort, verbosity control, and
multi-plugin arbitration to Hermes Agent (fork or plugin). Covers the wire injection
point, safe override mechanism, conflict resolution, and verbosity mixin.

For the research-level reasoning depth allocation protocol, see `adaptive-agent-reasoning`.
For fork-specific compression profiles, see `hermes-fork`.

## Reasoning config structure

`agent.reasoning_config` is a dict: `{"enabled": True, "effort": "medium"}`.
All transports consume this dict; never change the dict shape.

Effort ladder (low->high):
  EFFORT_LADDER = ("none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra")

`ultra` is Hermes-internal (Codex product tier); no wire accepts it. Provider-specific
vocabularies are narrower -- always go through `clamp_effort()` in `agent/reasoning_effort.py`.

## Key files -- do not add plugin logic to agent/ modules

  agent/reasoning_effort.py        EFFORT_LADDER, clamp_effort(), provider wire vocabularies
  agent/reasoning_params.py        ReasoningParamsMixin, provider capability probes
  agent/reasoning_summaries.py     Iteration-limit summary reasoning config
  agent/reasoning_timeouts.py      Timeout handling for thinking/reasoning phases
  agent/chat_completion_helpers.py _reasoning_config_for_wire() -- THE injection point
  agent/conversation_loop.py       Post-turn cleanup wire point (verbosity only; 3-5 lines max)

Direction constraint: agent/ must stay plugin-free. No imports of hermes_cli into agent/.
All plugin logic lives in hermes_cli/ or plugins/. Plugins write _adaptive_effort_override;
agent/ code only reads it.

## Injection point: _reasoning_config_for_wire()

`_reasoning_config_for_wire(agent)` in `agent/chat_completion_helpers.py` is called by
`_build_api_kwargs_for_mode()` immediately before every transport call. It reads
`agent.reasoning_config`, applies the one-shot ephemeral-off override, and returns
the final dict.

This is the ONLY correct injection point for per-turn effort overrides. Do not:
- Mutate `agent.reasoning_config` directly from plugins (breaks session-level config)
- Write effort overrides in the transport files (they run after this point)
- Use `agent.request_overrides` (different path, not reasoning-config aware)

## Safe per-turn override mechanism: _adaptive_effort_override

Set `agent._adaptive_effort_override = effort_str` from a plugin's `pre_llm_call` hook.
`_reasoning_config_for_wire` reads it, merges with `{**(cfg or {}), "effort": clamped}`,
then clears it to None (one-shot -- safe on retries).

Floor rule: override NEVER goes below the user's configured effort. Configured effort is a
floor, not a ceiling. If user configured `effort=high`, adaptive `low` clamps to `high`.

Safety gates -- skip the override when any of these are true:
- `cfg.get("enabled") is False`
- `cfg.get("effort") == "none"`
- `getattr(agent, "_reasoning_disable_rejected", False)` is set

Always wrap override application in try/except -- fall back to configured effort silently.

Call timing: `pre_llm_call` fires inside `_collect_pre_llm_call_context()` which is
called at turn_context.py:960 BEFORE `build_api_kwargs()` calls `_reasoning_config_for_wire`.
So setting `_adaptive_effort_override` in `pre_llm_call` always lands before the wire call.

## Plugin API surface (hermes_cli/plugins.py)

Add to PluginContext:

  set_adaptive_effort(effort, confidence=1.0, priority=0)
    Validates effort in EFFORT_LADDER (minus ultra).
    Registers with _reasoning_resolver (not direct assignment).

  get_adaptive_effort() -> Optional[str]
    Returns last resolved effort or None.

  set_verbosity_mode(mode: str)
    Validates mode in ('full', 'compact', 'suppress').
    Calls agent.set_reasoning_verbosity(mode) if available.

  reset_reasoning_state()
    Clears _reasoning_resolver for next turn.
    Called before pre_llm_call hooks run (at START of dispatch loop, not end).

## Conflict resolver (hermes_cli/reasoning_resolver.py)

When multiple plugins call set_adaptive_effort(), last-write-wins is wrong.
Use a priority + confidence model:

  add_recommendation(plugin_name, effort, confidence, priority=0)
    confidence: 0.0-1.0; priority: higher = more authoritative

  resolve(configured_floor: str) -> str
    1. Filter out confidence < 0.5
    2. Sort by (priority DESC, confidence DESC, effort_index DESC)
    3. Winner = first result, clamped to configured_floor
    4. Tie at same priority+confidence: take highest effort (conservative)

Priority conventions:
  lambda-tuner (primary classifier):    priority=10
  set_reasoning_mode() bridged calls:   priority=5, confidence=0.7
  other plugins (default):              priority=0

Bridge set_reasoning_mode() to effort via:
  _MODE_TO_EFFORT = {'fast': 'low', 'default': 'medium', 'deep': 'high'}
  When set_reasoning_mode(mode) is called, also:
    self.set_adaptive_effort(_MODE_TO_EFFORT[mode], confidence=0.7, priority=5)

This means mode hints contribute but are overridden by direct effort calls (priority=10).

## Verbosity mixin (agent/reasoning_verbosity.py)

Three modes for thinking block handling:
  full     (default): keep all thinking, no stripping
  compact: strip <think>/<thinking> blocks from historical assistant messages
           after turns where effort was low or medium (saves context window)
  suppress: skip thinking prefill (agent._suppress_thinking_prefill = True)
            for trivial turns where effort is none/low

API: set_reasoning_verbosity(mode), get_reasoning_verbosity() -> str, _should_compact_thinking() -> bool
Store in agent._reasoning_verbosity_mode; default 'full'.

NEVER strip the current streaming turn -- only completed historical turns.
NEVER strip if effort was high/xhigh/max -- those turns need thinking for quality continuity.
Reset _reasoning_verbosity_mode to 'full' in bind_session_state (/new boundary).

Wire into conversation_loop.py post-turn (3-5 lines max, wrapped in try/except):

  try:
      if getattr(agent, '_should_compact_thinking', lambda: False)():
          from agent.reasoning_verbosity import compact_thinking_history
          compact_thinking_history(agent)
  except Exception:
      pass

## Complexity -> effort mapping (lambda-tuner)

Score from TaskComplexityScorer (0.0-1.0, 8-signal mean):

  Score      Base effort  Research bias  Code bias
  < 0.25     low          medium         low
  0.25-0.50  medium       high           medium
  0.50-0.75  high         xhigh          high
  > 0.75     xhigh        xhigh          xhigh
  greeter    low (always) --             --

Research sessions: bias UP one level (low->medium, medium->high, high->xhigh, xhigh stays).
Code sessions: no bias. Mixed: no bias.

EMA smoothing: 3-turn rolling buffer of complexity scores. Map from EMA not raw score
to prevent thrash. Greeter override (hey, hi, ok, sure, thanks, continue, go ahead)
always maps to low regardless of EMA -- never EMA-smooth over greetings.

## Audit: tracing what effort reaches the wire

  _reasoning_config_for_wire()             reads cfg + _adaptive_effort_override
    -> transport _reasoning_config_for_model()  clamps to provider-specific set
      -> clamp_effort()                     provider wire vocabulary enforcement

## Test coverage required

For any effort override change, test:
  - Override below configured floor is clamped to floor
  - Override above floor applies correctly
  - Override skipped when enabled=False
  - Override cleared to None after wire read (retry safety)
  - No override -> cfg unchanged
  - Conflict resolver: highest priority wins; tie -> highest effort; low confidence filtered
  - Verbosity: compact strips low/medium effort turns; skips high/xhigh/max
  - Verbosity: idempotent (compact_thinking_history called twice is safe)
  - Session reset: all override state cleared in bind_session_state

## Pitfalls

- Idle compaction does NOT invoke pre_llm_call. Override set in compaction-adjacent
  code would never fire. Only the main inference call invokes the hook.
- The _adaptive_effort_override one-shot clear means retries get plain configured effort.
  This is correct: retries may be on different content and state.
- Verbosity compact on high-effort turns silently degrades future quality: high-effort
  thinking chains are the evidence the next turn's reasoning draws on. Never strip them.
- _reasoning_disable_rejected is set when a provider rejected a disable request; the agent
  is in mandatory-reasoning mode. Adaptive overrides must check this gate or the provider
  will silently strip or 400.
- set_reasoning_mode() bridge adds to the resolver at priority=5. If you also call
  set_adaptive_effort() directly

## AIMD for LLM Concurrency (Cross-Reference)

When running multiple parallel reasoning calls (e.g., fan-out to subagents for adversarial review), use AIMD concurrency control to avoid throttling:

```python
from aimd_controller import get_controller

# Per reasoning stage — independent controller per (provider, node)
ctrl = get_controller(provider="anthropic", node="llm_checks")
with ctrl.control():
    result = heavy_reasoning_call(prompt)
```

Default budget for reasoning checks: `llm_checks=2` concurrent slots.
For high-priority reasoning (main orchestrator): use `node="compiler"` (budget=4).

See `~/.hermes/scripts/aimd_controller.py` and `agent-runtime-loop-patterns` § AIMD section.
  set_adaptive_effort() directly at priority=10 in the same hook, the direct call correctly
  overrides. Do not call both and expect the mode-bridge call to win.
- Do NOT add reasoning_config mutations to agent/reasoning_effort.py or agent/reasoning_params.py
  -- those files are transport-facing constants/probes. Plugin logic belongs in hermes_cli/.
