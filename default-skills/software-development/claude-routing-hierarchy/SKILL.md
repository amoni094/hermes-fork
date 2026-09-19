---
name: claude-routing-hierarchy
description: >-
  Use when choosing models or fallbacks for Hermes. Routes by task complexity,
  role, and fallback — not by tier label alone.
version: 2.0.0
author: Hermes Agent
license: MIT
last_validated: "2026-09-14"  # routing optimization pass: confidence gate, 2D routing table, caching verdict, Grok worker audit, commercial router ruling updated
# note: daily parent is Sonnet 4.6; Grok-4.6 is delegation.model (user 2026-08-29)
triggers:
  - "which model should I use"
  - "llm routing"
  - "model for this task"
  - "fallback chain"
  - "provider routing"
  - "grok daily driver"
  - "gpt-5.6-sol"
  - "adversarial review model"
related_skills:
  - hermes-agent
  - complexity-gated-planning
  - adversarial-review
  - fable-orchestrate
  - async-agent-nightshift-patterns
  - hermes-cron-and-agents
  - trajectory-risk-guardrail
  - autonomous-agent-loop-design
  - hermes-context-hygiene
supersedes:
  - grok-routing-hierarchy
metadata:
  hermes:
    tags: [routing, models, grok, openai, anthropic, cost]
    related_skills: [hermes-agent, complexity-gated-planning, adversarial-review]
---

# Hermes routing hierarchy

Live wiring snapshot 2026-08-30. Treat every model ID below as **current wiring**, not an immortal name — re-check catalogs before repeating availability or price claims. Route by **capability class**; IDs are the live binding.

## Live map (config levers)

Verified 2026-08-30. Re-inventory every ~2 weeks; provider status changes.

Rationale: Grok-as-parent correlated with session stalls/crashes. Compression 422 (`extra_forbidden` on `reasoning`) was a separate, confirmed stall source — moving `auxiliary.compression` OFF Mistral fixed it (2026-08-29: `mistral-small-latest` → `claude-haiku-4-5`@anthropic). If ever moved back to Mistral, `reasoning_effort` MUST stay unset.

| Role | Model | Provider | Evidence / Why |
|------|-------|----------|---------|
| Daily parent / orchestrator | `claude-sonnet-4-6` | `anthropic` | `model.default`. TerminalBench 46.2%, Tau-2 79.5%, 100% on 38-task real-work suite. Best instruction-following+tool-use combo for session parent. |
| Primary fallback | `grok-4.6` | `xai` | `fallback_providers` #1. Frontier-tier (AA Intelligence Index 61, same as Sol) at $2/$6 (60% cheaper than Sonnet). |
| Workers / leaves | `grok-4.6` | `xai` | `delegation.model`. Terminal-Bench 88.4%, tau3-Banking top-2, turn-efficient (53 vs 103 turns for Opus 5), 40s first-token latency (vs 184s Sonnet 5). Well-evidenced for parallel agentic workloads. |
| Long context (>160k, near 200k ceiling) | `claude-opus-4-8` | `anthropic` | Dedicated session. 1M context. SWE-bench 69.2% Pro / 88.6% Verified, strong at knowledge+reasoning. Use when accuracy matters more than cost at high context. For pure knowledge work, consider Grok 4.6 session at 60% lower cost. |
| Long-horizon knowledge work | `deepseek-v4-pro` | `deepseek` | Dedicated session. $0.435/$0.87 per 1M (off-peak). Naive cost: ~28x cheaper than Sonnet; realistic saving ~5-10x after accounting for Sonnet prompt caching. SWE-bench Verified 80.6%, LiveCodeBench 93.5%, 1M context. **ELIGIBLE when**: (1) knowledge/synthesis task, (2) tools limited to web_search/web_extract/read_file (no execute_code/terminal loops), (3) reasoning_content 400 bug verified absent. **CRITICAL: use non-think mode only** — thinking mode + tool calls → reasoning_content 400 bug (multi-turn). Avoid Beijing peak hours (09:00–12:00, 14:00–18:00 CST) — pricing doubles 2x. Grok 4.6 remains fallback for this slot when DeepSeek is unavailable/rate-limited. |
| Adversarial review | `gpt-5.6-sol` | `openai-api` | **Use `openai-api`, NOT `custom:openai`** (400 error). Sol leads Coding Agent Index (80 pts, SOTA), Agents' Last Exam 53.6. Cross-family critique prevents sycophancy. Grok 4.6 (not Sol) leads Terminal-Bench v2.1. |
| Light adversarial check | `gpt-5.6-luna` | `openai-api` | ~$0.80-1/$4-6 (after July 2026 cut; re-verify). Terminal-Bench 84-87%. Low-stakes cross-family sanity check before paying Sol rates. Use for: draft review, simple contradiction check, non-critical output validation. |
| Compression / context | `claude-haiku-4-5` | `anthropic` | `auxiliary.compression`. Moved off Mistral 2026-08-29 (422 stall). Do not optimize away — failed compression turn costs more than $0.85/M savings. |
| Mechanical aux (high-volume) | `mistral-small-latest` | `mistral` | `auxiliary.*` (titles, triage, curator). $0.15/$0.60 vs Haiku $1/$5. 159 tok/s vs 88. 90%+ quality parity at 90%+ lower cost for classification/extraction. No `reasoning_effort`. |
| Vision | `claude-haiku-4-5` | `anthropic` | `auxiliary.vision` |
| Math / reasoning subtasks | `magistral-small-latest` | `mistral` | Dedicated session. Outperforms Mistral Large on MATH+GPQA via RL (arXiv:2506.10910). 10x faster than non-reasoning path. Cheaper than Grok delegation for single-session reasoning. |
| Coding scaffolding aid | `devstral-latest` | `mistral` | Sub-role within Sonnet-orchestrated loop for bulk/cheap edits. SWE-bench Verified 72.2% ($0.40/$2). Cost-efficient but not frontier-class — prefer Grok workers or Sonnet session for correctness-critical coding. |
| Parent outage fallback | `grok-4.6` → `mistral-large-latest` → `gemma-4-31B-it` | xai → mistral → sambanova | Continuity only. Cerebras removed (402). SambaNova gemma-4-31B-it live last-resort. |

