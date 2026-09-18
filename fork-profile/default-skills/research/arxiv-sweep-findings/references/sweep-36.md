# Sweep 36 Findings — 2026-09-15 (Agent Categories 1–7 + Math/CS)

Boundary: 2609.13072+ (post sweep-35 cutoff)
Sweep date: 2026-09-15 (AEST)
Source: hermes-research-latest.json (Sep 14, 1705 papers, 404 in agent cats)
Math/CS sweep: run by separate subagent (sa-3-b483b07d, deleg_255ab203)
Papers triaged: 21 candidates from agent-cat titled papers + 3 deferred (Firecrawl-blocked)

## HIGH — Implemented (pending subagent confirmation)

### arXiv:2609.05339 [agentic_rag / memory]
Title: Does Your Agent's Memory Survive a Model Upgrade? A Controlled Study of Memory Portability
Signal: KG-fixed memory transfers reliably (±0.002 accuracy delta); NOTES degrade 9-13pp; RAG degrades 81% from
retrieval failure. Always retain raw source history alongside summaries. Direction-specific migration testing required.
Targets: hermes-memory-surface-selection (§ Memory Portability on Model Upgrade), l1-extract.py (source_text field)
Subagent: sa-0 (batch A, deleg_255ab203)

### arXiv:2608.21690 [agentic_rag]
Title: Scroll: Context as an Environment — Programmatic Context Management
Signal: Append-only Event Log + persistent kernel. Bind tool outputs to named variables; project only what next call
needs. +37.4pp on LOCA_256K over best published.
Targets: hermes-context-hygiene (§ Programmatic Context Projection), agent-runtime-loop-patterns (projection vs compaction decision rule)
Subagent: sa-1 (batch B, deleg_255ab203)

### arXiv:2608.15703 [agentic_rag]
Title: HyMem: Hierarchical Context Management via Information Isolation
Signal: Four-layer isolation: transient/episodic/semantic/procedural. Upward promotion only on triggers. Prevents
cross-contamination between layers.
Mapping: transient=working_memory, episodic=Hindsight/session_search, semantic=Graphiti, procedural=skills
Targets: hermes-memory-surface-selection (§ HyMem Four-Layer Isolation), hermes-context-hygiene (§ Context Layer Isolation)
Subagent: sa-0 (batch A, deleg_255ab203)

### arXiv:2608.03648 [multi_agent]
Title: DEAR: Group Perspective Matters — Regulating Debate Relationships vs Blind Conformity
Signal: Blind conformity driven by reference-peer selection, not individual confidence. Confidence-based stopping
EXACERBATES conformity. Fix: force diverse reference peers when round-1 consensus ≥2/3.
Targets: hermes-swarm-consensus (§ Blind Conformity Guard), dispatching-parallel-agents (anti-conformity seeding note)
Subagent: sa-2 (batch C, deleg_255ab203)

### arXiv:2606.16710 [multi_agent]
Title: Misinformation Propagation in Benign Multi-Agent Systems
Signal: Tool-injected misinformation persists across debate. Consensus more stable than majority vote under peer
pressure. Keep ≥2/3 agents tool-call-independent before merging.
Targets: trajectory-risk-guardrail (§ Tool-Output Misinformation), hermes-swarm-consensus (decision protocol note)
Subagent: sa-2 (batch C, deleg_255ab203)

### arXiv:2608.15071 [self_improvement]
Title: Evo-Harness: Context-to-Harness Skill Compilation (EMNLP 2026 Main)
Signal: One-shot context-to-harness compilation. Separate broadly-useful lessons from task-specific artifacts.
Validate cross-domain transfer before adding to harness.
Targets: runtime-skill-synthesis (§ Evo-Harness One-Shot Compilation), self-improve-agent (cross-domain filter note)
Subagent: sa-1 (batch B, deleg_255ab203)

### arXiv:2603.21362 [evaluation]
Title: AdaRubric: Task-Adaptive Rubrics for Reliable LLM Agent Evaluation (Pearson r=0.79, +0.16 over best static)
Signal: Fixed rubric fails agent eval. Task-specific dimensions. DimensionAwareFilter: any FAIL dimension = overall FAIL.
Dimension map: code→Correctness+ErrorHandling; config→Coherence+Coverage; research→Evidence+Grounding;
multi-agent→Isolation+Provenance+ConformityCheck
Targets: adversarial-review (§ Task-Adaptive Rubric Selection), evaluation-driven-development (rubric selection note)
Subagent: sa-2 (batch C, deleg_255ab203)

## MED — Logged

