# Hermes Compression & Runtime Config — Full Reference (Aug 2026)

> **LIVE OVERRIDE 2026-08-30:** Live knobs are `threshold: 0.35` and `threshold_tokens: 120000`.
> The values 0.50 / 80000 below are from an earlier config snapshot and are stale. Do not copy them.
> Do not change `compression.*` settings mid-session.

> **LIVE OVERRIDE 2026-08-29:** do not copy the Cerebras `zai-glm-4.7` examples
> below into config. `auxiliary.compression` is now `claude-haiku-4-5` / anthropic
> (moved off `mistral-small-latest` 2026-08-29 — Mistral 422 on `reasoning` caused
> compression-loop stalls; `reasoning_effort` must stay unset if ever moved back).
> Other mechanical aux/leaves may still be `mistral-small-latest` / mistral. glm is
> archived (404). Canonical: `claude-routing-hierarchy`.

Discovered 2026-08-08 via `hermes config get compression` on a live v0.20 install.
The config.yaml only shows keys you've explicitly set; defaults are much richer.

## Compression keys (all under `compression:`)

```yaml
compression:
  # TRIGGER
  enabled: true
  threshold: 0.50              # Compress at 50% context fill. Default 0.50; 0.40 is too aggressive.
  threshold_tokens: 80000      # NEW v0.20: absolute cap (fires at lower of ratio vs absolute).
                               # Prevents misfiring when switching models. MISSING from many configs.
  target_ratio: 0.20           # Preserve 20% of threshold as tail. 200K×0.50×0.20 = 20K tail.
  protect_last_n: 15           # Keep last N messages uncompressed. Default 20; 15 works for CLI.
  protect_first_n: 3           # Pin first 3 non-system messages (opening goal). Default 3.
  min_tail_user_messages: 3    # Minimum user messages to preserve in tail. Default 1; 3 is safer.

  # MICRO-COMPACTION (v0.20 feature)
  micro_compact: true          # Per-turn amortised compaction. Prevents single large compress pause.
  micro_compact_every_n_turns: 3   # How often to run micro-compact. 3 is a good default.
  micro_compact_defrag_threshold_tokens: 2000  # Only defrag if gain > 2K tokens. Default.

  # PROACTIVE PRUNE (no LLM needed, fast)
  proactive_prune_tokens: 48000        # Prune old tool results when history > 48K. MISSING from many configs.
                                        # Strongly recommended for 200K models — prevents old terminal
                                        # dumps being re-sent every turn. Default 0 = disabled.
  proactive_prune_min_result_chars: 8000    # Only prune results larger than 8K chars.
  proactive_prune_min_reclaim_tokens: 4096  # Don't commit prune unless it saves 4K+ (prevents cache breaks).

  # SESSION RESUME
  idle_compact_after_seconds: 1800  # NEW v0.20: compact on resume after 30min idle.

  # MISC BEHAVIOR
  in_place: true               # Keep same session ID across compactions. v0.20 default.
  progress_notices: false      # Keep false for CLI; set true for gateway visibility.
  abort_on_summary_failure: false  # false = degrade gracefully; true = fail loud on compressor error.

  # TIMEOUTS (defaults usually fine)
  hygiene_timeout_seconds: 30
  hygiene_total_ceiling_seconds: 600
  hygiene_failure_cooldown_seconds: 300
  context_timeout_seconds: 120
  context_total_ceiling_seconds: 600
  hygiene_hard_message_limit: 5000  # Gateway death-spiral guard.
```

## Auxiliary task slots (all under `auxiliary:`)

Most configs only set `auxiliary.compression`. All other tasks default to `auto` → main model
(Anthropic claude-sonnet), which is expensive for cheap tasks.

