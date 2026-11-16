<p align="center">
  <img src="assets/banner.png" alt="Hermes Agent" width="100%">
</p>

# hermes-fork ☤

> **This is a personal fork of [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent).** It tracks upstream and layers a dense set of research-driven extensions on top. Not an official Nous Research product — one person's daily driver. For the supported version use the upstream repo.

<p align="center">
  <a href="https://hermes-agent.nousresearch.com/docs/"><img src="https://img.shields.io/badge/Docs-hermes--agent.nousresearch.com-FFD700?style=for-the-badge" alt="Documentation"></a>
  <a href="https://discord.gg/NousResearch"><img src="https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord"></a>
  <a href="https://github.com/NousResearch/hermes-agent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://nousresearch.com"><img src="https://img.shields.io/badge/Built%20by-Nous%20Research-blueviolet?style=for-the-badge" alt="Built by Nous Research"></a>
</p>

**227 commits ahead of upstream. 25 active plugins. 266 enabled cron jobs. 6 new agent/ modules.**

---

## What this fork adds over upstream

Additions are organised into five tiers by where they run:

1. **In the turn loop** — changes to agent core files that fire every turn
2. **At compress time** — plugins that modify or observe every compaction event
3. **Background jobs** — scheduled scripts that maintain indexes, scores, and stores
4. **Memory architecture** — a multi-tier memory system extending upstream's defaults
5. **Infrastructure** — sandbox, cron hardening, system maintenance

The turn loop itself (iteration, tool dispatch, stop conditions) is not replaced. All agent core changes are listed precisely in the "Agent core changes" section below.

---

## Agent core changes (what actually changed in `agent/`)

This is the most important section for accuracy. The fork adds six new modules to `agent/` and makes targeted changes to several existing ones. None of them rewrite the conversation loop.

### New `agent/` modules

**`agent/session_classifier.py`** — heuristic session-type classifier. Exports `classify()`, `get_routing_hint()`, `SESSION_TYPES` (`research`, `code`, `mixed`, `entropy-adaptive`), and maps session type to compression profile names. Currently `get_routing_hint()` always returns `fork_mixed` as the compression profile (domain-specific profiles were found to over-prune in v4 eval). `get_routing_hint()` also emits `reasoning_effort_bias` (`research→high`, `code→medium`, `mixed→default`) and `model_tier_hint` (`frontier`/`balanced`/`fast`) for plugins to consume.

**`agent/routing_harmonizer.py`** — 29-line stability shim that re-exports everything from `session_classifier`. Exists so plugins can import from a stable name while the classifier evolves.

**`agent/reasoning_verbosity.py`** — `ReasoningVerbosityMixin` on `AIAgent`. Adds three verbosity modes: `full` (default), `compact` (strips completed thinking tags from history on low/medium-effort turns), and `suppress` (sets `_suppress_thinking_prefill` read by `turn_empty_response.py`). `compact_thinking_history()` is not called from `conversation_loop.py` — it is available for plugins and lambda-tuner to invoke via `PluginContext.set_verbosity_mode`.

**`agent/adaptive_retrieval.py`** — library of relevance heuristics (Mallen 2023 / Yoran 2023, no LLM calls). Contains `should_retrieve_skill(query, top_score)` → `skip`/`names_only`/`full` (skip if BM25 < 0.15 and < 6 words; `names_only` if BM25 > 0.85; hard-domain regex forces `full`), `web_search_necessity()`, `filter_web_passages()` (drops passages below 0.12 keyword overlap unless that would drop all), `is_degenerate_tool_result()`, and `apply_tool_result_guards()`. Re-exported by `agent/skill_utils.py`. **No call sites in `conversation_loop.py` or `tool_executor.py`** — it is a library used by `skill_utils` and optionally by plugins.

**`agent/ssl_guard.py`** — re-exports `resolve_httpx_verify` / `install_truststore` from upstream's `ssl_verify` module. Ensures the agent never passes `verify=False`. Also contains a linter for skill frontmatter SSL fields.

**`agent/micro_compaction.py`** — MemForest partition pruning. `partition_messages_by_event()` and `apply_partition_prune_order()` apply weighted pruning: tool_result 0.4, reasoning 0.6, tool_call 0.8, assistant prose 0.7, user messages never pruned. Called from `context_compressor.py` before summarisation when MemForest mode is active.

### Changes to existing `agent/` modules

**`agent/conversation_loop.py`** (two changes):
- `invoke_hook("on_session_start", ..., agent=agent)` — added the live `agent` object as a keyword argument so plugins can access the agent instance from `on_session_start`. Upstream omitted this.
- `_persist_system_prompt(..., persist_tools=True)` on the Bot Chat capability-refresh path. Upstream used the default `persist_tools=False`.

**`agent/tool_executor.py`** (three changes):
- Calls `_governance_pre_check(function_name, function_args)` from `tool_guardrails` before each tool call. This is fire-and-forget: failures are swallowed, the return value is discarded, and execution always continues. It does not block.
- Calls `fire_pre_compress(...)` from `compaction_events` after a successful auto-compress, so `pre_compress` hooks receive the event.
- Removed the call to `maybe_apply_per_call_deadline()` from the deleted `tool_executor_deadline.py` module. Tool timeouts now rely on the argument/default only.

**`agent/tool_executor_deadline.py`** — deleted. This upstream module clamped `terminal`/`execute_code`/`process_manage` timeouts to `min(user_timeout, remaining_deadline)` with a 60-second floor. The fork removed this. Tool calls no longer have a remaining-deadline clamp.

