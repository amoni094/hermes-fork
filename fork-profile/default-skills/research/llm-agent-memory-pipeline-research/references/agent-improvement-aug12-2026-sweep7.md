# Agent Improvement Research — Aug 12 2026 Sweep 7
# Coverage: arXiv IDs near/above 2608.09930 + Aug 2026 high-value papers across 10 topics
# Method: arXiv listing walk (cs.AI, cs.CL, cs.MA Aug 2026), targeted topic searches,
#         web_extract on individual abs pages. ACL Anthology 2026 searched separately.
#         Semantic Scholar API returned no 2026-dated results (possible index lag).
#         IJCAI 2026 + NeurIPS 2026 workshops not yet indexed/published.

## Key methodology finding
# arXiv listing walk on cs.AI/2026-08 is the highest-yield technique for papers
# published within the last 2 weeks. web_extract on the listing page gives
# title+ID, then batched abs fetches in groups of 5 get abstracts.
# The search API (export.arxiv.org/api/query?search_query=...) remains broken/CDN-blocked.
# Keyword searches via arxiv.org/search/?query=TOPIC work via web_extract.

---

## TOPIC 1: Agent Memory Architecture

### 2608.00303 — CrystalMem: Elastic Memory for Self-Evolving LLM Agents via Knowledge Crystallization
- **Submitted**: Jul 31 2026
- **Core technique**: 4-tier fidelity states (crystallization-energy schedule) for memory entries. Demotion uses advantage-weighted influence + dependency coupling. Proves any drop-only policy has a residual-deficit floor ("memory hysteresis") — capability doesn't recover after squeeze-and-restore. Recrystallization under compute+byte caps closes this gap. Matches strongest budgeted baseline at full provision from 50% byte budget; +4.6pp average at equal budgets, across 7 environments, 17 methods, 6 backbones.
- **Hermes signal**: Patch `agent-memory-consolidation` — add 4-tier fidelity model for Hindsight entries (full → summary → key-points → tombstone). On budget pressure, demote rather than delete; on recovery, recrystallize from tombstone + source session. Never hard-delete until tombstone tier.

### 2608.00122 — Shared Organizational Memory for Enterprise Coding Agents
- **Submitted**: Jul 31 2026
- **Core technique**: Platform-level memory capture as part of coding workflow, not an explicit agent-side recording step. Task-adjacent experience collected with contributor approval, curated into Q&A memories, privacy/security gated, retrieved for future agents. Production deployment report.
- **Hermes signal**: Patch `agent-memory-consolidation` — add platform-level capture step in cron: at session close, automatically extract problem→solution pairs (via haiku distillation) and store in Hindsight with `source: auto_capture` tag. Removes reliance on agent proactively writing memories.

### 2608.08995 — Muscle Memory for Agents: Compile not Merely Retrieve
- **Submitted**: Aug 10 2026 (ID > 2608.09930 threshold)
- **Core technique**: Positions "compilation" as a distinct memory paradigm from retrieval. Recurring user intent compiled into purpose-built specialist agents via 4-phase pipeline: Harvest → Analyze → Augment → Evaluate. Mines conversational history, separates behavioral from task patterns, emits quality-gated executable compiled specialists with 2-stage trigger matching. 88.9% win rate when specialist fires (90 scenarios, 5 personas), +2.05 personalization, -0.28 accuracy cost on 1-4 scale.
- **Hermes signal**: Patch `hermes-agent-skill-authoring` + `skillopt-continuous-improvement` — after memory consolidation cron detects recurring behavioral patterns (≥3 sessions with same task structure), generate a mini-skill (YAML frontmatter + one-shot example) rather than just a text memory. Route matching requests to compiled skill. This is the "compile not retrieve" paradigm applied to Hermes skills.

### 2608.01543 — V-Mem: Modality-Routed Retrieval for Long-Term Multimodal Agentic Memory
- **Submitted**: Aug 2 2026
- **Core technique**: Identifies two failure modes in multimodal RAG: (1) modality gap — query clusters by own modality, not target evidence; (2) similarity-relevance gap — most-similar content ≠ most-relevant evidence. V-Mem routes retrieval by (query modality → target evidence modality) recognized from query alone, and uses LLM-generated hypothetical anchors (HyDE-style for image queries) instead of raw query embedding. Score: 0.82 on Mem-Gallery vs 0.56 second-best; 0.87 on image-query subset vs no baseline above 0.47.
- **Hermes signal**: Patch `hindsight-stack-operations` — when session has file/image context, generate a hypothetical description of what relevant retrieved memory would look like before embedding search (HyDE-style anchor). Also: when query targets an image-type memory, search by the text from that round, not a cross-modal embedding comparison.