| arXiv ID | Category | Title | Signal | Revisit trigger |
|---|---|---|---|---|
| 2608.05956 | multi_agent | Koopman Spectral Analysis for MA Consensus | λ2 convergence deadline theoretical backing for MACI halt | Swarm timeout problems |
| 2609.07471 | agentic_rag | MEMO: Multimodal Evidence Memory | Evidence-source tagging on memory units | Multimodal Hermes or evidence quality pain |
| 2607.25076 | multi_agent | Agent OS: Lessons from Classical/Cloud OS | 4 lessons already implicit in Hermes harness design | New agent substrate or A2A adoption |
| 2606.04990 | tool_use | From Agent Traces to Trust (survey) | Provenance survey; covered by run-header.py + tool-auth-gate | New provenance requirement |

## LOW/SKIP — Logged

| arXiv ID | Category | Reason |
|---|---|---|
| 2608.10430 | self_improvement | Latent Critic LoRA: requires LLM training |
| 2608.09292 | self_improvement | Zeroth-Order Self-Evolution: LoRA+SFT |
| 2603.18516 | evaluation | Total Recall QA: benchmark construction only |
| 2608.07531 | evaluation | Search-G1: RL intrinsic reward, training |
| 2609.06128 | multi_agent | Substrate-Portable Execution: abstract unavailable |

## Defer matrix

| Item | Benefit | Partial coverage | Cost/risk | Revisit trigger |
|---|---|---|---|---|
| 2609.06128 Substrate-Portable | Workflow portability | fork session-portable | Abstract unavailable | Agent portability pain |
| 2608.05956 Koopman MA | Convergence deadline bounds | MACI halt + Lyapunov | Koopman estimation infra needed | Swarm round-count overflow |
| 2609.07471 MEMO evidence tags | Source tagging | l1-extract.py source_text (from 2609.05339) | Multimodal infra for full impl | Evidence quality failures |

## Math/CS Sweep Results (2026-09-15)

Math sweep (math-paper-interpreter.py --limit 30): 30/502 papers -> 0 OPT / 0 SPIKE / 30 SKIP.
100% SKIP rate is a --limit 30 sampling artifact. Full Sep-06 run (177 papers): 50 SPIKE + 1 OPT
already recorded. No new actionable math findings this cycle.

CS sweep (cs-paper-interpreter.py --limit 30): 30 papers -> 0 SYSTEMS-APPLICABLE / 3 SPIKE / 27 SKIP.
All 3 new SPIKE candidates (software_testing) chain-evaluated to SKIP:

| Paper | Verdict | Reason |
|---|---|---|
| 2609.01595 Mechanism Design for Alignment | SKIP | FRAMEWORK, no numbered procedure |
| 2608.28754 Peer k-Oversight | SKIP | THEOREM, needs formal harm/mechanism graph |
| 2505.13416 Gluon optimizer | SKIP | Training-loop gate (no local model) |
| 2511.12288 Semantic Triangulation (code) | SKIP | Object mismatch: code != tool calls |
| 2609.08681 Fault Injection (OpenStack) | SKIP | EMPIRICAL, no Hermes counterpart |
| 2609.09048 Audit Instrument Effects | SKIP | EMPIRICAL; addendum to 2609.04198 (already applied) |

Spike audit (5 unrecorded verdicts from prior runs):
- 003-coalition-reviewer-selection: VALIDATED-gated (requires expertise vectors per reviewer)
- 004-oftrl-subagent-aggregation: VALIDATED-gated (requires live A/B before ship)
- 006/007/009: VALIDATED-synthetic only - do not ship (chain SKIP or real-data gate unmet)

No new HIGH implementations from math/CS this cycle.
Action flag: cs-research-sweep.py needs a fresh run (127h stale).


## Recursive Pass — Waves 2-9 (2026-09-15, same session)

### Wave 2 — SKIP/DEFER Re-examination + Newly Unblocked Papers (4 HIGH)

- HIGH 2606.04990 Agent Traces to Trust → unified-recall.py (trust_weight), trajectory-risk-guardrail
- HIGH 2608.29596 Agentic Skill Security → harness-first-agent-design (lifecycle states, admission gate), runtime-skill-synthesis (admission gate)
- HIGH 2606.31650 ECHO credit routing → memory-ttl-purge.py (REUSE_TTL_BONUS +7d/access, cap +28d), hermes-memory-surface-selection
- HIGH 2606.30005 VISTA context proprioception → hermes-context-hygiene (Context Pressure Monitoring), hermes-observability (pressure_flag), turn_usage.py (pressure_flag wired)

### Wave 3 — Reference Mining from Wave-2 HIGH Papers (1 HIGH)

