# Mixture-of-Agents (`hermes moa`) — Built-in Mixed-LLM Aggregation

Hermes ships a native MoA feature, separate from `delegate_task`/subagents: `hermes moa
list|configure|delete` manages named presets of reference models + one aggregator model,
invoked via `/moa <prompt>` in a session. This is the actual mechanism for "GPT + Claude
operating together on one prompt" — it already exists and is provisioned on this account, just
not wired into default routing.

## Current Live State (verified 2026-07-07)

**Corrected 2026-07-07**: the factory-default preset (`openai-codex:gpt-5.5` +
`openrouter:deepseek/deepseek-v4-pro` reference, `openrouter:anthropic/claude-opus-4.8`
aggregator) was replaced — OpenRouter has no key on this account, so that preset would have
failed at every reference/aggregator call. Current live state (verified via `hermes moa list`):
- Preset name: `default`
- Reference model: `openai:gpt-5.5` (the already-wired, credential-confirmed `custom_providers`
  entry — NOT `openai-codex`, which needs separate OAuth)
- Aggregator: `anthropic:claude-sonnet-4-6` (updated 2026-07-08; was claude-sonnet-5 — the
  native provider, always live — not `openrouter:claude-opus-4.8`, which needs a key this
  account doesn't have)
- `reference_max_tokens: 600` set to cap advisor latency (turn wall-time is dominated by the
  slowest advisor's token count).
- **Active in config: (off)** — still configured-but-not-default. Only fires on explicit
  `/moa <prompt>` or `/model default --provider moa`, never automatically.

Rule going forward: before trusting or recommending ANY moa preset (the shipped default or a
new one), cross-check its provider prefixes against the Ground truth table in SKILL.md — a
preset referencing a provider with no key in `.env` will fail or silently degrade at that step
regardless of whether MoA itself is toggled on.

## Caveats

- MoA (multiple models feeding one aggregator on a single prompt) is a different pattern from
  `delegate_task` orchestration (parallel independent subagents each with their own context) —
  see `hermes-role-pipelines` for the latter. When a request asks for both "multi-agent
  workflows" and "mixed LLM routing" in the same breath, treat them as two separate levers to
  evaluate independently, not one feature to flip.
- Flipping "Active in config" on changes default per-turn cost/latency for every prompt, not
  just an explicit override — get explicit user sign-off before doing that, same bar as any
  other routing-default change.

## Pitfall: `hermes moa configure <name>` (interactive wizard) writes a malformed duplicate block

`hermes moa configure default` is a PTY wizard (needs `pty=true` in `terminal`, and even then it
can hang waiting on stdin — background it, poll, then `pkill -f "hermes moa configure"` once you
see "Saved MoA preset" in the output). After it saves, it can leave BOTH a correct nested block
(`moa.presets.default.{reference_models,aggregator,...}`) AND a stray top-level
`moa.{reference_models,aggregator,max_tokens,fanout,enabled}` sibling with the OLD preset values
— the top-level keys are dead (the schema is `moa.presets.<name>.*`) but they clutter the file
and can confuse a future read. Also, `hermes config set moa.presets.default.reference_models
'[{"provider":"openai","model":"gpt-5.5"}]'` hits the exact same stringification footgun as
documented in SKILL.md (JSON-as-string instead of a real YAML list) — same rule applies: never
use `hermes config set` for a list/dict-valued key.

## Working Fix Sequence (verified 2026-07-07)

1. Run the wizard once via backgrounded `pty=true` terminal to pick reference/aggregator models
   interactively (or skip it and go straight to step 2 if you already know the exact model ids).
2. Read `config.yaml`, then do a direct `python3 -c "import yaml; ..."` read-modify-write that
   REPLACES the entire `moa:` key with a clean `{default_preset, presets: {<name>: {...}}}`
   dict — do not try to hand-patch around the stray top-level keys, just rebuild the block.
3. `yaml.safe_dump(..., sort_keys=False, default_flow_style=False)` to a scratch file, `diff`
   the parsed-YAML dump of old vs new config to confirm ONLY the `moa` block changed (catches
   accidental drops of comments/other keys from the round-trip), then move the scratch file over
   the real config.
4. `hermes config check` (no new warnings) + `hermes moa list` (prints the resolved preset —
   this is the fastest way to confirm the nested structure actually parsed, not just that the
   file is valid YAML) + `hermes doctor` (full regression check) before trusting the edit.
