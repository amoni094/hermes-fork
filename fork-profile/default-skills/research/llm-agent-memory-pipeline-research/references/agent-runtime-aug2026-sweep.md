# Agent Runtime Improvements — Post-Aug-8 2026 Research Sweep

Sweep date: 2026-08-11  
Scope: arXiv papers submitted August 1–10 2026, NOT in prior known baseline.  
Methodology: cs.AI/cs.MA category listing walk + batched web_extract on abs pages + targeted keyword searches.  
Target system: Python CLI agent (Anthropic API + SQLite FTS5 + Hindsight + skills-as-markdown, Fedora Linux).

---

## 1. Agent Memory: Eviction, Compression, Distillation, Working Memory

| arXiv ID | Title | Key Finding | Hermes Signal |
|----------|-------|-------------|---------------|
| 2608.03463 | **LeanMem** — Simple and Efficient Long-Term Memory | Classifies dialogue content into 3 compressibility tiers: profile (stable schema-guided facts), event (temporally evolving), record (verbatim immutable). Only event memories are updated dynamically; retrieval budget allocated per query type. Beats baselines by up to 15.1pp on LoCoMo/LongMemEval-S at lowest token cost. CODE AVAILABLE. | Implement as 3 Hindsight namespaces: `profile`, `event`, `record`. Only re-embed on event writes. |
| 2608.01742 | **MemSIF** — Dual-Track Fact Memory | Identifies Temporal-Structural Misalignment (temporal proximity ≠ topical relatedness) and Delayed Utility Manifestation (write-time salience ≠ future query utility). CoreFact: stable facts written eagerly. ActiveFact: formed on demand, promoted after repeated access. 2.3–8.8% improvement over baselines across 5 LLMs. CODE AVAILABLE (github.com/luoyufeihaha/MemSIF). | Add `access_count` column to SQLite staging table; promote to Hindsight only after access_count ≥ 2 (already in Priority 3 roadmap — MemSIF validates it). |
| 2608.05095 | **HiGram** — Hierarchical Graph Memory with Path-level Localization | Coarse upper-level nodes + fine MemoryUnits. Query-conditioned MicroGraphs localize minimal relevant subgraph before rewriting; jointly revises intra-unit + inter-unit dependencies. Improves QA under dynamic/static/conditional fact conflicts. | Hierarchical: Hindsight (fine-grain) + Graphiti (coarse entity graph). Path-level pre-localization before rewrite prevents cascading stale-fact errors. |
| 2608.01285 | **Router-Mem** — Evidence-Conditioned Progressive Memory Execution | Lightweight sufficiency router (single-token decision) decides after shared low-cost retrieval whether to terminate early or expand to deeper analysis. Reduces inference time 27.3–25.5% vs. full memory execution. Evidence-level supervision + rationale-conditioned distillation. | Add a "should I call Hindsight again?" binary gate in session search chain. Approx. as a small classifier trained on SQLite session data (positive = additional retrieval improved answer). |
| 2608.07169 | **AMD** — Agent Memory Distillation | Training-free: distills successful large-teacher-agent trajectories into 3 hierarchical memory types for small student agent: Workflow (task-level strategy), Subtask (intermediate behavioral examples), Function (per-tool pitfalls, retrieved reactively on errors). +27.2pp AppWorld, +11.2pp BFCL V3 with 4–8B student models. Under review. | Directly validates Hermes skills-as-markdown: Workflow=skill YAML, Subtask=step sections, Function=pitfall annotations. Suggests auto-populating skill files from successful Claude trajectory recordings. |
| 2608.01543 | **V-Mem** — Multimodal Agentic Memory with Modality-Routed Retrieval | Identifies modality gap (same-modality retrieved over cross-modality evidence) and similarity-relevance gap (similar ≠ relevant across modalities). Routes by (query modality, evidence modality); uses LLM-generated hypothetical anchors for cross-modal retrieval. LLM-judge 0.82 vs 0.56 for second-best. CODE AVAILABLE (github.com/Dingyi-Kang/V-Mem). | Relevant when Hermes computer_use screenshots are stored in Hindsight; hypothetical-caption anchoring is implementable in embedding pipeline. |

