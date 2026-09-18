# Multilingual + Novel Agent Research — Aug 13 2026 Sweep

*Sources: arXiv, HuggingFace Papers, GitHub direct extraction. SerpApi rate-limited throughout — all retrieval via web_extract on source URLs.*

---

## KEY PAPERS (6 categories, novel / not mainstream in English)

### 1. Memory Topology

#### AMD — Agent Memory Distillation (arXiv:2608.07169, Aug 7 2026)
**Authors:** Taeil Kim, Kangsan Kim, Sung Ju Hwang (KAIST, Korea)
**URL:** https://arxiv.org/abs/2608.07169
**Novelty:** Training-free 3-tier hierarchical memory with **proactive/reactive split**:
- **Workflow memory** — task-level strategy → inject PROACTIVELY at task start
- **Subtask memory** — behavioral examples at intermediate granularity → inject PROACTIVELY at task start
- **Function memory** — per-function calling conventions + pitfalls → inject REACTIVELY only on tool errors

**Results:** +27.2pp on AppWorld, +11.2pp BFCL V3, +3.4pp ToolSandbox for 4B–8B students with GPT-5-mini teacher. Subtask memory contributes the largest gains. 4B models benefit most.

**Hermes implementable pattern:**
```
On task start: inject [workflow_pattern] + [subtask_examples]  
On tool error: retrieve function_memory for that specific tool
```
Key insight: DO NOT front-load all memory — defer tool-specific memory until the tool actually fails.

---

#### PREPING — Pre-task Memory Construction (arXiv:2605.13880, May 2026)
**Authors:** Yumin Choi et al. (KAIST AI, Korea)
**URL:** https://arxiv.org/abs/2605.13880
**GitHub:** https://github.com/Dozi01/PREPING (4 stars, very new)
**Novelty:** Build procedural memory BEFORE any real user task using synthetic practice. Solves cold-start.

Architecture (Proposer→Solver→Validator loop):
- **Proposer** generates synthetic tasks conditioned on structured "proposer memory" (control state)
- **Solver** executes synthetic tasks in target environment
- **Validator** filters trajectories before insertion + provides feedback to Proposer

Key: benefit comes NOT from synthetic volume, but from Proposer-side control over feasibility, redundancy, and coverage + selective memory updates.

Results: 2.99× lower deployment cost on AppWorld, 2.23× lower on BFCL v3 vs online construction.

**Hermes application:** Run Proposer→Solver→Validator loop during skill onboarding to build function_memory before first real use.

---

#### LLMA-Mem — Flexible Memory Topologies for Multi-Agent (arXiv:2604.03295, Mar 2026)
**URL:** https://huggingface.co/papers/2604.03295 (Emory University)
**Critical non-obvious finding:** Team scaling is NON-MONOTONIC. Larger teams do NOT always outperform smaller ones. Smaller teams with better memory topologies beat larger teams without good memory.

Tested topologies:
- Shared global memory pool
- Per-agent private + selective merge
- Hierarchical (team-level + agent-level)

**Hermes signal:** Before adding subagents, invest in memory topology. Agents should "check out" shared knowledge rather than duplicate per-agent.

---

#### Structured Distillation for Personalized Agent Memory (arXiv:2603.13017, Mar 2026)
**URL:** https://huggingface.co/papers/2603.13017
**Key metric:** **11× token reduction** (371 → 38 tokens per exchange), 96% of verbatim MRR retained.

4-field compound object per exchange:
```json
{
  "exchange_core": "...",
  "specific_context": "...",
  "thematic_room_assignments": ["...", "..."],
  "files_touched": ["..."]
}
```
**Critical finding:** BM25 degrades significantly with distillation; vector search is NOT significantly affected. Cross-layer (distilled vector + verbatim BM25 drill-down) MRR 0.759 **exceeds** verbatim-only baseline MRR 0.745.

**Hermes signal:** Replace raw session compression with 4-field compound object. Use BM25 only on verbatim source, vector on distilled. Current micro_compact/compression_threshold could adopt this schema.

---

#### SuperLocalMemory V3.3 "The Living Brain" (arXiv:2604.04514, Apr 2026)
**URL:** https://huggingface.co/papers/2604.04514
**Author:** Qualixar (independent, 5,000+ monthly downloads, CPU-only, zero-LLM)
**Novelty: 7-channel cognitive retrieval:**
1. Semantic (vector)
2. Keyword (BM25)
3. **Entity graph** — graph-structured entity relationships
4. **Temporal** — time-decay weighted
5. **Spreading activation** — network traversal from seed node outward
6. **Consolidation** — distilled long-term summaries
7. **Hopfield associative** — content-addressed associative recall

**Fisher-Rao Quantization-Aware Distance (FRQAD):** 100% precision vs 85.6% for cosine at preferring high-fidelity embeddings over quantized. LoCoMo 70.4% zero-LLM Mode A.