Serving-efficiency routing signals (estudy LLM serving architecture, 2026): when selecting model providers for inference-heavy delegation tasks, factor serving metadata beyond cost/capability. Relevant signals: (1) dynamic batching capacity — providers running vLLM or SGLang with continuous batching have lower p99 latency under concurrent load; (2) quantization tier — INT4/FP8-quantized models at same advertised quality may return faster but degrade on precision-sensitive tasks; (3) TTFT vs throughput tradeoff — for interactive agent loops prefer low TTFT (Grok 4.6: 40s TTFT vs Sonnet 5: 184s). When a provider is known to use TensorRT or Triton with dynamic batching (e.g. Anthropic's Claude API), treat sustained throughput as reliable. Avoid providers where serving tier is unknown for latency-critical parallel delegation workloads.

Mid-tool reasoning (arXiv:2601.17234 or similar): models trained with mid-tool chain-of-thought outperform post-hoc reasoning on tool-heavy tasks. Prefer models with known mid-tool training when available (currently no Hermes-accessible model is documented as mid-tool trained; revisit when model cards improve).

Keep `model.context_length: 200000` even though Grok lists 500k — that is the Grok long-context price cliff.

## Critical: gpt-5.6-sol provider fix (2026-08-30)

`custom:openai` with `api_mode: chat_completions` sends tool schemas to `/v1/chat/completions` → HTTP 400 ("Function tools with reasoning_effort are not supported for gpt-5.6-sol in /v1/chat/completions. To use function tools, use /v1/responses") → fallback to grok-4.6. The model never actually ran.

Fix: use `--provider openai-api` or `provider: openai-api` in config. The `openai-api` first-class provider auto-upgrades GPT-5.x to the Responses API transport (confirmed in Hermes docs and verified working 2026-08-30).

The `custom_providers` openai entry with `chat_completions` remains useful for GPT-4.1/gpt-4.1-mini which do NOT auto-upgrade and need chat_completions. Do not remove it. Just don't use it for GPT-5.x.

For adversarial sessions: `hermes chat -m gpt-5.6-sol --provider openai-api -q "..."` (not `--provider custom:openai`).

## What Hermes cannot do

- `delegate_task` has **no per-call model**. `delegation.model` is one value for every child (`leaf` and `orchestrator`). Role only changes tools.
- There is **no runtime complexity router**. `model_routing` in config is dead (Hermes key is `smart_model_routing`, disabled). Policy lives in this skill.
- Do not `/model`-switch mid-task. Pick the parent model at session start.
- Cron jobs do **not** inherit `fallback_providers`. Pin `--model`/`--provider` on LLM crons. Memory/promote jobs stay on Anthropic unless the user says otherwise.
- `custom:openai` is **not** in the parent fallback chain. Explicit `--provider custom:openai` only.
- `openai-api` (first-class) is also not in parent fallback chain — explicit only. But it correctly handles GPT-5.x via Responses API.
- Claude Sonnet 5 / Opus 5 / Fable 5: **exception-only**, explicit user ask.

## Evidence-based task-dimension routing matrix (updated 2026-08-30)

All routing decisions below are grounded in verified benchmarks. Sources: Artificial Analysis Intelligence Index, Terminal-Bench v2.1, AA-Briefcase, SWE-bench Verified, tau3-Banking, arXiv:2603.04445, arXiv:2601.07206.

### Task dimension 1: Orchestration / long coherent reasoning
Best: **parent/orchestrator class** (live wiring: `claude-sonnet-4-6`). Do not name a successor as default Best — 5.x remains exception-only unless the user asks.
Evidence: Sonnet 4.6 TerminalBench 46.2%, Tau-2 79.5%, 100% pass rate on 38-task real-work benchmark (Ian Paterson 2026). A newer Anthropic orchestrator may win CLI-heavy benches; that is not an auto-upgrade.
Call: Keep the live parent. Escalate the orchestrator class only on explicit user ask or a classified stall (see stall mapping), not because a newer ID exists.

### Task dimension 2: Agentic parallel workloads (delegate_task workers)
Best: **worker class** (live: `grok-4.6`)
Evidence: Grok 4.6 Terminal-Bench v2.1 88.4%, tau3-Banking 50.7% (top 2), AA-Briefcase Elo 1577 at $2/$6 (60%+ cheaper than Opus 5, same frontier-tier scores as Sol). Turn-efficient: 53 turns vs 103 for Opus 5 on long-horizon tasks. First-token latency 40s vs 184s Sonnet 5 — critical for interactive agent loops.
Call: Grok 4.6 workers are well-evidenced. The session stalling correlated with Grok-as-parent (not Grok-as-worker); the exact root cause was not fully isolated but the fix (Sonnet parent + Grok workers) resolved it. Workers remain the correct slot for Grok.

### Task dimension 3: Agentic coding (SWE-bench-class tasks)
Best: **parent/orchestrator class** for correctness-critical coding (live: `claude-sonnet-4-6`). Scaffolding class = cheap code-edit model (live: `devstral-latest`). Worker class for parallel chunks (live: `grok-4.6`).
Evidence: snapshot 2026-08-30 — parent SWE-bench Verified ~79.6%; scaffolding 72.2% at much lower cost. Newer Anthropic IDs are exception-only (user must ask), not an automatic Best.
Call: Serious agentic coding stays on the live parent. Use scaffolding only for bulk/cheap edits inside a parent-orchestrated loop.

### Task dimension 4: Adversarial review / independent critique
Best: **cross-family adversarial class** via the first-class OpenAI Responses transport (live: `gpt-5.6-sol` / `openai-api`). Light class (live: `gpt-5.6-luna`) for low-stakes checks. NEVER `custom:openai` (HTTP 400 → silent worker fallback).
Evidence: snapshot 2026-08-30 — Sol Coding Agent Index 80; worker class (not Sol) leads Terminal-Bench v2.1 at 'high' compute. Sol's strength is professional coding workflows and adversarial depth, not raw tool-use throughput. At 'ultra' compute Sol may lead Terminal-Bench; do not collapse 'high' vs 'ultra' into one ranking.
Call: Cross-family adversarial session for merge/deploy critique. Light class first when stakes are low. Re-verify prices before quoting.

### Task dimension 5: Long context (>160k working set, approaching 200k config ceiling)
Best: **long-context/accuracy class** (live: `claude-opus-4-8`). Re-verify prices before quoting.
Evidence: Opus 4.8 SWE-bench Verified 88.6% / Pro 69.2% (morphllm.com 2026), better at pure reasoning/knowledge work. Sonnet 5 wins Terminal-Bench 2.1 but Opus 4.8 wins agentic coding at high context. Long-horizon knowledge work (AA-Briefcase) is Grok's strong suit at 4x lower cost.
Call: Opus 4.8 for RAG-over-large-corpus or sessions with >160k working-set tokens where coding/reasoning accuracy matters. For long-horizon knowledge work consider dedicated Grok 4.6 session instead — same Elo at 60% lower cost.

### Task dimension 6: Classification / extraction / triage (high-volume aux)
Best: **mechanical-aux class** for volume (live: `mistral-small-latest`); **nuance/safety class** (live: `claude-haiku-4-5`)
Evidence: Mistral Small 4 costs $0.15/$0.60 vs Haiku 4.5 at $1.00/$5.00 = 6-8x cheaper. Speed: 159 tokens/sec vs 88. For classification/extraction 90%+ quality parity at 90%+ lower cost (APIpulse 2026). Haiku justified for: safety-critical classification, fine-grained output formats, tasks requiring nuanced reasoning.
Call: Keep Mistral Small on triage/title/curator aux. Consider whether any current Haiku aux tasks are actually classification-tier and should move to Mistral Small.

### Task dimension 7: Compression / context window management
Best: **compression class** (live: `claude-haiku-4-5`)
Evidence: Compression is fundamentally context understanding at large scale. Mistral Small 422 (extra_forbidden on reasoning) caused compression loop stalls. Haiku at $1/$5 handles large context summarization reliably. This is the right call — do not optimize away from Haiku on compression purely on cost; a failed compression turn costs far more than the $0.85/M price difference.
Call: Keep Haiku on compression. Do not move back to Mistral.

### Task dimension 8: Math / reasoning subtasks
Best: **cheap-reasoning class** (live: `magistral-small-latest`) for easy/medium math and GPQA-class single-session work. Hard/olympiad-class → worker class or long-context/accuracy class, not cheap-reasoning.
Evidence: Magistral (arXiv:2506.10910) outperforms Mistral Large on MATH and GPQA via RL. Do not treat that as a blanket "all math → Magistral" rule — it contradicts the hard-reasoning path in the benchmark notes.
Call: Cheap-reasoning session when the subtask fits in one session and is not olympiad-class. Do not spend a worker turn on easy/medium isolated math.

Formal proof / logic / type theory tasks (Huth-Ryan logic, Thompson type theory, Harrison HOL, Sipser automata): same cheap-reasoning-class rule. Easy/medium formal derivations and proof-checking -> magistral-small-latest. Hard proof search or interactive theorem proving -> worker class or long-context/accuracy class, not cheap-reasoning.

### Task dimension 9: Complex knowledge work / research synthesis
Best: **worker class dedicated session** for long-horizon synthesis (live: `grok-4.6`); **parent/orchestrator class** when the work is still orchestration (live: `claude-sonnet-4-6`)
Evidence: Grok 4.6 AA-Briefcase Elo 1577, tau3-Banking 50.7%, cost $0.84/task vs Opus 5 ~$4-8/task for same output quality. For long research synthesis where multiple tool calls accumulate context: Grok's turn-efficiency (4x less tokens to same answer) makes it cheaper than Opus 5 even at comparable intelligence.
Call: For long-horizon research synthesis tasks, a dedicated Grok 4.6 session is price-optimal. Sonnet 4.6 parent is better for orchestration; Grok 4.6 dedicated is better for raw knowledge work.

## Decision procedure

Stay on the session model unless a row below is true. Escalate the **decision/synthesis** step, never the whole pipeline (arXiv:2608.09155).

1. Single coherent decision over shared state (one repo, one narrative) → parent/orchestrator class stays (live: `claude-sonnet-4-6`); no `delegate_task`.
2. Mechanical / high-volume / extract / title / triage → mechanical-aux class via `auxiliary.*` (triage_specifier, title_generation, curator, web_extract) (live: `mistral-small-latest`). Compression class on `auxiliary.compression` (live: `claude-haiku-4-5`). Do not spend worker or parent/orchestrator turns on these.
3. Independent parallel chunks (research fan-out, unrelated file audits) → `delegate_task` leaves on worker class (live: `grok-4.6`). Parent/orchestrator synthesizes.
4. Agentic coding: parent/orchestrator class (live: `claude-sonnet-4-6`). Scaffolding class (live: `devstral-latest`) is cost-efficient (72.2% SWE-bench Verified, $0.40/$2) but not frontier-class — bulk/cheap edits **inside a parent-orchestrated loop only**; prefer worker class or parent/orchestrator session for correctness-critical coding.
5. Working context >160k (approaching 200k config ceiling) → **new session** long-context/accuracy class (live: `claude-opus-4-8`). For pure knowledge work at high context, consider a worker-class dedicated session (live: `grok-4.6`) instead (4x cheaper, same Elo tier). Do not raise `model.context_length` to 500000 — Grok's advertised 500k window is not the Hermes config setting (long-context price cliff).
6. Adversarial review / independent critique → **new session** cross-family adversarial class (live: `gpt-5.6-sol`) via `openai-api`. NEVER via `custom:openai` (HTTP 400). For low-stakes cross-family checks, use light adversarial class first (live: `gpt-5.6-luna`) (4-5x cheaper than Sol, Terminal-Bench 84-87%). Escalate to adversarial class when: correctness is critical, output is adversarial target for a merge/deploy, or stakes require frontier-quality critique.
7. Math/reasoning subtask in isolation → cheap-reasoning class (live: `magistral-small-latest`) for easy/medium only. Hard/olympiad-class → worker or long-context/accuracy class, not cheap-reasoning.
8. Long-horizon knowledge/research synthesis → **dedicated deepseek-v4-pro session** (primary, $0.03/task).
   Non-think mode only. Fallback to dedicated Grok 4.6 session if DeepSeek unavailable.
   Command: `hermes chat -m deepseek-v4-pro --provider deepseek -q "..."`
9. Vague "this seems hard" is NOT an escalation trigger (UCCI). Ask user or stay on parent/orchestrator class.

```
# pin deepseek for long-horizon knowledge/research (28x cheaper than Grok dedicated)
# ALWAYS non-think mode (thinking=off or omit param) -- tool calls in think mode = 400
hermes chat -m deepseek-v4-pro --provider deepseek -q "..."

# fallback if deepseek unavailable
hermes chat -m grok-4.6 --provider xai -q "..."

# long context
hermes chat -m claude-opus-4-8 --provider anthropic -q "..."

# adversarial — MUST use openai-api (not custom:openai) to get Responses API for tools
hermes chat -m gpt-5.6-sol --provider openai-api -q "..."

# scaffolding class — bulk/cheap edits inside a parent-orchestrated loop, not a dedicated coding parent
hermes chat -m devstral-latest --provider mistral -q "..."

# mistral reasoning (lighter than Grok delegation for single reasoning tasks)
hermes chat -m magistral-small-latest --provider mistral -q "..."
```

## Harness-typed routing (OMH B7)

Derived from oh-my-hermes harness catalog. Maps OMH harness type to Hermes model routing:

  coding-handling  -> sonnet-parent + grok-workers (delegate_task). Scaffolding sub-role: devstral inside parent loop.
  research         -> deepseek-v4-pro dedicated session (eligible: synthesis-only, web tools only, non-think) or dedicated grok-4.6 session.
  qa / reviewer    -> gpt-5.6-sol adversarial session via openai-api. Light: gpt-5.6-luna first.
  planning         -> sonnet-parent (sequential shared state; no delegate_task for planning steps).
  operator/ops     -> sonnet-parent orchestrating grok workers for parallel data collection.
  memory           -> no model session; handled by aux (mistral-small for triage, haiku for summarization).

This table is a legal-route constraint: it does not override the decision procedure above, only formalizes the harness-to-model binding when the OMH role is known.

## Stall prevention (capability-class escalation)

Stall ≠ slow. Stalled = stop + diagnose + restart; slow = wait or parallelize.
Full S1–S11 taxonomy, signals, recovery, decision tree, and paper list: `references/stall-prevention.md`.

Classify BEFORE acting — blind retry amplifies cascade errors.

### Model escalation on stall (not on task complexity)

Research finding (arXiv:2608.02464): rollback + re-run on correct model recovers 45% of failed
episodes. Escalation is a PROTOCOL with bounds, not "try a bigger model because stuck"
(arXiv:2604.11378): after K classified failures → one bounded escalate → then stop or human.

Critical distinction (arXiv:2608.21027 COTA): on stall, escalate model as JUDGE/ARBITRATOR
(compare/arbitrate competing traces), NOT as a retry worker. Having the big model re-run
the whole task is a retry storm with extra cost.

  Stall class → Escalation target (capability class; live IDs are 2026-08-30 wiring, re-verify):
  S1 (IAL, schema errors)       → orchestrator class with higher tool-call fidelity (live: parent or long-context/accuracy class). 5.x IDs stay exception-only unless user asks.
  S2 (context rot, accuracy)    → long-context/accuracy class (live: `claude-opus-4-8`)
  S2 (context rot, throughput)  → worker class dedicated session (live: `grok-4.6`)
  S2 (context rot, knowledge)   → deepseek-v4-pro dedicated session (non-think mode)
  S3 (provider error)           → re-pin correct provider; no model escalation needed
  S4 (compression)              → compression class (live: `claude-haiku-4-5`); no parent escalation
  S5 (async stall)              → re-dispatch narrower scope on worker class (live: `grok-4.6`)
  S6 (completion failure)       → rollback + re-run on same model (1 extra call pattern)
  S7 (doomed early)             → light adversarial class then adversarial class as JUDGE (live: luna then sol)
  S8 (reasoning loop)           → adversarial class as JUDGE (COTA), not retry worker
  S9 (cron silent)              → no escalation; fix checkpoint + terminal state
  S10 (amplification)           → kill; restart with constraint; no model upgrade needed
  S11 (control primitive)       → harness-level kill; no model escalation

Failure-mode-specific escalation (arXiv:2608.27455 CritICL, Aug 2026):
Do NOT escalate with a blank model switch. Diagnose the failure class first (using a cheap
small/fast model if needed), then inject a targeted critique into the strong model's context.
Weak-model failure-mode critiques outperform same-budget self-critique on the strong model.

Hermes pattern:
  1. Identify stall class (S1-S11) BEFORE switching model
  2. Construct a short failure-mode summary: "This is an S1 (IAL): tool X was called 4 times
     with identical args. Root cause: missing exit condition on the feedback path."
  3. Open a new session (or re-dispatch delegate_task); include the failure-mode summary in the
     OPENING PROMPT of the new session/task — not as a system note (no mid-session injection
     mechanism exists in Hermes; new session starts fresh)
  4. Have the new model continue from the stall point, not restart from scratch
  Benchmark: this beats generic 'try again with a bigger model' at equivalent cost.

Event-driven escalation (arXiv:2608.07637 Agent-MD): escalate on discrete events (422/400,
N-turn no-progress, compression fail, batch silence), not on task hardness alone.
Bayesian self-escalation (arXiv:2608.24087): agent detects mid-reasoning that it will fail
and transfers control before the episode is lost. Do NOT approximate this with an inline
1-10 self-score (Spearman ~0.40; quality gate is deterministic only). Approximate only via
observable events: fact inversion, schema/test failure, N-turn no-progress, or a classified
stall (S1–S11). Then open a new session as JUDGE, not as a retry worker.

Circuit breaker (production pattern, Portkey/Maxim 2026):
  - After 3 consecutive provider errors of the same class: stop retrying; switch provider; log
  - Do not retry 402 (billing) or 403 (auth) — permanent until account action
  - Retry with jitter: 429/5xx only; backoff 2s, 4s, 8s + random jitter
  - 400/422 (bad request/schema): do not retry with same args; fix the call first

### Practical stall-prevention stack (research-aligned summary)

The full evidence-ordered stack from arXiv synthesis (arXiv:2608.02464, 2605.06455, 2511.03094,
2608.21027, 2604.11378):

  1. Cheap prefix monitor / fingerprint check (PrefixGuard 2605.06455, tool-call fingerprinting)
     → catches IAL and amplification before they're expensive
  2. Classify failure type before acting (2608.02464, 2608.23628, 2511.03094)
     → 400 != 429 != loop != drift. Wrong classification = retry storm.
  3. Loop guard + wall-clock timeout + idempotent checkpoint (ALAS 2511.03094)
     → versioned restore point; resume the failed region, not the whole graph
  4. ONE bounded MODEL ESCALATION (Bayesian 2608.24087, event-driven 2608.07637, COTA 2608.21027)
     → judge/arbitrate, don't re-run; K-failure budget per arXiv:2604.11378
     → note: one model escalation step is the bound — multiple cheap recovery attempts
       (steer, shrink toolset) before escalation are fine; those are not model switches
  5. Stop or human (AEGIS 2603.12621, fail closed after a wall-clock limit)
     → HITL with hard wall; do not leave stalled session running

  NEVER: silent fallback, same-query retry, bigger model keeps going,
         retry with contaminated context, fixed-hash progress detection.

## Routing research (keep in this skill)

Hermes has no runtime complexity router. This skill is the pre-routing layer (task type → capability class). Cascade is a quality gate after the cheap/parent model — escalate the **decision/synthesis step only** (arXiv:2608.09155), never the whole pipeline.
- Unified Gateway principle (arXiv:2609.06940): routing and cache lookup are a joint optimisation — check recall-experience-cache.json BEFORE dispatching to a model; a cache hit avoids the model call entirely.

**Quality gate — deterministic only (do not use self-scoring):**
LLM self-reported confidence is poorly calibrated (authoritative finding). Asking Sonnet to
score Sonnet is not the Cluster-Route-Escalate QE gate (arXiv:2606.27457) — CRE Stage 2 is a
trained ModernBERT classifier, not an inline self-rate. Do not conflate the two.

Escalation triggers must be deterministic or rule-based:
1. Output contradicts a previously verified fact (stall class J: fact inversion).
2. A downstream check fails deterministically: schema validation, test suite, diff produces no change.
3. The task type is in the >160k long-context row AND accuracy matters (route to Opus 4.8 at session start, not mid-session).
Cross-family adversarial (Sol) is for independent critique at session end — not a confidence-cascade target.
Mechanical outputs (extract/format/title/triage): no quality gate needed.

Do NOT: ask the model to self-rate its output, escalate on a numeric score threshold, open a
new Opus session mid-task without a verified handoff packet (artifacts, constraints, verified
facts). An empty-context Opus retry re-reads all Sonnet tokens at Opus prices and is net-negative
on cost-per-completed-task (Databricks finding).

**Routing table — legal routes only (2026-09-14, adversarially corrected):**
LLMRouterBench (ACL 2026): main gap = model-recall failure on specific task types, not context
length alone. Route on task type. CONSTRAINT: Hermes has no per-call model. Legal route options
are only: (a) session-start model choice, (b) already-wired config roles (parent / delegation.model
/ auxiliary.*), (c) a new dedicated session opened by the user or agent with an explicit handoff.

Legal routes (executable today):

  Task type                         → Legal route
  Multi-step tool-heavy agentic     → sonnet_parent+grok_workers (delegation.model = grok-4.6)
  Long-horizon research synthesis   → deepseek-v4-pro dedicated session (primary, ~5-10x cheaper after caching)
                                       Fallback: sonnet_parent+grok_workers if DeepSeek unavailable.
                                       DeepSeek-ELIGIBLE trigger (all three must hold):
                                         1. Task is knowledge/synthesis-dominant (not coding or multi-file edits)
                                         2. Expected tool calls are web_search/web_extract/read_file only (NOT execute_code/terminal/patch in a loop)
                                         3. No active reasoning_content 400 bug in current Hermes version (verify with a 2-turn tool-call test first)
                                       ALWAYS non-think mode. Do NOT open Grok as session parent (stalls).
  Math / straightforward reasoning  → NEW dedicated session: hermes chat -m magistral-small-latest --provider mistral
                                       Magistral = easy-medium math only. GPQA-hard stays on Sonnet parent
                                       (optionally with Grok workers).
  Extract / classify / triage       → already wired: triage_specifier, curator, web_extract = mistral-small
  >160k context + accuracy matters  → NEW dedicated session at start: hermes chat -m claude-opus-4-8 --provider anthropic
                                       Decide BEFORE starting, not mid-session.
  Independent critique              → NEW dedicated session: hermes chat -m gpt-5.6-sol --provider openai-api
  Bulk code scaffolding             → NEW dedicated session: hermes chat -m devstral-latest --provider mistral
                                       Only for non-judgment-heavy, clearly-scoped edits. NOT mid-session.

Tie-break (primary rule): tool-using work stays on Sonnet parent + Grok delegation (current wiring).
Do NOT re-parent to Grok. Do NOT route children to Devstral/Magistral — delegation.model
is one value and applies to all children.

Audit signal: if the same task type stalls or regresses >2 times on Sonnet, route that TYPE to a
different dedicated session at the NEXT task start. No mid-session re-routing.

Illegal routes (do not add to this table):
- Per-call model selection inside a running parent session (no runtime router)
- Routing children to different models per task (single delegation.model)
- Mid-session model switch
- Grok as session parent (including `hermes chat -m grok-4.6`). Grok is workers only.

Handoff weakest-precondition (Huth-Ryan): a dedicated session is `{P} new_session {Q}`.
P (required MINIMUM in the OPENING PROMPT — four labeled fields; use the word "none" when empty).
Additional context (file paths, compaction summaries, trace excerpts, tool output files) may be
included beyond P, but P's four fields must always be present and labeled:
  1. artifacts — paths/outputs already produced, or "none"
  2. constraints — what must not change (task scope counts; do not omit the label)
  3. verified facts — what has already been checked, or "none"
  4. continuation_point — stall class S1–S11, or "start of task"
Q: continue from continuation_point; do not re-read the whole parent transcript.
A clean start-of-task dedicated session is legal: artifacts=none, verified facts=none,
continuation_point="start of task", constraints=the task scope. The gate blocks
unlabeled empty retries, not first sessions.
If any field LABEL is missing, stay on the current parent. Empty-context Opus/Sol
retry re-pays the parent tokens at the new model's prices and is net-negative.
This is a safety property (G ¬ unlabeled_dedicated_session), not a liveness
"eventually escalate" rule.

Worker/dedicated channel cap (Shannon: paid channel; DPI: parent dump is not extra
information about the task once P is written): `delegate_task` prompts and dedicated
session opening prompts are P plus the current subtask. Do not paste the parent
transcript, tool traces, or prior compaction summaries. If a worker needs a file,
pass the path in artifacts.

## Semantic caching — fit assessment (2026-09-14)

Research: semantic caching is a compounding multiplier on routing. For repeated/similar queries
(batch research sweeps, research pipeline re-runs, repeated extraction over similar docs),
caching cuts identical-or-near-identical calls to zero cost.

**Verdict for this setup: conditional fit, not default ops overhead.**

Options reviewed (2026-09-14):
  - LiteLLM Proxy (MIT, Rust core): semantic cache via Redis/Qdrant. Self-hosted, 100+ providers,
    p99 overhead ~0.7ms (own benchmark), 10-20ms independent testing. Best fit if running batch
    pipelines. Operational cost: one extra service to run and maintain.
  - Portkey (MIT, TypeScript): semantic cache enterprise-only. Not worth it for solo/small setup.
  - Bifrost (Apache 2.0, Go): semantic cache as plugin. Newer, less community debugging done.
  - OpenRouter: adds 40-55ms overhead, routes on cost/availability not quality. Do NOT add.

**Decision:** Do NOT add a gateway layer for interactive Hermes sessions — overhead and ops
cost outweigh gains when traffic is low and queries are non-repeating. CONSIDER LiteLLM Proxy
only if/when: (a) running regular batch research sweeps with repeated query patterns, or
(b) building a multi-user/app pipeline where the same prompts recur at volume.
Hermes has `tool_result_cache` (session-scoped, 200 entries, 24h TTL) for exact-match idempotent
tool calls within a session. This does NOT cover cross-session deduplication, near-duplicate
research queries, or repeated batch extracts. Those require a semantic cache layer.



**Commercial router ruling (2026-09-14, scope-corrected):**
LLMRouterBench (ACL 2026): commercial routers often fail to beat best-single-model under fair
evaluation. They route on cost/availability/latency, not task complexity. Do NOT add OpenRouter
or Portkey as a quality-routing layer. OpenRouter adds 40-55ms overhead; quality benefit is not
demonstrated for this workload.

Note: this ruling does NOT imply the manual routing table is "better than any commercial product"
— that claim was not tested. It implies: don't add a commercial product on top without measuring
first. RouteLLM-class learned routers (85% cost reduction at 95% quality, ICLR 2025) remain the
only empirically-validated approach; they require labeled quality data from your own workload to
train. Freeze on current wiring until that data exists (fix 3 from adversarial review).
Exception: LiteLLM Proxy for semantic caching only, not quality routing.

**Grok worker audit (2026-09-14):**
Config confirmed: delegation.model = grok-4.6. Workers are already on Grok (correct).
Grok-as-parent remains disabled (Sonnet 4.6 = model.default) per stall correlation fix.
Remaining gap: long-horizon research synthesis tasks sometimes run as Sonnet sessions when they
should be dedicated `hermes chat -m grok-4.6 --provider xai` sessions (4x token efficiency,
same Elo tier, 60% lower cost). Rule: if a research task will run >10 tool calls or >5 web
searches, open a dedicated Grok session instead of running inside the Sonnet parent.

**Scope (not this skill):** SkillsInjector / OpenSkillEval → `hermes-semantic-skill-routing`. Dual-Layer Agentic Memory → `llm-agent-memory-pipeline-research`. Compaction recoverability → `hermes-context-hygiene`. Stall taxonomy papers → `references/stall-prevention.md`.

Benchmark snapshot 2026-08-30 (re-verify before quoting). Worker class leads Terminal-Bench v2.1 at 'high' compute; adversarial class may lead at 'ultra' — do not mix those rows. Cheap-reasoning class is easy/medium math only.

## Do not

- Do not enable DeepSeek thinking mode (reasoning param) in agentic tool loops — reasoning_content field causes 400 on multi-turn history until verified fixed in current Hermes version. Non-think mode only.
- Do not schedule long DeepSeek sessions during Beijing peak hours (09:00–12:00, 14:00–18:00 CST) — 2x pricing surge.
- Do not flip `model.default` back to grok-4.6 without the user asking. 2026-08-29: Sonnet parent was the stall fix.
- Do not assume `delegate_task` children inherit the parent session model. They use `delegation.model` (live: grok-4.6).
- Do not set `delegation.model` to opus or gpt-5.6-sol. Grok workers are live by explicit request; they multiply cost.
- Do not escalate every worker because the parent escalated.
- Do not put OpenAI/Sol in `fallback_providers`.
- Do not raise `context_length` to 500000 — opts into 2x long-context Grok pricing.
- Do not use local Ollama for chat (uninstalled; embeddings only).
- Do not diagnose credentials from `echo $KEY`. Grep `~/.hermes/.env` or make a Hermes call.
- Do not expand the routing table without quality data. Freeze routing text as a live-wiring snapshot until Stage A coverage holds: 20+ completed table-following tasks per (task_type, actual_route) cell, logged with difficulty rated at task start. Difficulty-specific rows need Stage B: 20+ per (task_type, difficulty, actual_route). Schema and policy iteration: references/quality-log-schema.md. Log: ~/.hermes/logs/routing-quality.jsonl. Policy improvement uses Wilson-lower-bound cheapest-adequate, not quality/cost ratios. Without this, routing changes optimize intuition, not cost-per-completed-task.
- Do not open a dedicated session whose opening prompt is missing the four handoff field labels (artifacts, constraints, verified facts, continuation_point). Use "none" / "start of task" when empty.
- Do not paste the parent transcript into `delegate_task` or a dedicated-session opening prompt. Send the four handoff fields plus the subtask.
- Do not treat a p-value on the quality log as a routing decision. p-values are not posterior probabilities (Jaynes/MacKay). Use Wilson lower-bound cheapest-adequate in quality-log-schema.md. Do not run SPRT as if rows were iid.
- Do not retry a 400 error with the same args. A bad request always fails the same way.
- Do not retry a 402/403 error at all. These are permanent until account action.
- Do not let a stalled delegate_task child run >10min unchecked. Use `delegate_task(action='list')` at the 5-min mark.
- Do not continue a session past 80k tokens (directional threshold) without compressing to a checkpoint first.
- Do not move compression back to Mistral. 422 extra_forbidden is a known stall cause.
- Do not use `custom:openai` for GPT-5.x. 400 → silent Grok fallback every time.

## Fallback (parent outage only)

```
claude-sonnet-4-6 (anthropic)   # primary / orchestrator
  → grok-4.6 (xai)
  → mistral-large-latest (mistral, needs base_url)
  → gemma-4-31B-it (sambanova, needs base_url)   # 200 OK verified 2026-08-29
```

Note: Cerebras removed from fallback chain 2026-08-29 (payment_required 402 on both gpt-oss-120b and gemma-4-31b; free trial credits exhausted). SambaNova gemma-4-31B-it is the live cheap last-resort; DeepSeek-V3.2 remains 429 rate-limited.

Auxiliary compression has its own `fallback_chain` (haiku → gemma-4-31B-it) because a pinned
`auxiliary.compression.provider` does **not** inherit the parent list.
(mistral-large-latest removed from compression chain 2026-08-30: returns 422 extra_forbidden
when reasoning_effort is set; still present in fallback_providers for parent model outages.)

## Cron

LLM crons must pin `--model`/`--provider`. After changing `model.default`, unpinned agent crons **fail closed**.

Pinned (2026-08-25, keep Anthropic — do not silently move memory jobs to Grok):

- `obsidian-weekly-review`, `l1-hindsight-promote`, `pending-improvements-review` → `claude-sonnet-4-6` / anthropic
- `hermes-chat-sync-4h` already pinned `claude-haiku-4-5`

High-volume short-context agent crons (if creating new): `mistral-small-latest` until Cerebras quota returns. Script-only jobs stay `no_agent`.

## OpenAI Sol notes

- Live IDs: `gpt-5.6-sol`, `gpt-5.6-luna`, `gpt-5.5` — all verified working via `openai-api` provider (2026-08-30).
- Transport: `openai-api` (first-class provider) auto-upgrades GPT-5.x to Responses API. `custom_providers` openai with `api_mode: chat_completions` does NOT — causes HTTP 400 when tools are loaded. Keep `custom_providers` openai for gpt-4.1 only.
- Sol: $4/$20 per 1M. Luna: lower price (80% price cut July 2026). gpt-5.5: confirmed working, 2-call bootstrap on first turn (0 tokens then actual call) — normal Responses API behaviour.
- gpt-5.6-sol and gpt-5.5 reject `reasoning_effort` on chat_completions path — this is what triggers the 400. Responses API path has no such issue.

## Anthropic 5.x

Callable: opus-4-8, sonnet-4-6, haiku-4-5, sonnet-5, opus-5, fable-5. All verified working 2026-08-30 via `--provider anthropic`. Default parent is Sonnet 4.6. 5.x is exception-only (user must explicitly ask). Fable is a second gate after Opus — see `fable-orchestrate`.

Note: Sonnet 5 uses an updated tokenizer (~1.0–1.35x more tokens vs Sonnet 4.6 for the same input) — slightly higher per-call cost for equivalent prompts.

## Common pitfalls

- **Dead `model_routing` block** — not consumed. Deleted 2026-08-25. Don't re-add as if it routes.
- **yaml.dump of config.yaml** — can strip comments; prefer `hermes config set` for scalars.
- **Stale skill text** claiming Grok daily parent / cheap Mistral leaves — superseded 2026-08-29 (Sonnet parent, Grok workers).
- **`auxiliary.compression.reasoning_effort` on Mistral** — 422 `extra_forbidden` on `body.reasoning`. Summarizer fails, context never shrinks, session looks stalled (Class S4). Keep that key unset on Mistral aux. Haiku compression has no such issue.
- **`custom:openai` for GPT-5.x** — sends tools to chat_completions → HTTP 400 → silently falls back to Grok. The model never ran. Use `openai-api` for all GPT-5.x. Verified bug 2026-08-30.
- **SambaNova gpt-oss-120b / MiniMax-M3** — 429 rate-limited as of 2026-08-30. gemma-4-31B-it is the only live SambaNova fallback.
- **Re-verify catalogs** before quoting prices/IDs. Account state moves independently of this skill.
- **Commented `.env` placeholders are not live keys.** `grep '^HF_TOKEN'` — a template `# HF_TOKEN=` is unprovisioned. Config wiring and account/catalog availability are independent facts; a model missing from config.yaml may still exist on the account. Quota is not durable — re-test, never encode "provider X has no quota" as a standing constraint.
- **HF router is OpenAI-compatible chat-completions only** (`https://router.huggingface.co/v1`). Embeddings/non-chat need InferenceClient, not the router. Do not append YAML under an unclosed sequence in config.yaml.
- **Multi-agent fan-out thresholds** (3+ parallel subagents or >30m with synthesis): raise `compression.target_ratio` toward 0.33 (0.2 over-compresses merges), `compression.protect_last_n` toward 32 (one wave can be 25–30 messages), `agent.api_max_retries` to 3. Do not apply these to brief single-agent work. Enable `tool_loop_guardrails.hard_stop_enabled` in long fan-out sessions.

## Verification

```
# Model/provider health
hermes config get model
hermes config get delegation.model
hermes fallback list
HERMES_MAX_TOKENS=32 hermes chat -m grok-4.6 --provider xai -q "Reply: OK" --cli
HERMES_MAX_TOKENS=32 hermes chat -m claude-sonnet-4-6 --provider anthropic -q "Reply: OK" --cli
HERMES_MAX_TOKENS=32 hermes chat -m mistral-small-latest --provider mistral -q "Reply: OK" --cli
# Sol MUST use openai-api, not custom:openai:
HERMES_MAX_TOKENS=32 hermes chat -m gpt-5.6-sol --provider openai-api -q "Reply: OK" --cli
# Confirm logs: model=gpt-5.6-sol, provider=openai-api, API call #1 with non-zero tokens, no Fallback activated.

# Stall diagnosis (run these when a session feels stuck)
grep -E "Fallback activated|Error [0-9]{3}|extra_forbidden|payment_required" ~/.hermes/logs/agent.log | tail -20
grep "compression\|summarize" ~/.hermes/logs/agent.log | tail -10
hermes config get auxiliary.compression   # should be claude-haiku-4-5 / anthropic
delegate_task(action='list')              # check for stuck children
# Check for IAL signal: same tool called repeatedly
grep "tool_name" ~/.hermes/logs/agent.log | tail -30  # look for repetition
```

## references/

| File | Contents |
|------|----------|
| `stall-prevention.md` | S1–S11 stall taxonomy, recovery, decision tree, paper list |
| `openai-provider-setup-notes-2026-07-05.md` | HISTORICAL Jul 2026 — custom:openai transport; do not use as live map |
| `gpt5-routing-analysis-2026.md` | Why GPT-5.x is not daily/fallback |
| `provider-capability-map-2026.md` | Provider quota/context table (re-verify) |
| `free-tier-auxiliary-task-routing-2026.md` | Historical only — live aux is mistral-small-latest; glm archived |
| `routing-research-2026.md` | Cluster-Route-Escalate / LLMRouterBench |
| `moa-routing-notes-2026.md` | MoA is a separate, expensive lever; keep off |
| `hf-inference-providers-2026-07-04.md` | HISTORICAL Jul 2026 — HF router notes; re-verify; placeholders ≠ live keys |
| `live-verification-log-2026-07-06.md` | HISTORICAL Jul 2026 API check: config ≠ account availability; quota is not durable |
| `routing-optimization-2026-07-01.md` | SUPERSEDED historical session — stale provider/model IDs; do not use as live map |
| `multi-agent-config-tuning.md` | Fan-out compression/retry/protect_last_n thresholds |