**`agent/tool_guardrails.py`** (two changes):
- `_governance_pre_check(tool_name, args)` added. If `tool_name` is in `{write_file, patch, terminal, execute_code}` and an argument value contains a critical-path indicator (`.hermes/hermes-fork/agent/`, `.hermes/profiles/`, `.hermes/plugins/`, `config.yaml`), it launches `improvement_governance.py propose` as a background subprocess with a 5-second timeout. Logging only — no blocking, no return value used.
- `check_skills_guard()` rewritten. The upstream `_FORGET_RULES` regex list (jailbreak-ish patterns: "ignore previous", "you are now", etc.) was removed. The new logic only logs `[skills_guard]` when `skill_name` is in `{skill_manage, write_file, patch}` or `target_file` contains `SKILL.md`. Upstream blocked matching content; the fork does not block.

**`agent/context_compressor.py`** (additions, no removal of core logic):
- `_message_text_for_entropy(msg)` — flatten message content to plain text for analysis.
- `_CAUSAL_TOOLS`, `_NOISE_TOOLS`, `_CHEAP_REACQ_TOOLS` — constants defined for tool classification. Used by eval harness; not wired into live `compress()` calls in this survey.
- `_last_ratio: float | None` on `ContextCompressor`; `last_ratio` property.
- `_fork_policy_set_exists()` — True if `self._policy_set` is a non-empty dict.
- `set_compression_profile(profile_name, **overrides)` — looks up `COMPRESSION_PROFILES` from `agent.compression_config`, copies into `_policy_set`, applies overrides (`target_ratio`, `protected_roles`, `protected_last_n`, `max_tokens`). Called by lambda-tuner.
- `_extract_fact_ledger(turns)` / `_prepend_fact_ledger(summary, turns)` — harvest paths, arXiv IDs, model names, SHAs, and numbered facts from turns and prepend as `FACT LEDGER:` to the compaction summary to mitigate lost-in-the-middle effects. Tested; live call site in `compress()` not confirmed in this survey.
- `importance_biased_prune_enabled: bool = False` flag. No new importance-scorer class. JEV lives in the `jev-compaction` plugin, not in this module.
- `_should_compress()` now gates on `billion_context.should_skip_for_growth()`.

**`agent/prompt_builder.py`**:
- Imports `skill_tier_string` from `agent.skill_utils`. This stub always returns `"full"` (BPS budget-aware selection is not wired into the prompt builder yet).
- Skill focus-mode demotion: textbook-category skills collapse to `category [names only]: name, …` when `is_coding=True` and `config_mode="focus"`. Frontmatter `category:` now overrides path-derived category, so textbook skills demote regardless of directory structure.
- New: `skill_is_model_invocable()` — `metadata.hermes.disable_model_invocation: true` excludes a skill from `<available_skills>` while still allowing `skill_view()` calls. Applied in `_parse_skill_file`, plugin skill rows, and snapshot fast-path. Snapshot version incremented to 6.

**`agent/subagent_lifecycle.py`**:
- `SubagentTerminalState` gains `unsupported: bool = False`.
- `SubagentLifecycle.wait()` timeout no longer raises — it now sets a failed terminal state with a diagnostic message instead of letting the exception propagate.

**`agent/agent_init.py`**:
- `_init_memory` binds `agent.emit_memory = MethodType(emit_memory, agent)` as a fail-open wrapper to `hindsight_retain` via `_memory_manager`. Re-bound at end of `init_agent` if missing.
- `_inject_context_engine_tools` calls `register_session_agent(agent.session_id, agent)` so `PluginContext.compressor` in `pre_llm_call` is a per-session weakref rather than a process global.

**`agent/agent_runtime_helpers.py`**:
- `effective_cache_ttl(ttl, *, model="", provider="")` — the `base_url=` parameter was removed. Qwen/Alibaba TTL clamping (`1h → 5m`) is now detected by provider/model name rather than base URL.

**`agent/moa_loop.py`**:
- Removed `last_aggregator_route` / `last_aggregator_attempt` prompt-cache clock attributes. `agent/prompt_cache_clock.py` was deleted (−650 lines vs upstream). Cache TTL no longer reads `base_url`.

**`agent/billion_context.py`** (new module vs upstream):
- `maybe_ccr_store()` — scores tool results with `keyword_overlap_score` and offloads oversized results to disk, inserting an `acp_retrieve` placeholder. Called from `tool_executor`.
- `crush_message_list()` — JSON-fold / log-select compression pass before the LLM summarisation step. Called from `context_compressor.py`.
- `should_skip_for_growth()` — delays auto-compress until context growth reaches `growth_floor`. Wired into `ContextCompressor._should_compress`.
- `classify_turn()` / `verbosity_directive()` — classify turn as `new_user_ask`, `mechanical_continuation`, or `error_continuation`. Used by billion-context plugin; not called from `conversation_loop.py`.

**New: `hermes_cli/plugins_context.py`** (+347 lines, not in `agent/` but new vs upstream):
- `PluginContext` gains: `compressor` (per-session weakref), `set_model_preference()`, `set_reasoning_mode()` / `get_reasoning_mode()`, `set_verbosity_mode()`, `set_adaptive_effort()` / `get_adaptive_effort()` / `apply_adaptive_effort_to_agent()`, `set_intent()`, `emit_episode()` → `agent.emit_memory`, `recall_episodes()`, `suggest_skill_update()`, `compact_tool_result()`.
- `set_compression_profile()` delegates to `ContextCompressor.set_compression_profile()`.

**New: `agent/compaction_events.py`**:
- `fire_pre_compress(session_id, turn_count, context_tokens, trigger_reason, agent=None)` — fires the `pre_compress` hook with these arguments.
- `fire_post_compaction(...)` — fires `post_compaction` hook with `agent=` forwarded.

---

## Memory architecture

The fork runs four distinct memory stores. They are not unified — each has its own write path and its own retrieval mechanism.

### The four stores

