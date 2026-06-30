---
name: hermes-performance-tuning
description: Tune Hermes for lower latency and lower local CPU/RAM pressure without swinging hard on capability or token spend.
---

# Hermes performance tuning

Use this when Hermes feels slow, CPU-heavy, RAM-heavy, or unusually expensive, and the goal is a conservative optimization pass rather than a radical reconfiguration.

For general workflow/token-efficiency decisions, load `hermes-workflow-optimization` first. For session-bloat/compression-discipline issues, load `hermes-context-hygiene`. Use this skill when the question is specifically runtime performance, local heat, auxiliary-model load, or conservative config tuning.

Reference: `references/hermes-maintenance-hygiene.md` for the maintenance-first pass to run before deeper tuning.
Reference: `references/prompt-surface-pruning.md` for token-optimization passes centered on enabled toolsets, MCP servers, and low-use skills.
Reference: `references/conservative-disable-only-pruning.md` for the safest first-pass cleanup pattern: disable toolsets and low-use skills first, verify before/after counts, and keep the final report concise and in English.
Reference: `references/config-guarded-hermes-edit-pattern.md` for the safe fallback when Hermes config files are protected from direct patch/write tools.
Reference: `references/tuning-boundary-map.md` for the quick routing boundary between workflow optimization, context hygiene, memory-surface choice, and runtime tuning.
Reference: `references/conservative-tuning-order.md` for the shortest safe sequence when you only need the order of operations.

## When to use

## Maintenance-first pass
Before deeper tuning, do a hygiene pass when the setup already mostly works:
- run `hermes doctor --fix`, then verify with `hermes config check` and `hermes doctor`
- inspect cron health before changing architecture; broken or outdated jobs can be the real source of drift
- for unsupported-model cron failures: update the job, force a run, then verify `hermes cron list`
- for noisy/timed-out watchdogs: pause first, test manually, then decide whether to resume or redesign
- when multiple watchdog-style cron jobs exist, inventory the live jobs, their backing scripts, and the job purpose before touching schedules; merge only jobs that share the same schedule shape, quiet-on-success behavior, and operational surface
- keep service-specific watchdogs and policy/enforcement jobs separate from general platform-health checks, even if they are all "maintenance"
- if a check fails because a time-scoped note/file was not present yet but the same script passes later, treat it as schedule/error-handling hygiene first (reschedule it later or make the missing artifact a quiet no-op) rather than recording the script as broken
- on laptop-class systems, prefer remote main reasoning plus local retrieval instead of adding more local background inference
- write a short architecture note after the pass so later tuning stays grounded in the real stack

Reference: `references/cron-consolidation-and-watchdog-hygiene.md` for a concrete overlap-audit pattern.

## When to use
- Recent Hermes sessions feel slower than usual.
- Local Ollama / auxiliary model processes are consuming too much CPU or RAM.
- Compression or memory-related background work appears frequently in logs.
- The user wants Hermes a bit faster or lighter, but does not want aggressive cost-cutting or capability loss.

## Goals
1. Reduce local resource pressure first.
2. Avoid increasing token spend unless the user explicitly wants that tradeoff.
3. Prefer reversible config changes.
4. Verify with live config/status output, not guesses.

## Core workflow
1. Inspect current Hermes config and recent logs/status.
   - Check model, auxiliary models, compression settings, resume display, and config version.
   - Look for repeated compression activity, large-context turns, or background memory churn.
2. Identify whether the main cost is:
   - main model latency,
   - auxiliary local model weight,
   - compression frequency,
   - resume/context bloat,
   - or background memory/dashboard activity.
3. Apply conservative changes first:
   - migrate config if outdated;
   - keep the main model unchanged unless the user asked for more aggressive speed/cost tuning;
   - move auxiliary local tasks to a smaller local model if it still has enough context for the job;
   - slightly raise compression threshold to avoid compressing too eagerly;
   - reduce resume verbosity so resumed sessions inject less context by default.
4. Re-run config validation and confirm the exact keys changed.
5. Report tradeoffs plainly.

## Conservative tuning defaults
Use these before considering anything more aggressive:

### 1) Migrate config first
If `hermes config check` shows an outdated config version, run migration before tuning so you are not optimizing stale structure.

### 2) Prefer a smaller local auxiliary model
If auxiliary tasks are on a heavier local Ollama model and a smaller installed local model has enough context, switch auxiliary workloads first.