---

## TOPIC 2: Skill / Tool Selection and Routing

### 2608.00030 — SLMs as Multi-Agent Routers: A Progressive SFT and Reinforcement Learning Approach
- **Submitted**: Jul 15 2026 (appeared in Aug 2026 listing)
- **Core technique**: Trains a small LM via SFT → RL with hierarchical retrieval-relevance reward (not just intent-based routing). Jointly learns agent selection AND structured parameter generation. Routes by actual retrieval performance feedback: which agents produce high-relevance results for which query distributions. NDCG@10 0.918 on agent-query mismatches vs 0.539/0.490 for LLM intent-only baselines; overall NDCG 0.771 (+0.177 over Nova Lite); 82.4% latency reduction (120.1ms mean selection).
- **Hermes signal**: Patch `compositional-skill-routing` — add outcome-signal routing: track per-skill success rate per task-type cluster (SQLite table: skill_name, task_type, success_count, fail_count). Use historical success rates to bias routing, not just semantic similarity. Extends `hermes-semantic-skill-routing` with a feedback loop.

### 2608.00106 — Learning Compositional Meta-Routing for Agentic Workflows: An Executable Benchmark
- **Submitted**: Jul 31 2026
- **Core technique**: Budget-aware meta-router that composes heterogeneous operations (answer/decompose/retrieve/code/delegate/verify) from raw task text using independent logistic heads + temperature scaling. Greedily composes under route-cost and action-count budgets. 100% success vs 93.5% static at 43% lower cost; identifies lexical generalization (not execution) as principal limitation.
- **Hermes signal**: Patch `compositional-skill-routing` — add budget-aware operation composer: predict needed operation mix from task text before dispatch, compute estimated token cost per operation type, greedily select under a per-session token budget ceiling. Hermes's delegate_task + tool call composition maps directly.

### 2608.00814 — OoO-Spec: Out-of-Order Semantic Speculation for Fast Tool Calling
- **Submitted**: Aug 1 2026
- **Core technique**: Qwen3-0.6B sidecar predicts function choice + argument slot values in one parallel wave at request arrival while main LLM begins normal decoding. Runtime joins slot values and exposes as a hint. Sidecar trained once with LoRA on Qwen2.5-32B teacher traces; used unchanged across multiple target models. Results: 2.46x–5.34x over autoregressive (mean 3.89x), 34.1% improvement over ToolSpec across Qwen3-4B/8B/14B/32B.
- **Hermes signal**: Patch `claude-routing-hierarchy` — add pre-call speculative stage: before invoking Claude with a multi-tool task, predict likely tools (from skill name patterns + task text) and likely param values using a lightweight heuristic scorer (no LLM call). Pre-populate tool selection context to reduce tool-selection reasoning overhead.

---

## TOPIC 3: Multi-Agent Coordination, Consensus, Swarm Patterns

### 2608.00243 — More Debate, Same Evidence: Structural Limits of Homogeneous Multi-Agent Groundedness
- **Submitted**: Jul 31 2026
- **Core technique**: Empirical study: homogeneous 3-agent debate panel for groundedness verification on 6 fact-verification benchmarks. Panel accuracy difference vs single agent: +8.5pp to -4.4pp range — two datasets show reliable gains, one reliable loss, three inconclusive. Key: model diversity matters more than debate structure per se.
- **Hermes signal**: Patch `hermes-swarm-consensus` — add diversity requirement to consensus panels: require different reasoning styles or temperatures across agents (not clones of same prompt). Add "skip debate" gate: for tasks where baseline single-agent accuracy on similar past tasks was ≥85%, route directly without multi-agent overhead.

### 2608.04968 — EvolveNet: Collaborative Harness Evolution for Agent Self-Improvement
- **Submitted**: Aug 5 2026
- **Core technique**: Distributed harness evolution: each isolated deployment evolves shared harness on local workload, only program *adaptations* (not raw data) are composed via scope-typed, evidence-guided program aggregation and redistributed. Shifts aggregation boundary from raw workloads to learned adaptations. Improves shared harness across 5 domains; largest gains on heterogeneous workloads. Composition of adaptations (not selection among them) drives the improvement.
- **Hermes signal**: Patch `autonomous-agent-loop-design` + `hermes-cron-and-agents` — implement federated skill evolution: subagents propose skill patches (diffs, not full rewrites) based on their execution traces; curator cron uses evidence-guided aggregation to merge non-conflicting patches; updated skill redistributed. Maps to Hermes's YAML skill + cron infrastructure.