---

## 2. Agent Runtime: Context Management, Tool Schema Optimization, Efficiency

| arXiv ID | Title | Key Finding | Hermes Signal |
|----------|-------|-------------|---------------|
| 2608.06503 | **Active Context Compression** for Long-Horizon Agents | Per-step: small auxiliary LM selects which prior context segments are still causally active (relevant to current plan); discards the rest. ~40% token cost reduction on long-horizon tasks without catastrophic forgetting. | Pre-call context pruner in Anthropic API wrapper: drop prior tool outputs that aren't causally referenced in the current plan skeleton. |
| 2608.02113 | **Width, Memory, Delay** — Three Axes of Context Pressure | Empirically separates tool schema width (schemas loaded), memory injected per step, and planning delay. Tool schema width is the dominant cost driver; selective schema loading outperforms full-schema padding by a large margin. | Highest-ROI optimization: build a tool relevance router that selects which MCP schemas to inject per request. Aligns with MemTool pattern already in this skill. |
| 2608.04588 | **EASy** — Efficient LLM-Based Agentic System | RL-trained orchestrator with explicit executor capability+cost profiles; milestone→dependency-graph→parallelized execution; tree-structured rollout for training; adapts to intermediate outcomes. Consistently better performance-efficiency trade-offs. | Hermes cron+subagent dispatch: decompose into milestones before fan-out; route to Claude Haiku vs Sonnet based on cost+capability profile of each milestone. |
| 2608.05643 | **Refining Over Resampling** — Test-Time Self-Correction | Breadth (multiple rollouts) + depth (iterative self-critique per rollout) + majority vote on refined answers beats greedy, best-of-N, verifier-based, beam, and lookahead decoding. Works on 1.5B–7B models. MATH500 58.0% (Qwen2.5-1.5B). | Adopt for high-stakes Hermes tasks: generate N rollouts, self-refine each, then majority-vote — not just sample more. |

---

## 3. Multi-Agent Orchestration: Consensus, Conflict Resolution

| arXiv ID | Title | Key Finding | Hermes Signal |
|----------|-------|-------------|---------------|
| 2608.03648 | **DEAR** — Dynamically Regulating Debate Relationships | Reformulates MAD as group-state problem: Selection RL-Agent picks which peers each LLM references (suppresses echo-chambers); Behavior RL-Agent adjusts generation style. MARL joint optimization. Superior performance + significantly fewer tokens vs. fixed debate topologies. | Hermes swarm consensus: randomize peer reference graph between debate rounds; penalize agents whose output closely echoes a prior agent's. |
| 2608.02827 | **Biased Consensus in Multi-Agent LLM Debates** | Consensus amplifies opinions of first-speakers regardless of ground-truth correctness. Order-randomization and confidence normalization are effective mitigations. | Hermes swarm consensus: randomize agent turn order per round; normalize confidence scores before tallying. |
| 2608.05956 | **Certifying Collective Reasoning via Koopman Operator Theory** | Formal convergence certificates for multi-agent consensus: can prove whether a debate topology converges within N rounds with high probability. | Can gate when a Hermes consensus loop may terminate vs. must continue deliberating — formal stopping criterion. |
| 2608.03421 | **Misinformation Derails Collective Fact Recovery** | A single misinformed agent can dominate a majority-correct network; communication graph topology, not just vote count, determines robustness. | For Hermes research tasks, isolate subagents relying on stale cached web content (e.g. separate node in communication graph) to prevent contamination of correct majority. |

---

## 4. Skill / Tool Learning: Composition, Selection, Transfer

