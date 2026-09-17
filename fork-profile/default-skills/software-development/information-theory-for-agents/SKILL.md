---
name: information-theory-for-agents
version: 1.2.0
author: Hermes Agent
license: MIT
description: "Use when choosing compaction/lambda/memory-policy or signal-vs-noise tradeoffs. IT status table, RR scorer params, ECS proxy, SelfCompact alignment."
tags: [information-theory, context-compression, memory, compaction, lambda, pruning]
related_skills:
  - rr-compaction-scorer
  - hermes-context-budgeting
  - hermes-context-hygiene
  - hermes-memory-surface-selection
metadata:
  hermes:
    tags: [information-theory, context-compression, memory, compaction]
    related_skills: [rr-compaction-scorer, hermes-context-budgeting, hermes-context-hygiene]
---

# Information Theory for Hermes Agent Engineering

Built 2026-09-08. Adversarially reviewed same day. v1.1.0 strips overclaims.

## Inference-Time Constraint (hard limit)

Hermes has NO logits, attention weights, or gradients at inference time.
Available proxies only: token counts, tool-type metadata, string overlap, Hindsight embeddings.

All formal IT measures below require proxies. The proxy is not the measure.
Never claim to compute exact entropy/MI/KL without model internals.

## IT Implementation Status (actual, as of 2026-09-09)

| Concept | Real status | Location |
|---|---|---|
| CAUSAL/STRUCTURAL/NOISE tagging | Prompt instruction to LLM | focus_compress.py, hermes-context-hygiene |
| RR compaction scorer | PRODUCTION (v2): budget-capped (max 1–8 per pass), exec-state-protected (execute_code/write_file/patch/terminal/skill_manage skip), RR-sorted. use_rr_scorer=true, lambda=0.2 | context_compressor.py L2817 _EXEC_STATE_TOOLS, L2858 candidates filter |
| Addressable stubs (ARC-inspired) | PRODUCTION: _lean_recovery_stub includes turn_idx metadata + tool name resolution via call_id_to_tool. Recovery hint uses keyword query, not DB row_id (no row_id available at demotion time) | context_compressor.py L768, L3238 |
| Budget dashboard (VISTA-inspired) | PRODUCTION: appended to compaction summary when last_prompt_tokens > 0. Uses self.last_prompt_tokens (real field). Shows post-compaction token bar + pressure | context_compressor.py L838, L3326 |
| CCA violation check | PRODUCTION: heuristic pass after summarization — detects negation inversions on key facts (exit codes, pass/fail, error messages). Annotates summary with [CCA-WARNING] if violations found | context_compressor.py L3244 _cca_violation_check |
| Static extractive compression rules | PRODUCTION: in _summarizer_preamble — verbatim exit codes/paths/errors, no paraphrase of constraint-bearing tokens, causal direction preservation, SIGNAL VS NOISE proxy, VERBATIM WINS priority, ACCUMULATION FALLACY | context_compressor.py ~L3536 |
| Rate-distortion taxonomy | Reading list pointer | hermes-context-budgeting |
| KL drift heuristic | Coarse concept-overlap proxy; not KL | hermes-context-hygiene |
| Sequential structure | Not implemented (RR reorder is not sequence coding) | - |
| MI-based retention | Not implemented (no MI estimator) | - |
| ECS pragmatic utility | NOT IMPLEMENTED (requires logits). Proxy: Fisher demotion test in hermes-context-hygiene. Accumulation Fallacy rule added to summarizer preamble (context_compressor.py ~L3536). | arXiv:2601.11585 |
| SelfCompact rubric | SKILL-LEVEL only: when to fire/suppress compaction (arXiv:2606.23525). Not wired into threshold trigger. | hermes-context-hygiene |
| Semantic staleness check | SKILL-LEVEL: STALE-inspired flag list for system-state memory facts (arXiv:2605.06527). No automated detector. | hermes-context-hygiene, hermes-memory-surface-selection (TEPA section) |
| TEPA conflict detection | SKILL-LEVEL: contradictory-fact heuristic + resolution order (tool_output > this-session retain > MEMORY.md > old hindsight). No automated revocation. | hermes-memory-surface-selection (arXiv:2608.07429) |

## 1. Shannon Entropy H(X) - Information Density Proxy

Math: H(X) = -sum P(x) log2 P(x). Max when outcomes uniform.

Proxy: Variety of tool names, decision types, named entities in a segment. High variety = retain.
Repeated searches with near-identical results = low variety = evict first.

Pitfall: Token length is not entropy. Long JSON with unique IDs is high-entropy.
Never evict by character count alone. Shannon 1951 describes printed English (~1 bit/char),
not LLM tokens -- do not apply that bound to agent context.