**Ebbinghaus Adaptive Forgetting:** Mathematical forgetting curve coupled to progressive embedding compression (6.7× discriminative power). First instance in open-source agent memory.

**Hermes signal:** Add spreading activation traversal to Graphiti/FalkorDB queries — start from seed entity, propagate relevance to neighbors 1–2 hops.

---

### 2. Skill Library Architecture

#### GenericAgent (arXiv:2604.17091, Apr 2026)
**URL:** https://arxiv.org/abs/2604.17091
**GitHub:** https://github.com/lsdefine/GenericAgent (**13,800 stars** ⭐)
**Affiliation:** Fudan University (中国)
**Core principle:** "Context information density is all a self-evolving LLM agent needs"

**4-component architecture:**
1. Minimal atomic tool set — reduce tool surface area
2. Hierarchical on-demand memory — show top-level title only; expand body on demand
3. Self-evolution: trajectories → reusable SOPs + executable code automatically
4. Context truncation + compression layer — maintains density not raw length

**Novel framing — Structural Trilemma (not in English arXiv before Apr 2026):**
- **Completeness** (all decision-critical info present) vs **Conciseness** (exclude everything else)
- This tension persists EVEN with unbounded context — not just a budget problem
- Naturalness is a secondary constraint
- Three failure modes: (a) positional bias buries mid-context evidence, (b) irrelevant content actively degrades reasoning, (c) effective hallucination-free context is ~10× shorter than nominal window

**Hermes signal:** Current micro_compact trigger should target content relevance decay, not just turn count. The hierarchical on-demand pattern — show skill titles only, expand body on demand — tightens existing Hermes skill loading.

---

#### GEMS — Agent-Native Generation with Memory and Skills (arXiv:2603.28088, Mar 2026)
**URL:** https://arxiv.org/abs/2603.28088 | Project: https://gems-gen.github.io/
**Affiliation:** Chinese team (ZJU)
**Key pattern:** On-demand skill loading with explicit domain taxonomy. Skills as "extensible collections" organized by domain tag. Agent Loop optimizes skill selection via closed-loop feedback.

---

#### SciToolAgent-Evo — Ontology-Aware Self-Evolving Agent (arXiv:2607.28692, Jul 2026)
**URL:** https://arxiv.org/abs/2607.28692
**Affiliation:** ZJU (中国浙江大学)
**Novel contributions:**
1. **Ontologized tool graph** — skills have typed semantic relationships (IsA, Uses, Requires, Conflicts), not flat lists
2. **LinUCB bandit gate** — balances exploration (try underused skills) vs exploitation (use known-good ones). Prevents skill library from going stale.
3. **Contrastive trajectory distillation** — generalizable knowledge extracted from success vs failure pairs
4. **Online ontology completion** — when a new tool acquired, agent auto-infers type, relationships, constraints from description + one execution, integrates into graph immediately

**Hermes signal:** 
- Add (recency × success_rate) weight to skill metadata → bandit-weighted selection
- Add typed edges between related skills in skills index
- Use contrastive failure trajectories as a guard: embed new plan, query failure store, warn if similarity > threshold

---

### 3. Runtime Context Compression

#### GenericAgent Compression Layer (from 2604.17091 above)
- Per-tool-call-result compression, not per-turn
- Maintains information DENSITY not raw length
- Identifies "decision-relevant vs background" content before compression
- Combined truncation + selective summarization (not uniform)

**Key implication for Hermes:** Current compression_threshold 0.35 + micro_compact every 3 turns may use the wrong trigger axis. Should trigger on content relevance decay, measured as delta between current context information density and a rolling baseline.

#### Structured Distillation 11× Pattern (from 2603.13017 above)
- 4-field compound object per exchange → 38 tokens average
- Cross-layer retrieval: vector on distilled + BM25 on verbatim drill-down
- Cross-layer MRR 0.759 > verbatim-only 0.745

---

### 4. Multi-Agent Workflow Orchestration

#### LLMA-Mem Non-Monotonic Team Scaling (from 2604.03295 above)
- Key: invest in memory topology BEFORE adding agents
- Agent "experience reuse registry" — agents write learned patterns to shared store

#### OpenViking (ByteDance/volcengine)
**URL:** https://github.com/volcengine/OpenViking
**Pattern:** Production-scale multi-agent capability routing:
- Agents self-describe capabilities → orchestrator matches tasks via capability embeddings
- Agents report confidence scores → Bayesian aggregation of confidence decides accept vs re-delegate
- Dynamic routing, not fixed routing tables

---

### 5. Knowledge Graph / Ontology for Agents

#### NLKGQ — Natural Language Knowledge Graph Query (arXiv:2607.18029, Jul 2026)
**URL:** https://arxiv.org/abs/2607.18029
**Critical finding:** "Readable entity names and semantic annotations are the dominant factors in accuracy — more significant than model choice or prompt engineering."
OWL ontology with readable labels + semantic annotations → zero-shot SPARQL, 100% accuracy on benchmark.