| arXiv ID | Title | Key Finding | Hermes Signal |
|----------|-------|-------------|---------------|
| 2608.02356 | **SkillTrace** — Query-Skill Graph for Composable LLM Agents | Three-level graph: compositional query hierarchy → similarity-to-skill-library → skill dependency propagation. Finds complete executable skill compositions, not just individually relevant skills. 53.17% SkillsBench, 91.43% ALFWorld — SOTA. CODE AVAILABLE. | Hermes skills-as-markdown: add `requires:` YAML frontmatter field listing prerequisite skills; SkillTrace's dependency propagation is the loading logic. Fixes skill composition failures where a prerequisite is missed. |
| 2608.04719 | **Canary Tools** — Diagnosing Tool-Selection Reasoning | 6-type canary taxonomy planted in MCP tool set: semantic decoys, parameter traps, capability mirages, prerequisite blindness, temporal decoys, granularity traps. CSR varies 36× across models; capability mirages uniquely trap frontier models. Claude Opus 4.8 lowest CSR. CODE AVAILABLE (8,640 runs). | Plant canary probes in Hermes tool schemas during skill development/testing. Use the 6-type taxonomy as test checklist for every new Hermes tool. |
| 2608.06811 | **PMCoder** — Coupling Planning with Episodic Memory | Bidirectional plan↔memory coupling: current plan phase conditions retrieval; memory trajectory statistics detect stuck states and trigger replanning. +5.0pp on SWE-bench Verified; works across Claude Haiku 4.5, DeepSeek-V4-Flash. CODE AVAILABLE. | Hermes coding subagents: retrieve different session history slices in "exploration" vs "implementation" vs "verification" phases, not the same FTS5 query throughout. |
| 2608.05573 | **SkillTV-Bench** — Skill-Aware Trajectory Verification | 681-case benchmark (50 tasks, 11 domains). Introduces SkillTV-Evolve: JudgeSkill that guides agent-judge to plan targeted inspections + evidence-grounded verdicts. Automated evolution loop refines JudgeSkill from misjudged cases. +14.8pp accuracy on benchmark. CODE AVAILABLE (github.com/HanZhi306/SkillTV-Bench). | Add a JudgeSkill: a verification skill that reads another skill's YAML frontmatter (expected behavior) and checks whether the trajectory actually executed it before task sign-off. |

---

## 5. Ontology / Knowledge Graph: Evolution, Entity Resolution, Temporal KGs

| arXiv ID | Title | Key Finding | Hermes Signal |
|----------|-------|-------------|---------------|
| 2608.01904 | **CoEvoKG** — Co-Evolving Knowledge Graphs with Self-Evolving Search Agents | KG generates RL training tasks (multihop QA from entity chains); agent writes successful search trajectories back to KG as enriched evidence on nodes/edges. +10–11.6 macro-average points over base models on 6 QA benchmarks. CODE AVAILABLE (github.com/lazzy1225/CoEvoKG). | Graphiti+Hindsight co-evolution: successful tool-use trajectories distilled into Graphiti facts, which seed future skill lookup and session retrieval. The CoEvoKG loop at agent-memory scale. |
| 2608.07023 | **Agentic Hybrid KG Generation** for Multilingual Skill Taxonomies | Five-stage: entity reconciliation → multilingual canonicalization → active curation → deduplication → iterative recovery of unmapped concepts. Reflexion pattern for self-healing. Five European languages from noisy HR text. | Hermes skill library has same "noisy text → structured taxonomy" problem. Active curation + deduplication stages applicable to skill-library consolidation audit runs. |

---

## 6. Agent Self-Improvement: Reflection, Error Correction, Trajectory Optimization