Good candidates for downshifting:
- compression
- title_generation
- triage_specifier
- profile_describer
- curator

Do this before changing the main model, because auxiliary jobs can generate steady background load.

### 3) Raise compression threshold modestly
If Hermes is compressing often, increase the threshold a little rather than disabling compression.

Default conservative move:
- `compression.threshold`: `0.5 -> 0.6`

Reason: fewer compression passes, less local summarization work, small increase in average prompt size, usually still within a sensible token budget.

### 4) Reduce resume payload
Prefer more compact resume behavior for CLI use when the user wants lower overhead.

Default conservative move:
- `display.resume_display = compact`
- `display.resume_exchanges = 6`

Reason: resumed sessions start with less injected transcript while preserving short continuity.

### 5) Prune unused skills from autoload eligibility
If the user wants Hermes to load less support material by default, audit skill usage and disable skills that have not been used recently, especially newly added update-era skills that have never been touched.

Conservative workflow:
1. Review `~/.hermes/skills/.usage.json`.
2. Compare it against `skills.disabled` in `~/.hermes/config.yaml`.
3. Add skills with no recent `last_used_at` (for example, 14+ days) or no `last_used_at` at all.
4. Verify the config still stores `skills.disabled` as a real YAML list, not a quoted JSON string.

Why this helps:
- reduces candidate skill surface for automatic loading;
- keeps newly introduced bundled/hub skills from adding noise before the user actually needs them;
- is reversible and low-risk.

### 6) Prune prompt surface in the right order
When the user explicitly asks for token optimization across Hermes itself, do not start with skill-file deletion. Audit the live prompt surface in this order:
1. enabled toolsets via `hermes tools list`
2. enabled MCP servers via `hermes mcp list`
3. enabled vs disabled skills via `hermes skills list`
4. skill usage via `~/.hermes/skills/.usage.json`
5. large enabled umbrella skills by file size

Default decision rule:
- toolsets first
- MCP servers second
- low-use enabled local skills third
- large umbrella refactors last

Reason: eligibility to load into sessions matters more than raw disk usage, and a single enabled MCP or media/toolset family can add more live surface than many dormant skill files.

### 7) Prefer disable-only cleanup on the first pruning pass
When the user asks for Hermes cleanup or token optimization and does not explicitly ask for aggressive deletion, prefer a disable-only pass first.

Default order:
1. disable low-value default toolsets
2. disable low-use enabled local skills
3. leave MCP removal for a second pass unless the user explicitly wants it now
4. if Hermes config files are protected from direct patch/write tools, make a timestamped backup and do a minimal scripted edit instead of forcing a broader rewrite
5. verify with before/after counts and `hermes config check`

Reporting rule for this task class:
- keep the final report concise and in English
- list exact toolsets/skills changed
- show before/after enabled-vs-disabled counts
- state clearly whether MCP servers were changed or left untouched

Why this helps:
- it reduces live prompt surface faster than file deletion
- it is reversible
- it keeps verification simple and legible

## Decision rules
- Do not change the main model unless the user wants a stronger speed/cost tradeoff.
- Do not disable memory providers or dashboard processes as a first step unless evidence shows they are the dominant problem and the user is okay with feature reduction.
- Do not over-optimize by stacking many speculative tweaks at once; keep the pass attributable and reversible.

## Verification
Always verify all of the following:
- config version after migration
- exact tuned keys in config
- that chosen auxiliary model is actually installed / available
- if relevant, that the smaller local model still has adequate context length for the auxiliary job

## Diagnosing "Hermes is idle but CPU is hot"
When the user reports high CPU or temperature even though they only see the Hermes terminal open, do not assume the visible CLI process is the real source. Check for Hermes-triggered local auxiliary workloads first.

Recommended workflow:
1. Inspect live top CPU consumers and process trees.
2. If `ollama` or another local model runner is dominant, identify the exact model process.
3. Check Hermes auxiliary routing in `~/.hermes/config.yaml`, especially:
   - `auxiliary.title_generation`
   - `auxiliary.triage_specifier`
   - `auxiliary.profile_describer`
   - `auxiliary.curator`
   - `auxiliary.summarization`
   - `auxiliary.compression`
4. Correlate with recent Hermes logs for auxiliary calls, retries, and fallbacks.
5. If the hotspot is low-value auxiliary work on a local model, reroute those auxiliary tasks to a lightweight remote/main mini model before changing the main agent model.