## 2. Conditional Mutual Information I(X;Y|Z) - Turn Relevance

Math: I(X;Y|Z) = H(X|Z) - H(X|Y,Z). How much does turn Y reduce uncertainty about
task outcome X, given already-kept context Z?

Practical proxy (CAUSAL/STRUCTURAL/NOISE tagging):
- CAUSAL: result changed a decision, produced an artifact, answered a blocking question
  NOTE: focus_compress.py prompt tags "command was run" as CAUSAL (too broad).
  Hygiene definition requires "changed a decision" (narrower). Use the narrower one.
- STRUCTURAL: planning, setup, with downstream dependency
- NOISE: repeated searches, confirmations, superseded output -- evict first

Internal spike result (hermes-context-hygiene, spike 006, 2026-09-07, NOT from any arXiv paper):
MI@K=5 accuracy 0.765 vs recency@K=30 accuracy 0.487. All 4 causal turns in top-4.
Source: internal Hermes benchmark, not externally validated.

Pitfall: Tags are model-applied and will drift across turns without an audit mechanism.
Three definitions exist (focus_compress.py prompt, hygiene skill, IT skill) -- they disagree.
Do not add more tag types.

## 3. Rate-Distortion R(D) - Compaction Quality Framing

Math: R(D) = min I(X; Xhat) subject to E[d(x,xhat)] <= D.

Key shift (arXiv:2609.01131, Sep 2026 -- AI-native communication / predictive state):
Distortion D is not text difference from the original. Under log loss, D equals
conditional MI lost through communication -- lost predictive performance, not lost tokens.

Practical implication: measure compaction quality by what future decisions become impossible,
not by how much text was shortened. After compaction, check 2-3 facts that should survive.

Reading list: arXiv:2607.08032 (rate-distortion taxonomy for LLM compaction -- KV eviction,
prompt pruning, recurrent state, agent memory as one RD problem). Use as framing, not
as a claim that any Hermes mechanism implements RD optimally.

Safety note from arXiv:2608.16370: at 5x compression, task completion is stable but
retrieval calls triple. Use reacquisition rate (re-reads of dropped facts) as the
distortion signal, not task pass rate.

## 4. Information Bottleneck - Lambda as Compression-Accuracy Knob

Math: min I(T;X) - beta * I(T;Y). T = kept context, X = full window, Y = task outcome.
Large beta = keep more task-predictive content. Small beta = compress harder.

lambda in RR scorer = inverse-beta in spirit. BUT: the math is not equivalent.
RR score = pp - lambda * cp. This is a linear combination, not an IB optimization.
Treat lambda as an empirical knob, not as a calibrated IB parameter.

lambda analysis (adversarial finding, 2026-09-08):
- Score = 0.5*density + 0.3*recency + 0.2*proximity - lambda * (tokens/max_tokens)
- An old large execute_code (density=0.85, cp~1.0) scores: 0.5*0.85 - lambda*1.0 = 0.425 - lambda
- An old small skill_view (density=0.40, cp~0.05) scores: 0.5*0.40 - lambda*0.05 = 0.20 - 0.05*lambda
- execute_code > skill_view only when 0.425 - lambda > 0.20 - 0.05*lambda => lambda < 0.235
- At lambda=0.4, large execute_code scores LOWER than small skill_view -- gets demoted first
- "Coding=0.3, protect execute_code" is also wrong: need lambda < 0.235 to protect large results

Per-task guidance (empirical, NOT corpus-derived, NOT validated):
- If RR ever becomes selective: lambda < 0.24 to protect large high-density tool results
- Current default 0.4 is safe only because RR is a no-op (order-only, all results demoted)
- Do not change lambda until RR has a demotion budget limit and measured pp-loss on 20+ sessions

## 5. KL Divergence D_KL(P||Q) - Drift Detection

Math: D_KL(P||Q) = sum P(x) log(P(x)/Q(x)). Requires probability distributions.

arXiv:2510.07777 ("Drift No More"): measures token-level KL between current policy and
goal-consistent reference model. Requires logits. Finding: drift reaches stable equilibria,
not runaway; reminders restore alignment. NOT implementable at Hermes inference time.

Hermes proxy (coarse, not KL):
Every ~15 tool calls on long sessions:
1. Name the top-3 entities/concepts referenced in last 5 turns
2. Name the top-3 from the first user message
3. Overlap < 1: re-read original task spec before next tool call

Pitfalls: misses legitimate vocabulary shift (task constant, language changes);
false-alarms on paraphrase; misses silent constraint drop with same surface nouns.
This is a set-overlap check, not KL divergence. Label it as such.