| arXiv ID | Title | Key Finding | Hermes Signal |
|----------|-------|-------------|---------------|
| 2608.06701 | **LivePlan** — Online Monitoring and Corrective Steering | Deterministic rule-based monitor detects trajectory problems without LLM; advisor LLM called only on trigger. +9.9% average resolution on SWE-bench at $0.08/instance additional cost. Gains concentrate on medium/hard instances. | SQL-backed loop watchdog in Hermes: track (tool_name, success, result_hash) per turn; trigger corrective prompt after N consecutive failures of same tool — no LLM for monitoring. |
| 2608.09885 | **SHE** — Trajectory-Driven Safety Harness Evolution | 4-artifact harness (System Prompt, Rule Bank, Safety Memory, Tool Policy) with attribution-guided evolution: trajectory failures → structured diagnosis → artifact-specific refinement. 3.1× ASR reduction. Generalizes to unseen risks. CODE AVAILABLE (github.com/RainbowQTT/SHE). | 1:1 Hermes mapping: System Prompt → config.yaml, Rule Bank → skill files, Safety Memory → Hindsight safety-tagged facts, Tool Policy → MCP permissions. SHE formalizes skill-file patching as the correct response to trajectory failures. |

---

## 7. Novel Benchmarks (Post August 2026)

| arXiv ID | Title | Key Finding | Hermes Signal |
|----------|-------|-------------|---------------|
| 2608.00805 | **AgentSLABench** — Agents Under Resource Constraints | 16-task framework measuring correctness + latency + cost + CPU/memory/network under declared budgets. Introduces EASR (Efficiency-Adjusted Success Rate = success weighted by resource consumption). Specialized agents 100% on 3/5 core tasks; general baselines fail 4/5. CODE AVAILABLE (github.com/MeherBhaskar/agentslabench). | Adopt EASR as primary metric for Hermes skill benchmark runs — success at excessive token cost is penalized. |
| 2608.05573 | **SkillTV-Bench** | (See §4 above) | Skill-aware trajectory verification — 681 cases, 11 domains. |
| 2608.06909 | **Long-Horizon Agent Trajectory Attribution** | Unified annotation schema across heterogeneous trajectories; 1,300+ annotated cases (task-aligned, unsafe, safety-refusal). Provides reusable "annotation skill" for standardizing new trajectories. CODE AVAILABLE (github.com/chenjing-2024/agent-trajectory-attribution). | Adopt annotation skill to tag Hermes SQLite session logs; attribute skill failures to specific trajectory components (planning / tool-call / verification phase). |
| 2608.02444 | **ParEvalLayer** — Partial Agent Evaluations (ACM AIMLSystems 2026) | Decision layer applying comparison policy to paired agent system outcomes; enables early stopping when sufficient evidence is collected. Three benchmarks reach confident verdict after only 15–25% of tasks. | When A/B testing Hermes skill variants, use ParEvalLayer's early-stopping framework to terminate evaluation runs when sufficient evidence is collected. |

---

## Methodology Note — How These Papers Were Found

Standard approach for incremental delta sweeps against a known baseline (Aug 2026):

1. **arXiv category listing walk** (`web_extract` on `arxiv.org/list/cs.AI/current` and `arxiv.org/list/cs.MA/current`) — provides the last ~2 weeks of papers sorted by submission date BEFORE they are indexed by search engines. This is the highest-yield step for very recent papers.
2. **Batched `web_extract` on specific arXiv abs pages** (≤5 per call) — fastest way to get full abstracts once IDs are known.
3. **Read cached `.md` files** from prior `web_extract` calls — when a page was already fetched in the same session, read from cache (printed file path) rather than re-fetching.
4. **Targeted `web_search` queries** per topic axis — used to discover papers not on the listing pages.

The listing-walk approach (steps 1–2) recovered ~70% of papers found; keyword search (step 4) added ~30%.

Non-English sources (CNKI, J-STAGE, RISS, Cyberleninka, HAL) yielded no papers not already on arXiv for this domain at this recency window. One French-affiliated paper (2608.07023) appeared on arXiv. For HAL-exclusive papers, query `hal.science/search/index/?q=LLM+agent+memory&rows=30&sort=producedDate_tdate+desc` directly.
