# LLM Agent Memory Topology: Research Knowledge Bank (August 2026)

Compiled from multi-source sweep: arXiv (English + Chinese-institution papers),
GitHub, Reddit r/LLMDevs, vectorize.io, mem0 benchmark report, Neo4j NODES AI 2026.
Full structured output: `/tmp/research_memory_topology.md` (382 lines, 36KB).

Complementary file (Jul 2026 sweep):
`agent-memory-consolidation/references/agent-memory-systems-2024-2026.md`

**New coverage vs Jul 2026 sweep**: G-Memory, GAM, SuperLocalMemory V3.3,
Are We Ready? (Tsinghua), POLE+O practitioner ontology, AriGraph,
Agent Lifespan Engineering, LTM Security (Peking U), localized maintenance finding.

---

## F1.1 — G-Memory: Three-Tier Graph for Multi-Agent Systems

- **Source**: https://arxiv.org/abs/2506.07398 | NeurIPS 2025 poster
- **Authors**: Guibin Zhang et al. (SkyWork / Kunlun Tech)
- **GitHub**: https://github.com/bingreeky/GMemory
- **Architecture**: insight graph (cross-trial generalizations) → query graph (per-task distillations) → interaction graph (raw collaboration trajectories). Bi-directional traversal.
- **Metrics**: +20.89% success rate on embodied action tasks; +10.12% on knowledge QA (5 benchmarks, 3 LLM backbones, 3 MAS frameworks). No framework modification required.
- **Hermes signal**: Add an **insight tier** above staging.md — activated when same pattern appears in 3+ sessions (aligns with RecMem recurrence gate). Implemented as cross-session haiku distillation: session facts → staging (query tier) → Hindsight (insight tier).

---

## F1.2 — GAM: Graph-based Agentic Memory with Semantic-Shift Trigger

- **Source**: https://arxiv.org/abs/2604.12285 | Apr 2026
- **Authors**: Zhaofen Wu et al. (UBC, UIUC, UMontreal, McGill)
- **Architecture**: event progression graph (isolated ongoing dialogue, dense raw extracts) + topic associative network (promoted long-term). Consolidation fires on *detected semantic shift*, not session end.
- **Retrieval formula**: `score = 0.6·semantic_sim + 0.25·recency_weight + 0.15·access_freq`
- **Metrics**: outperforms Mem0, A-Mem, MemoryBank on LoCoMo and LongDialQA.
- **Hermes signal (two changes)**:
  1. **Semantic-shift trigger**: compute rolling embedding centroid of current session; cosine distance from previous centroid > 0.3 → trigger mini-consolidation flush to staging.md within session (within-session, not just cron-time).
  2. **Multi-factor reranking**: implement `0.6·cosine + 0.25·recency + 0.15·freq` in Hindsight retrieval. Requires `last_accessed` + `access_count` metadata fields.

---

## F1.3 — Memory in the LLM Era: Modular Architectures Survey

- **Source**: https://arxiv.org/abs/2604.01707 | v3 Aug 6 2026 (most recent major survey)
- **Authors**: Yanchen Wu et al. (HKUST, CUHK — Chinese institutions)
- **Framework**: four modules: representation & storage, extraction, retrieval & routing, maintenance.
- **Key finding**: composite method combining best modules from each system outperforms all SOTA on long-horizon benchmarks.
- **Hermes signal**: *routing* is absent — all queries go to Hindsight. Add routing layer dispatching to: (a) FTS5 for exact/keyword, (b) Hindsight for semantic, (c) future KG for relational, (d) recency-weighted Hindsight for temporal. Classify query type via haiku before dispatch.

---

## F1.4 — Are We Ready For An Agent-Native Memory System?

- **Source**: https://arxiv.org/abs/2606.24775 | Jun 23 2026
- **Authors**: Wei Zhou, Xuanhe Zhou et al. (Tsinghua, Renmin, Fudan — Chinese institutions)
- **GitHub**: https://github.com/OpenDataBox/MemoryData (11-dataset evaluation harness)
- **Evaluation**: 12 memory systems + 2 baselines across 5 benchmark workloads, 11 datasets.
- **Key findings**:
  - No single architecture dominates across all scenarios
  - Effectiveness depends on how well structure aligns with *workload bottleneck*
  - **Localized maintenance is more cost-efficient than global reorganization** (confirmed across all 5 workloads)