## 6. Channel Capacity - Subagent Context Budget

15K tokens of filtered task-relevant context outperforms 50K mixed noise for subagents.
Maximize I(task_result; context) by filtering before delegate_task.

Parallel subagents need complementary information subsets, not the same blob twice.
See hermes-context-budgeting for the token-budget allocation tables.

Data Processing Inequality (DPI): summaries cannot add information.
A summary of a summary loses more than the original. Keep breadcrumb pointers
(path, decision, ID) before discarding the blob, not after.

## 7. MDL - Skill Body Discipline

Keep the skill section whose description length + remaining task bits is minimal.
A section unreferenced in 30+ uses is an MDL violation.
Prefer 80% coverage at 1x token cost over 100% coverage at 5x.

## 8. Renyi H_2 - Recurring Dead Matter

Content appearing 3+ times verbatim has high collision probability (low H_2).
Stub these first before other eviction. See NECROPHORESIS pattern in hermes-context-hygiene.

## 9. Fisher Information Heuristic

No gradients. Proxy: "If I had not seen this turn, how much would my next action change?"
High change = retain. No change = evict. This is the decision-sensitivity test.
Do not construct a "Fisher score" from token counts -- that is not Fisher information.
ACTION: Apply the Fisher demotion test (hermes-context-hygiene skill) before any manual
context eviction. It operationalizes this heuristic into a 3-question checklist.
Proxy label: decision-sensitivity check. Source: arXiv:2606.08151 counterfactual memory selection.

## 10. Slepian-Wolf / Distributed Compression

Each subagent should encode only its innovations H(context | shared_task_spec).
Pass plan + constraints + open questions to subagents, never raw parent tool logs.
Return: one paragraph + artifact paths. Gate context sync on actual divergence,
not on turn count.

## New Findings — Sweep 3 (2026-09-10, multilang deep research)

Papers evaluated via manual applicability chain or triage:

| Paper | Verdict | Key finding |
|-------|---------|-------------|
| 2605.10870 DeMem | SPIKE (check feasibility) | Decision-centric rate-distortion: distortion = loss in achievable decision quality, not text fidelity. Forgetting boundary = decision-indifference set. Memory discard = keep only distinctions that change actions. Stronger than descriptive fidelity framing. |
| 2511.01202 Semantic IT for LLMs | SPIKE (weak) | Token-semantic entropy != bit-level entropy. Shannon 1 bit/char must not be applied to LLM tokens (already warned above). Semantic information unit = token-cluster with coherent denotation. |
| 2608.01388 LTL Monitor Coverage | NEGATIVE RESULT | Formal LTL safety monitors have bounded coverage = f(attack distribution entropy). Cannot guarantee exhaustive coverage of adversarial agent behavior. IMPLICATION: do not over-rely on formal verification guards; use probabilistic/entropy-based safety bounds instead. |
| 2604.16471 Semantic Channel Theory | SPIKE (deferred) | Structural fidelity for multi-agent communication via semantic channels. Deductive compression preserves semantic structure. Applies to subagent context-passing (Slepian-Wolf section above). |
| 2609.00748 Optimal Transport in Transformers | SKIP | Measures OT distance between layer representations. Requires model internals. |

### DeMem Decision-Centric Rate-Distortion (2605.10870) — Full Note

Distortion D_action(x, xhat) = loss in achievable expected reward under xhat vs x.
Forgetting boundary: two memories are equivalent iff optimal policy does not change.
Near-minimax regret with exact forgetting boundary (sequential-decision setting).

Hermes gap: current compaction policy uses CAUSAL/STRUCTURAL/NOISE tagging with
presence-of-decision heuristic. DeMem says: the correct test is "does this memory
change the optimal action?" not "was a decision made near this turn?"

Proxy (no action space at inference time):
  Fisher demotion test already approximates this: "would next action change without
  this turn?" — DeMem provides the formal justification for that proxy.
  STRENGTHEN the Fisher demotion test with an explicit "action-relevance" framing:
  not just "would my next tool call change" but "would the FINAL task action change."

Feasibility gate: DeMem requires a known action space to compute exact boundary.
Hermes has open-ended tool actions — exact boundary not computable.
Degrade to: Fisher demotion proxy labeled as decision-sensitivity approximation.

## CS Sweep Results (hermes-cs-research, 2026-09-09)

216 CS papers swept; 8 SYSTEMS-APPLICABLE, 23 SPIKE, 185 SKIP from interpreter.
Manual 7-step chain run on top 3 CS items:

| Paper | Title | Chain verdict | Reason |
|-------|-------|---------------|--------|
| 2609.00759 | CCA: Compile, Don't Memorize | SPIKE | Violation-gated correction loop new; typed IR already in focus_compress.py YAML |
| 2608.20280 | LLM Cache Eviction Policy | SKIP | Interpreter conflated TTL vs eviction; primary finding is negative (2% quality hit rate); not applicable to Hermes prefix cache |
| 2606.17182 | Concurrency Anomalies in Multi-Agent LLM | SKIP (session) | TLA+ spec work, process artifact; durable-replay model doesn't match Hermes |

SPIKE implemented: _cca_violation_check() in context_compressor.py — heuristic outcome-inversion
detection after _generate_summary. Flags PASSED/FAILED/exit_code inversions between source
turns and summary. 6 tests added. No extra LLM call.

23 CS SPIKEs (confidence=0.7 uniform) deferred: gateway/transport/CRDT domain — wrong
domain for Hermes runtime. k-Reciprocal re-ranking, intent tracking, MoE caching all
require deeper review before implementation.


1. Can it be computed from token counts, tool metadata, string overlap, or Hindsight embeddings?
2. Is there a simpler 3-line heuristic at 80% benefit? Start there.
3. Is there a way to measure whether it helped (reacquisition rate, pp-loss)?
4. Is the proxy labeled as a proxy, not the measure?

## Papers (verified, correctly interpreted)

- arXiv:2609.01131  Predictive state = sufficient + minimal fidelity object; D = lost predictive MI (Sep 2026)
- arXiv:2607.08032  Rate-distortion taxonomy: KV eviction / prompt prune / agent memory as one problem (Jul 2026)
- arXiv:2608.16370  Reacquisition cost: 5x compression triples retrieval calls (Aug 2026)
- arXiv:2510.07777  KL drift to stable equilibria; reminders restore; needs logits (Oct 2025)
- arXiv:2606.18746  Domain separation: memory must distinguish states requiring different actions (Jun 2026)
- arXiv:2604.14004  Abstract memories transfer; raw traces cause negative transfer (Apr 2026)
- arXiv:2601.11585  ECS: pragmatic utility = P(a|ctx+turn) shift; Llama-3.1-8B on LoCoMo turn-level F1=0.265 vs TF-IDF 0.154 (71.8% relative gain, single model/dataset). Qwen on same benchmark: ECS F1=0.020 loses to TF-IDF 0.154. Do not cite the 71.8% as a general result. (KAIST, 2026)
- arXiv:2606.23525  SelfCompact: rubric for compaction fire/suppress; no fine-tuning needed (2026)
- arXiv:2605.06527  STALE: semantic staleness detection for LT memories (2026)
- arXiv:2608.07429  TEPA: stale memory revocation for conflict-robust agents (2026)
- arXiv:2606.08151  Decision-Aware Memory Cards: counterfactual impact > recency for memory selection (2026)
- arXiv:2307.03172  Lost-in-the-Middle (Liu et al. 2023): middle context systematically underweighted — canonical citation for this effect
- arXiv:2604.11462  Context Bottleneck (ContextCurator RL, Li et al. 2026): RL-based active curation to escape long-context degradation — NOT the Lost-in-the-Middle source

## Verified Paper Verdicts — Sweep 2 (math-cs-applicability-reasoning 7-step chain, 2026-09-09)

| Paper | Title | Verdict | Action |
|-------|-------|---------|--------|
### Post-adversarial corrections (2026-09-09)

All three SPIKE implementations were reviewed by a cold adversarial subagent (Grok-4.6).
Findings applied:
- ARC (2607.25066): stub enriched with turn_idx metadata ONLY; query='turn N' FTS
  approach removed (DB row_id unavailable at demotion; FTS would not match).
  Recovery hint corrected: session_search(query='<tool_name> output', role_filter=['tool']);
  default role_filter=['user','assistant'] silently skips tool results.
- VISTA (2606.30005): dashboard wired to last_prompt_tokens (real field); not
  _last_preflight_pressure (lives on preflight verdict object, not compressor).
- ACON (2510.00615): relabeled as "static extractive rules informed by" not "ACON
  implemented"; iterative guideline refinement not run (critique-bank has 0 compression
  failures to use as oracle). Alice/Bob example removed; rule overlap fixed.
- D-state protection renamed exec-state protection; set corrected: {execute_code, write_file, patch, terminal, delegate_task, web_extract}.
  skill_manage removed; delegate_task+web_extract added to match code.
- 33 targeted tests added (test_it_research_implementations.py). 236/236 pass.