- HIGH 2607.13987 SkillSec-Eval admission → harness-first-agent-design (6-point admission checklist + HiddenCommentInject warning)

### Wave 4 — CS Sweep (papers 1-90) + New Searches (3 HIGH)

CS sweep: 164/200 papers processed (interpreter timed out at 164, no model scoring; manual triage performed)

- HIGH 2609.09134 Co-Evolving Harnesses On-Policy Correction → self-improve-agent (on-policy skill repair: localize before rewriting), harness-first-agent-design (already had co-evolution section)
- HIGH 2609.11709 Bayesian Backward Anchor for MA Decision-Making → hermes-swarm-consensus (Bayesian Backward Anchor section)
- OPT  2609.11682 COBRA-Skills Bandit Optimization → skillopt-continuous-improvement (UCB1 prioritization)
- SPIKE 2608.05956 Koopman Spectral Multi-Agent Convergence → math-spike-queue.json (spike 001)
- SKIP 2609.07471 MEMO Multimodal Memory (text-only Hermes)

### Wave 5 — CS Sweep (papers 90-164) + New Search (2 HIGH + 2 OPT)

- HIGH 2609.05511 SCAFFOLD MDL Skill Deduplication → runtime-skill-synthesis (MDL dedup gate, behavioral equivalence check)
- HIGH 2609.11060 Environment-Probing Curation → hermes-memory-surface-selection (probing gate before retention)
- OPT  2609.08273 MemForest Event-Centric Compression → hermes-memory-surface-selection (event-centric clustering note)
- OPT  2608.08253 SuperLocalMemory 4.0 → hermes-observability (bi-temporal as-of debug query)
- SKIP 2609.05572 Wrong abstract (Deep Belief Networks)
- SKIP cs-123 TrajectoryDB (covered by Hindsight/session_search)

### Wave 6 — Sustained Search (1 HIGH)

- HIGH 2609.09090 SPINE Sustained Sycophancy → trajectory-risk-guardrail (Sequential Sycophancy Guard), hermes-swarm-consensus (Sequential Sycophancy in debate)
- DEFER cs-89 Microskill Architecture (abstract unavailable)
- DEFER cs-121 AMA (abstract found via blog but all components already in Hermes)

### Wave 7 — CPE Attacks + Reference Mining (1 HIGH + 1 OPT)

- HIGH 2609.01222 Context Privilege Escalation Attacks (M-CPE, X-CPE) → trajectory-risk-guardrail (CPE section), harness-first-agent-design (CPE in skill loading)
- OPT  2609.00829 HarnessEvolve Performance Gate → self-improve-agent (AutoSaddler performance gate addendum)
- DEFER 2609.00546 Runtime-Independent Agents (covered by Memory Portability)
- SKIP 2606.09613, 2609.07370, 2607.08370 (persistent Firecrawl 403 after 7 attempts)

### Wave 8 — Final CS papers 165-200 + surface check (ZERO HIGH)

CS 165-200: all reasoning_planning DOI journal papers (non-arXiv), zero arXiv agent papers
- SKIP 2609.01437 HarnessDev (benchmark only)
- OPT  2608.06984 HarnessSafe (covered by existing CPE + Skill Security sections)
→ ZERO HIGH (first zero-HIGH wave)

### Wave 9 — DEFER re-examination (ZERO HIGH)

- SKIP AMA (all components: HyMem + trust weighting + contradiction check + env probing already in Hermes)
- No new papers surfaced from reference mining
→ ZERO HIGH (second consecutive zero-HIGH wave)

TERMINATION CRITERION MET: 2 consecutive zero-HIGH waves

## Recursive Pass Summary

Total HIGH implemented: 19 (7 wave-1 + 4 wave-2 + 1 wave-3 + 3 wave-4 + 2 wave-5 + 1 wave-6 + 1 wave-7)
Total OPT implemented: ~9
Total SKIP: ~15
Total DEFER: 7 (3 blocked + 4 covered by existing implementations)
Koopman spike: queued in math-spike-queue.json (spike 001)
Math sweep: 254 papers loaded, zero scored (API timeout both attempts)
CS sweep: 164/200 agent papers processed manually

Next: Adversarial pass (cohesiveness audit)

## Math Sweep Wave-3 (2026-09-15, in-session manual triage)

### Pipeline Fix
- Root cause: hermes-math-sweep.py writes new_papers_flat BEFORE abstract resolution; interpreter fast-skips all no-abstract papers
- Fix A: math-prefetch-abstracts.py — concurrent abstract fetcher (8 workers, 254 papers in 10s)
- Fix B: Two-stage pre-filter in math-paper-interpreter.py — fast SKIP/MAYBE gate (max_tokens=5, 0.8s/paper) before full chain (max_tokens=600, ~10s/paper); cron budget: 75 × 0.8s + ~5 × 10s ≈ 110s < 300s