Important pattern:
- A remote main model does NOT guarantee low local CPU.
- Local auxiliary tasks like title generation can still spin up Ollama in the background and dominate CPU/RAM.
- Repeated timeout/retry/fallback cycles on a small local model can create heat and noise even when the user thinks Hermes is "doing nothing."

Conservative fix pattern:
- Move background-style auxiliary tasks from local Ollama to `anthropic` with a small remote model such as `claude-haiku-4-5`.
- Verify the changed keys after editing.
- Remind the user that an already-running local model process may continue until the in-flight request ends or the process is stopped; config changes mainly affect new sessions / new auxiliary calls.

## Pitfalls
- A very large main-model context can trigger repeated compression and long turns even when the model itself is fine; check logs before blaming only the provider.
- Heavy local auxiliary models can dominate CPU/RAM even when the main model is remote.
- Lowering capability too far on auxiliary tasks can save RAM but degrade summaries/titles; choose the smallest model that still fits the job.
- A smaller local model can still be the wrong compression model if large-summary prompts routinely hit its timeout window. If logs show repeated `Auxiliary compression ... Request timed out` on Ollama followed by failed context summaries, move compression to a more reliable remote mini model and disable `compression.abort_on_summary_failure` so Hermes degrades gracefully instead of surfacing repeated abort messages.
- Hermes Hindsight local_embedded config is two-part: `~/.hermes/hindsight/config.json` stores the provider/model choice, and `~/.hindsight/profiles/<profile>.env` is the daemon env that Hindsight actually launches with. When changing Hindsight away from local Ollama, update both and verify the live daemon env instead of assuming the JSON alone is authoritative.
- Changing persisted Hindsight config does not necessarily retune the already-running Hermes process. A live Hermes parent can keep launching `hindsight-api` with the old in-memory env/provider until Hermes itself is restarted. After editing Hindsight config, inspect the live daemon environment and connections; if it still shows the old provider, plan for a Hermes restart before declaring the switch complete.
- `hermes config set skills.disabled ...` may serialize the disabled-skill list as a quoted JSON string instead of a YAML sequence. If that happens, normalize `skills.disabled` back to a proper YAML list before finishing, then verify the parsed type.
- Direct file-mutation tools may refuse writes to `~/.hermes/config.yaml` because Hermes treats it as security-sensitive. When that happens, do not stop at the refusal: take a timestamped backup, perform the smallest possible scripted edit, then verify with config readback plus `hermes config check` and live inventory commands.
- Do not encode transient setup failures as durable rules.

## Hindsight-specific local heat diagnosis
If the hotspot is `ollama runner` but the main Hermes model is remote, check whether the Hindsight memory provider is the real caller before blaming auxiliary summarization or the visible CLI turn.

Workflow:
1. Confirm `memory.provider: hindsight` in Hermes config/status.
2. Inspect Hindsight persisted config in `~/.hermes/hindsight/config.json` for `mode`, `llm_provider`, and `llm_model`.
3. Inspect `~/.hindsight/profiles/<profile>.env` because local_embedded Hindsight launches from this env file.
4. Check the live `hindsight-api` process environment for `HINDSIGHT_API_LLM_PROVIDER` / `HINDSIGHT_API_LLM_MODEL`.
5. Verify with live evidence: active TCP connections to `127.0.0.1:11434`, metrics labels showing provider/model, or a spawned `ollama runner` process.
6. If reconfiguring to a remote provider, verify support in Hindsight itself, not just Hermes. `anthropic` is the recommended Hindsight provider; set `auxiliary.compression.provider: anthropic` and `model: claude-haiku-4-5`.
7. After changing config, restart Hermes if the live daemon still inherits old values from the current parent process.

## References
- `references/conservative-local-first-tuning.md` — concrete tuning pattern for local-first Hermes setups with heavy auxiliary Ollama load.
- `references/latency-aware-routing.md` — conservative model-routing adjustments for lower perceived latency without large token-spend increases.
- `references/delegation-escalation.md` — when to put a stronger model on delegation instead of the main session or fallback chain.
- `references/hindsight-local-heat-and-provider-switch.md` — Hindsight-specific diagnosis and reconfiguration notes for moving local_embedded memory off Ollama.

## Latency-aware routing without over-spending
Hermes may not expose a true built-in policy of "switch models mid-task when latency crosses X seconds." For that class of request, use a conservative approximation instead of inventing a nonexistent knob.

