# Latency-aware routing for Hermes

Use this when the user wants Hermes to feel faster without aggressively cutting capability or increasing token spend.

## What to tune first

1. Keep the primary model unless the user asks for a stronger tradeoff.
2. Lower default reasoning effort.
   - Conservative default: `agent.reasoning_effort = low`
3. Reduce retry count on the primary path.
   - Conservative default: `agent.api_max_retries = 1`
4. Reorder or trim the fallback chain so heavy local models do not sit ahead of faster remote fallbacks.

## Why

A true latency-threshold auto-escalation policy may not be available as a first-class Hermes setting. The practical substitute is to:
- make the initial request cheaper,
- avoid long retry tails,
- and ensure fallback does not jump to a CPU/RAM-heavy local model unless the user explicitly values local/offline resilience more than responsiveness.

## Good conservative pattern

Primary:
- `anthropic / claude-sonnet-4-6`

Fallbacks:
1. `anthropic / claude-haiku-4-5`
2. `anthropic / claude-sonnet-4-6`

Avoid putting a heavy local model such as `qwen3:8b` first in the fallback chain when the complaint is slowness, because fallback activation can amplify local resource pressure.

## Verification checklist

- Back up `~/.hermes/config.yaml` before edits.
- Confirm `agent.reasoning_effort` after the change.
- Confirm `agent.api_max_retries` after the change.
- Confirm the fallback chain with Hermes' own fallback-listing command, not only by reading YAML.
- Check recent agent logs to distinguish between:
  - provider latency,
  - large-context latency,
  - retry drag,
  - and heavy local fallback behavior.

## Tradeoff summary

Pros:
- lower average latency
- less local CPU/RAM burst during fallback
- modest or reduced token spend

Cons:
- somewhat less reasoning depth by default
- less persistence through transient provider errors because retries are reduced
- weaker offline/local resilience if remote fallbacks are preferred over local ones