**Hermes signal:** Ensure all Graphiti/FalkorDB entity nodes have human-readable labels AND semantic type annotations. This unlocks zero-shot graph querying without fine-tuning.

#### SuperLocalMemory Spreading Activation + Entity Graph Channel
After top-K vector query, propagate relevance scores 1–2 hops through entity relationship edges. Surfaces related entities that cosine query missed.

#### SciToolAgent-Evo Online Ontology Completion (from above)
When new skill added → agent auto-infers type, relationships, constraints → integrates into ontologized graph immediately.

#### Entropy-based Uncertainty Scoring on KG Insertions
From multi-agent clinical KG work (Jan 2026): Facts with high extraction entropy are flagged provisional before insertion. High-uncertainty facts trigger validation rather than silent commit.
**Hermes signal:** Extend Hindsight insertion with uncertainty flag; high-entropy facts = provisional (searchable, not default-returned).

---

### 6. Agent Safety / Alignment

#### Contrastive Failure Trajectory Store (SciToolAgent-Evo)
Store both success AND failure trajectories. Before executing a multi-step plan: embed plan, retrieve top-K failure trajectories, warn if similarity > threshold BEFORE execution.

#### AMD Reactive Injection Safety Property
Function memory injected reactively means agent cannot pre-plan around known exploit patterns in tool-calling conventions. Security-through-delayed-exposure.

#### MementoGUI — Agentic Memory Control (arXiv:2605.18652, May 2026)
**URL:** https://huggingface.co/papers/2605.18652
Memory access control: agent tracks which memories drove a decision. "Committed" vs "provisional" states. Provisional memories can be retracted without side effects.

#### Bayesian Confidence Aggregation (OpenViking)
When subagents return conflicting results: Bayesian combination of confidence scores. Single highly-confident correct agent can override multiple low-confidence agents (vs simple majority vote).

---

## GitHub Repos Confirmed

| Repo | Stars | Category | Key Pattern |
|------|-------|----------|-------------|
| https://github.com/lsdefine/GenericAgent | **13,800** | skill-library + memory | SOP auto-generation, context density trilemma |
| https://github.com/volcengine/OpenViking | ~2,000+ | multi-agent | Capability-embedding routing, Bayesian confidence |
| https://github.com/Dozi01/PREPING | 4 (new) | agent-memory | Pre-task Proposer→Solver→Validator bootstrapping |

*Note: GitHub search blocked by anti-bot (requires auth). Star counts sourced from HuggingFace paper pages.*

---

## Multilingual Source Access Findings

### Chinese
- Zhihu search blocked (anti-bot/login wall). Chinese-institution work surfaces on arXiv.
- Dominant Chinese institutions: Fudan (GenericAgent), ByteDance/volcengine (OpenViking), ZJU (SciToolAgent-Evo, GEMS)
- Chinese ML community focus: "知识图谱增强记忆" (KG-enhanced memory), "动态技能路由" (dynamic skill routing)
- Novel Chinese concept NOT in English: **"技能熵"** (Skill entropy) — measuring information entropy of a skill's trigger conditions to detect over-broad skills that should be split

### Japanese
- **ArXiv returns zero results for Japanese-language queries** (confirmed). ArXiv does not index Japanese-language papers.
- Japanese AI contributions appear in English arXiv (NeurIPS/ICLR submissions).
- To access J-Stage (日本の学術論文) requires institutional access — not reachable via web_extract.
- **Do not attempt Japanese-language arXiv searches — waste of calls.**

### Korean
- KAIST AI is dominant Korean institution in agent memory research.
- AMD (2608.07169) and PREPING (2605.13880) are both KAIST, both 2026.
- Korean research pattern: memory efficiency as substitute for larger models (industrial compute constraints).

### German / French
- ArXiv returns zero results for German-language queries (confirmed).
- European academic contributions appear in English.
- Pattern: privacy-first, local-first, CPU-only memory systems (GDPR tradition).
- SuperLocalMemory's zero-LLM, CPU-only design philosophy aligns with this.
- NLKGQ paper (2607.18029) emphasizes local LLMs for privacy-sensitive data.

---

## Priority Recommendations for Hermes Runtime

### Immediate (low effort)
1. AMD proactive/reactive injection — workflow+subtask at start, function on tool error
2. 4-field compound object for session compression (11× with 96% recall)
3. Cross-layer retrieval: vector on distilled, BM25 on verbatim

### Medium effort
4. Spreading activation on Graphiti (1–2 hop propagation after top-K vector query)
5. LinUCB bandit weight on skill selection (recency × success_rate)
6. Entropy-based uncertainty on Graphiti insertions → provisional flag

### Strategic
7. Ontologized skill graph with typed edges
8. PREPING cold-start loop for new skill onboarding
9. Contrastive failure trajectory store as pre-execution guard
10. Invest in memory topology before adding subagents (LLMA-Mem finding)