Recommended order:
1. Lower default reasoning effort before changing the primary model.
   - Good conservative move: `agent.reasoning_effort = low`
   - Effect: lower average latency and token use on normal turns, with less capability loss than swapping the main model immediately.
2. Reduce retry drag on slow/flaky upstream calls.
   - Good conservative move: `agent.api_max_retries = 1`
   - Effect: Hermes spends less time repeating a slow failing request before surfacing or falling through.
3. Put fast remote fallbacks ahead of heavy local models.
   - If the primary is remote and the first fallback is a heavy local Ollama model, that fallback can worsen perceived slowness by adding local CPU/RAM pressure exactly when the session is already degraded.
   - Prefer a fallback chain such as remote `claude-haiku-4-5` / `claude-sonnet-4-6` before a local `qwen3:8b`-class model when the user's goal is responsiveness rather than offline resilience.
4. Keep the main model unchanged unless the user explicitly wants a stronger speed/cost tradeoff.

## Verification for latency-aware tuning
When making the above changes, verify:
- `agent.reasoning_effort`
- `agent.api_max_retries`
- the current fallback chain as actually parsed by Hermes
- recent logs for whether the slower path was retries, large-context latency, or local fallback activation

## When the UI shows huge context but Hermes is not compressing
If the user reports a session showing something like `316k/128k` or otherwise obviously oversized context, do not assume compression is broken in the abstract. First verify whether auto-compaction was disabled in config.

Recommended workflow:
1. Read `compression` from `~/.hermes/config.yaml`.
2. Check `compression.enabled` before chasing threshold math or provider quirks.
3. Inspect recent `agent.log` lines for `Preflight compression`, `context compression started`, `context compression done`, or explicit disabled-state messaging.
4. Remember that `compression.enabled: false` disables BOTH preflight compression and overflow-triggered auto-compaction paths.
5. If the setting was off unexpectedly, restore it first, then read back the config to confirm.
6. If the current conversation is already massively bloated, advise a fresh session after reenabling compression; the persisted fix may be correct while the live session remains in a bad state.

Conservative repair default:
- `compression.enabled: true`
- keep `compression.threshold` at a conservative value such as `0.5` unless the user explicitly wants later compaction.

Important pitfall:
- a large displayed context ratio plus missing recent compression events is often a config-state problem (`compression.enabled: false`), not proof that the compression subsystem or provider is malfunctioning.

## Escalation options
Only after the conservative pass, consider:
- switching the default main model to a faster/cheaper sibling (for example a `-mini` class model), or
- trimming/pausing background dashboard or memory activity if logs show it is the sustained hotspot and the user accepts the feature tradeoff.

## Complex-work escalation without slowing the main session
When the user wants stronger handling for rare hard tasks but does not want everyday Hermes turns to get slower or more expensive, prefer delegation-level escalation over changing the primary model or fallback chain.

Recommended order:
1. Keep the main session on the user's normal model.
2. Verify the stronger model/provider is actually usable with a tiny one-shot Hermes call before wiring it into config.
3. Set `delegation.provider` and `delegation.model` to the stronger model.
4. Keep `delegation.reasoning_effort` conservative (`low` is a good default) unless the user explicitly wants max-depth reasoning.
5. If the user is spend-sensitive, reduce `delegation.max_concurrent_children` (for example `3 -> 2`) to cap burst token spend during multi-branch delegation.

Why this is usually better than fallback escalation:
- fallback is failure-based, not complexity-based;
- putting a heavier model into fallback does not mean Hermes will choose it for hard tasks, only that it may try it after errors/rate limits;
- delegation lets only the hard subtask pay the stronger-model cost while the parent session stays faster.

Verification and rollout notes:
- confirm the model works with a real one-shot query before saving the config;
- verify `delegation.provider`, `delegation.model`, `delegation.reasoning_effort`, and `delegation.max_concurrent_children` after changes;
- remind the user that delegation settings may be snapshotted by the running Hermes session/process, so a fresh CLI session or gateway restart may be needed before subagents actually use the new model.

## References
- `references/conservative-local-first-tuning.md` — concrete tuning pattern for local-first Hermes setups with heavy auxiliary Ollama load.
- `references/latency-aware-routing.md` — conservative model-routing adjustments for lower perceived latency without large token-spend increases.
- `references/delegation-escalation.md` — when to put a stronger model on delegation instead of the main session or fallback chain.