**1. Hindsight (live, per-turn)**

The primary long-term memory backend. `Hindsight` is an in-process `MemoryProvider` that runs every turn.

- API mode: connects to a local Hindsight server at `http://127.0.0.1:9177`.
- Configuration: `~/.hermes/hindsight/config.json` — `retain_every_n_turns=1`, `retain_async=true`, `auto_recall=true`, `recall_types=observation`, embeddings via `text-embedding-3-small`.
- **Write path**: on every turn, `HindsightMemoryProvider.sync_turn()` retains the conversation async. `hindsight_retain` tool is also available for explicit retention. LRU dedup on the last 20 writes prevents double-commit.
- **Read path**: `HindsightMemoryProvider.prefetch()` runs before each turn via the MemoryProvider interface (auto-recall). The model also has the `hindsight_recall` and `hindsight_reflect` tools.
- **Not** the same as the Graphiti write path. Hindsight writes are synchronous with the turn; Graphiti writes are batch cron jobs.

**2. MEMORY.md / USER.md (always-injected)**

Standing facts injected into every system prompt. 2200 character budget. Managed manually or by background scripts — not a retrieval store.

**3. L1 markdown facts (batch extraction, not per-turn)**

A pipeline that extracts important facts from session history into dated markdown files (`profiles/fork/memory-facts/YYYY-MM-DD.md`).

- `l1-extract.py` runs daily at 01:00 (direct, not sandboxed). Source code is a wrapper; actual logic runs from a restored `.pyc` (original source was zeroed). Extracts bullet-point facts from recent sessions.
- `l1-promote.py` runs at 01:30, promotes high-confidence extracted facts to a query tier.
- `l1-graphiti-write.py` runs every 250 minutes via `l1-graphiti-periodic` cron, writing promoted facts to Graphiti as episodes before truncating the staging file.
- `l1-graphiti-reconcile.py` retries failed Graphiti writes using `graphiti-state.db`.
- `l1-hindsight-promote.py` is currently a **stub**: it counts bullets, writes a log entry with `status: pending_gateway`, and exits 0 without calling `hindsight_retain`. The corresponding cron job (`l1-hindsight-promote`) is an **agent-prompt job** that reads `staging.md` and is supposed to call the tool directly — this is the actual promotion path, not the script.
- `l1-gmemory-consolidation.py` — G-Memory tier promotion: session → query (≥2 references) → insight (≥3).
- `l1-hypermem-promote.py` — promotes facts referenced by ≥3 shared entities to a hypergraph tier in Graphiti.
- `l1-tracegrant.py` — tracks which source types are authorised to write which memory namespaces.

**4. Graphiti (entity/relation graph, via MCP)**

A knowledge graph running at `http://127.0.0.1:8765/mcp/`. Fed by the L1 cron pipeline, not directly by the turn loop. The model can query it on-demand via `search_memory_facts`, `search_nodes`, and `add_memory` MCP tools.

### CLI-only recall tools (not in the agent loop)

- `unified-recall.py` — queries Hindsight REST + Graphiti MCP, fuses results with Reciprocal Rank Fusion into L0/L1/L2 tiers. CLI tool and standalone script; **not called during turns**.
- `dual-backend-memory-fuser.py` — fuses results from two arbitrary backends (relevance − redundancy). CLI/offline use only.
- `memory-query-router.py` — `route_query()`: `semantic` → Hindsight, `temporal` → session search then Graphiti, `relational` → Graphiti, `exact` → FTS5. Library; **not called from the loop**.

### Background memory maintenance scripts (~50 cron jobs)

The ~50 `memory-*.py` scripts in `hermes-scripts/` run as cron jobs and write results to `cache/*.json`. They are **not** the retrieval path. They maintain health metrics on the memory stores — when to evict old entries, whether the embedding space has drifted, whether duplicate facts should be merged, etc. See the cron job section for which ones run and when. None of these scripts are called during a conversation turn.

---

## Skill routing

There are two completely separate routing layers: one that fires every turn (the nudge plugin), and a large set of background scripts that maintain an offline bandit model.

### What runs during turns: `skill-routing-nudge` plugin

The only live routing change in the turn is the `skill-routing-nudge` plugin (`pre_llm_call` hook). It:

1. Scores the user message against `profiles/fork/scripts/skill-router-index.py` using BM25/TF-IDF (k1=1.5, b=0.75).
2. If the message is ≥8 words, the top score is ≥0.3, and either the top-2 gap is ≥0.1 or the top score is ≥0.5, injects a `[SKILL ROUTING HINT]` block into the user message naming the top-3 candidates.
3. Safety-related skills trigger at a lower threshold (0.2).
4. Fail-open: any failure is swallowed and the message is sent unmodified.

The index is a BM25 index over skill names and descriptions, rebuilt weekly. The nudge does not select the skill — it hints the model, which still makes the final call.

Additionally, `skill-access-logger` (`post_tool_call` hook) appends every `skill_view` call to `cache/skill-access.log` for offline analysis.

**`adaptive-retrieval` plugin** exists but is not in `plugins.enabled` — it is shadow/disabled.

**`skill_is_model_invocable()`** in `agent/prompt_builder.py` — a new mechanism: skills with `metadata.hermes.disable_model_invocation: true` in their frontmatter are excluded from the `<available_skills>` block in the system prompt, while still being accessible via `skill_view()`. This runs every turn.

### What runs in background: the bandit infrastructure

The ~60 `routing-*.py` and `skill-*.py` scripts in `hermes-scripts/` are background cron jobs. They maintain an offline bandit model (LinUCB, d=16 hashed features) whose weights live in `cache/routing-linucb*.json`. These weights are **not currently wired** into the live turn routing — the nudge plugin uses a plain BM25 index, not the bandit weights. The bandit infrastructure is research/forward-looking infrastructure that tracks routing quality offline.