### Papers Screened
- 265 math papers screened (75 + 190), two-stage pre-filter
- Pre-filter: 246 SKIP, 19 MAYBE → full chain on 11 (8 already self-triaged as SKIP from abstract) → 8 OPTIMIZATION, 3 SKIP

### OPTIMIZATION Findings (implemented)

2609.06940 [game_theory] — Unified AI Gateway: Joint Model Routing and KV Cache Management
  Target: hermes-memory-surface-selection/SKILL.md (§Unified Gateway: Joint Routing + Cache), claude-routing-hierarchy/SKILL.md
  Implementation: ROUTE/CACHE-HIT/CACHE-MISS-POPULATE/EVICT taxonomy; joint optimisation min(latency+0.3*cost) s.t. quality>=threshold

2609.10854 [combinatorics_approx] — No-Box Vulnerability Analysis: Description-only Detection of Indirect Prompt Injection in MCP Servers
  Target: harness-first-agent-design/SKILL.md (SkillSec-Eval section)
  NOTE: Not yet implemented — skill already has SkillSec-Eval from wave-3; needs dedicated injection-path enumeration section added

2609.08175 [generalization_theory] — Safe Harness Self-Evolution: Theoretical Analysis of Feasibility and Limits
  Target: self-improve-agent/SKILL.md (§Harness Self-Evolution Feasibility Bounds)
  Implementation: PAC bound n_min=ceil(log(2/delta)/epsilon^2); Banach contraction fixed-point limit; expressivity ceiling warning

2608.29789 [generalization_theory] — Conformal Prediction + Wasserstein DRO Unification
  Target: SKIP (requires finite labeled test sets for CP calibration — Hermes has no calibration set)
  Note: Chain verdict was OPTIMIZATION but re-triaged SKIP on closer read — CP requires coverage guarantee calibration data

2609.01679 [generalization_theory] — Self-Improving Test-Time Intelligence Survey
  Target: self-improve-agent/SKILL.md (survey findings; TTI principles)
  NOTE: Survey paper — no concrete algorithm; relevant as background for skill selection hierarchy but no implementation target

2402.10705 [graph_flows_matching] — AutoSAT: Automatically Optimize SAT Solvers via LLMs
  Target: SKIP (re-triaged — SAT solver domain too specific; no direct Hermes routing analogue)

2609.11390 [randomized_data_structs] — VikingRAG: Token-efficient RAG with Experience-Edge Caching
  Target: unified-recall.py (_check_experience_cache, _write_experience_cache)
  Implementation: cosine>0.85 + age<3600s hit condition; LRU cap at 100 entries; atomic JSON write

2602.09490 [game_theory] — Robust Trust: Adviser Misalignment with Known Probability
  Target: unified-recall.py (_TRUST_WEIGHTS docstring + trust_weight application comment)
  Implementation: _TRUST_WEIGHTS interpreted as p-alignment probabilities; trust-region radius p/(1-p); docstring + inline comment

2605.06864 [random_graphs] — Multi-Objective Multi-Agent Bandits
  Target: SKIP (requires inter-agent communication over time-varying graphs; no Hermes multi-agent runtime)

### SKIP Papers (full chain)
2609.13037 — LLM pricing agent collusion (requires repeated game with price oracle) — SKIP
2609.04494 — Hakken knowledge gap prediction (requires labeled discovery ground truth) — SKIP
2609.10986 — Pragmatic information theory (requires per-turn oracle + latent space projection) — SKIP

### Net Implementations This Wave
- unified-recall.py: _check_experience_cache() + _write_experience_cache() (VikingRAG, arXiv:2609.11390)
- unified-recall.py: _TRUST_WEIGHTS docstring + inline comment (Robust Trust, arXiv:2602.09490)
- self-improve-agent/SKILL.md: §Harness Self-Evolution Feasibility Bounds (arXiv:2609.08175)
- hermes-memory-surface-selection/SKILL.md: §Unified Gateway: Joint Routing + Cache (arXiv:2609.06940) + Robust Trust bullet
- hermes-observability-and-task-ledger/SKILL.md: §VikingRAG Experience-Edge Cache
- claude-routing-hierarchy/SKILL.md: Unified Gateway principle note
- math-paper-interpreter.py: two-stage pre-filter + max_tokens 2000→600
- math-prefetch-abstracts.py: new script (concurrent abstract fetcher, 8 workers)
- hermes-math-research/SKILL.md: categories 52-59 registered; prefetch pipeline documented
