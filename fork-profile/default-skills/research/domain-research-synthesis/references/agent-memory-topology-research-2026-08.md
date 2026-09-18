# AI Agent Memory Topology & Architecture — 2026 Research Knowledge Bank
*August 2026 | Verified arXiv IDs + Hermes gap analysis*

## Already Implemented in Hermes Stack (do not re-implement)
ACM 5-primitives (2607.21503), MemoryOS (2506.06326), NEMORI (2508.03341), SCM (2604.20943), FFD taxonomy (2512.13564), MRAgent Cue-Tag-Content (2606.06036), A-MEM (2502.12110), AutoMem (2607.01224), Selective Persistent Memory (2607.09493), FARMA/SENTINEL (2607.05029), GhostWriter/AM-Sentry (2607.06595).

---

## NEW PAPERS — Verified (June–August 2026 Focus)

### MemCon — Memory as a Controlled Process (MDP)
- **ID**: `2607.13591` | Jul 15, 2026 | UCLA/MIT+
- **Result**: +15.2 task success points (6 benchmarks, 3 frameworks, 3 LLMs); token cost -5–20%
- **Key idea**: All memory routing decisions (retrieval timing, plan injection, consolidation triggering, forgetting) modeled as MDP, solved by lightweight tabular contextual bandit (UCB exploration). Backend-agnostic, converges within tens of tasks from binary task-success feedback. No pretraining, no extra LLM calls.
- **Hermes gap**: Hermes uses static heuristics for all memory operations. MemCon's bandit policy would learn per-context-type optimal timing.

### Agent-Native Memory System? (SIGMOD 2026 Tutorial)
- **ID**: `2606.24775` | Jun 23, 2026 | Tsinghua/PKU/Zhejiang
- **Result**: 12 systems × 5 workloads × 11 datasets. "No single architecture dominates — effectiveness depends on workload-bottleneck alignment."
- **Key idea**: 4-module decomposition: (1) representation+storage, (2) extraction, (3) retrieval+routing, (4) maintenance. Localized maintenance more cost-efficient than global reorganization.
- **Code**: github.com/OpenDataBox/MemoryData
- **Hermes gap**: No systematic maintenance module; no workload profiling.

### MemOps — Lifecycle Operations Benchmark
- **ID**: `2607.12893` | Jul 14, 2026 | mixed
- **Result**: Session-level retrieval beats turn-level; long-context models weak at ordered memory-state reconstruction. QA metrics mask lifecycle failures.
- **Key idea**: Memory = lifecycle of REMEMBER, FORGET, UPDATE, REFLECT, COMPOSE operations. Each event: {trigger, target, scope, state_transition, supporting_evidence}.
- **Hermes gap**: No structured lifecycle traces in Graphiti writes. Adding MemOps schema to edges would enable diagnostic analysis.

### TRUSTMEM — Trustworthy Memory Consolidation
- **ID**: `2606.25161` | Jun 23, 2026 | Amazon
- **Result**: -40.1% omission, -79.1% corruption, -50.0% hallucination vs. strongest per-category baseline. +12.14 F1 on HaluMem. SOTA on MemoryAgentBench, HaluMem, Mem-alpha.
- **Key idea**: Memory Transition Verifier checks 3 criteria before any write: (1) Coverage—no prior facts dropped, (2) Preservation—no unintended corruption, (3) Faithfulness—no hallucinated additions. Constructs preference pairs → preference-guided RL on memory update behavior.
- **Hermes gap**: MEMORY.md/USER.md writes have no transition verification. This is Tier A (immediate win).

### Shared Organizational Memory for Enterprise Coding Agents
- **ID**: `2608.00122` | Jul 31, 2026 | Industry (production deployment)
- **Key idea**: Platform-level experience capture (not agent-level). Contributor-approved QA memory schema. Security/privacy gating before persistence. Captures task-adjacent experience automatically.
- **Hermes gap**: No cross-session organizational curation workflow with approval gates.

### Organizational Memory for Agentic Business Process Execution
- **ID**: `2607.03228` | Jul 3, 2026 | SAP Research
- **Key idea**: Shared reference layer of procedural knowledge, separate from episodic/semantic. Governance layer for consistency across agents.
- **Hermes gap**: No procedural memory surface. Skills are closest analogue but not agent-consumable at runtime.