Background jobs that run on a schedule include:
- `skill-router-index-rebuild` (Saturdays 05:00) and `skill-index-weekly-rebuild` (Sundays 03:00) — rebuild the BM25 index the nudge plugin reads
- `concept-lattice-rebuild` (daily 02:00) — semantic fallback index (used if BM25 top-2 gap < 0.12)
- `routing-linucb-0910` (daily 09:10) — updates the offline bandit state
- `routing-weight-updater` (daily 07:00) — FTRL weight file update
- `omni-skill-scan` (daily 01:00) — skill health scan

The ~30 other routing scripts (`routing-azuma-concentration.py`, `routing-pac-bayes-bound.py`, `routing-mobius-audit.py`, etc.) write alarm logs and cache JSONs. They are observability/research infrastructure, not the live routing path.

---

## Compaction pipeline

The fork modifies what happens at compress time and measures quality in background jobs. These are two separate things.

### What runs at compress time (every compaction)

Compression is triggered by `ContextCompressor.maybe_compress()` / `compress()`. The fork fires `fire_pre_compress()` before compression, which invokes the `pre_compress` hook on all registered plugins. What actually runs:

**`jev-compaction` plugin** — the most significant compaction modification. Monkeypatches the compressor's `_prune_old_tool_results()` method on the live instance:
- Scores tool results by recency/relevance density and divides them into thirds
- For the middle tier, makes up to 8 `logprob_classify` calls to score informativeness
- Uses exponential moving average thresholds to decide what to drop
- Configuration: `call_budget: 8`, `rr_lambda: 0.18`
- Fail-open: wraps the whole thing so any failure falls back to the original prune behaviour

**`compaction-gate` plugin** — observability only, does not block. Runs sentence extraction + zlib MDL + Jaccard similarity and appends a quality record to `cache/compaction-gate-log.jsonl`. If `turn_count ≤ 50`, it logs a skip notice. It does not reject or modify any compaction.

**`context-pressure-guard` plugin** — computes a rate-distortion lambda target and writes it to `cache/rd-lambda-target.json` as a signal for the advisor. Does not block.

**`billion-context` plugin** — most aggressive live modification. Runs `crush_message_list()` to fold tool results to JSON / log-select before the LLM summary step. Applies growth gating (`should_skip_for_growth()`) to defer auto-compress until context growth rate meets a minimum. Handles CCR placeholder offloading for oversized tool results.

**`pre-compact.sh` hook** — fires a loopback HTTP request to `http://127.0.0.1:49374` (ai-memory endpoint). Fail-open.

**`lambda-tuner` plugin** (in-repo, not profile) — fires `pre_compress` and sets the compression profile via `ctx.set_compression_profile()` → `ContextCompressor.set_compression_profile()`. Profile is currently always `fork_mixed` (`target_ratio=0.50`, `protected_last_n=20`, `max_tokens=32k`) regardless of session type.

### Offline evaluation pipeline (not at compress time)

A separate eval harness lives in `evals/compaction/` (`runner.py`, `policies.py`, `report.py`, `jev_arm.py`, `octeval/`). It compresses a saved transcript under different policies, asks recall questions about the dropped content, and uses an LLM to judge the answers. This is a manual CLI tool for evaluating compaction quality — not a cron job.

Background quality metrics that run on a cron schedule (not modifying the compressor):
- `score-compaction-rouge-nightly` (daily 04:50) — ROUGE-1 precision/recall between pre/post compaction. Alarms if precision < 0.3 (fabrication) or recall < 0.2 (coverage loss).
- `compaction-aep-typical-set` (hourly) — AEP typical-set coverage score
- `pre-compact-annotate` (every 30 minutes, `no_agent=True`) — rate-distortion advisor; writes JSON signal
- `compression-quality-monitor` (every 15 minutes) — monitors quality metrics

---

## Plugin inventory (what is actually enabled)

23 plugins are enabled in `config.yaml`. All are fail-open except where noted.

| Plugin | When it runs | What it actually does |
|---|---|---|
| `hindsight` | Every turn (MemoryProvider) | The primary long-term memory backend. Auto-retains every turn async via the Hindsight server. Auto-recalls before each turn. Tools: `hindsight_retain`, `hindsight_recall`, `hindsight_reflect`. |
| `jev-compaction` | `pre_compress` | Monkeypatches `_prune_old_tool_results()` to score tool results by recency/relevance. Up to 8 LLM classify calls per compaction. |
| `compaction-gate` | `pre_compress` | Observability: computes MDL/Jaccard compaction quality and logs it. Does not block anything. |
| `context-pressure-guard` | `pre_compress` | Computes rate-distortion lambda; writes advisory JSON. |
| `billion-context` | `pre_compress`, `transform_tool_result`, and others | Growth-gated compression; CCR offloading of oversized tool results; `crush_message_list()` before LLM summary. |
| `jev-turn-evaluator` | `post_llm_call` | Scores each LLM turn via a secondary model. Writes scores; gates policy updates until ≥20 turns scored with mean ≥3.5. |
| `governance-hard-block` | `register()` only | **Currently disabled.** `register()` logs `"DISABLED — gate not registered"`. The `pre_tool_call` stub always returns `None`. Does not block tool calls. |
| `cobra-guard` | `post_tool_call` | Tracks decision outcomes. Blocks repeated failures on the same decision type until manually reviewed. |
| `tool-auth-gate` | `post_tool_call` | Probabilistic spot-check: verifies auth tokens on a sampled subset of external service calls. |
| `tool-result-audit` | `post_tool_call` | Scans external tool results for prompt injection patterns before they enter the context. |
| `memory-ransac-gate` | `post_tool_call` | Checks new facts against existing memories before commit; rejects statistical outliers. |
| `decision-audit` | `post_tool_call` | Accumulates tool resolvability stats per session; writes to lifecycle.db every 10 calls. |
| `delegation-audit-hook` | `post_tool_call` | Records subagent delegation outcomes (success/failure, duration). |
| `deductive-verifier` | `post_llm_call` | Checks that the agent's stated conclusions follow from its stated premises. |
| `formal-verify-plugin` | `post_tool_call` | Enforces proof-state integrity on tool calls that claim to verify formal properties. |
| `compliance-score-hook` | `post_tool_call` | Scores tool outputs for compliance red flags and excessive length; logs to `cache/compliance-scores.jsonl`. |
| `post-tool-compliance` | `post_tool_call` | Independent compliance scorer; observation-only, never blocks. |
| `turn-behavior-logger` | `post_llm_call` | Logs per-turn behavioural metrics: length, tool count, model, compaction events. |
| `skill-routing-nudge` | `pre_llm_call` | Scores user message against BM25 skill index; injects `[SKILL ROUTING HINT]` into message if score threshold met. The only live routing change. |
| `skill-access-logger` | `post_tool_call` | Appends `skill_view` calls to `cache/skill-access.log` (≤100KB). |
| `skill-latency-logger` | `post_tool_call` | Records skill load/use latency. |
| `adaptive-retrieval` | `pre_tool_call` | **Shadow/disabled** — not in `plugins.enabled`. |
| `orca-status` | Lifecycle events | Reports lifecycle events to an external monitoring service. |
| `camofox` | Browser tool calls | Stealth browser backend with fingerprint evasion. |

