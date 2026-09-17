# Runtime probes and rationale

## Durable facts from the session
- `get_model_context_length()` in `agent/model_metadata.py` is the authoritative runtime resolver.
- The resolver documents a final default fallback of `256K`, but can return lower or higher values earlier based on provider-aware probes, caches, and explicit overrides.
- For the active `gpt-5.4` + `openai-codex` path in this environment, the live runtime probe returned **272000** before any explicit override.
- The same code path accepts an explicit `config_context_length` override and returns it directly when positive.
- Hermes defines `MINIMUM_CONTEXT_LENGTH = 64000` and probe tiers beginning at `256000`, then `128000`, then `64000`.
- `tools/tool_search.py` contains an internal note that when context size is unknown, a fixed **20K-token** deferrable cutoff is used because larger payloads showed quality drops.

## Prompt-size budgeting notes
- In the observed session, system prompt + tool schemas totaled about **94 KB** of text.
- A rough `chars / 4` estimate produced about **23.5K startup tokens**.
- Approximate post-startup headroom by cap:
  - `64K` cap → ~`40K` remaining
  - `128K` cap → ~`104K` remaining
  - `160K` cap → ~`136K` remaining
  - `192K` cap → ~`168K` remaining
  - `272K` cap → ~`248K` remaining

## Chosen default and why
For a user optimizing for token discipline with decent usability, `128000` was selected because it:
- stays well above Hermes' 64K minimum,
- leaves roughly ~100K working headroom after startup overhead,
- is much smaller than the provider-resolved 272K path,
- pairs naturally with `compression.enabled: true` and `compression.threshold: 0.35` (live default; do not change mid-session).

## Apply/verify pattern
1. Probe resolved context before changes.
2. Estimate startup token load from `hermes prompt-size`.
3. Set:
   - `model.context_length = 128000`
   - `compression.enabled = true`
   - `compression.threshold = 0.35` (live default — 0.5 is stale)
4. Re-run the runtime probe and verify `resolved_context_length == 128000`.
5. Remind the user that a fresh session or `/reset` may be needed.