### Memory Architecture Drives Language Emergence (multi-LLM)
- **ID**: `2607.00233` | Jun 30, 2026 | Univ. Alberta
- **Key idea**: Memory topology shapes emergent communication protocols. Structured memory → compositional language; flat memory → degenerate codes. Chain-of-thought/scratchpad are memory topology choices.
- **Hermes gap**: Flat MEMORY.md. Structured memory types would improve multi-turn coherence.

---

## NEW PAPERS — Verified (May 2026, not yet in stack)

### RecMem — Recurrence-Based Consolidation (ACL 2026 Findings)
- **ID**: `2605.16045` | May 15, 2026 | CUHK
- **Result**: -87% token cost for memory construction vs. 3 SOTA systems while exceeding accuracy.
- **Key idea**: Subconscious memory layer (lightweight embedding-indexed raw interactions). LLM invoked only when sufficient recurrence observed for semantically similar interactions. Semantic refinement recovers fine-grained facts missed during extraction. "Lazy consolidation."
- **Hermes gap**: A-MEM runs LLM enrichment on every write. RecMem trigger = recurrence threshold, not every interaction. **Tier A immediate win** — 87% cost reduction.

### MEMTIER — Tripartite Tiered Architecture
- **ID**: `2605.03675` | May 5–25, 2026 | Ben-Gurion University
- **Result**: LongMemEval-S: 5% → 38% Acc (+33pp) with Qwen2.5-7B on 6GB consumer GPU. Single-session recall 0.686–0.714 with DeepSeek-V4-Flash pre-population. Temporal reasoning 0.323, multi-session synthesis 0.173.
- **Key idea**: 3 tiers: T1 episodic JSONL (always written, lightweight) → async consolidation daemon → T2 semantic (promoted facts). 5-signal weighted retrieval: temporal recency + semantic similarity + frequency + confidence + user-signal (attention-attributed cognitive weight).
- **Hermes gap**: Hermes has 3 independent silos (session_search, Hindsight, Graphiti) with no promotion daemon and no 5-signal fusion. **Tier B medium-term.**

### H-Mem — Hybrid Tree+Graph Memory
- **ID**: `2605.15701` | May 15, 2026 | HK institutions
- **Result**: SOTA on 3 agent memory benchmarks for QA task.
- **Key idea**: Temporal+semantic **tree** (short-term episodes evolve into long-term summaries with parent/child links) + knowledge **graph** (entity relationships). Hybrid retrieval exploits both. Tree provides progressive summarization; graph captures relationships.
- **Hermes gap**: Graphiti = graph-only, Hindsight = vector-only. Missing temporal tree for tracking fact evolution. **Tier B.**

### Memory-R2 — Fair Credit Assignment in Multi-Session RL
- **ID**: `2605.21768` | May 20, 2026 | LMU Munich MCML
- **Result**: Solves fundamental RL pathology for multi-session memory training. LoGo-GRPO = local credit (current session ops) + global credit (how current edits affect future sessions).
- **Hermes gap**: Training infrastructure gap — any RL training of Hermes memory ops needs LoGo-GRPO, not standard GRPO.

### MemGraphRAG — Multi-Agent Graph RAG (KDD 2026)
- **ID**: `2606.00610` | May 30, 2026 | XMU DeepLIT
- **Result**: SOTA on multiple benchmarks with comparable efficiency.
- **Key idea**: 3-layer memory: raw passages → extracted facts → abstract schema. Multi-agent society with SHARED memory providing global context during extraction — dynamic conflict resolution.
- **GitHub**: github.com/XMUDeepLIT/MemGraphRAG (132 stars)
- **Hermes gap**: Graphiti constructs graph per-episode without global coherence checking. **Tier B.**

---

## IMPORTANT EARLIER PAPERS (Jan–Apr 2026, not yet in stack)