- **Workload-aligned retrieval**: knowledge QA → semantic wins; temporal/sequential → recency wins; multi-hop relational → graph traversal wins; exact-match → BM25/FTS5 wins.
- **Hermes signal**: switch to cluster-aware ingest — update only top-K=3 nearest embedding clusters on new fact addition, not full re-index.

---

## F1.5 — Graph-based Agent Memory: Taxonomy, Techniques, Applications

- **Source**: https://arxiv.org/abs/2602.05665 | Feb 5 2026
- **Authors**: Chang Yang, Chuang Zhou et al. (18 authors, PolyU/CUHK/Jilin — Chinese institutions)
- **GitHub**: https://github.com/DEEP-PolyU/Awesome-GraphMemory
- **Taxonomy**: short-term vs long-term; knowledge vs experience memory; non-structural vs structural.
- **Key**: *experience memory* (outcomes, corrections, reasoning traces) is a distinct category from factual knowledge memory.
- **Hermes signal**: l1-extract.py currently extracts only factual claims. Add `memory_type` tag: `fact|correction|outcome|preference|reasoning`. Different retention policies per type.

---

## F2.1 — POLE+O Ontology: Production-Validated Base Schema

- **Source**: https://www.reddit.com/r/LLMDevs/comments/1ts3qc3/ | Paul Iusztin, ~Jun 2026
- **Schema**: Person, Object, Location, Event, Organization. Extend on *collision* (when LLM misclassifies a node type), not upfront.
- **Deduplication thresholds**: ≥0.95 cosine → auto-merge; 0.85–0.95 → human review queue; ≤0.85 → new node. Entity resolution (name normalization, same-type matching) must precede deduplication.
- **Relation label explosion**: LLM produces ~360 distinct labels in production; must collapse to ~80 canonical before multi-hop traversal is reliable.
- **Reasoning memory**: store per-run trace `{strategy, tools_used, success/failure, cost}` as a third memory tier — "RL at the database layer."
- **Edges as first-class documents**: not adjacency lists — enables native graph traversal + simpler writes.
- **Immutable log + materialized graph**: too RAM-expensive simultaneously for most deployments — pick one.
- **Hermes signal**: l1-extract.py should emit typed JSON: `{entity_type: POLE+O, relation, confidence, source_session_id, timestamp, extraction_confidence, memory_type}`.

---

## F2.2 — AriGraph: Separating Semantic vs Episodic Memory

- **Source**: https://arxiv.org/abs/2407.04363 | 2024, heavily cited 2026
- **Architecture**: entity attributes (semantic, stable) vs state transitions (episodic, dynamic) — different retention and update policies.
- **Hermes signal**: tag Hindsight embeddings with `memory_subtype: semantic|episodic`. Apply different decay rates:
  - Semantic: λ=0.01 (~69-day half-life) — stable entity knowledge
  - Episodic: λ=0.05 (~14-day half-life) — dynamic state/event data

---

## F2.3 — Graphiti Bi-Temporal Property Graph (Zep, production 2025–2026)

- **Source**: https://github.com/getzep/graphiti | https://vectorize.io/articles/best-ai-agent-memory-systems
- **Schema**: each edge has `valid_from`, `valid_to`, `invalidated_by`. Fact invalidation without deletion — expired facts remain with temporal bounds, enabling historical "what did the agent believe on date T?" queries.
- **Contradiction handling**: LLM verification → set `invalid_at=now` on old edge → insert new edge with `valid_at=now`.
- **Hermes signal**: add `valid_from`, `valid_to`, `superseded_by` to memory-facts JSON schema. When l1-promote detects contradiction (cosine > 0.85 + haiku confirms), mark old fact `valid_to: now`, `superseded_by: <new_fact_id>`. Never delete — preserve for historical queries.

---

## F3.1 — Human-Inspired Memory Architecture (Microsoft Research)

- **Source**: https://arxiv.org/abs/2605.08538 | May 8 2026
- **Authors**: Kerestecioglu, Robsky, Vasters, Sharma, Kesselman (Microsoft Research)
- **Six mechanisms**:
  1. Sleep-phase consolidation: batch dedup + integration runs offline after session end
  2. Interference-based forgetting: new contradicting memories degrade older ones (proactive interference)
  3. Engram maturation: facts gain confidence with repeated exposure; below-threshold = pruning candidates
  4. Reconsolidation upon retrieval: retrieved memories re-evaluated and optionally updated
  5. Entity knowledge graphs: entity-centric indexing for structured traversal
  6. Hybrid multi-cue retrieval: multiple strategies in parallel
