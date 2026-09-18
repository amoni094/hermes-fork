# Memory Topology & Evaluation — Post-Aug 8 2026 Sweep

Research sweep completed Aug 11, 2026. All findings are net-new relative to Aug 8 baseline.
Baseline (already in skills): MEMTIER, MemCube, MAGMA, 3-tier, Du2026 write-manage-read taxonomy.

---

## 1. ScrubJay-MEM — Type-Conditioned Perishability Decay
**Source:** arXiv:2608.04746v1, BITS Pilani, **August 5, 2026** ← post-cutoff
**Result:** Only retrieval system with positive Generalization Gap (+0.108 on TGT benchmark); ablating type-conditioned decay collapses GenGap 5.7×. +2.66 F1 over Mem0 on MemoryAgentBench EventQA-64k.

**Core mechanism:** Each memory is encoded as a jointly-bound `(What–Where–When)` Episodic Memory Unit (EMU) with:
- `perishability π` — auto-classified coefficient (0.0–1.0)
- `utility_horizon τ` — seconds until memory is no longer useful
- Retrieval score: `value_score × exp(-π × age/τ)` with four adaptive weights `[α, β, γ, δ]`

**4 perishability classes (keyword-fallback classifier — exact values from paper):**
| Label | π | τ | Trigger keywords |
|---|---|---|---|
| `ephemeral` | 0.9 | 2h | today, immediate, right now, session, temporary |
| `task_specific` | 0.6 | 24h | task, ticket, issue, meeting, project |
| `procedural` | 0.3 | 10d | how to, steps, process, procedure, workflow |
| `factual` | ~0.1 | 45d | (default) |

**LLM classifier prompt (from appendix):**
```
Classify memory perishability and utility horizon. Return strict JSON:
{"label": str, "pi": float, "tau_sec": float}
Labels: factual, procedural, task_specific, ephemeral.
Context: {context}
Memory: {text}
```

**Additional mechanisms:**
- **Prospective Memory Buffer (PMB):** pre-loads anticipated memories before task execution (sub-linear retrieval)
- **Retroactive Contextual Integration (RCI):** revises decay parameters when new information arrives (O(1) LLM calls per update)
- **Memories stored in a hypergraph** (not flat list)

**RCI delta-extraction prompt:**
```
Given new information, infer latent memory update deltas. Return strict JSON:
{"delta_value": float, "delta_pi": float, "delta_tau": float, "summary": str}
delta_tau is relative ratio change where +0.2 means +20%.
Context: {context}
New information: {new_info_text}
```

**Hermes implementation:** Add `perishability`, `pi`, `tau_sec`, `inserted_at` columns to Hindsight SQLite memories table. Apply keyword-fallback classifier at ingest. Weight retrieval: `score × exp(-π × elapsed_seconds/τ)`.

**Benchmark introduced:** Temporal Generalization Test (TGT) + GenGap metric (see §5 below).

---

## 2. Synapse — Episodic-Semantic Graph with Spreading Activation
**Source:** arXiv:2601.02744v3, U. Georgia, Jan 2026; ACL Findings 2026
**Result:** +7.2 F1 on LoCoMo benchmark; 23% better multi-hop reasoning accuracy; 95% fewer tokens vs full-context methods.

**Architecture: Unified Episodic-Semantic Graph**
- **Episodic nodes:** raw interaction logs (granular, time-stamped)
- **Semantic nodes:** synthesized abstract concepts (distilled from episodic nodes)
- **Edge types:** temporal, causal, semantic (lateral inhibition suppresses irrelevant distractors)
- **Spreading activation:** energy injected at query anchors propagates through edges — surfaces structurally relevant memories even with zero lexical/embedding overlap

**"Contextual Tunneling" problem (solved by Synapse):** Standard cosine-only retrieval misses causally linked but lexically distant memories (e.g., "anxiety" query fails to surface a schedule conflict logged weeks ago that is the root cause).

**Lateral inhibition:** Suppresses hub-explosion in dense semantic graphs; enforces sparsity so fan-effect is bounded.

**Triple Hybrid Retrieval:** fuses geometric embeddings + activation-based graph traversal + temporal decay.

**vs GraphRAG:** GraphRAG uses global community detection (expensive, coarse); Synapse propagates along specific transitive paths from query anchors — faster, more precise for episodic memory.

**vs HippoRAG:** HippoRAG uses Personal PageRank (can hub-explode); Synapse adds lateral inhibition as hard architectural constraint.

**Hermes implementation:** Extend Hindsight/Graphiti schema with explicit `causal` and `temporal` edge types. Implement 2-hop BFS retrieval propagating activation scores through those edges alongside cosine similarity.

**Code status:** forthcoming on ACL acceptance.

---

## 3. LongMemEval-V2 (LME-V2) — 5-Dimension Memory Benchmark + AgentRunbook Pattern
**Source:** arXiv:2605.12493v1, UCLA, May 2026
**Result:** AgentRunbook-C achieves 72.5% vs 48.5% for strongest RAG baseline.

**5 core memory abilities (the evaluation framework):**
1. **Static state recall** — can agent remember stable facts?
2. **Dynamic state tracking** — can agent track facts that changed over time?
3. **Workflow knowledge** — does agent know how to do environment-specific procedures?
4. **Environment gotchas** — does agent remember failure modes specific to the environment?
5. **Premise awareness** — does agent know what pre-conditions hold?