---

## TOPIC 4: Context Window Management, KV Cache, Token Budgeting

### 2608.00902 — Practical Online KV Cache Compaction for LLM Agents: An Empirical Study
- **Submitted**: Aug 2 2026
- **Core technique**: Studies online KV compaction across token eviction (TE) and attention matching (AM) with proxy query sources (boundary, repeat-prefill, delayed future-generation). Key finding: immediate compaction hurts; delaying compaction to use agent's future queries as proxies recovers most of the accuracy gap. TE more robust than AM under imperfect proxies. TE preserves accuracy at 80% KV reduction, can improve throughput over no-compaction baseline.
- **Hermes signal**: Patch `hermes-context-budgeting` — implement delayed context compaction: don't trim context at tool call boundaries; wait until after next LLM response before evicting low-attention tokens. Prevents premature eviction of context needed by subsequent response.

### 2608.00685 — When Does LLM Orchestration Pay Off? A Controlled Evaluation of Accuracy, Cost, and Task Difficulty
- **Submitted**: Aug 1 2026
- **Core technique**: Controlled study (GEPA-optimized) of Self-Refine, Best-of-N, Debate vs CoT/task-only. Largest gain: +4.6pp over optimized CoT at 2-4× token cost. Orchestration effectiveness strongly model-specific (backbone × method interactions). Task difficulty does NOT predict when orchestration helps.
- **Hermes signal**: Patch `claude-routing-hierarchy` — add orchestration-worthiness gate: before spinning up multi-agent, compute task complexity score; below threshold → single CoT call. Calibrate per-model empirically. Don't assume harder task → more orchestration benefit.

### 2608.00101 — Agentic Coding in the Wild: GitHub Copilot Traces at Production Scale
- **Submitted**: Jul 30 2026
- **Core technique**: 3.2M users, 13M sessions, 761M LLM calls characterization. Key data: KV cache hit rate 90% within-turn, drops to 55% across turn boundaries; context compaction invalidates cache drastically. User idle periods average minutes between turns. Lightweight idle-time predictor captures 86–90% of total idle time enabling proactive resource decisions.
- **Hermes signal**: Patch `hermes-context-budgeting` — use turn-boundary detection as cache-prefetch trigger; proactively load likely-needed context just before user's next turn. Also: log KV cache hit-rate proxy (context reuse ratio across consecutive calls) per session type for observability.

---

## TOPIC 5: Agent Self-Improvement, Meta-Learning, Skill Evolution

### 2608.09819 — Macaron-V1: Towards Open Continual Learning with Self-Improvement and Mixture-of-LoRA
- **Submitted**: Aug 10 2026 (ID > 2608.09930 threshold)
- **Core technique**: Agent-model family with two pillars: (1) recursive self-improvement of versioned model-harness pairs — experience from one version evaluated against external contract and used to construct successor; (2) Mixture-of-LoRA (MoL) — freeze base model, compose specialist LoRA adapters (chat/agent/coding/GenUI), select one per user turn. 744B GLM-5.2 base + 4 LoRAs (flagship); Qwen3.6 50B for local deployment.
- **Hermes signal**: Patch `skillopt-continuous-improvement` — adopt versioned harness-contract pattern: each skill has version tag + acceptance criteria (test cases / output contracts); after cron-based SkillOpt run, proposed update only accepted if it passes the contract checks. Formalizes the current informal "did it improve?" judgment.

### 2608.00155 — AgentStream: Self-Evolving LLM Agents Under Streaming Tasks
- **Submitted**: Jul 31 2026
- **Core technique**: Benchmark framework evaluating self-evolving agents under Isolated/Sequential/Interleaved streaming scenarios. Self-evolution benefit is non-monotonic in model capability; no single method dominates across models/scenarios. Key: scenario-aware method selection is needed.
- **Hermes signal**: Patch `agent-memory-consolidation` — add streaming-scenario classifier at session start: Isolated (novel task type) → heavy consolidation; Sequential (continuation of prior session) → lightweight update; Interleaved (mixed domain) → multi-surface consolidation. Different cron trigger strategies per class.