- **Calibration**: all thresholds derived synthetically without benchmark exposure (no eval leakage).
- **Metrics**:
  - VSCode issue tracking (13K issues, 120K events): **97.2% retention precision, 58% store reduction** (+21.8pp over baseline)
  - LongMemEval M-tier (475 sessions, ~540K turns): 70.1% vs 71.2% (overlapping CI)
  - LongMemEval S-tier (50 sessions): +**13.3 pp** preference recall
- **Hermes signals**:
  - (a) **Dedup gate** (PRIORITY 1): query Hindsight top-1 before ingest; cosine > 0.92 → skip + increment `access_count`.
  - (b) **Interference forgetting**: when new fact contradicts existing (cosine > 0.85 + LLM confirms), additionally penalize old fact's retention score (separate from time-decay).
  - (c) **Engram maturation**: promote staging.md → Hindsight only after `access_count ≥ 2` or confidence threshold.
  - (d) **Reconsolidation**: add `last_reconsolidated` + `reconsolidation_score` to Hindsight metadata; when retrieved fact's query context differs (cosine > 0.4), queue for haiku re-eval.

---

## F3.3 — SuperLocalMemory V3.3: Mathematical Lifecycle Dynamics

- **Source**: https://arxiv.org/abs/2604.04514 | Apr 6 2026
- **Author**: Varun Pratap Bhardwaj
- **GitHub**: https://github.com/qualixar/superlocalmemory | npm+PyPI: `superlocalmemory`
- **Key mechanisms**:
  - Ebbinghaus Adaptive Forgetting: `S(t) = S₀ · e^(-λt/r)` where r = retrieval count. 6.7× discriminative power vs flat retention.
  - Fisher-Rao Quantization-Aware Distance (FRQAD): 100% precision at preferring high-fidelity embeddings (vs 85.6% for cosine).
  - 7-channel cognitive retrieval: semantic, keyword, entity graph, temporal, spreading activation, consolidation, Hopfield associative.
  - Three-stage forgetting: Active → Archived (stored, deprioritized, not default-returned) → Deleted.
  - Lifecycle-aware quantization: full 1536d → 768d PCA → 256d for older/less-accessed facts.
- **Metrics**: 70.4% on LoCoMo (zero-LLM mode); +23.8pp multi-hop; +12.7pp adversarial; 100% session-boundary continuity.
- **Hermes signals**:
  - `retention_score = confidence * e^(-days_since_access/30) * log(1+access_count)`. Archive < 0.1, delete < 0.05.
  - `memory_status: active|archived|deleted` field. Archived = searchable with explicit flag, not default-returned.
  - `quantization_tier: 0|1|2` field. Tier 2 (256d) for oldest/least-accessed facts.
  - Serialize full lifecycle state alongside fact text for cross-session continuity.

---

## F4.2 — Agent Lifespan Engineering: Boundary Controller Pattern

- **Source**: https://arxiv.org/abs/2605.26302 | May 2026
- **Key**: "between-session boundary controller" — reads session artifacts, distills persistent state, injects relevant state into next session's working memory preamble.
- **Hermes signal**: l1-promote.py is currently a one-way pipeline (store only). Formalize as a boundary controller: at session start, inject top-N Hindsight facts relevant to current task into working context, not just passively store.

---

## F4.3 — Long-Term Memory Security (arXiv:2604.16548, Peking University)

- **Source**: https://arxiv.org/abs/2604.16548 | v2 Jun 11 2026
- **Authors**: Zehao Lin et al. (Peking University — Chinese institution)
- **Framework**: 6-phase Memory Lifecycle: Write → Store → Retrieve → Execute → Share/Propagate → Forget/Rollback. VMG (Verifiable Memory Governance): 5 architectural primitives.
- **Key finding**: robust LTM security requires storage-time provenance — cannot be retrofitted at retrieval time.
- **Hermes signal**: add `source_session_id` + `extraction_confidence` provenance fields to all memory-facts/. Gate: `confidence < 0.5` → do not promote. Dual-purpose: quality filter + audit trail.

---

