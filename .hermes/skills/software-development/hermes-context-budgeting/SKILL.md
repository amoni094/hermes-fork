---
version: 1.2.0
name: hermes-context-budgeting
triggers:
  - User asks what context window Hermes is actually using
  - User wants a smaller practical context cap than the model's advertised maximum
  - Tuning Hermes context-length or compression thresholds for a long session
  - Configuring compression.threshold or max_tokens in Hermes config to reduce cost
  - Choosing compression cadence by task type (research vs debug vs implement), not token count alone
description: >
  Use when: Tune Hermes context-length and compression settings with live verification, favoring token-efficient caps that still preserve usable agent headroom.
related_skills:
  - hermes-context-hygiene
  - hermes-session-hygiene
  - symbolic-context-offload
  - information-theory-for-agents
  - rr-compaction-scorer
  - hermes-semantic-skill-routing
---

# Hermes Context Budgeting

## When to use
- The user asks what context window Hermes is actually using.
- The user wants a smaller practical cap than the model's advertised maximum.
- You need to reduce token use or latency without making Hermes brittle.
- You see inconsistent numbers between docs, provider marketing, cached metadata, and Hermes runtime behavior.

If the problem is general session bloat or missed compression discipline rather than runtime cap tuning, load `hermes-context-hygiene` instead. Use this skill for measured context-cap and compression-setting decisions.

---

## CoT Scratchpad — External Reasoning Offload (arXiv:2608.21265, Aug 2026) <!-- rationale: 60% token cost reduction on long multi-step tasks at equivalent accuracy; offloads intermediate reasoning conclusions rather than keeping full chain in context -->

Empirical result: external scratchpad storing intermediate CoT steps achieves comparable
performance at 60% token cost vs. keeping the full chain-of-thought in active context.

The mechanism: intermediate reasoning conclusions are written to an external store (file or
Hindsight) after each reasoning phase. When a related sub-problem arises later, the agent
retrieves just the relevant conclusion — not the full reasoning chain that produced it.

**Hermes implementation for long multi-step tasks:**

```python
# At the end of each major reasoning phase, offload the conclusion:
hindsight_retain(
    content="[CoT-scratch] Phase: {phase_name}. Conclusion: {one_sentence_conclusion}",
    context="cot-scratchpad"
)

# When revisiting a related sub-problem, retrieve rather than re-reason:
result = hindsight_recall(query="CoT-scratch {related_phase_or_topic}")
# Use result.conclusion directly — don't re-derive from first principles
```

**Trigger condition:** Apply when a task has >5 major reasoning phases AND each phase
produces a conclusion that a later phase may depend on. The 60% saving only materialises
when the full chain would otherwise be kept in context across phases.

**Integration with existing LangChain compress_messages() pattern (already in this skill):**
CoT scratchpad is complementary — compress_messages() handles conversational history;
the scratchpad handles intermediate reasoning that would otherwise stay as assistant turns.
The two together can reduce context from >50K tokens to <15K on long reasoning tasks.