### MAGMA — Multi-Graph Architecture (ACL 2026)
- **ID**: `2601.03236` | Jan 6, 2026 | ACL anthology: 2026.acl-long.1709
- **Result**: LoCoMo judge score 0.70 — highest known as of early 2026 (MemoryOS 0.553, A-MEM 0.58, NEMORI 0.59)
- **Key idea**: Multiple concurrent graphs with independent retrieval policies: Entity graph, Event graph, Relationship graph. Decoupled retrieval logic per graph type.
- **GitHub**: github.com/FredJiang0324/MAGMA (149 stars)
- **Hermes gap**: Single mixed Graphiti graph. Multi-graph schema would allow different eviction/retrieval policies per memory type.

### EverMemOS — Self-Organizing Memory OS (ACL 2026)
- **ID**: `2601.02163` | Jan 5, 2026 | ACL anthology: 2026.acl-long.2125
- **Result**: SOTA on multiple long-context memory benchmarks.
- **Key idea**: Engram-inspired lifecycle. **MemCell schema**: {episodic_trace, atomic_facts[], foresight_signals[], timestamp, stability_score}. Foresight signals = predictions about future relevance. Self-organizing consolidation with conflict resolution.
- **Hermes gap**: No Foresight signals in Hermes memory entries. Adding `predicted_future_relevance` at write time enables proactive retrieval.

### AgeMem — Unified LTM/STM RL (ACL 2026)
- **ID**: `2601.01885` | Jan 2026 | ACL anthology: acl-long.981
- **Result**: Significantly outperforms strong baselines on 5 long-horizon benchmarks.
- **Key idea**: LTM tools (ADD, UPDATE, DELETE) + STM tools (RETRIEVE, SUMMARY, FILTER) unified into single RL policy via 3-stage progressive RL + step-wise GRPO.
- **Hermes gap**: Hermes treats STM (context window) and LTM (Graphiti/Hindsight) separately. Unified policy would learn when to SUMMARY→LTM vs. FILTER-from-STM.

### Memory-R1 — RL Memory Operations (Data-Efficient)
- **ID**: `2508.19828` | Aug 27, 2025 (updated Jan 14, 2026) | Fudan/Tencent
- **Result**: With only 152 training QA pairs, beats MemP, Mem0, A-MEM, Zep on LoCoMo/MSC/LongMemEval across 3B–14B models.
- **Key idea**: Two RL-trained agents: Memory Manager (ADD/UPDATE/DELETE/NOOP via PPO or GRPO) + Answer Agent (distill relevant memories + answer).
- **Hermes gap**: A-MEM write enrichment is heuristic. RL-trained memory manager is SOTA direction. Even 200 Hermes session examples would be sufficient.

### LLMA-Mem — Multi-Agent Memory Topologies
- **ID**: `2604.03295` | Mar 27, 2026 | Illinois Tech et al.
- **Result**: Smaller teams with better memory outperform larger teams. Non-monotonic scaling.
- **Key idea**: 3 topology configurations: Local (private), Shared (common pool), Hierarchical (broker agent mediates). Hierarchical wins for long-horizon tasks.
- **Hermes gap**: No multi-agent memory topology protocol. Hierarchical maps to Graphiti MCP pattern but not instantiated for parallel subagents.

### SSGM — Memory Governance Framework
- **ID**: `2603.11768` | Mar 12, 2026
- **Key idea**: 3-gate architecture: Consistency Verification Gate + Temporal Decay Modeling + Dynamic Access Control. Taxonomy of 7 memory corruption risks including topology-induced leakage and semantic drift. Temporal decay model prevents old project context from polluting current retrieval.
- **Hermes gap**: FARMA/SENTINEL covers injection at write time; SSGM covers post-write drift prevention (complementary). Adding temporal decay scores to Graphiti edges is Tier A.

### MemRL — Runtime RL on Episodic Memory
- **ID**: `2601.03192` | Jan 6, 2026 | Fudan/Tencent/SEU (14 authors)
- **Result**: Superior stability vs. MemP baseline; lower forgetting rate growth over episode count.
- **Key idea**: Decouples stable cognitive reasoning from dynamic episodic memory. RL policy at runtime decides what to write/update/evict. Addresses stability-plasticity tradeoff.
- **Hermes gap**: Hindsight grows monotonically. RL-based eviction policy prevents retrieval noise accumulation.