## F4.4 — Mem0 Cross-Session Benchmark Results

- **Source**: https://arxiv.org/abs/2504.19413 | Apr 2025 | LOCOMO benchmark
- **Metrics**:
  - Mem0 base: **+26% relative improvement** on LLM-as-a-Judge vs OpenAI baseline
  - Mem0 + graph memory: ~+2% further over base Mem0
  - **91% lower p95 latency** vs full-context method
  - **>90% token cost reduction** vs full-context
- **Key insight**: the +2% marginal gain from graph vs flat vector suggests graph structures help at the margins but are not a silver bullet over well-tuned vector memory.
- **Hermes signal**: prioritize improving extraction quality and retrieval routing before switching storage backends.

---

## F5.3 — Localized vs Global Maintenance (arXiv:2606.24775)

See F1.4 above. The localized maintenance finding specifically means:
- Do not re-embed the full Hindsight index on every new fact ingest.
- On new fact ingest, find the top-K=3 nearest embedding clusters and update only those.
- Full re-index should run only on scheduled maintenance windows, not on every l1-promote.py run.

---

## F7.1 — Practitioner: A Year Building Agent Memory on Knowledge Graphs

- **Source**: https://www.reddit.com/r/LLMDevs/comments/1ts3qc3/ | Paul Iusztin, ~Jun 2026
- **5 mistakes + resolution** (see SKILL.md body). Key addition for Hermes:
  - Reasoning memory (per-run trace: strategy, tools, outcome, cost) as a third tier is the most-missed category.
  - Commenter added: relation resolution ≠ entity resolution; edge labels also explode (~360→80 applies to edges too, not just nodes).

---

## F7.2 — Best Agent Memory Systems 2026: Comparative Analysis

- **Source**: https://vectorize.io/articles/best-ai-agent-memory-systems | 2026
- **Star counts (Aug 2026)**: Mem0 ~48K; Letta ~21K; Zep/Graphiti ~24K; Hindsight ~4K growing.
- **Critical observation**: "Vector-only retrieval fails on terminology mismatch" — demonstrated with Vendor X example where 'format' and 'template' fail to retrieve the same fact. Multi-strategy (semantic + keyword + entity) is minimal viable for production.
- **Hermes signal**: ensure FTS5 session_search AND Hindsight semantic search are BOTH queried for every retrieval, with results merged and deduped before ranking.

---

## F7.3 — Mem0 2026 Benchmark Report: Graph Memory Production Shift

- **Source**: https://mem0.ai/blog/state-of-ai-agent-memory-2026 | 2026
- **Key observation**: "Graph is needed for relational/temporal queries; flat vector is still optimal for semantic similarity." Production shift: not "every agent needs a graph" but "graph augments vector for relational queries."
- **Hermes signal**: Graphiti (open-source Zep component) could be added as a lightweight entity-relation layer alongside Hindsight, without replacing it. Augment, don't replace.

---

## Benchmark Reference (Aug 2026)

| Benchmark | Best Score | System |
|-----------|-----------|--------|
| LoCoMo | 74.8% | SuperLocalMemory zero-LLM mode (arXiv:2604.04514) |
| LongMemEval M-tier | 70.1% | Human-Inspired MS Research (arXiv:2605.08538) |
| LOCOMO multi-session | +26% vs OpenAI baseline | Mem0 base (arXiv:2504.19413) |
| LongDialQA | SOTA (delta undisclosed) | GAM (arXiv:2604.12285) |

**Hermes target**: ~90%+ on retrospective long-conversation questions (per ACM framework arXiv:2607.21503, 92% LongMemEval — already in agent-memory-consolidation body).

---

## International Sources Finding

- **J-STAGE (Japan)**: No directly relevant papers in English on agent memory topology (2025–2026). Neo4j NODES AI 2026 had "Multi-Agent Shared Graph Memory" talk — not J-STAGE indexed.
- **CyberLeninka (Russia)**: No relevant papers found. Russian ML in this area routes through arXiv.
- **Chinese institutions**: Dominant contributor via arXiv — PolyU, CUHK, Tsinghua, Renmin, PKU, Jilin, HKUST. CNKI is paywalled; Chinese-institution papers are on arXiv concurrently.
- **CNKI workaround**: search arXiv with `authors:"Tsinghua" OR "Peking" OR "HKUST" agent memory` for Chinese-institution coverage.