| 2607.25066 | ARC addressable stubs | SPIKE | Enrich `_lean_recovery_stub` with turn index — DONE |
| 2606.30005 | VISTA budget dashboard | SPIKE | Add `_build_budget_dashboard` to `_augment_summary_lean` — DONE |
| 2510.00615 | ACON guideline refinement | SPIKE | Add VERBATIM PRESERVATION RULES to `_summarizer_preamble` — DONE |
| 2606.13177 | MemRefine LLM judge | SPIKE (weak, deferred) | Verify hindsight enumerate-all API first |
| 2601.17532 | IGP information gain | SPIKE (weak) | Opt-in re-ranker only; O(k) cost prohibitive for default path |
| 2607.18265 | Two-agent relay JSON | SPIKE (weak) | Structured mode for CAUSAL segments in focus_compress |
| 2605.10870 | DeMem decision-centric | SKIP | No action space at inference time; feasibility=0 |
| 2602.02050 | Entropy tool-use | SKIP | Training loop required |
| 2604.15877 | Experience spectrum | SKIP | FRAMEWORK only, no algorithm |
| 2602.09789 | Scaling paradox | SKIP | Already implemented (haiku-4-5 is the small compressor) |
| 2602.03784 | ComprExIT | SKIP | Model internals required |
| 2608.22963 | Multimodal pruning | SKIP | Out of domain |

### Chain evidence for strong SPIKEs

**2607.25066 (ARC):** ALGORITHM. Structural match: stub generation. Implementation: turn_idx added as
comment metadata only. Recovery hint corrected to pass role_filter=['tool'] — without it, default
role_filter=['user','assistant'] silently drops all tool output from search results.

**2606.30005 (VISTA):** HEURISTIC. Structural match: compaction summary. Fix: append budget dashboard to
compaction summary via `_augment_summary_lean`. Token counts drawn from self.last_prompt_tokens
(real, API-driven), threshold_tokens, max_tokens. Zero-guard: omit block when last_prompt_tokens==0.

**2510.00615 (ACON):** ALGORITHM (primary: guideline refinement, no fine-tuning). Structural match: `_summarizer_preamble`. Critique-bank has 0 compression-specific failures — offline oracle unavailable. Applied one-time static improvements: VERBATIM PRESERVATION RULES (4 rules covering file paths, numerics, direct quotation, no causal-relationship paraphrase). Grounded in Size-Fidelity Paradox paper (2602.09789) which confirms semantic drift in larger compressors.

## Verified Paper Verdicts — Sweep 1 (math-cs-applicability-reasoning 7-step chain, 2026-09-09)

All three run to Step 6 on full text. Verdicts are terminal.

arXiv:2607.08032 -- SPIKE
  Principle: reversibility > scoring tricks. At same budget, re-fetch beats irreversible evict.
  Hermes gap: Phase-1 stub is irreversible; no within-session re-fetch for demoted tool bodies.
  Disanalogy: paper assumes reversible operators exist at runtime; Hermes has no such path.
  Verification: check focus_compress.py/agent_init.py for within-session re-fetch.
  Metric: pp-loss (rr_compaction_spike.py), session token count at compaction.
  Action: design within-session reversible buffer for demoted tool bodies.

arXiv:2608.16370 -- SPIKE
  Principle: classify context by execution-relevance (D-state); retain that class;
    measure retrieval calls, not just completion. GPT-5.5: completion 80%->85% (p=1.0),
    retrieval 21->64 (p=.002) at 5x compression.
  Hermes gap: CAUSAL tag exists in focus_compress.py but NOT wired into Phase-1
    demotion in context_compressor.py.
  Disanalogy: paper uses oracle D-state ground truth; Hermes uses LLM-prompt
    classification with unknown error rate.
  Verification: audit focus_compress.py CAUSAL tags on 5 real sessions manually.
  Metric: tool call count per turn (retrieval vs execution split).
  Action: audit precision, then wire CAUSAL class as protected in context_compressor.py.

arXiv:2604.14004 -- SKIP (critic downgrade from SPIKE-weak)
  Convention confirmed: abstract insights transfer, raw traces cause negative transfer.
  Critic: "write abstract insights not traces" is already Hermes convention
    (skill write-guard, hindsight_retain). Hermes semantic retrieval also partially
    mitigates negative transfer. No new procedure needed. as validating Hermes mechanisms

- arXiv:2604.15356  KV quantization via PLT tries; 3.3-4.3 bits/token-position, not 10-15; not about RR
- arXiv:2608.12322  Armed-conflict self-reflection ablation; typed routing there != compression tags
- arXiv:2607.28103  Memory-injection attack detector (MIND); not IB lambda compression
- arXiv:2608.01056  Agent control context collapse at 35% retained budget -- method-dependent, not universal