**In-repo plugins** (tracked in git, not in the profile plugins directory):
- `hindsight` — the full `HindsightMemoryProvider` implementation (~81KB). Registers via `ctx.register_memory_provider()`.
- `lambda-tuner` — `TaskComplexityScorer`; fires `on_session_start`, `pre_llm_call`, `pre_compress`, `on_session_finalize`, `transform_tool_result`. Writes `cache/last-session-type.json`. Sets compression profile (currently always `fork_mixed`). Complexity lambdas: research 0.55, code 0.2, mixed/entropy-adaptive 0.4.

---

## Safety and approval changes

**`tools/threat_patterns.py`** — the approval pattern list was updated. Some patterns that were triggering false positives on legitimate operations were removed; patterns more specific to actual injection vectors were added. Exact set of added/removed regexes was not fully captured in this survey but the diff is ~150 lines.

**`tools/approval.py`** — session-keyed approval and pattern tracking added (`session_key`, `pattern_key`). `get_current_session_key` from `tools.approval_context` and detection helpers from `tools.approval_detection`. Core approval UI flow is unchanged; session scoping is the fork delta.

**`_governance_pre_check()` in `tool_guardrails.py`** — fire-and-forget subprocess call to `improvement_governance.py propose` on high-risk writes. 5-second timeout. Does not block execution. Fail-open.

**`check_skills_guard()` in `tool_guardrails.py`** — upstream blocked tool calls matching jailbreak-ish regex patterns (`ignore previous`, `you are now`, etc.). Fork replaced this with logging-only behaviour. Matching tool calls are logged but not blocked.

---

## Infrastructure and cron

**Cron scale**: 270 total jobs, 266 enabled. The majority are research/alarm scripts that write cache JSON and are not in any critical path. The ones that actually matter for agent operation:

| Job | Schedule | Role |
|---|---|---|
| `l1-extract-direct` | Daily 01:00 | Extract facts from recent sessions to markdown |
| `l1-promote-direct` | Daily 01:30 | Promote high-confidence extracted facts |
| `l1-graphiti-periodic` | Every 250 min | Write promoted facts to Graphiti graph |
| `l1-hindsight-promote` | Daily 09:00 | Agent-prompt job: retain staging.md facts via hindsight_retain |
| `skill-router-index-rebuild` | Sat 05:00 | Rebuild BM25 skill index the nudge plugin reads |
| `skill-index-weekly-rebuild` | Sun 03:00 | Unconditional skill index rebuild |
| `concept-lattice-rebuild` | Daily 02:00 | Semantic fallback index |
| `score-compaction-rouge-nightly` | Daily 04:50 | ROUGE-1/L compaction quality score |
| `compaction-aep-typical-set` | Hourly | AEP typical-set coverage score |
| `system-update` | Daily | OS/package/firmware updates with per-step timeouts |
| `graphiti-edge-health-check` | Every 6h | Graphiti graph health |
| `routing-linucb-0910` | Daily 09:10 | Offline bandit state update |

**Cron sandbox**: every cron script runs inside an openshell landlock sandbox defined by `profiles/fork/openshell-policy.yaml`. Read-only: `/usr`, hermes-scripts, profile scripts/lib. Read-write: tmp, `cache/`, `memory-facts/`, `logs/`. `HERMES_NO_SANDBOX=1` is blocked in the wrapper. The `cron-admission-control.py` script drops low-priority jobs under system load.

**System updates** (`daily-silverblue-update.sh`): per-step timeouts (package manager 20 min, firmware 5 min, each git repo 1 min). Flatpak metadata errors non-fatal. Login-trigger variant for headless-incompatible steps.

**Data versioning** (`dolt-merge.py` / `lifecycle-changelog.py`): Git-style three-way merge for `jobs.json` concurrent writes (field-level conflict detection, never silent last-write-wins). Append-only change history on `lifecycle.db` with `get_history()`, `time_travel()`, `blame()`.

**ROUGE scorer** (`score-compaction-rouge.py`): stdlib ROUGE-1 (unigrams) and ROUGE-L (longest common subsequence). Case-insensitive. Sampled LCS for inputs >10,000 tokens (2500 from each end, denominators adjusted to sampled lengths). Fabrication alarm if precision < 0.3; coverage alarm if recall < 0.2.