**Context-gathering formulation (for evaluation):**
- `Insert(trajectory)` → memory system ingests trajectory
- `Query(question)` → returns compact evidence for downstream QA
- Scores: answer accuracy + query latency (both reported)

**AgentRunbook-R pattern (efficient RAG tier, no coding agent):**
Maintain a `knowledge_pools` table with 3 sub-tables:
- `raw_observations` — raw state observations
- `events` — significant events
- `strategy_notes` — generalizable lessons

Query all three with weighted boosting during retrieval.

**Hermes implementation:** Add `knowledge_type` tag to Hindsight memories (`observation|event|strategy`). Weight retrieval: strategy_notes get 1.3× boost, events 1.1×, observations 1.0×.

---

## 4. IFCMemoryBench — Domain-Transfer Gap + 3-Axis Memory Judge
**Source:** arXiv:2607.26072v1, TU Munich + Nemetschek; KDD 2026 Workshop, **August 9, 2026** ← post-cutoff
**Result:** Best system achieves only 32.4% accuracy on domain-specific professional tasks even with oracle-filtered ingestion (<60%).

**Key finding:** General-purpose memory systems retrieve *topically relevant* context but store domain knowledge as *incomplete or fragmented facts*, failing axis 2 (key fact coverage) even when passing axis 1 (relevance).

**3-Axis Memory Judge (LLM-evaluatable):**
```
1. retrieval_relevant: Retrieved content is relevant to the probe and target facts.
   (May include noise, but must contain useful memory facts.)

2. retrieval_covers_key_facts: Retrieved content covers the KEY facts needed to answer.
   Must be FALSE if content omits, contradicts, reverses, or replaces any central fact.

3. answer_uses_memory: The agent's answer actually uses the retrieved memory accurately.
   Should not rely only on live tool output when remembered facts are needed.
```

**Domain-aware representation requirement:** memories must link conversational facts to structured data entities — not just store text.

**Hermes implementation:**
- Tag each Hindsight memory with entity references (`{skill_name, tool_id, session_type}`) as structured FK alongside text embedding
- Score retrieval on entity alignment AND semantic similarity
- Run monthly judge evaluation using haiku, logging all three axes to SQLite
- Alert: high `retrieval_relevant` + low `retrieval_covers_key_facts` = fragmented storage problem

---

## 5. New Evaluation Metrics (post-Aug 8 2026)

### TGT + GenGap (from ScrubJay-MEM, arXiv:2608.04746)
**GenGap** = memory system performance at *held-out* retention intervals minus performance at *trained* intervals.
- Positive GenGap → system generalized temporal decay knowledge
- Negative GenGap (≤-0.022 for all flat-retrieval baselines) → overfit to seen intervals
- ScrubJay-MEM: +0.108 (only system with positive GenGap)

**Implementation:** Hold out 30/60/90-day retention intervals from training. Measure whether perishability-weighted retrieval correctly deprioritizes stale memories at unseen intervals.

### Skill Contribution Score — Dual-Rollout Protocol (from arXiv:2606.11435)
Run same task WITH and WITHOUT each skill; delta = skill contribution score.
- Shrinking delta over time = agent bypassing skill library (reward hacking signal)
- Negative delta = skill actively harmful; flag for deprecation
- Hermes: weekly cron running 3 representative tasks per skill, logging delta to SQLite

---

## 6. OL-KGC — Ontology-Enhanced KG Completion
**Source:** arXiv:2507.20643v2, **Tianjin University** (China) + U. Manchester, Oct 2025
**Code:** https://github.com/xiumu-gg/OL-KGC  ← code available
**Result:** SOTA on FB15K-237, UMLS, WN18RR benchmarks.

**Key mechanism:** LLM-based automatic extraction of ontological knowledge from sparse KGs:
1. **Relation domain/range** — entity class constraints to filter erroneous triples
2. **Relation compositions** — path-based inference of new knowledge (`A→B, B→C → A→C`)
3. **Complex constraints** — equivalence, disjointness relations

**Why standard LLMs fail:** They rely on semantic correlation between entities but lack explicit symbolic reasoning for ontological constraints — they can't verify that a generated triple is consistent with domain/range restrictions.

**Neural-symbolic integration:** align KG embeddings in vector space with LLM text tokens; inject symbolic KG structure alongside text at fine-tuning time.

**Hermes/Graphiti implementation:** After Graphiti ingests triples, run an LLM extraction pass to generate domain/range rules and relation-composition chains. Store as `ontology_rules` table in SQLite consulted before returning triples. Auto-trigger when Graphiti node count exceeds 100.

---

## 7. Auton AgenticFormat — Cognitive Blueprint Separation
**Source:** arXiv:2602.23720v1, Snapchat AI, Feb 2026

**Constraint Manifold pattern:** Safety constraints expressed as code-level specifications that project agent policy into safe action subspace *before* action emission — not post-hoc output filtering.

**Reflector-Driven Consolidation Protocol:** compresses raw event streams into semantic insights; these persist across sessions enabling cross-session experience without model retraining.

**Cognitive Map-Reduce:** analyze dependency graphs within execution plans and parallelize independent steps, bounding total time by critical path rather than sum of step latencies.

**Hermes SKILL.md application:** Add a `constraints` block to YAML frontmatter specifying forbidden capability conjunctions (e.g., `deny: [file_read AND network_out]`) evaluated before skill execution begins.
