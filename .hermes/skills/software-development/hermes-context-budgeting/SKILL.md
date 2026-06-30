---
name: hermes-context-budgeting
description: Tune Hermes context-length and compression settings with live verification, favoring token-efficient caps that still preserve usable agent headroom.
---

# Hermes Context Budgeting

## When to use
- The user asks what context window Hermes is actually using.
- The user wants a smaller practical cap than the model's advertised maximum.
- You need to reduce token use or latency without making Hermes brittle.
- You see inconsistent numbers between docs, provider marketing, cached metadata, and Hermes runtime behavior.

If the problem is general session bloat or missed compression discipline rather than runtime cap tuning, load `hermes-context-hygiene` instead. Use this skill for measured context-cap and compression-setting decisions.

## Core rule
Do **not** answer from provider marketing pages or raw config alone. Verify the **resolved runtime context** Hermes will use, then size the cap against the actual startup prompt cost.

## Procedure
1. **Read the runtime resolution path first.**
   - Check `agent/model_metadata.py`, especially `get_model_context_length()`.
   - Treat the runtime resolution order as authoritative over model-card claims.
2. **Check the live resolved context.**
   - Use a runtime probe that loads config and calls `get_model_context_length(...)` with the active model/provider/base_url and any explicit `model.context_length` override.
   - Confirm whether the value comes from override vs metadata resolution.
3. **Estimate startup prompt cost.**
   - Use `hermes prompt-size` when available.
   - Add the system-prompt and tool-schema sizes and convert to a rough token estimate. A simple heuristic is `chars / 4` when you only need a cap decision, not billing precision.
4. **Choose a practical cap, not the maximum.**
   - For token-efficient Hermes usage, prefer a cap that leaves comfortable working headroom after startup overhead rather than exposing the full provider maximum.
   - Treat **64k** as the floor for Hermes agent workflows, not the target.
   - A **128k** cap is a strong default when startup overhead is already around 20–25k tokens and the user wants a balance of cost and usability.
5. **Enable compression with an early enough trigger.**
   - If the goal is ongoing token discipline, turn on `compression.enabled: true`.
   - A good default is `compression.threshold: 0.5` so compression begins well before the cap is exhausted.
   - Keep `abort_on_summary_failure: true` unless the user explicitly wants availability over summary correctness.
6. **Apply with durable config changes.**
   - Set `model.context_length` to the chosen cap.
   - Set/verify compression values in `~/.hermes/config.yaml` via Hermes config commands.
7. **Verify after applying.**
   - Re-run the runtime probe and confirm `resolved_context_length` equals the configured override.
   - Re-check config to ensure the expected values were persisted.
8. **Warn about restart/session reset requirements.**
   - If Hermes is already running, tell the user a new session, `/reset`, or process restart may be needed for the new context budget to take effect cleanly.

## Default recommendation
When the user wants a "reasonable" cap for Hermes itself rather than maximum bragging rights:
- set `model.context_length: 128000`
- set `compression.enabled: true`
- set `compression.threshold: 0.5`

Use this default unless live prompt-size evidence suggests either:
- startup overhead is so large that 128k would be cramped, or
- the user explicitly wants a more aggressive cap like 96k.

## Pitfalls
- **Do not trust provider docs alone.** The public model page may advertise a larger window than the active Hermes provider path actually resolves to.
- **Do not trust raw `hermes config get model.context_length` alone.** Empty output only means there is no explicit override; Hermes may still resolve a provider/model-specific context length.
- **Do not preserve stale overreported cache values.** If code comments mention invalidation for stale high values, believe the runtime path, not historical summaries.
- **Do not leave compression disabled** when the user explicitly wants token minimization.
- **Do not choose 64k by reflex.** Hermes treats that as minimum viable working memory; it is often too tight once the system prompt and tools are loaded.

## Heuristic for picking the cap
After estimating startup tokens:
- `<40k` remaining headroom at cap: usually too cramped for general Hermes use.
- `~100k` remaining headroom: usually a good balance.
- `>200k` remaining headroom: usually optimized for capacity, not efficiency.

## Verification checklist
- Active model/provider identified.
- Resolved context measured via `get_model_context_length(...)`.
- Startup prompt cost estimated from `hermes prompt-size`.
- Chosen cap written to config.
- Compression enabled and threshold verified.
- Post-change resolved context re-checked.
- User told whether restart or `/reset` is needed.

## References
- `references/runtime-probes.md` — concise runtime facts and the cap-selection rationale from a live Hermes tuning session.