---

## What is not changed from upstream

- Core conversation loop iteration, tool dispatch flow, and stop conditions
- Installation procedure, model provider support, MCP server integration, messaging gateway, TUI/CLI interface
- The approval UI interaction flow (session scoping was added; prompting behaviour is unchanged)

For anything not covered here: **[hermes-agent.nousresearch.com/docs](https://hermes-agent.nousresearch.com/docs/)**

---

## Upstream merge policy

This fork rebases or merges from `NousResearch/hermes-agent` main periodically. Conflicts on core agent loop files resolve in favour of upstream; fork additions win on scripts, plugins, and config.

**Current base:** See `git log --oneline upstream/main..HEAD` for fork-only commits.

---

## Running this fork

```bash
hermes-fork          # start CLI on the fork profile
hermes-fork doctor   # health check
hermes-fork -z       # fork profile with zero context (fresh session)
```

The fork profile lives at `~/.hermes/profiles/fork/`. The binary at `~/.local/bin/hermes-fork` pins to the Py3.14 store interpreter (not `venv/bin/hermes` 3.11 — pydantic_core ABI mismatch).

---

## Original upstream README

---


Everything below is the original Hermes Agent README.

---

<p align="center">
  <img src="assets/banner.png" alt="Hermes Agent" width="100%">
</p>

# Hermes Agent ☤
<p align="center">
  <a href="https://hermes-agent.nousresearch.com/">Hermes Agent</a> | <a href="https://hermes-agent.nousresearch.com/">Hermes Desktop</a>
</p>
<p align="center">
  <a href="https://hermes-agent.nousresearch.com/docs/"><img src="https://img.shields.io/badge/Docs-hermes--agent.nousresearch.com-FFD700?style=for-the-badge" alt="Documentation"></a>
  <a href="https://discord.gg/NousResearch"><img src="https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white" alt="Discord"></a>
  <a href="https://github.com/NousResearch/hermes-agent/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License: MIT"></a>
  <a href="https://nousresearch.com"><img src="https://img.shields.io/badge/Built%20by-Nous%20Research-blueviolet?style=for-the-badge" alt="Built by Nous Research"></a>
  <a href="README.zh-CN.md"><img src="https://img.shields.io/badge/Lang-中文-red?style=for-the-badge" alt="中文"></a>
  <a href="README.ur-pk.md"><img src="https://img.shields.io/badge/Lang-اردو-green?style=for-the-badge" alt="اردو"></a>
  <a href="README.es.md"><img src="https://img.shields.io/badge/Lang-Español-orange?style=for-the-badge" alt="Español"></a>
</p>

**The self-improving AI agent built by [Nous Research](https://nousresearch.com).** It's the only agent with a built-in learning loop — it creates skills from experience, improves them during use, nudges itself to persist knowledge, searches its own past conversations, and builds a deepening model of who you are across sessions. Run it on a $5 VPS, a GPU cluster, or serverless infrastructure that costs nearly nothing when idle. It's not tied to your laptop — talk to it from Telegram while it works on a cloud VM.

Use any model you want — [Nous Portal](https://portal.nousresearch.com), OpenRouter, OpenAI, your own endpoint, and [many others](https://hermes-agent.nousresearch.com/docs/integrations/providers). Switch with `hermes model` — no code changes, no lock-in.

<table>
<tr><td><b>A real terminal interface</b></td><td>Full TUI with multiline editing, slash-command autocomplete, conversation history, interrupt-and-redirect, and streaming tool output.</td></tr>
<tr><td><b>Lives where you do</b></td><td>Telegram, Discord, Slack, WhatsApp, Signal, and CLI — all from a single gateway process. Voice memo transcription, cross-platform conversation continuity.</td></tr>
<tr><td><b>A closed learning loop</b></td><td>Agent-curated memory with periodic nudges. Autonomous skill creation after complex tasks. Skills self-improve during use. FTS5 session search with LLM summarization for cross-session recall. <a href="https://github.com/plastic-labs/honcho">Honcho</a> dialectic user modeling. Compatible with the <a href="https://agentskills.io">agentskills.io</a> open standard.</td></tr>
<tr><td><b>Scheduled automations</b></td><td>Built-in cron scheduler with delivery to any platform. Daily reports, nightly backups, weekly audits — all in natural language, running unattended.</td></tr>
<tr><td><b>Delegates and parallelizes</b></td><td>Spawn isolated subagents for parallel workstreams. In Desktop, choose their provider, model, and limits under Settings → Model → Subagents, then Apply the complete route. Write Python scripts that call tools via RPC, collapsing multi-step pipelines into zero-context-cost turns.</td></tr>
<tr><td><b>Runs anywhere, not just your laptop</b></td><td>Six built-in terminal backends — local, Docker, SSH, Modal, Daytona, and Vercel Sandbox — plus plugin backends such as Singularity/Apptainer. Daytona and Modal offer serverless persistence — your agent's environment hibernates when idle and wakes on demand, costing nearly nothing between sessions. Run it on a $5 VPS or a GPU cluster.</td></tr>
<tr><td><b>Research-ready</b></td><td>Batch trajectory generation, trajectory compression for training the next generation of tool-calling models.</td></tr>
</table>

---

## Quick Install

### Linux, macOS, WSL2

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

### Windows (native, PowerShell)

> **Heads up:** Native Windows runs Hermes without WSL — CLI, gateway, TUI, and tools all work natively. If you'd rather use WSL2, the Linux/macOS one-liner above works there too. Found a bug? Please [file issues](https://github.com/NousResearch/hermes-agent/issues).

Run this in PowerShell:

```powershell
iex (irm https://hermes-agent.nousresearch.com/install.ps1)
```

The source installer delegates Python 3.14, Node.js, npm, pnpm, ripgrep, FFmpeg,
and Python dependencies to PM. If Git is absent, it stages the verified Git
for Windows archive in Hermes' tool store. It does not replace your system Git.
See [installation methods](https://hermes-agent.nousresearch.com/docs/getting-started/installation)
for the separate MSIX/App Installer package and its update ownership.

> **Android / Termux:** A signed APT repository is available for aarch64 devices, with a `stable` channel (tagged releases) and a prerelease `canary` channel. The package includes Python, Node.js, and the TUI. Use the [Termux guide](https://hermes-agent.nousresearch.com/docs/getting-started/termux), not the desktop/server installer script.
>
> **Windows:** Native Windows is fully supported — the PowerShell one-liner above installs everything. If you'd rather use WSL2, the Linux command works there too. Native Windows install lives under `%LOCALAPPDATA%\hermes`; WSL2 installs under `~/.hermes` as on Linux.

After installation:

```bash
source ~/.bashrc    # reload shell (or: source ~/.zshrc)
hermes              # start chatting!
```

### Troubleshooting

#### Windows Defender or antivirus flags `uv.exe` as malware

If your antivirus (Bitdefender, Windows Defender, etc.) quarantines `uv.exe` from the Hermes `bin` folder (`%LOCALAPPDATA%\hermes\bin\uv.exe`), this is a **false positive**. The file is Astral's `uv` — the Rust Python package manager Hermes bundles to manage its Python environment. ML-based antivirus engines commonly flag unsigned Rust binaries that download and install packages.

**To verify your copy is authentic:**

```powershell
# Install GitHub CLI if needed
winget install --id GitHub.cli

# Login to GitHub
gh auth login

# Run verification
$uv = "$env:LOCALAPPDATA\hermes\bin\uv.exe"
$ver = (& $uv --version).Split(' ')[1]
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$zip = "$env:TEMP\uv.zip"
Invoke-WebRequest "https://github.com/astral-sh/uv/releases/download/$ver/uv-x86_64-pc-windows-msvc.zip" -OutFile $zip -UseBasicParsing
gh attestation verify $zip --repo astral-sh/uv
Expand-Archive $zip "$env:TEMP\uv_x" -Force
(Get-FileHash "$env:TEMP\uv_x\uv.exe").Hash -eq (Get-FileHash $uv).Hash
```

If attestation says "Verification succeeded" and the last line prints `True`, you're good.

**To whitelist Hermes:**
- **Windows Defender:** Run PowerShell as Admin → `Add-MpPreference -ExclusionPath "$env:LOCALAPPDATA\hermes\bin"`
- **Bitdefender:** Add an exception in the Bitdefender console (Protection > Antivirus > Settings > Manage Exceptions)
- Whitelist the **folder**, not the file hash — Hermes updates `uv` and the hash changes every version

For more context, see the upstream Astral reports: [astral-sh/uv#13553](https://github.com/astral-sh/uv/issues/13553), [astral-sh/uv#15011](https://github.com/astral-sh/uv/issues/15011), [astral-sh/uv#10079](https://github.com/astral-sh/uv/issues/10079).

---

## Getting Started

```bash
hermes              # Interactive CLI — start a conversation
hermes model        # Choose your LLM provider and model
hermes tools        # Configure which tools are enabled
hermes config set   # Set individual config values
hermes config get   # Print individual config values
hermes gateway      # Start the messaging gateway (Telegram, Discord, etc.)
hermes setup        # Run the full setup wizard (configures everything at once)
hermes update       # Update to the latest version
hermes doctor       # Diagnose any issues
```

📖 **[Full documentation →](https://hermes-agent.nousresearch.com/docs/)**

---

## Skip the API-key collection — Nous Portal

Hermes works with whatever provider you want — that's not changing. But if you'd rather not collect five separate API keys for the model, web search, image generation, TTS, and a cloud browser, **[Nous Portal](https://portal.nousresearch.com)** covers all of them under one subscription:

- **300+ models** — pick any of them with `/model <name>`
- **Tool Gateway** — web search, image generation (FAL), text-to-speech (OpenAI), cloud browser (Browser Use), all routed through your sub. No extra accounts.

One command from a fresh install:

```bash
hermes setup --portal
```

That logs you in via OAuth, sets Nous as your provider, and turns on the Tool Gateway. Check what's wired up any time with `hermes portal info`. Full details on the [Tool Gateway docs page](https://hermes-agent.nousresearch.com/docs/user-guide/features/tool-gateway).

You can still bring your own keys per-tool whenever you want — the gateway is per-backend, not all-or-nothing.

---

## CLI vs Messaging Quick Reference

Hermes has two entry points: start the terminal UI with `hermes`, or run the gateway and talk to it from Telegram, Discord, Slack, WhatsApp, Signal, or Email. Once you're in a conversation, many slash commands are shared across both interfaces.

| Action                         | CLI                                           | Messaging platforms                                                              |
| ------------------------------ | --------------------------------------------- | -------------------------------------------------------------------------------- |
| Start chatting                 | `hermes`                                      | Run `hermes gateway setup` + `hermes gateway start`, then send the bot a message |
| Start fresh conversation       | `/new` or `/reset`                            | `/new` or `/reset`                                                               |
| Change model                   | `/model [provider:model]`                     | `/model [provider:model]`                                                        |
| Set a personality              | `/personality [name]`                         | `/personality [name]`                                                            |
| Retry or undo the last turn    | `/retry`, `/undo`                             | `/retry`, `/undo`                                                                |
| Compress context / check usage | `/compress`, `/usage`, `/insights [--days N]` | `/compress`, `/usage`, `/insights [days]`                                        |
| Browse skills                  | `/skills` or `/<skill-name>`                  | `/<skill-name>`                                                                  |
| Interrupt current work         | `Ctrl+C` or send a new message                | `/stop` or send a new message                                                    |
| Platform-specific status       | `/platforms`                                  | `/status`, `/sethome`                                                            |

For the full command lists, see the [CLI guide](https://hermes-agent.nousresearch.com/docs/user-guide/cli) and the [Messaging Gateway guide](https://hermes-agent.nousresearch.com/docs/user-guide/messaging).

---

## Documentation

All documentation lives at **[hermes-agent.nousresearch.com/docs](https://hermes-agent.nousresearch.com/docs/)**:

| Section                                                                                             | What's Covered                                             |
| --------------------------------------------------------------------------------------------------- | ---------------------------------------------------------- |
| [Quickstart](https://hermes-agent.nousresearch.com/docs/getting-started/quickstart)                 | Install → setup → first conversation in 2 minutes          |
| [CLI Usage](https://hermes-agent.nousresearch.com/docs/user-guide/cli)                             | Commands, keybindings, personalities, sessions             |
| [Configuration](https://hermes-agent.nousresearch.com/docs/user-guide/configuration)               | Config file, providers, models, all options                |
| [Messaging Gateway](https://hermes-agent.nousresearch.com/docs/user-guide/messaging)               | Telegram, Discord, Slack, WhatsApp, Signal, Home Assistant |
| [Security](https://hermes-agent.nousresearch.com/docs/user-guide/security)                         | Command approval, DM pairing, container isolation          |
| [Tools & Toolsets](https://hermes-agent.nousresearch.com/docs/user-guide/features/tools)           | 40+ tools, toolset system, terminal backends               |
| [Skills System](https://hermes-agent.nousresearch.com/docs/user-guide/features/skills)             | Procedural memory, Skills Hub, creating skills             |
| [Memory](https://hermes-agent.nousresearch.com/docs/user-guide/features/memory)                    | Persistent memory, user profiles, best practices           |
| [MCP Integration](https://hermes-agent.nousresearch.com/docs/user-guide/features/mcp)              | Connect any MCP server for extended capabilities           |
| [Cron Scheduling](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron)             | Scheduled tasks with platform delivery                     |
| [Context Files](https://hermes-agent.nousresearch.com/docs/user-guide/features/context-files)      | Project context that shapes every conversation             |
| [Architecture](https://hermes-agent.nousresearch.com/docs/developer-guide/architecture)            | Project structure, agent loop, key classes                 |
| [Contributing](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing)            | Development setup, PR process, code style                  |
| [CLI Reference](https://hermes-agent.nousresearch.com/docs/reference/cli-commands)                 | All commands and flags                                     |
| [Environment Variables](https://hermes-agent.nousresearch.com/docs/reference/environment-variables)| Complete env var reference                                 |

---

## Migrating from OpenClaw or another agent

If you're coming from OpenClaw, Claude Code, Codex CLI or Cursor, Hermes can import your settings, memories and skills (and, for OpenClaw, API keys when you ask for them).

**During setup:** `hermes setup` asks whether to import from another agent, pre-selects the ones it finds (`~/.openclaw`, `~/.claude`, `~/.codex`, `~/.cursor`), installs the official `agent-importers` plugin and runs the import with a preview first.

**Anytime after install:**

```bash
hermes plugins install agent-importers          # once per profile
hermes import-agent openclaw                    # interactive migration (full preset)
hermes import-agent openclaw --dry-run          # preview what would be migrated
hermes import-agent openclaw --migrate-secrets  # also bring allowlisted API keys
hermes import-agent claude-code                 # or codex / cursor
```

What gets imported from OpenClaw:

- **SOUL.md** — persona file
- **Memories** — MEMORY.md and USER.md entries
- **Skills** — user-created skills → `~/.hermes/skills/openclaw-imports/`
- **Command allowlist** — approval patterns
- **Messaging settings** — platform configs, allowed users, working directory
- **API keys** — allowlisted secrets (Telegram, OpenRouter, OpenAI, Anthropic, ElevenLabs), only with `--migrate-secrets`
- **TTS assets** — workspace audio files
- **Workspace instructions** — AGENTS.md (with `--workspace-target`)

`hermes claw migrate` still works as the older spelling. See the [OpenClaw migration guide](https://hermes-agent.nousresearch.com/docs/guides/migrate-from-openclaw) and [Import from Other Agents](https://hermes-agent.nousresearch.com/docs/user-guide/import-from-other-agents).

---

## Contributing

We welcome contributions! See the [Contributing Guide](https://hermes-agent.nousresearch.com/docs/developer-guide/contributing) for development setup, code style, and PR process.

Start with the [PM developer workflow](website/docs/reference/package-management.md#developer-workflow)
for activation, daily use, dependency changes, and leaving the environment.
[Development Setup](CONTRIBUTING.md#development-setup) covers the separate test environment and verification commands.

---

## Community

- 💬 [Discord](https://discord.gg/NousResearch)
- 📚 [Skills Hub](https://agentskills.io)
- 🐛 [Issues](https://github.com/NousResearch/hermes-agent/issues)
- 🔌 [computer-use-linux](https://github.com/avifenesh/computer-use-linux) — Linux desktop-control MCP server for Hermes and other MCP hosts, with AT-SPI accessibility trees, Wayland/X11 input, screenshots, and compositor window targeting.
- 🔌 [HermesClaw](https://github.com/AaronWong1999/hermesclaw) — Community WeChat bridge: Run Hermes Agent and OpenClaw on the same WeChat account.

---

## License

MIT — see [LICENSE](LICENSE).

Built by [Nous Research](https://nousresearch.com).