```yaml
auxiliary:
  compression:
    provider: cerebras
    model: zai-glm-4.7
    base_url: https://api.cerebras.ai/v1
    reasoning_effort: "low"    # v0.20: disable extended thinking for summaries. SAVES COST.
    max_concurrency: 2
    fallback_chain:
      - provider: sambanova
        model: DeepSeek-V3.2
        base_url: https://api.sambanova.ai/v1
      - provider: mistral
        model: mistral-large-latest
        base_url: https://api.mistral.ai/v1

  vision:                      # Image analysis — route to cheaper vision model
    provider: anthropic
    model: claude-haiku-4-5
    reasoning_effort: "none"
    timeout: 120

  web_extract:                 # Web content summarisation — fast cheap model fine
    provider: cerebras
    model: zai-glm-4.7
    base_url: https://api.cerebras.ai/v1
    reasoning_effort: "none"
    timeout: 360
    fallback_chain:
      - provider: sambanova
        model: DeepSeek-V3.2
        base_url: https://api.sambanova.ai/v1

  title_generation:            # Session auto-titling — trivial task
    provider: cerebras
    model: zai-glm-4.7
    base_url: https://api.cerebras.ai/v1
    max_concurrency: 2

  curator:                     # Skill lifecycle review (v0.18+)
    provider: cerebras
    model: zai-glm-4.7
    base_url: https://api.cerebras.ai/v1
    reasoning_effort: "low"

  triage_specifier:            # Intent classification — fast model fine
    provider: cerebras
    model: zai-glm-4.7
    base_url: https://api.cerebras.ai/v1
```

**Constraint:** Compression model context window must >= main model context window.
glm-4.7 should be verified for 200K support. If summaries fail silently, switch compressor.

## Agent loop keys (under `agent:`)

```yaml
agent:
  max_turns: 500               # v0.20 raised default 90→500. Running 150 is artificially low.
  gateway_timeout: 1800
  tool_use_enforcement: permissive   # Claude doesn't need enforcement.
  verify_on_stop: auto         # "auto" = on for CLI, off for gateway. Better than hard false.
  api_max_retries: 1           # Fail fast to fallback_providers. Default 3 is too slow.
  # reasoning_effort: ""       # Set "high" for complex coding; default medium is fine.
```

## Tool loop guardrails (entire block missing from most configs)

```yaml
tool_loop_guardrails:
  warnings_enabled: true       # Inject warning when agent loops. Default true.
  hard_stop_enabled: false     # Keep false for interactive CLI; true for cron workers.
  warn_after:
    exact_failure: 2           # Same failing call repeated 2× → warn.
    same_tool_failure: 3       # Same tool, different args, 3× failures → warn.
    idempotent_no_progress: 2  # Same result, no progress, 2× → warn.
```

## Applying changes

All keys above can be set via:
```bash
hermes config set compression.micro_compact true
hermes config set compression.threshold 0.50
hermes config set compression.threshold_tokens 80000
hermes config set agent.max_turns 500
hermes config set agent.api_max_retries 1
hermes config set tool_loop_guardrails.warnings_enabled true
# etc.
```

Multi-level nested keys (auxiliary slots) require individual `hermes config set` calls.
The `patch` file tool is blocked on `~/.hermes/config.yaml` (security-sensitive).

## Verified live state (2026-08-08, config_version 33)

After applying the above:
- `compression.threshold: 0.5` ✓
- `compression.threshold_tokens: 80000` ✓
- `compression.proactive_prune_tokens: 48000` ✓
- `compression.micro_compact: true` ✓
- `compression.micro_compact_every_n_turns: 3` ✓
- `compression.protect_last_n: 15` ✓
- `compression.min_tail_user_messages: 3` ✓
- `compression.idle_compact_after_seconds: 1800` ✓
- `agent.max_turns: 500` ✓
- `agent.verify_on_stop: auto` ✓
- `agent.api_max_retries: 1` ✓
- `tool_loop_guardrails.warnings_enabled: true` ✓
- All auxiliary task slots routed to cerebras/zai-glm-4.7 ✓