### Graph-Based Agent Memory Taxonomy (PolyU Survey)
- **ID**: `2602.05665` | Feb 5, 2026 | PolyU DeepLIT
- **GitHub**: github.com/DEEP-PolyU/Awesome-GraphMemory
- **Key ontology**: Taxonomy axes: short-term vs. long-term × knowledge vs. experience × non-structural vs. structural. **Topology Optimization** as first-class memory op: restructure graph edges to shorten paths between frequently co-accessed concepts.
- **Hermes gap**: Graphiti lacks edge-weight optimization over time. Knowledge vs. experience split not formally enforced.

---

## QUANTIFIED RESULTS SUMMARY (for quick reference)

| Paper | Metric | Result |
|-------|--------|--------|
| MemCon 2607.13591 | Task success delta | +15.2 points |
| MemCon 2607.13591 | Token reduction | 5–20% |
| TRUSTMEM 2606.25161 | Corruption reduction | -79.1% |
| TRUSTMEM 2606.25161 | Hallucination reduction | -50.0% |
| TRUSTMEM 2606.25161 | HaluMem F1 | +12.14 |
| RecMem 2605.16045 | Token cost reduction | up to -87% |
| MEMTIER 2605.03675 | LongMemEval-S accuracy | 5% → 38% |
| MAGMA 2601.03236 | LoCoMo judge score | 0.70 (vs. MemOS 0.553) |
| Memory-R1 2508.19828 | Training data | 152 QA pairs sufficient |
| CORAL 2604.01658 | Improvement rate | 3–10× vs. baseline |

---

## HERMES IMPLEMENTATION PRIORITY TIERS

**Tier A — Immediate wins (< 2 days)**
- A1: Add lifecycle tags to Graphiti writes (MemOps schema)
- A2: TRUSTMEM 3-criteria write verifier for MEMORY.md/USER.md
- A3: Temporal decay scores on Graphiti edges (SSGM)
- A4: Recurrence threshold before LLM consolidation (RecMem — 87% cost reduction)
- A5: Workload-type retrieval routing (SIGMD 2606.24775)

**Tier B — Medium-term (1–2 weeks)**
- B1: Async T1→T2 consolidation daemon (MEMTIER)
- B2: Foresight signals in memory writes (EverMemOS)
- B3: Multi-graph schema in Graphiti (MAGMA — separate entity/event/relationship graphs)
- B4: Conflict detection during graph construction (MemGraphRAG)
- B5: Session-level vs. turn-level retrieval aggregation (MemOps)

**Tier C — Research-grade (2+ weeks)**
- C1: RL-learned memory operations (Memory-R1/AgeMem pattern, ~200 session examples)
- C2: Bandit-based retrieval timing policy (MemCon)
- C3: Multi-agent hierarchical memory topology (LLMA-Mem)
- C4: Organizational memory surface (cross-session QA memory bank)
- C5: Tree+graph hybrid structure (H-Mem)

**Tier D — Evaluation (instrumentation only)**
- D1: LoCoMo baseline benchmarking
- D2: HaluMem evaluation for Hermes write operations
- D3: Forgetting rate tracking for Hindsight (non-retrieved entries = eviction candidates)
- D4: MemOps lifecycle operation tracing

---

## SOCIAL/COMMUNITY CONSENSUS (August 2026)

**Reddit consensus** (via web_search snippets):
- Pure vector stores: universally considered insufficient for production agents
- Knowledge graph layer: now considered necessary, not optional
- RL-trained memory operations (Memory-R1, AgeMem): seen as breakthrough direction
- Lazy consolidation (RecMem pattern): praised for practical token cost management
- Memory security/poisoning: increasingly prioritized concern

**Hacker News on SIGMD 2606.24775**: "The 4-module decomposition finally gives engineers a vocabulary for discussing this." Strong interest in "no single architecture dominates" finding. Memory-as-infrastructure vs. memory-as-agent-capability debate; infrastructure camp winning.

**Chinese community (Zhihu)**: Strong preference for explicit layered architectures over flat vector stores. Graph-based memory (KG + episodic vector) considered production-ready. BUPT MemoryOS team + Huawei published comprehensive 4W framework (Who/What/When/Why memory classification).

**Japanese community**: No J-STAGE papers found for agent memory topology. Community interest in governance/privacy-preserving memory (consistent with SSGM themes).

---

*Research date: August 8, 2026. Full report: /tmp/memory-topology-research-2026-08.md*