**When NOT to use:** Single-phase tasks, tasks where reasoning steps are independent (each
step doesn't need prior conclusions), or tasks already using execute_code for batch work.

Reference: arXiv:2608.21265, "Memory Augmentation Unlocks Efficient Chain-of-Thought Reasoning", Aug 2026.

## PRAXIS — Tacit Knowledge Surfacing at Code Interaction Points (arXiv:2608.19784, Sweep 20) <!-- why: business rules, interface contracts, and operational conventions are invisible to standard RAG retrieval but are the most common cause of correctness failures -->

PRAXIS extracts tacit domain knowledge (business rules, interface contracts, operational conventions) by simulating human development workflows. It maps this knowledge onto a code dependency graph and proactively surfaces it at the point of code interaction — not at session start and not on every turn.

Hermes implementation for context budgeting:
- Don't inject all skill context at session start; inject at the point of first relevant tool call
- For code tasks: map skill content to the files being edited; surface the relevant skill section when touching that file, not globally
- Tacit knowledge (implicit constraints, "never do X in this project", operational conventions from AGENTS.md) should be linked to the specific action that could violate them, not injected as a preamble
- ReCache principle (arXiv:2608.19662): KV blocks are per-resource; the skill context for `terminal` is different from context for `browser_navigate` — load skill sections relevant to the active tool, not all at once

## Memory Dosage Model — 3-Tier Injection (IBM Research ALTK-Evolve-HMM, Aug 2026, Sweep 20) <!-- why: wrong-guideline injection degrades accuracy; dosage tiering maximises signal per token -->

IBM Research finding: more memory injected is NOT always better. Wrong-guideline injection actively degrades accuracy by filling context with irrelevant constraints. Key metric: support count (how many task instances benefited from a guideline).

Dosage tiers:
- Full injection: only when ALL guidelines are task-relevant (rare)
- Selective retrieval: inject guidelines with support-count >= threshold for current task type
- Skip: for task types where no guideline has demonstrated support

Prompt caching makes full guideline injection affordable (+5% tokens) — but only inject what matches the task, not the whole library.

Hermes application:
1. Tag each skill section mentally by support-count: how often was this section decisive vs skipped?
2. Sections with near-zero support over 90 days → MDL candidate for removal
3. On skill loading under context pressure: prefer partial section load over full-skill body when the section is the only relevant part
4. For skills with many sections (>15), load L0 trigger + L1 overview first; load body on demand

## Harness vs Model Failure Distinction (Latent Space, Aug 22 2026, Sweep 20) <!-- why: model and harness failures require different remediation; conflating them wastes patch cycles -->

Every agent capability failure is either a model failure or a harness failure — distinguish before patching:
- Model failure: LLM produced wrong reasoning given correct context and tools
- Harness failure: tool contract, context flow, or safety envelope allowed the wrong action

Only harness failures are patchable via skills. Model failures require different routing (escalate to stronger model, add verification step, or rephrase the prompt).

First diagnostic question when a task fails: "Did the model reason correctly given what it was shown?" If yes → harness failure (fix the skill, tool contract, or context). If no → model failure (routing or prompt issue).

---

## L0/L1/L2 Tiered Context Loading (OpenViking, Aug 2026)

volcengine/OpenViking (29.6k stars) demonstrates that 3-tier tiered loading dramatically reduces tokens while increasing retrieval accuracy (LoCoMo benchmark: 33.4% → 82.9% accuracy; input tokens reduced 34–91%):

- **L0** (~100 tokens): 1-sentence abstract / trigger line — loaded for all candidate matches
- **L1** (~2k tokens): overview / summary section — loaded when L0 match is strong enough  
- **L2** (full content): loaded only when L1 confirms the content is needed for the current task

**Hermes skill loading analogy**: the skill index trigger line is L0; the `skills_list` description is L1; `skill_view(name)` is L2. Only load L2 when L0+L1 confirm the skill is genuinely needed. This is why `skills_list` exists separately from `skill_view` — respect the tier discipline, don't bulk-load all skill bodies speculatively.

**Control-plane tax** (arXiv:2608.15127): auxiliary LLM calls for routing, tool-schema loading, and context injection crowd out productive context. Minimize tool schema exposure via `enabled_toolsets` in delegate_task calls; avoid re-loading known skill bodies mid-task.

---

## Memory Policy Dominates Model Capability (AgingBench, Aug 2026)

AgingBench (arXiv:2605.26302): memory policy alone drove a **4.5× spread in agent half-life**. Upgrading Sonnet 4.6 → Opus 4.7 *dropped* PyTest pass rate by 15% in long-horizon sessions because the stronger model handled memory compression differently.

**Rule**: any model upgrade must be validated against the existing memory/compression policy on a real task sample before deployment. Do not assume a stronger model performs better on long-horizon tasks with an existing memory harness.

**Minimal Mode threshold** (Qiita/JP, Aug 2026): in production local agent loops, context overhead causes TPS degradation past ~20K tokens. Apply minimal context stripping at this boundary — strip non-essential skill body content, summarize accumulated tool results, use session_search for specific fact retrieval rather than keeping the full session in context.

---

## Stage Separability — Principled Ablation for Retrieval Stack Decisions (CyberLeninka/RU, 2026)

Before adding a retrieval stage to the Hermes stack (e.g. Graphiti KG on top of session_search), measure whether it actually separates relevant from non-relevant results:

- **Cohen's d** between relevant vs non-relevant score distributions: d > 0.5 = meaningful; d < 0.2 = redundant
- **Spearman correlation between stages**: high correlation = stage N is just rescaling stage N-1, not adding signal
- **Hermes retrieval stack**: session_search → Hindsight → Graphiti → web_extract. Only add a stage if Cohen's d > 0.5 vs the previous stage on your actual query distribution.

Reference: Grigorenko et al. 2026, CyberLeninka / Moscow Technical University of Communications.

---

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
   - To size a **single component** (skills block, tool schemas, a memory section) rather than the whole prompt, measure it directly from the on-disk artifact the builder produced — do **not** import hermes modules to do it (see pitfalls + `references/prompt-component-sizing.md`).
   - Note: as of 2026-07-03, the skills block render format changed: description cap is 40 chars (was 60), category descriptions capped at 80 chars, single-skill categories render inline, preamble condensed. The sizing recipe in `prompt-component-sizing.md` reflects this.
4. **Choose a practical cap, not the maximum.**
   - For token-efficient Hermes usage, prefer a cap that leaves comfortable working headroom after startup overhead rather than exposing the full provider maximum.
   - Treat **64k** as the floor for Hermes agent workflows, not the target.
   - A **128k** cap is a strong default when startup overhead is already around 20–25k tokens and the user wants a balance of cost and usability.
5. **Enable compression with an early enough trigger.**
   - If the goal is ongoing token discipline, turn on `compression.enabled: true`.
   - Live config is `compression.threshold: 0.35` and `compression.threshold_tokens: 120000`. Do not change compression.* settings mid-session.
   - Keep `abort_on_summary_failure: true` unless the user explicitly wants availability over summary correctness. **Note:** As of Aug 2026, this key does not exist in the live `compression` config block — it may have been renamed or removed. Verify against `~/.hermes/config.yaml` before setting.
6. **Apply with durable config changes.**
   - Set `model.context_length` to the chosen cap.
   - Set/verify compression values in `~/.hermes/config.yaml` via Hermes config commands.
7. **Verify after applying.**
   - Re-run the runtime probe and confirm `resolved_context_length` equals the configured override.
   - Re-check config to ensure the expected values were persisted.
8. **Warn about restart/session reset requirements.**
   - If Hermes is already running, tell the user a new session, `/reset`, or process restart may be needed for the new context budget to take effect cleanly.

## Context Decay Threshold (32K Soft Ceiling)

Model accuracy degrades significantly past ~32K tokens of active context, well before the advertised 1M+ limit. This is called context decay or context rot: long, messy contexts cause hallucinations and misguided answers. Context rot is responsible for ~80% of "my agent stopped working" failures.

Practical rule: treat 32K tokens as the soft ceiling for reliable context content. This means:
- System prompt + tools + injected memory should ideally leave ~32K+ of clean working space.
- If active in-context content (prior tool output, conversation history, injected docs) grows past ~32K tokens, trigger compression before adding more.
- When stuffing reference material into a subagent prompt, be brutal about trimming — a subagent given 50K of context is less reliable than one given 15K of well-filtered context.
- Prefer surgical reads (`read_file` with offset/limit, `search_files` for targeted extracts) over dumping full files into context.

The live compression floor is `threshold=0.35` / `threshold_tokens=120000`. Do not change compression.* settings mid-session. If the cap is set to 128K, compression fires well above the 32K decay zone. Pair with active hygiene discipline (`hermes-context-hygiene`) for long sessions.

## Task-type adaptive compression (not token count alone)

Runtime `compression.threshold` / `threshold_tokens` are **one global knob**. ACC-RAG (arXiv:2507.22931), ACON (arXiv:2510.00615), TokenPilot (arXiv:2606.17016), and the 35% safety cliff (arXiv:2608.01056) all show fixed-ratio compaction is the wrong unit: compress when **task relevance expires**, and protect different artifacts by task class.

Live profile floor (do not retune mid-session unless the user asks): `threshold=0.35`, `threshold_tokens=120000`, `protect_last_n=32`, `micro_compact_every_n_turns=4`, `proactive_prune_tokens=48000`, `intent_conditioned_offload=true`. Use the table below for **manual snip/gist + subagent tool-registry**, not per-turn `hermes config set`.

Classify the current work first. Then apply the matching row. If the class is mixed, use the stricter (earlier-snip) row for tool output and the stricter (later-compact) row for user/constraint text.

| Task class | Manual snip / gist trigger | Protect verbatim | Evict first | Leaf `enabled_toolsets` |
|---|---|---|---|---|
| Research / extract-heavy | After each **closed source** (facts extracted), not at 50% fill | URLs, paper IDs, dates, named claims | Raw `web_extract` / search bodies | `["web","file"]` |
| Debugging / retries | After each failed-attempt triplet (branch-and-prune) | Exact error text, last failing command | Retry chains, successful-then-superseded logs | `["terminal","file"]` |
| Implementation / patch | Only at a **phase boundary** (tests green or patch landed) | Diffs, paths, failing test names | Repo-wide search dumps, already-applied reads | `["terminal","file"]` |
| Multi-agent synthesis | After each leaf returns | Independent verdicts / deltas | Peer full transcripts (interaction tax) | `["file"]` (+ `delegation` only if nested) |
| Short Q&A / config check | Do **not** compact | User constraint | Nothing | No extra toolsets |

**Decision rules (stop at the first match):**

1. **Relevance before fill.** If the current subtask does not reference the previous subtask's tool output, snip that output now — even if tokens are well below `proactive_prune_tokens`. Irrelevant context degrades reasoning; it is not just waste. If task class is Implement: snip only at phase boundaries, not mid-phase even if unreferenced.
2. **Section drop, never uniform squeeze.** Never reduce a coherent section below ~35% of its length. Drop a whole stale section (after a 1-line gist + path) rather than compressing everything equally past the cliff.
3. **Toolformer call gate.** Skip a tool call when session_search / Hindsight / the current turn already answers it. Keep a call only if it would change the next action (self-supervised filter: if executing it cannot reduce uncertainty, do not call).
4. **Collapse multi-turn tool chains.** If ≥5 sequential calls have a known stable sequence and intermediates need no model judgment (read N files, aggregate, write), use one `execute_code` program instead of N LLM round-trips.
5. **Width before memory.** Tool-schema width dominates cost (arXiv:2608.02113). Do not load extra MCP/skill bodies "just in case." Map-guided harness (arXiv:2608.17433) and interaction tax (arXiv:2608.23541) are already in `autonomous-ai-agents` / `dispatching-parallel-agents` — follow those for leaves; this table is the parent-session counterpart.
6. **Do not retune the global knob mid-task.** Changing `compression.threshold` mid-session busts prefix cache. Adapt via snip/gist/toolset, not config writes.

## Default recommendation
When the user wants a "reasonable" cap for Hermes itself rather than maximum bragging rights:
- set `model.context_length: 128000`
- set `compression.enabled: true`
- match live knobs: `compression.threshold: 0.35`, `compression.threshold_tokens: 120000`
- Do not change compression.* settings mid-session.

Use this default unless live prompt-size evidence suggests either:
- startup overhead is so large that 128k would be cramped, or
- the user explicitly wants a more aggressive cap like 96k.

## Full compression key inventory (v0.20, Aug 2026)

The config.yaml only shows keys you've explicitly set; defaults are much richer. Key v0.20
additions missing from most configs:

```yaml
compression:
  threshold: 0.35              # Live profile. Do not retune mid-session.
  threshold_tokens: 120000     # Live absolute cap (fires at lower of ratio vs absolute).
                               # Prevents misfiring when switching models.
  target_ratio: 0.20           # Preserve 20% of threshold as tail.
  protect_last_n: 15           # 15 works well for CLI (default 20).
  min_tail_user_messages: 3    # Safer than the default of 1.

  # MICRO-COMPACTION (v0.20) — prevents single large compress pause
  micro_compact: true
  micro_compact_every_n_turns: 3
  micro_compact_defrag_threshold_tokens: 2000

  # PROACTIVE PRUNE (no LLM, fast) — strongly recommended for 200K models
  proactive_prune_tokens: 48000        # Prune old tool results when history > 48K.
  proactive_prune_min_result_chars: 8000
  proactive_prune_min_reclaim_tokens: 4096  # Don't commit unless saves 4K+ (prevents cache breaks).

  idle_compact_after_seconds: 1800    # NEW v0.20: compact on resume after 30min idle.
```

Agent loop keys worth checking:
```yaml
agent:
  max_turns: 500               # v0.20 raised default 90→500. Running 150 is artificially low.
  api_max_retries: 1           # Fail fast to fallback_providers. Default 3 is too slow.
  verify_on_stop: auto         # "auto" = on for CLI, off for gateway.
```

Tool loop guardrails (often missing entirely):
```yaml
tool_loop_guardrails:
  warnings_enabled: true
  hard_stop_enabled: false     # Keep false for interactive CLI; true for cron workers.
  warn_after:
    exact_failure: 2
    same_tool_failure: 3
    idempotent_no_progress: 2
```

Apply via: `hermes config set compression.threshold_tokens 120000` (etc.). Multi-level nested
keys for `auxiliary:` slots require individual `hermes config set` calls.

Constraint: compression model context window must >= main model context window. If summaries
fail silently, the compressor model is probably too small — switch to a larger one.

## Progressive Disclosure Skill Injection (Haystack 3.0, Aug 2026)

Current Hermes behavior: inject full skill YAML descriptions into every system prompt.
Improved pattern from Haystack 3.0 SkillToolset: 30-50% context token reduction.

Pattern:
1. First pass: inject only skill name + one-line trigger description (< 20 tokens/skill)
2. Model requests a specific skill by name → inject full SKILL.md body for that skill only
3. Skills the model never requests never inflate context

For Hermes CLI: the skills list in system prompt is already a compact index. The improvement
is to NOT inject any skill body text unless skill_view() is explicitly called for that skill
within the current turn. Any skill body pre-loaded "just in case" is wasted context.

Implementation note: this is already partially how Hermes works (skills are tools, not injected
bodies). Enforce more strictly: if a skill's body is loaded but never referenced in the turn's
reasoning, flag it as a candidate for lazy-load optimization.

## ToolResultOffload — Large Tool Results to Disk (Haystack 3.0)

When a tool result exceeds 2KB (web_extract, terminal output, file reads):
- Write full result to temp file under /tmp/hermes-tool-results/
- Inject into context: "[tool_result: TRUNCATED — full output at /tmp/hermes-tool-results/<hash>.txt]"
- Agent reads the reference if needed via read_file, but context stays lean by default
- Estimated gain: 20-40% context reduction on tool-heavy sessions
- Current Hermes behavior: full tool results always in context (sub-optimal for long sessions)

## Step Count + Token Watermark Tracking (Haystack 3.0 Agent State)

Hermes has a spend circuit breaker but no native step-count or token-watermark-based compaction.
Pattern from Haystack 3.0's agent `step_count` + `token_usage` built-in state:
- Track step_count per agent run (already implicit in tool call count per session)
- At 70% context fill: trigger proactive_prune (already configured at 48K tokens)
- At 90% context fill: force micro_compact before next tool call
- Cap tool-call loops: if same tool called >5 times with similar args in one task → warn user

## Needle 2 — KV Cache Sink for Tool Declarations (cactuscompute.com, Aug 11 2026)

Anthropic cache_control already pins system prompt. The novel improvement: pin TOOL SCHEMAS
separately as permanent cache sinks (not just system prompt). Implement via:
- Add a `cache_control: {"type": "ephemeral"}` block specifically to the tools array in API calls
- This mirrors the Anthropic system prompt caching but for tool definitions
- Zero additional token cost per turn; prevents tool schema eviction in deep conversations
- Source: Needle 2 inference engine; translates to Anthropic's existing cache_control API

## Stale Call Detector (session exits mid-turn)

When Hermes exits silently mid-session — no error, no crash, just drops — on a large-context
session, the likely culprit is the **stale call detector** firing at its 90-second default.

Default `HERMES_API_CALL_STALE_TIMEOUT=90s`. With a 200K-token context, a single Anthropic
streaming call regularly takes 120–300s. The detector treats silence as a hung process and
kills the session.

**Fix (one command):**
```
hermes config set providers.anthropic.stale_timeout_seconds 900
```

This raises the per-call stale threshold to 15 minutes for Anthropic only, without touching
request_timeout_seconds (which governs absolute max wait). The setting lives under the
top-level `providers:` key in config.yaml — a distinct block from `custom_providers`.

Example config.yaml shape after applying:
```yaml
providers:
  anthropic:
    stale_timeout_seconds: 900   # default was 90s — too aggressive for large context
```

`request_timeout_seconds` (absolute hard stop per request) defaults to 1800s — leave it
unless you want faster hard failures. Only raise `stale_timeout_seconds` to fix spurious exits.

Also pair with:
- `agent.api_max_retries: 5` — retries transient API failures before giving up
- `agent.session_stall_timeout: 1800` — session-level stall limit (separate from per-call)
- `fallback_providers` chain — if Anthropic is fully down, auto-falls back mid-session

**How to confirm it was the stale detector (diagnosis):**
```
tail -200 ~/.hermes/logs/errors.log | grep -iE "(stale|timeout|killed)"
tail -200 ~/.hermes/logs/agent.log  | grep -iE "(stale|exit|timeout)"
```
If both are mostly empty and the session just dropped, the stale detector is the most likely
culprit — it exits cleanly without writing a crash log.

## Pitfalls
- **Do not trust provider docs alone.** The public model page may advertise a larger window than the active Hermes provider path actually resolves to.
- **`--also-uncompacted` eval arm overflows the API.** The uncompacted control arm in `evals/compaction/runner.py` serializes the capped transcript with `char_cap=900_000` (~225K tokens), exceeding Anthropic's 200K context limit. Fix: change `char_cap` to `600_000` (~150K tokens) at the relevant `serialize_for_exam` call. The uncompacted recall ceiling (~96.7%) is already established in the Aug-15 SCORECARD — skip `--also-uncompacted` for policy-arm comparison runs unless specifically testing a new transcript.
- **tail_mode: lean is the upstream default (post-2026-09-11, main @ 036a20b3ca).** Eval policy arms or fork profiles that only change threshold/protect_last_n are already on the lean algorithm. Do not add `tail_mode: lean` to policy `ctor` dicts — it is redundant and misleads readers into thinking the default was something else. Only set `tail_mode` explicitly when testing a genuinely non-lean mode.
- **Do not trust raw `hermes config get model.context_length` alone.** Empty output only means there is no explicit override; Hermes may still resolve a provider/model-specific context length.
- **Do not preserve stale overreported cache values.** If code comments mention invalidation for stale high values, believe the runtime path, not historical summaries.
- **Silent session exits on large-context turns are usually the stale call detector, not a crash.** Default `HERMES_API_CALL_STALE_TIMEOUT=90s` kills requests that take >90s — common at 200K context. Fix: `hermes config set providers.anthropic.stale_timeout_seconds 900`. See "Stale Call Detector" section above for full details.
- **Do not leave compression disabled** when the user explicitly wants token minimization.
- **Do not choose 64k by reflex.** Hermes treats that as minimum viable working memory; it is often too tight once the system prompt and tools are loaded.
- **"Context length exceeded (N tokens). Cannot compress further." on a small prompt is a compressor failure, not a real overflow.** The N in that message is the token count *after* compression, not before. If N is tiny (e.g. 14–20 tokens), the compressor ran, produced a near-empty result, the re-attempt failed for the same underlying reason, and Hermes gave up. Root cause is almost always a broken `auxiliary.compression` provider (bad provider name, missing `custom_providers` entry, unreachable API). Fix: check and fix the compressor provider config, not the context size settings.
- **Do not import hermes modules to measure a prompt component.** Calling `build_skills_system_prompt()` / importing `agent.prompt_builder` can trigger config/gateway side effects and is often blocked in restricted sessions. Parse the read-only disk artifact instead (e.g. `~/.hermes/.skills_prompt_snapshot.json` for the skills block) and reconstruct the rendered string using the exact formatting from source. Recipe + measured baseline in `references/prompt-component-sizing.md`.
- **KVDiagnosis placement rule (arXiv:2608.09412):** 63.2% of long-context failures are caused by low/partial evidence coverage. Place Hindsight memories and injected skill chunks NEAR the current query, not buried mid-context. Repeat 1-2 most critical retrieved facts immediately before the question. Placement matters as much as retrieval quality.

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

## Prompt Caching: Strict Ordering for 60-90% Cost Reduction

Already partially covered in `references/compression-research-2026-08.md`. The key
ordering rule, consolidated here for direct use:

**Section order that maximises cache hits (Anthropic/OpenAI/Google):**
1. Tool definitions (largest static block — cache it first)
2. System prompt / AGENTS.md / persona (never changes per session)
3. Injected docs / skill bodies (static at session start; do not add mid-session)
4. Conversation history / compressed anchor (changes every turn — always LAST)
5. Current user query (always the very last token — never in any cached block)

**RACS stability-rank ordering (cache efficiency):** order context blocks
system_prompt → persona/skills → memories → conversation history (most to least stable)
to maximize prefix cache hit rate. A mutation in an earlier block invalidates every later
cache breakpoint. Pair with `~/.hermes/scripts/racs-prefix-tracker.py` to log unexpected
hash changes on the stable prefix.

**Diagnostic signal:** if cache hit rate is <60%, something dynamic (timestamp,
session ID, randomly-ordered list) is polluting the stable prefix. Find and remove it.
Any volatile token in the stable zone breaks the entire cache prefix from that point down.

**GenericAgent context info density (arXiv:2604.17091):** inject only a high-level
hierarchy view by default; expand to full detail only on explicit demand. Applied to
Hermes: skill descriptions in the prompt use the 57-char cap + category grouping
(already implemented). Extend this by collapsing skills not matching the current task
to name-only lines — this is the "hierarchical on-demand memory" principle. The
SkillReducer / progressive-disclosure pattern (39-48% body reduction, already in
`compression-research-2026-08.md`) is the direct implementation path.

## Headroom: Tool Output Compression Library (Tier-2, ~60-95% token reduction)

**Source:** github.com/headroom-ai/headroom (Apache 2.0, ~65k stars as of Aug 2026)

Tool outputs are the single biggest context consumers in Hermes agent loops — raw JSON,
HTML, terminal output, file contents. Headroom is a dedicated open-source library for
compressing these before they enter the context window.

**Key figures:**
- 60-70% token reduction on average tool outputs
- 90-95% on HTML/JSON-heavy outputs (search results, API responses)
- Negligible accuracy loss on standard agent benchmarks
- Already has an open GitHub issue on the Hermes repo for native integration (#39691)

**Install:**
```
pip install headroom-ai[all]
```

**Usage pattern (wrap any tool call result before injecting into context):**
```python
from headroom import compress

raw_output = web_extract(["https://..."])
compressed = compress(raw_output["results"][0]["content"], budget_tokens=2000)
# compressed is a shorter but semantically equivalent string
```

**When to apply manually (before native integration lands):**
- Any `web_extract` result before summarising or passing to a subagent
- Terminal output from long-running commands (logs, test output)
- File reads of large files when you need only a summary

**Relation to existing compression:** Headroom acts BEFORE context compaction — it
reduces tool output size at ingestion, so less content accumulates to begin with.
This is complementary to the `micro_compact` + `proactive_prune_tokens` pipeline
which compresses already-accumulated context. Apply both: Headroom at ingestion,
micro_compact at accumulation, idle_compact at session end.

## Information-Bottleneck Lambda Tuning (Sep 2026, from information-theory-for-agents)

RR scorer lambda IS the information bottleneck beta parameter (inverse relationship):
high lambda = aggressive compression (low beta, compress more); low lambda = protect
causal turns (high beta, preserve task-relevant information).

The default config ships lambda=0.2, tuned conservatively for coding sessions (protects causal turns). This is often too conservative for research-heavy sessions.
Switch lambda PER TASK CLASS before starting long sessions:

| Task class | Lambda | Rationale |
|---|---|---|
| Pure coding/implementation | 0.2 | Protect CAUSAL execute_code/patch turns (current default) |
| Mixed research + coding | 0.4 | Balanced — raise from default for mixed work |
| Pure research/extract-heavy | 0.7 | Aggressively evict web_extract, skill_view bodies |
| Post-task synthesis | 0.8+ | Gisting safe; task is done |

Switch command: `hermes config set compression.rr_scorer_lambda 0.7` (effective next session).
Do NOT retune mid-session (busts prefix cache). Set at session start when task class is known.

### rr_scorer_lambda is set at compressor init — plugins cannot mutate it live

`rr_scorer_lambda` is bound to `self.rr_scorer_lambda` in `ConversationCompressor.__init__()` (`agent/conversation_compression.py`). No plugin hook receives the compressor object, and there is no global agent singleton exposed to plugins. A `pre_llm_call` hook firing on the first turn CANNOT change the lambda that was already set when the session started.

The only way to apply a different lambda for a session is to write `config.yaml` BEFORE launching Hermes and start a new session. Mid-session config writes have no effect on compression. Do not attempt to patch the live compressor via sys.modules — no supported accessor exists.

### Autodetection pattern: plugin hint file + launch wrapper

To approximate per-session-type lambda tuning automatically, two cooperating pieces are installed:

1. **Plugin** (`~/.hermes/plugins/lambda-tuner/`) — registers `pre_llm_call`; on `is_first_turn=True`, classifies the user message via keyword regex (research vs code signals) and writes `~/.hermes/cache/last-session-type.txt`. Fail-open: any exception is swallowed so it never surfaces into the hook dispatch.
2. **Launch wrapper** (`~/.local/bin/hermes-session`) — reads the hint file at startup, patches `config.yaml` via env-var-injected Python (never bare shell vars inside a python -c string), then `exec hermes`. The lambda written takes effect for THIS launch because the compressor reads config at init.

The lag is intentional and unavoidable: the hint is written at end of session N and consumed at start of session N+1. This is the tightest loop possible given the compressor init constraint.

Example wrapper invocation modes:
- `hermes-session` — auto (reads hint file; falls back to cwd/git heuristic)
- `hermes-session research` — force research lambda (0.7)
- `hermes-session code` — force coding lambda (0.2)
- `hermes-session mixed` — force balanced lambda (0.4)

**Key implementation pitfalls:**
- Pass config path and lambda value to `python3 -c` via env vars (`CONFIG="$CONFIG" LAMBDA="$lambda" python3 -c "import os; ...os.environ['CONFIG']..."`) — never interpolate shell variables inside the Python string. Shell-var interpolation inside python -c breaks on paths with spaces and produces opaque failures.
- The key-absent fallback (appending `rr_scorer_lambda:` to the compression block) must use `re.MULTILINE` and strip the trailing newline before appending — a plain regex append silently no-ops when the compression block is the last block at EOF.
- Drop any backup-file mechanism from the wrapper — it creates false restore intent with no actual restore path. The config is intentionally mutable; document it as such.

## Reacquisition Cost (arXiv:2608.16370, Aug 2026)

Compression completion rate alone is a misleading metric. At 5x compression, task
completion is barely affected, but retrieval calls (session_search / re-reads of
dropped facts) can triple. Measure compaction quality by reacquisition rate, not
task pass rate.

Operational rule: after any context compact (micro or full), count how many
subsequent tool calls re-read or re-search something that was in the pre-compact
context. If >20% of next 10 tool calls are re-reads, the compaction was lossy.

Fact-preserving over drop: bind/extract named facts before pruning blobs. Prefer
naming a URL, path, or decision before dropping the surrounding blob.

## Related skills

- `information-theory-for-agents` - IT primer with formal grounding and Hermes-specific heuristics
- `rr-compaction-scorer` - RR-based Phase-1 demotion ordering (Vervaeke opponent-process two-signal scorer); enable via `compression.use_rr_scorer: true` after running spike script to validate pp-loss improvement on your session corpus


At each agent step, a small auxiliary model scores each prior context segment for
"still active" (causally relevant to the current plan) vs. droppable. Inactive segments
are evicted immediately — not summarised, just dropped. ~40% token reduction on
long-horizon tasks with no accuracy loss on standard benchmarks.

**Key distinction from micro_compact:** micro_compact summarises the full accumulated
history on a schedule. Active Context Compression decides per-step which specific segments
are still causally relevant and discards only the irrelevant ones. The two are complementary:
active compression runs intra-step; micro_compact runs inter-step.

**Hermes approximation (no auxiliary model needed):**
Before each LLM call in a long loop, scan prior tool outputs and ask:
"Is this result still needed to complete the current plan step?" If not — drop it from
the messages array before the call. Tool results from completed sub-tasks, intermediate
search results that were superseded, and error messages from paths that were abandoned
are all candidates for immediate eviction. This is a discipline, not a tool — apply it
manually in long agentic sessions.

**Trigger:** apply when accumulated tool outputs in the session exceed ~15K tokens.
At that point, each active-segment pass can recover 30-50% of that before the next call.

## Marginal Value Estimation: Stop Before Diminishing Returns (arXiv:2608.08389, Aug 2026)

Stage-aware pruning for long-horizon research agents. Key empirical result: early pruning
(pre-retrieval) yields the largest end-to-end savings. Late pruning (pre-synthesis) mainly
refines final context quality. Lightweight heuristics (length, recency, overlap) beat learned
models on the efficiency/quality tradeoff, reducing tokens by up to 73% with minimal quality loss.

Hermes apply:
1. web_search loops: after each retrieved doc, score marginal value = (new unique concepts /
   total concepts seen). If <0.1, stop searching — do not fetch the next result.
2. execute_code data collection: after each tool call, ask "does this change my answer?"
   If no new information in 2 consecutive calls, exit the loop.
3. delegate_task research tasks: cap at 5 web sources by default; only continue if the prior
   source contained at least 1 net-new fact relevant to the goal.
Rule: "If the next token costs more than it's worth, don't spend it."

## 3-Tier Auto-Offload Before Summarization (LangChain Deep Agents v0.7, Aug 2026)

Source: LangChain engineering blog, "Building Deep Agents" (Aug 7, 2026). Empirical: 65% base input token reduction (6K→2K/turn).

Three compression tiers applied in cascade order:
1. **Tier 1 (always-on):** Tool results >20K tokens → write to filesystem, inject 10-line preview + filepath pointer. Never compress in-context.
2. **Tier 2 (at 85% fill):** Completed write operations whose args are on disk → replace with filepath pointer only. Stale tool inputs evicted before summarization.
3. **Tier 3 (fill exhausted):** LLM generates structured summary: session intent + artifacts + next steps. Originals preserved to filesystem for needle recovery.

Additional findings that enabled the 65% reduction:
- Modern models (Claude 4+) don't need repeated instructions between system prompt and tool descriptions. Remove duplications.
- `TodoListMiddleware` (planning scaffolding) slightly *hurts* performance on capable models — make it opt-in, not default.
- `SummarizationMiddleware` trigger threshold should be configurable (current Hermes: `compression.threshold=0.35`, `proactive_prune_tokens=48000`).

**Hermes approximation:** Apply tier-1 discipline manually: any tool result >5K tokens should be written to a temp file with `write_file` and the filepath passed forward, not held in-context. Tier-2 applies naturally via `micro_compact`. Tier-3 is existing Hermes summarization.

## Marginal Value Estimation: Stop Researching When Evidence Plateaus (arXiv:2608.08389, Aug 2026)

"Not Worth Another Token" — framework for knowing when a research/retrieval agent has gathered enough evidence without over-spending.

Key insight: research agents continue searching long past the point of diminishing returns. Marginal value of the N+1th search result can be estimated without running it: if the last 3 retrievals added <5% new unique facts to the assembled context, the evidence has plateaued — stop and synthesize.

**Hermes implementation:**
- In web research loops, track unique-fact count across results. If 3 consecutive `web_extract` calls add <3 new named entities/claims to the assembled set, stop.
- For `delegate_task` research agents: include a `max_new_facts_threshold` in context; the agent self-terminates when evidence plateaus rather than exhausting its token budget on redundant results.
- This complements the tool-width optimization: fewer tools + early stopping = 40-60% total token reduction in research sessions.

## Prompt Minimization Audit (Anthropic "New Rules of Context Engineering", Jul 2026)

From Claude 5 generation context engineering guidance (claude.com/blog, Jul 24, 2026):

**Audit checklist for Hermes system prompt and tool descriptions:**
- Remove any instruction that duplicates a default Claude behavior (e.g. "be helpful", "think step by step")
- Remove any guard rail that Claude 4+ models handle natively without instruction
- Check for duplication between system prompt sections and tool description prose
- Remove legacy "don't do X" instructions added for older model versions

Estimated token recovery: 40-65% of per-turn base input tokens for well-audited prompts. The skill bodies (loaded on demand) and memory injections are separate — audit those independently.

**Deferred-loading tool registry:** Tools used in <10% of sessions should be excluded from the default tool manifest and loaded only when explicitly needed (e.g. `browser_*` tools when the user hasn't asked to browse). This is the highest single ROI action from the audit.

## Tool Schema Width is the Dominant Cost Driver (arXiv:2608.02113, Aug 2026)

Three orthogonal axes of context pressure were empirically separated:
- **Width:** number of tool schemas loaded simultaneously
- **Memory:** volume of memory injected per step
- **Delay:** planning horizon (how far ahead the agent reasons before emitting)

**Key finding:** Width is the dominant cost driver — more than memory injection or planning
depth. Loading all available tool schemas every turn even when only 2-3 tools will be used
wastes more tokens than any other single factor.

**Direct action for Hermes:** build a tool relevance router that selects which MCP tool
schemas to inject per request. For a memory-only task, inject only Hindsight + memory tools.
For a web research task, inject web_search + web_extract + browser. Never inject all schemas
by default. This is the highest-ROI optimization available for Hermes context budgets.

**Current state:** Hermes injects all tool schemas at session start. The compression-
research-2026-08.md already notes that tool definitions should be in the stable prefix for
caching — this is still true. The fix is: have *fewer* tools in that prefix per session
type, not just stable placement. Session-type routing (memory session vs. research session
vs. coding session) is the implementation path.

## LangGraph compress_messages() — Selective Middle-Turn Summarization Pattern (Aug 2026)

LangGraph v0.3+ added a `compress_messages()` helper and `TokenBudget` callback that apply
selective summarization to the middle turns of a conversation, preserving:
- The first system prompt (always)
- The last N exchanges (configurable, default 3)
- Summaries of everything in between

This is distinct from Hermes's existing `micro_compact` (which compresses the full accumulated
history on a schedule). `compress_messages()` is surgical — it targets only the middle portion.

**Hermes approximation (without LangGraph):**
When context is above proactive_prune threshold and you need to continue a long session:
1. Identify "closed subtasks" in the conversation — completed tool chains with no further reference
2. Write a 1-3 sentence summary of each closed subtask to Hindsight
3. Drop the original tool calls + results for those subtasks from the active context
4. Keep: system prompt, current task tool calls, last 3 user/assistant turns
This replicates compress_messages() behavior without the framework dependency.

Note: `TokenBudget` callback fires automatically when the agent's token count exceeds a
threshold — for Hermes this is the `proactive_prune_tokens=48000` config value.

## References
- `references/runtime-probes.md` — concise runtime facts and the cap-selection rationale from a live Hermes tuning session.
- `references/prompt-component-sizing.md` — read-only recipe (no hermes imports) for measuring one prompt component's char/token cost; skills-block formatting facts (40-char desc cap, 80-char category desc cap, single-skill inlining, `compact_categories` demotion), and measured baselines pre- and post-2026-07-03 optimization pass.
- `references/compaction-eval-harness.md` — how to run the `evals/compaction/` harness: adding policy arms, lineage reconstruction, question pre-seeding, and pitfalls (`--also-uncompacted` overflow, policy arm isolation, parallel run limits).

## Cloudflare Project Think: Named Context Blocks + Code-Mode Execution (Aug 2026)

**Named context blocks** (https://blog.cloudflare.com/project-think/): named, token-budgeted sections the model can self-update. Hermes approximation: MEMORY.md typed sections (`[factual]`, `[procedural]`) already function as named blocks. The missing piece is a visible budget indicator per section. Enforced indirectly by the 2200-char MEMORY.md cap. Self-update via `memory(action='replace', ...)`.

**Code-mode execution** — collapse N sequential tool calls into 1 program:
When a task requires 5+ predictable sequential tool calls (read 10 files, aggregate, write output), write a single Python script via `execute_code` instead of N LLM round-trips. One LLM call + one execution replaces N turns. This is a prompt discipline change — `execute_code` already exists. Trigger: tasks with a known, stable action sequence where intermediate outputs don't need model reasoning.

## Aug 2026: Online KV Cache Compaction for Agent Trajectories (arXiv:2608.00902)

Source: https://arxiv.org/abs/2608.00902 — "Practical Online KV Cache Compaction for LLM Agents: An Empirical Study" (Liu et al., Aug 2026)

LLM agents accumulate long tool-call trajectories making KV cache a major bottleneck.
Key empirical findings:
- **Immediate compaction hurts** — trimming context right at the tool-call boundary loses accuracy because the evicted tokens are still needed for the next step
- **Delayed compaction recovers the gap** — wait until the agent's *future* queries are available as a proxy signal, then compact using those queries to guide eviction
- **Token Eviction (TE) beats Attention Matching (AM)** under imperfect proxies (more robust)
- **80% KV cache reduction** with TE while preserving most accuracy; also improves throughput vs. no-compaction baseline

**Hermes implementation guidance:**
- Hermes's proactive_prune_tokens=48000 is the threshold for proactive context trimming — this is equivalent to "delayed compaction". Do not lower it further (makes trimming more frequent = more immediate = worse accuracy)
- When Hermes compacts mid-session, the trim happens AFTER receiving the next user message (which acts as the "future query proxy") — this is the correct ordering already
- The takeaway for skill design: do not front-load verbose tool results at the top of context; instead allow Hermes's proactive pruning to evict them naturally based on recency + future-query relevance
- structure tool results as: summary first, full content appended — so pruning evicts the full content while preserving the summary

## Aug 2026: Additional Context Research

### Copilot Production Data — Turn-Boundary Cache Prefetch (arXiv:2608.00101)
Source: "Agentic Coding in the Wild" — 3.2M users, 13M sessions, 761M LLM calls.
KV cache hit rate 90% within a turn, drops to 55% across turn boundaries. Context compaction
events drastically invalidate cache. User idle periods average minutes — predictable.
**Hermes:** Use turn-boundary as a cache-prefetch trigger. At each user turn start, proactively
load skill content that's likely needed (based on last tool used / task category) before the
LLM call, not after. Idle-time predictor: if session has been idle >2 minutes, warm up the
most recent skill's content before responding.

### Rate-Distortion Taxonomy for Compaction Decisions (arXiv:2607.08032)
Unifies KV-cache eviction, prompt pruning, and agent memory consolidation as a single
rate-distortion problem. Key failure pattern: **attention-magnitude-based keep/discard fails
because it discards information before the query is known and can't undo it**.
7-axis taxonomy for classifying what each compression step does.
**Hermes safeguard:** Never evict context tagged as "may be referenced by future tool output"
until after that output is processed. Practical implementation: before any proactive prune,
scan for pending tool calls — if any tool result is expected, delay eviction until it arrives.
This directly implements the paper's "query-agnostic failure" safeguard.

## Content-Type Compression Budgets

When compressing context, apply different token-preservation targets by content type:
- **Tool results** (most compressible): target 70-80% reduction — keep only the return value
  and error, drop scaffolding, stack traces from successful calls, progress noise
- **User messages**: target max 20% reduction — user intent must survive verbatim
- **Assistant reasoning**: target 40-60% — keep conclusions, drop intermediate steps

Apply budgets sequentially: compress tool results first, then system context, then assistant
turns. Compress user turns last and only if still over budget.

## PagedEviction — Block-Wise Eviction Pattern

Instead of evicting individual messages, evict in blocks:
1. Group messages into logical pages: one page = one tool-call round-trip (invoke + result)
2. Rank pages by recency x relevance (keep most recent + the first page = session context anchor)
3. Evict the lowest-ranked complete page, never a partial page
4. Before evicting any page, check: does it contain an unresolved reference (a file path,
   a session ID, a PR number) that a later message depends on? If yes, keep it.

PagedEviction preserves logical coherence better than line-level eviction and avoids the
"query-agnostic failure" where a truncated tool result leaves an orphaned reference.

## Reference files

- `references/compression-config-reference-2026-08.md` — Hermes Compression & Runtime Config — Full Reference (Aug 2026)

## Agent-Native Model Cost Horizon (Interconnects.ai, Aug 2026)

NVIDIA's agent-native model thesis predicts a cost-efficiency crossover where local inference becomes competitive with cloud API for skill-invocation-heavy workloads. Implications for context budgeting:

1. Design skills to minimize token footprint not just for immediate cost but for future portability — a skill that requires 5K tokens per invocation is expensive on Anthropic API now AND on any future local model.
2. Skill routing should be model-agnostic: route by task complexity and tool requirements, not by assumption of a specific model's capability. Skills that assume sonnet-4-6 context depths will break if the backend changes.
3. Begin tracking per-skill-invocation token cost now as a baseline metric — the crossover point can only be measured if you have historical data.

Concretely: when writing new skills, add a `# Token cost class: [low <500 | medium 500-2000 | high >2000]` annotation in the YAML front matter so skill-routing logic can factor cost into selection.

---

## Compaction Cliff — Knowledge Triage by Type (arXiv:2608.22752, Aug 2026) <!-- why: safety rules and episodic logs compacted at the same rate — safety rules need exact wording; after 5 compactions only 10% survive intact -->

Empirical result on 20 production configs: Claude /compact on Sonnet 4.6 preserves 53% of
safety rules after 1 compaction, 10% after 5. The Compaction Cliff is when rules become
unenforceable because their wording was lossy-compressed alongside episodic content.

Knowledge Triage fix — classify each memory/context element by type before compaction:

| Type | Retention policy | Operator |
|---|---|---|
| Safety rule (must be exact) | Pin verbatim; never summarise | TypeCompact: replicate in-scope rules across all partitions |
| Procedural step (ordered) | Compress to numbered list; keep verbs | TypeCompact: ordered → condensed ordered |
| Episodic log (freeform) | Summarise aggressively | TypeCompact: narrative → 1-sentence |
| Fact (entity+relation) | Compress to shortest form preserving entity names | TypeDecompose if too large to compact safely |
| Reference pointer (path/URL) | NEVER compress — keep exactly or evict entirely | TypeRetrieve: fetch from external storage; pin in-scope rules first |

**Hermes application:**
- MEMORY.md `[factual]` and `[procedural]` sections have different compaction budgets. `[factual]` entries are episodic (aggressive compress); `[procedural]` entries are ordered (preserve sequence, compress prose).
- Mandatory rules in MEMORY.md must be outside Hindsight (already enforced by hermes-memory-drift-audit.py). This is why: they survive Compaction Cliff only in a deterministic store.
- For context blocks passed to delegate_task: prefix safety constraints before task description — TypeCompact preserves in-scope rules pinned at the top of a partition.

**Diagnostic:** if a subagent ignores a safety constraint it was given, check whether the constraint survived compaction. Run: `grep -c "never\|must not\|always" /tmp/compacted_context.txt` before vs after compaction.

Reference: arXiv:2608.22752, "The Compaction Cliff in Long-Running AI Agent Memory", Aug 2026.

## Sweep 21: Context Compression Research

### SUPO — End-to-end RL Context Compression (ACL 2026, aclanthology.org/2026.acl-long.966/) ★ HIGH
Integrates summarization directly into RL training: compression strategy and task behavior
are co-optimized (not post-hoc). Result: agents scale beyond fixed context windows while
maintaining compact working context.

**Hermes implication:** the standard approach of adding a separate compression step after task
performance plateaus is suboptimal. Compression should be part of the operational loop, not a
cleanup afterthought.
- In long sessions: compress early (before 50% context fill) and frequently — don't wait for
  context pressure to force a lossy emergency compaction
- Treat the compacted summary as part of the task artifact, not just session bookkeeping

### ACE — Agentic Context Engineering (ICLR 2026) ★ HIGH
Treats agent contexts as evolving playbooks via generate→reflect→curate cycles.
Two failure modes to actively prevent:
- **Brevity bias**: compressed summaries lose domain-specific insight — the model prefers
  shorter output even when detail matters
- **Context collapse**: iterative rewriting erodes accumulated detail — later summaries are
  shallower than earlier ones even though they cover more events

**Hermes pattern:**
- When summarizing a long session, include a "what must survive compression" checklist:
  open decisions, unresolved tool results, file paths in use, outstanding tasks
- After compaction, verify: are all numbered todos still present? Any file path references intact?
- ACE achieved +10.6% on agent benchmarks vs baseline compression — structured incremental
  updates beat full rewrites

## Sweep 24: Turn-Boundary Gisting (HN, Aug 2026) ★ HIGH

**Gisting** compresses agent context at each turn boundary rather than at a fixed interval
or token threshold. Key insight: each completed tool call + result is a natural compression
unit — once a tool result is consumed and its conclusion is recorded in the working state,
the raw tool output can be replaced with a single-sentence gist.

**Mechanism:**
1. At the END of each assistant turn, scan the context for tool results that have been
   "acted on" (their conclusion appears in the assistant's reasoning or a subsequent write).
2. Replace the full tool output with a gist: `[result gist: <1 sentence conclusion>]`
3. Keep the original result if it contains reference data still in active use (file paths,
   numeric data being compared, error messages under active diagnosis).
4. Never gist the most recent turn (it's still active working memory).

**Hermes config relationship:** This is complementary to `micro_compact_every_n_turns`:
gisting is aggressive within a turn; micro_compact handles cross-turn accumulation.
Gisting should run BEFORE micro_compact to reduce the surface micro_compact has to process.

**Pitfall:** Don't gist tool results whose raw data is needed for verification (e.g., a
diff output before a commit, or a test result whose exact text will be compared to a spec).
Gisting is correct for: web_extract pages after key facts extracted, search results after
top hits selected, terminal output after exit code checked. <!-- why: premature gisting of verification artifacts causes false confidence in correct execution -->

**Source:** HN community thread "Gisting: compressing LLM agent context at turn boundaries"
(Aug 2026, 2 pts — early-signal finding, technique independently validated by SUPO/ACE principles above)


## Sweep 29 Additions (Aug 2026)

### Breadcrumb Memory: Compact = Map, Not the Memory (Zenn JP, Aug 2026) ★ HIGH

Compaction must never destroy the path back to the original evidence.
Schema for a Breadcrumb entry:
```json
{ "summary": "...", "source_range": "session:abc:msgs:120-145",
  "query_hints": ["keyword1", "keyword2"], "status": "active|superseded|conflicted" }
```
Pipeline: Retrieve → Decide → Recall (from source_range) → Extract (exact value from original).
Metric: **Source Hit@k** (did retrieval reach the evidence?) not "did we answer?".

**Never regenerate regex, SQL, paths, or exact values from a summary.**
If you compacted a fact that contained an exact regex pattern, the compacted form must
include the `source_range` so the original can be recalled on demand.

**Applied to:** focus_compress.py should emit `source_range` with every compressed segment.
Current gisting implementation stores the summary only — this is a gap to fix.

### ACM: Agentic Context Management — Five Primitives (HN/arXiv:2607.21503) ★ HIGH

Naive accumulation is quadratic; only validated compaction is linear-cost with fidelity.
Five primitives for context as a lifecycle (not RAG):
1. **Architect** — define memory topology before the session starts
2. **Ingest** — filter what enters (observer skip-list, tool-body exclusion)
3. **Scope** — bound what stays in context (SKILL.state obs ring buffer)
4. **Anticipate** — pre-load what will be needed (plan_from_memory)
5. **Compact & Consolidate** — validated compaction only (Breadcrumb + source_range)

Reports: 92% LongMemEval / 93.2% LoCoMo (vendor impl). Key: Ingest and Scope are the
biggest wins in practice — filtering at entry beats compressing after accumulation.

### Vector ROI Threshold: ~10k Documents (Habr RU, Aug 2026)

Embedding-based retrieval ROI starts at ~10k documents, not hundreds.
Below that: a catalog (1 line/memory, 21KB) + on-demand body files is more precise
than cosine similarity. The LLM does semantic matching over the catalog text directly.

**`description` in memory should be a search query, not a title.**
Current MEMORY.md entries use titles — consider reformatting as query-shaped descriptions
for better LLM-driven catalog matching at the hundreds scale.

## Technique Class: Gated Working-Memory Routing (Sweep 31)

### Gated-Memory Write Gate + Compact Retrieval (arXiv:2609.00237) ★ HIGH

Empirical study of 12 agentic benchmarks: unbounded working-memory writes accumulate noise
that degrades answer quality even when context fits comfortably. The fix is a write gate,
not compression: only write to working memory when both conditions hold:
1. **Relevance gate**: the candidate fact overlaps with at least one of the current task's
   active goals (cosine sim > 0.65 or keyword overlap ≥ 2 relevant terms). <!-- why: off-topic facts injected into working memory actively degrade reasoning per 2609.00237 -->
2. **Novelty gate**: the candidate fact is not already represented in working memory
   (deduplicate before writing, not just before retrieval).

**Retrieval discipline**: at each step boundary, retrieve top-3 most relevant working-memory
items — not the full dump. Empirical finding: top-3 outperforms full-dump by 11.2% on
multi-step tasks because irrelevant items crowd out the useful ones.

**Hermes implementation:**
```python
# Before calling hindsight_retain for working-memory-class facts:
# 1. Check relevance: does this fact serve the current goal?
# 2. Check novelty: has this been stored in this session already?
# 3. Only call hindsight_retain if both pass

# At step boundaries, retrieve selectively:
results = hindsight_recall(query=current_step_goal)  # top-k by default
# Use top-3 results only; do not inject the full memory bank
```

**Integration with dosage tiers (IBM ALTK-Evolve-HMM above):** The write gate enforces
not even creating support-count-0 entries — novelty + relevance checks at write time are
stronger than support-count pruning at read time.

**Reference**: arXiv:2609.00237, "Gated Memory Routing for Agentic Task Completion", Sep 2026.

## Information-Theoretic Compression Principles

### AEP / Typical Sequences for Token Compression (Cover-Thomas Ch 3)

**Theory:** The Asymptotic Equipartition Property (AEP) states that for large n, almost all sequences drawn from a source have probability approximately 2^(-nH(X)), where H(X) is the source entropy. The "typical set" of size ≈ 2^(nH(X)) contains nearly all the probability mass; sequences outside it are essentially noise.

**Hermes rules:**
- For long tool outputs, the information-carrying tokens form the typical set (≈ n·H(X) bits). Tokens outside the typical set add size but not information.
- Compress aggressively when output entropy is near-uniform: if H(X) ≈ log₂(vocab_size), the output is essentially random/noise — compress or discard.
- For structured outputs (code, JSON, deterministic text), H(X) is low → high redundancy → high compression ratio is safe.

**Citation:** Cover & Thomas — *Elements of Information Theory* (2nd ed.), Ch 3 (Asymptotic Equipartition Property).

### Rate-Distortion Theorem for Compression Depth (Cover-Thomas Ch 10)

**Theory:** The rate-distortion function R(D) gives the minimum number of bits needed to describe a source with distortion at most D. Operating below R(D) for a given distortion tolerance is information-theoretically impossible — no lossless compression below this rate exists.

**Hermes rules:**
- Compression quality vs token reduction follows the rate-distortion tradeoff: operate at the rate-distortion boundary by compressing to the minimum representation that preserves task-relevant information.
- Do NOT compress below R(D) for the task's distortion tolerance D (where D = acceptable information loss measured by downstream task quality).
- Practical proxy: if compression causes 2+ downstream decisions to change, the distortion exceeds tolerance — restore more context.

**Note:** The existing Rate-Distortion Taxonomy section (arXiv:2607.08032) covers compression architecture. This section covers the Cover-Thomas theorem governing the fundamental compression limit.

**Citation:** Cover & Thomas — *Elements of Information Theory* (2nd ed.), Ch 10 (Rate Distortion Theory).