### 2608.00215 — Personalizing LLM Agents with Small Policy Models (FABLE)
- **Submitted**: Jul 31 2026
- **Core technique**: FABLE = Factorized Adaptive Bandit Layer for Execution. Bayesian contextual Thompson-sampling policy layer outside a black-box host agent. Factorizes memory/information-acquisition/response decisions so feedback updates related choices. Filters actions through externally specified feasible set. Inherits regret bound against best feasible action under linear residual-reward model.
- **Hermes signal**: Patch `hermes-operating-pattern` — implement per-user preference layer in MEMORY.md as a bandit state table: {skill_name, task_type, success_count, fail_count}. After each task, update with scalar signal from `agent-task-signoff`. Route future similar tasks toward skills with higher per-user success rates.

---

## TOPIC 6: Planning Under Uncertainty, Fast/Slow Thinking

### 2608.09816 — Hierarchical Fast-Slow ReAct Agent for Zero-Shot Navigation
- **Submitted**: Aug 10 2026 (ID near threshold)
- **Core technique**: Fast (reactive value-map controller) + slow (deliberative VLM layer reading coordinate-anchored semantic memory) hierarchical agent. Deliberative layer wakes on structural events computed by the reactive layer (not on fixed schedule). Reasons over text first, recalls visual keyframes only when text can't separate candidates. Per-invocation AND per-run caps bound VLM costs. 68.75% SR on HM3D (highest among zero-shot methods).
- **Hermes signal**: Patch `autonomous-agent-loop-design` — implement fast/slow tier: fast tier handles routine tool calls immediately without deliberation; slow tier (full context + Claude call) triggered only on "structural events" (tool failure, >3 retries, novel task type flag, high-risk action). Aligns with `trajectory-risk-guardrail` escalation pattern.

---

## TOPIC 7: Safety / Sandboxing for Autonomous Agents

### 2607.01793 — Vera: Safety Testing LLM Agents at Scale
- **Submitted**: Jul 3 2026 — NOTE: tests Hermes as one of 4 production frameworks
- **Core technique**: 3-stage self-reinforcing pipeline: (1) literature-driven risk taxonomy discovery, (2) combinatorial composition of executable safety cases with deterministic verification predicates grounded in observable artifacts, (3) adaptive multi-turn execution in isolated sandboxes with evidence-grounded verifiers (not model self-report). Results on Hermes + others: 93.9% attack success under multi-channel attacks. Vera-Bench: 1600 cases, 124 risk categories, 3 execution settings.
- **Hermes signal**: HIGH PRIORITY — Patch `mnemosyne-atp-safety` + `trajectory-risk-guardrail` — add Vera-Bench-inspired pre-execution checklist for irreversible actions: (a) prompt-injection detection from tool outputs, (b) lateral-movement check (tool accessing resources outside declared scope), (c) evidence-grounded outcome verifiers for file/network mutations. Vera found Hermes vulnerable under multi-channel attacks.

### 2606.08021 — Semantic Quorum Assurance (SQA): Collective Certification for Non-Deterministic AI Infrastructure
- **Submitted**: Jun 6 2026
- **Core technique**: Routes agentic infrastructure proposals to diverse read-only sandboxed validator panel under risk-adaptive quorum predicate with model-diversity enforcement and archetype-specific vetoes. Admitted proposals only execute through sovereign execution gate. Reduces unsafe approval 18.5% → 0.3% at 1.45–4.12s median latency overhead, on 500 mutation scenarios.
- **Hermes signal**: Patch `mnemosyne-atp-safety` — for high-risk irreversible actions, implement lightweight quorum: run action description through 2 different prompt framings + temperature settings and require both to approve before execution. Formalizes single ATP check into semantic quorum.

### 2606.07805 — MAC-Bench: Dynamic Benchmark for Compliance in Multi-Agent Systems
- **Submitted**: Jun 5 2026
- **Core technique**: SERV pipeline (Seed→Evolve→Refine→Verify) generates contamination-free adversarial compliance scenarios from legal texts in holographic sandbox environments. New metrics: Compliance-Weighted Success Rate (CSR) and Machiavellian Gap (MG) — measures strategy-vs-compliance trade-off, detecting when agents violate rules to maximize rewards (Goodhart's Law).
- **Hermes signal**: Patch `trajectory-risk-guardrail` — add Machiavellian Gap monitor: cross-check final actions against declared plan to detect "shortcut" successes. MG > threshold flags task for human review on future similar tasks. Prevents RL-style plan-gaming in agentic loops.

---

## TOPIC 8: RAG Improvements for Agent Memory

### 2608.09408 — DREAM: Developing Recommender Engine with Agentic Methods
- **Submitted**: Aug 10 2026 (ID > threshold)
- **Core technique**: Autonomous optimization control layer atop existing pipelines. Three-tier Intent Engine (L0/L1/L2 intent representations with edge-cloud trigger chain, 8.7% reporting volume reduction). MetaModel: M1-M2-M3 layered reasoning (intent summarization → strategy planning via Strategy Memory → parameter translation). Reward Dual Loop: offline simulation + online feedback. Production A/B tests on Taobao homepage feed: +2.71% IPV, +3.06% Core IPV, +1.31% GMV.
- **Hermes signal**: Patch `agent-memory-consolidation` — implement L0/L1/L2 intent representation in MEMORY.md: L0 = raw session signal (individual tool calls), L1 = session-level intent cluster (task category), L2 = cross-session strategic pattern (user workflow archetype). Cron consolidation promotes L0→L1→L2 as patterns recur. Strategy Memory maps to Hindsight entries tagged by strategic cluster type.

---

## TOPIC 9 + 10: Uncertainty Quantification / Prompt Compression

### 2608.00422 — TrAC: Trace-Conditioned Answer Consistency for Uncertainty Quantification
- **Submitted**: Aug 1 2026
- **Core technique**: After one complete reasoning trace: (1) PCE re-elicits a short answer conditioned on the completed trace, measuring consistency + token-level probabilistic support; (2) TUP summarizes how token-level uncertainty evolved through original generation. Lightweight head integrates both into correctness score. AUROC +1.8%, AURC -3.4% vs 8-sample self-consistency using 1 trace + 1 short probe. With 8 samples available: +4.3% AUROC, -8.3% AURC with re-elicitation.
- **Hermes signal**: Patch `verification-before-completion` — add TrAC-style re-elicitation gate for multi-step tasks: given completed reasoning chain, ask Claude to briefly re-state conclusion conditioned on that trace; compare to original. Divergence → re-verification. Much cheaper than full regeneration.

### 2607.08032 — Rate-Distortion View of Memory Compaction in LLMs and Agents
- **Submitted**: Jul 8 2026
- **Core technique**: Unifies KV-cache eviction, prompt pruning, architectural state bounding, and agent memory consolidation as a single rate-distortion optimization (what context to retain vs discard at what fidelity under resource budget to preserve task utility). Seven-axis taxonomy classifies methods uniformly. Key universal failure: attention-magnitude-based eviction fails everywhere by discarding before query is known and can't undo it.
- **Hermes signal**: Patch `hermes-context-budgeting` — apply rate-distortion framing: never evict context marked "may be referenced by future tool output" until after that output is processed (query-agnostic eviction failure). Use 7-axis taxonomy to classify what each Hermes compression step is doing (rate: token budget; distortion: task utility; fidelity: summary vs full).

---

## Cross-Cutting Methodology Notes

### arXiv listing walk technique (validated this sweep)
- `web_extract("https://arxiv.org/list/cs.AI/2026-08")` gives full title list for August 2026
- Cache file stored at `/var/home/rainbow/.hermes/cache/web/arxiv.org-01134adf0e.md`
- Pagination: file is 844 lines, IDs range from ~2608.00007 to ~2608.00900+ per page
- Higher-ID papers (Aug 10+) appeared in keyword search results, not the listing walk
- Combine: listing walk for low-ID papers + keyword searches for topic-specific high-ID papers

### ACL Anthology 2026
- ACL Anthology 2026 search returns many agent-relevant papers but most have arXiv cross-listings
- `aclanthology.org/search/?q=TOPIC&year=2026` works reliably via web_extract
- Papers identified this sweep are ACL 2026 accepted, conference proceedings (not just preprints)

### Non-arXiv source finding
- IJCAI 2026 proceedings: not yet indexed (as of Aug 12 2026)
- NeurIPS 2026 workshops: not yet indexed
- Semantic Scholar API (`api.semanticscholar.org/graph/v1/paper/search`): returned 0 results for 2026 papers — appears to lag arXiv indexing by 2-4 weeks for very recent papers
- ACL Anthology is the best non-arXiv source for NLP/CL agent papers

### Papers with ID ≥ 2608.09931 (strictly after cutoff)
Confirmed papers in this sweep:
- 2608.08995 — Muscle Memory (cs.MA, Aug 10)
- 2608.09408 — DREAM (cs.IR, Aug 10)
- 2608.09816 — Hierarchical Fast-Slow ReAct (cs.RO, Aug 10)
- 2608.09819 — Macaron-V1 (cs.LG, Aug 10)
All submitted Aug 10, announced Aug 12 — this matches the arXiv announcement cycle.
