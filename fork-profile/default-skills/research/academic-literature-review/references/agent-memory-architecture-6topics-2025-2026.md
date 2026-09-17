# Agent Memory Architecture — 6-Topic Research Survey (July 2026)

*Scope: MemOS tiered promotion · FTS5+vector hybrid retrieval · RAGFlow chunking · KG ontology induction · Deep Dream memory distillation · CowAgent 3-tier memory*  
*Target stack: Python, Hindsight (ChromaDB + text-embedding-3-small + claude-haiku-4-5), Graphiti (FalkorDB), session_search (FTS5/SQLite), durable MEMORY.md, cron consolidation*  
*Non-English sweep: Chinese (Tsinghua/PKU/SJTU/HKUST), Korean (PyTorchKR digest), Japanese (IPSJ/Qiita), Russian (CyberLeninka), European (French TALN/LREC)*

---

## Topic 1 — MemOS L1→L4 Tiered Memory Promotion

### MemOS (short paper) — Memory Operating System (arXiv May 2025)

| Field | Detail |
|-------|--------|
| **Paper** | *MemOS: An Operating System for Memory-Augmented Generation (MAG) in Large Language Models* |
| **arXiv** | 2505.22101 (May 28, 2025) |
| **Venue** | arXiv (short paper precursor) |
| **Institution** | MemTensor team — multi-institution Chinese + SJTU (Junchi Yan), Zhejiang University (Ningyu Zhang), ECNU (Linfeng Zhang), SJTU (Siheng Chen) |
| **GitHub** | github.com/MemTensor/MemOS (Apache-2.0) |
| **Technique** | Introduces MemCube as the standard unit: encapsulates content + provenance + versioning. Unifies 3 memory types: parametric (weights), activation (KV states), plaintext (external text). Manages all three as first-class OS resources with lifecycle control. |
| **Quantified Benefit** | Short paper (arXiv:2505.22101) — vague claims. Full paper (2507.03724) has 5 tables of results on LongMemEval, personalization tasks. |
| **Hermes Feasibility** | **Medium** — Python SDK (`pip install MemoryOS`), local-first backends (Neo4j / PolarDB / PostgreSQL), MCP server. |

### MemOS (full paper) — A Memory OS for AI System (arXiv July 2025)

| Field | Detail |
|-------|--------|
| **arXiv** | 2507.03724 (Jul 4, 2025; v4 Dec 3, 2025) |
| **Authors** | Zhiyu Li, Chenyang Xi, Huajun Chen, Ningyu Zhang (Zhejiang), Junchi Yan (SJTU), Wei Xu, Siheng Chen, Wentao Zhang, Linfeng Zhang (ECNU) + 30 others |
| **Technique** | Full MemOS architecture. Core memory management: read, write, delete, update, migrate across memory types. MemCube migration: plaintext → activation → parametric as usage frequency/value warrants. Scheduler handles migration decisions. Dream system does background consolidation. |
| **Key Metric** | 36 pages, 10 figures, 5 tables. Results not fully extractable from abstract — see PDF. |

### L1/L2/L3 Tiered Architecture (Reflect2Evolve / memos-local-plugin)

*Confirmed from DeepWiki index of MemTensor/MemOS at commit e8204062 (Jul 25, 2026)*

| Tier | Name | Storage | Description |
|------|------|---------|-------------|
| L1 | Grounded Traces | Local DB | Raw execution step-by-step records. Captured by `capture.ts`. Batch-scored with `batch-scorer.ts` on turn end. Scoring factors: task success, novelty, surprise, action type. |
| L2 | Tactical Policies | Local DB | L1 traces promoted to reusable policies. L2 subscriber listens for high-scoring L1 traces; LLM reflection call generates policy. Score threshold controlled by `reward.ts` prompts. |
| L3 | World Model | Local DB | Abstract, generalizable facts induced from L2 policies. Higher-level beliefs about the environment/task domain. |
| L4 | Crystallized Skills | SKILL.md / external | (In Hermes context) Skills extracted from L3 world-model patterns. Explicit procedural SKILL.md artifacts. The `skill_crystallization` pipeline. |

**Promotion heuristics (from DeepWiki/source):**
- L1→L2: novelty × success rate × reuse potential (scored by small LLM). Threshold: configurable, default empirically ~0.65.
- L2→L3: cross-episode consistency check — policies that appear in ≥3 different episodes get world-model candidacy.
- L3→L4 (crystallization): explicit trigger from skill_invoke or curator decision.

**Retrieval strategy by context trigger:**
| Trigger | L1 Traces | L2 Policies | L3 World | Purpose |
|---------|-----------|-------------|----------|---------|
| `turn_start` | Yes | Yes | Yes | Full context injection |
| `tool_driven` | No | Yes | Yes | Just-in-time tool guidance |
| `skill_invoke` | No (primary only) | Yes | No | Guide specific skill |
| `sub_agent` | No | Yes | Yes | Sub-agent context |
| `decision_repair` | Yes | Yes | No | Unblock failure loops |

**Implementation Ideas for Hermes Python stack:**
1. L1 promotion: use NEMORI's `predict-calibrate` principle (see Topic 5) for L1→L2 threshold — measure prediction error on episode content rather than fixed importance score.
2. Cross-episode consistency: implement as FTS5 query on session_search for recurring n-grams across N sessions before promoting to policy.
3. L3→L4 crystallization: already happening in Hermes via `agent-memory-consolidation` cron — label that pipeline explicitly as L4 crystallization.

**Non-English coverage:**
- Chinese: MemOS originates from Chinese institutional consortium (Zhejiang/SJTU/ECNU/MemTensor). This IS the Chinese-origin tiered-memory paper. Authors Ningyu Zhang (Zhejiang KG group), Junchi Yan (SJTU) are major Chinese ML figures.
- Russian (CyberLeninka): Malakhov's 3-tier memory paper (prior sweep) proposes Redis/ChromaDB/files tiers — independently validates tiered approach, weaker on promotion heuristics.
- Korean (PyTorchKR): Tiered memory consistently surfaced across multiple Korean-curated digests (MemAgent, Memora, AutoMem).
- Cross-language convergence: **VERY STRONG** (4+ independent tracks). Tiered memory with explicit promotion is the dominant answer across Chinese/Russian/Korean/Japanese academic communities. See prior sweep multilingual-agent-efficiency-sweep-jun-jul-2026.md.

---

## Topic 2 — FTS5 + Vector Hybrid Retrieval for Agent Memory

### vstash — Local-First Hybrid Retrieval with Adaptive Fusion (arXiv Apr 2026)

| Field | Detail |
|-------|--------|
| **Paper** | *vstash: Local-First Hybrid Retrieval with Adaptive Fusion for LLM Agents* |
| **arXiv** | 2604.15484 (Apr 16, 2026) |
| **Venue** | arXiv (cs.IR) |
| **Institution** | Jayson Steffens (independent researcher) |
| **GitHub** | See paper — single SQLite file, sqlite-vec + FTS5 + RRF |
| **HuggingFace** | `Stffens/bge-small-rrf-v2` (fine-tuned model) |
| **Technique** | SQLite-only stack: sqlite-vec for ANN + FTS5 for keyword matching + adaptive per-query IDF-weighted RRF. Self-supervised embedding refinement: uses disagreement between vec-heavy and FTS-heavy rankings as training signal (no human labels). Fine-tunes BGE-small with MultipleNegativesRankingLoss on 76K disagreement triples. |
| **Quantified Benefit** | Adaptive IDF-weighted RRF: up to +21.4% NDCG@10 on ArguAna vs. fixed weights. Fine-tuned BGE-small: up to +19.5% NDCG@10 on NFCorpus vs. BGE-small base + RRF. Search latency: 20.9 ms median at 50K chunks with stable NDCG. **NEGATIVE RESULT**: post-RRF reranking (frequency+decay, history-augmented recall, cross-encoder) ALL failed to improve NDCG — don't add more layers. |
| **Hermes Feasibility** | **Very High** — pure SQLite, already matches Hermes stack (session_search = FTS5 on SQLite). Adaptive IDF weighting is a drop-in parameter. |
| **Hermes Action** | Implement adaptive per-query IDF weighting in Hindsight hybrid search path. Use vstash's disagreement-triple self-supervision as a free training signal to fine-tune text-embedding-3-small or BGE-small (no labels needed). |

### agentmemory / agent-memory-toolkit — BM25 + Vectors + KG + Ebbinghaus (GitHub 2026)

| Field | Detail |
|-------|--------|
| **GitHub** | github.com/autosre-ai/agentmemory (MIT, 2026) |
| **Stack** | SQLite FTS5 (BM25) + vector search + knowledge graph + RRF fusion + Ebbinghaus forgetting decay |
| **Benchmark** | **95.2% R@5 on LongMemEval-S** — claimed state-of-the-art for long-term agent memory recall |
| **Latency** | BM25 (FTS5): ~0.5ms; Vector: ~5ms; Hybrid: ~8ms; Rule-based extraction: ~1ms/KB |
| **Key innovation** | Ebbinghaus decay: memory items have decaying relevance weights over time (recency bias), so recent memories naturally surface more. Combined with RRF over 3 sources (BM25, vector, KG). |
| **Hermes Feasibility** | **Very High** — Python 3.10+, MIT, MCP-compatible. Direct integration pattern for Hindsight+Graphiti+session_search stack. |
| **Hermes Action** | Add Ebbinghaus time-decay weighting to Hindsight retrieval path (timestamp × decay function → re-weighting before RRF fusion). Already using ChromaDB for vectors and SQLite FTS5 for session_search — the 3-source RRF is the gap to close. |

### Agentic Hybrid Retrieval Architecture (arXiv Apr 2026)

| Field | Detail |
|-------|--------|
| **arXiv** | 2604.16394 (Apr 2026) |
| **Technique** | Reference architecture for bounded, auditable agentic hybrid retrieval. BM25 + dense embedding + RRF, orchestrated by an LLM agent that iteratively plans queries, evaluates partial results, and modifies subsequent retrievals. |
| **Key Insight** | LLM-orchestrated iterative retrieval: agent plans query → retrieves → evaluates → modifies → re-retrieves until sufficient. Applies to dataset search but generalizes to agent memory. |
| **Hermes Feasibility** | **High** — architecture pattern, no special infrastructure |

**Implementation recipe for Hermes hybrid retrieval:**
```python
def hybrid_retrieve(query: str, n_results: int = 10) -> list[dict]:
    # 1. FTS5 (BM25) via session_search
    fts_results = session_search(query=query, limit=n_results*2)
    # 2. Vector search via Hindsight ChromaDB  
    vec_results = hindsight.query(query, n_results=n_results*2)
    # 3. Graphiti entity/edge search
    kg_results = graphiti.search_facts(query, max_facts=n_results)
    # 4. Adaptive IDF-weighted RRF (from vstash)
    idf_weight = compute_per_query_idf(query)  # higher for rare terms
    vec_weight = 1 - idf_weight
    rrf_results = rrf_fuse([
        (fts_results, idf_weight),
        (vec_results, vec_weight),
        (kg_results, 0.3),
    ], k=60)
    # 5. Ebbinghaus decay (from agentmemory)
    decay_reranked = apply_ebbinghaus_decay(rrf_results)
    return decay_reranked[:n_results]
```

**Non-English coverage:**
- Chinese: CSDN/Zhihu commentary on BM25+vector hybrid RAG is widespread (e.g., csdn.net 2025 article on HybridRetriever). No independent Chinese academic paper advances beyond what's in vstash — commentary is derivative.
- Korean (PyTorchKR): Memori (discuss.pytorch.kr/t/8922) specifically introduces "SQL-native memory with BM25+vector" for LLMs — independent Korean practitioner implementation of the same pattern. **Verdict: MODERATE cross-language convergence** (EN+KR on SQL/BM25+vector hybrid for LLM memory).
- Russian: CyberLeninka Malakhov paper uses Redis (hot)/ChromaDB/files 3-tier — mentions hybrid retrieval but no original FTS+vector fusion contribution.
- Japanese: No independent Japanese-venue FTS5+vector fusion research found. Topic-maturity gap (engineering topic, not academic research).

---

## Topic 3 — RAGFlow Template-Based Chunking per Document Type

### Meta-Chunking — LLM-Based Adaptive Chunking (arXiv Oct 2024 / May 2025)

| Field | Detail |
|-------|--------|
| **Paper** | *Meta-Chunking: Learning Text Segmentation and Semantic Completion via Logical Perception* |
| **arXiv** | 2410.12788 (Oct 2024; v3 May 21, 2025) |
| **Venue** | arXiv cs.CL |
| **Institution** | Jihao Zhao, Zhiyu Li, Bo Tang, Feiyu Xiong + others — **IAAR-Shanghai** (Institute of AI Application Research, Shanghai; appears associated with MemOS team) |
| **GitHub** | github.com/IAAR-Shanghai/Meta-Chunking |
| **Technique** | Two adaptive chunking strategies using LLM logical perception: (1) **Perplexity Chunking** — segments at points where LLM perplexity spikes (logical discontinuity); (2) **Margin Sampling Chunking** — segments at uncertainty peaks in next-token distribution. Global information compensation: 2-stage hierarchical summary + 3-stage chunk rewriting (missing reflection → refinement → completion). Works with small models (no large instruction-following required). |
| **Quantified Benefit** | "Effectively addresses chunking challenges in RAG" — vague in abstract. See paper for benchmarks. Cited in BUPT/CAS RAG survey (2026) as a key advancement. Works with smaller models — cost-efficient. |
| **Hermes Feasibility** | **Medium** — requires LLM inference at index time (chunk boundary detection); can use claude-haiku-4-5 economically. |
| **Hermes Action** | Apply Perplexity Chunking to session transcripts in Hindsight ingestion pipeline. High-perplexity boundaries = topic shifts = better chunk points than fixed-size windows. |

### Adaptive Chunking — Metric-Guided Strategy Selection (arXiv Mar 2026)

| Field | Detail |
|-------|--------|
| **Paper** | *Adaptive Chunking: Optimizing Chunking-Method Selection for RAG* |
| **arXiv** | 2603.25333 (Mar 26, 2026) |
| **Venue** | **LREC 2026** (accepted) |
| **Institution** | Paulo Roberto de Moura Júnior, Jean Lelong, Annabelle Blangero — **Ekimetrics** (French data science consultancy) 🇫🇷 |
| **GitHub** | github.com/ekimetrics/adaptive-chunking |
| **Technique** | **5 novel intrinsic metrics** for per-document chunking quality: (1) **References Completeness (RC)** — are cross-references preserved?; (2) **Intrachunk Cohesion (ICC)** — semantic coherence within chunk; (3) **Document Contextual Coherence (DCC)** — cross-chunk coherence; (4) **Block Integrity (BI)** — structural element (table, code block) preservation; (5) **Size Compliance (SC)** — adherence to size target. Framework evaluates multiple chunking strategies against these 5 metrics, selects best for each document. Also introduces LLM-regex splitter and split-then-merge recursive splitter. |
| **Quantified Benefit** | **+10pp answer correctness** (72% from 62-64%) on diverse corpus spanning legal, technical, social science. **+33% more questions answered** (65 vs. 49 successfully answered). No model/prompt changes — pure chunking improvement. |
| **Hermes Feasibility** | **High** — Python, open-source, LREC accepted. The 5 metrics are computable without LLM (mostly string analysis). Strategy selector is a lightweight scoring function. |
| **Hermes Action** | HIGH PRIORITY. Implement the 5 intrinsic metrics (RC, ICC, DCC, BI, SC) as a Hindsight chunking quality evaluator. Per-document strategy selection rather than uniform chunk_size=512. Especially: BI (Block Integrity) for code chunks from session transcripts; DCC for skill documents; RC for research papers. |

### RAGFlow Template-Based Chunking (Production System)

*No arXiv paper — implementation reference from RAGFlow codebase (infiniflow/ragflow)*

| Field | Detail |
|-------|--------|
| **Source** | deepwiki.com/infiniflow/ragflow/6.2-chunking-methods (Jun 22, 2026 index) |
| **GitHub** | github.com/infiniflow/ragflow (~80K stars) |
| **Architecture** | Template-based, per-document-type chunking rules. Each template applies domain-specific rules: detect structure (headings, bullets, tables, code) → preserve semantic boundaries → apply type-specific granularity. |
| **Document Types** | Articles/papers (paragraph-boundary with heading context), Tables (row-as-chunk with column headers), Q&A (question+answer as atomic unit), Image descriptions (caption+surrounding text), Contract clauses (clause-boundary detection), Code (function/class boundaries). |
| **Key Design Principle** | Chunking is NOT a black box — different document types need different strategies. Structural awareness beats statistical chunking. |
| **Hermes Feasibility** | **Very High** — directly applicable to Hindsight ingestion |
| **Hermes Action** | Define 4 document templates for Hermes ingestion: (1) SESSION — dialogue turns as chunks with session header context; (2) SKILL — section headings as boundaries; (3) WEB — paragraph with title/heading metadata; (4) CODE — function/class boundaries. |

**Non-English coverage:**
- Chinese (IAAR-Shanghai / Meta-Chunking): **CONFIRMED** Chinese institutional origin (IAAR = Shanghai AI institute). Meta-Chunking is from the MemOS team — same group.
- French (Ekimetrics / Adaptive Chunking at LREC 2026): **CONFIRMED** French institutional origin, peer-reviewed, with quantified metrics. This is the strongest non-English contribution in this topic.
- Korean (PyTorchKR): Document chunking discussed in context of RAG improvements — no independent Korean-origin chunking paper found.
- Cross-language convergence: **STRONG** (ZH + FR independently developing metric-guided adaptive chunking as the answer to RAGFlow's template-based approach).

---

## Topic 4 — Knowledge Graph Ontology Induction from Corpus

### AutoSchemaKG / ATLAS — Fully Autonomous KG with Dynamic Schema Induction (arXiv May 2025)

| Field | Detail |
|-------|--------|
| **Paper** | *AutoSchemaKG: Autonomous Knowledge Graph Construction through Dynamic Schema Induction from Web-Scale Corpora* |
| **arXiv** | 2505.23628 (May 29, 2025; v3 Aug 1, 2025) |
| **Venue** | arXiv cs.CL |
| **Institution** | Jiaxin Bai, Wei Fan, Yangqiu Song et al. (20 authors) — **HKUST (Hong Kong University of Science and Technology)** 🇭🇰 (KnowComp lab) |
| **GitHub** | github.com/HKUST-KnowComp/AutoSchemaKG |
| **Technique** | Fully eliminates predefined schemas. LLM simultaneously extracts knowledge triples AND induces schemas directly from text. Conceptualization organizes instances into semantic categories. Processes 50M+ documents → ATLAS KG (900M+ nodes, 5.9B edges). Schema induction: abstracts instance-level patterns into reusable ontology classes and relations. |
| **Quantified Benefit** | **92% semantic alignment with human-crafted schemas** (zero manual intervention). Outperforms SOTA baselines on multi-hop QA. Enhances LLM factuality. |
| **Hermes Feasibility** | **Low** (billion-scale is overkill) → Pattern is **Very High feasibility** for small-scale deployment: the schema induction algorithm applied to Graphiti's entity/edge types. |
| **Hermes Action** | Use AutoSchemaKG's schema induction algorithm as a post-processing step on Graphiti's extracted entities/edges: cluster entity types → propose ontology classes → validate against existing edge_types. This can auto-discover new entity_types beyond what Graphiti's defaults capture (e.g., tool names, project names, decision types). |

### MemGraphRAG — 3-Layer Schema-Fact-Passage with Ontology Induction (KDD 2026)

*Already in prior sweep baseline (rag-robustness-multilingual-memory-papers-2025-2026.md)*

| Field | Detail |
|-------|--------|
| **arXiv** | 2606.00610 (KDD 2026) |
| **Institution** | **Xiamen University** (XMUDeepLIT) 🇨🇳 |
| **Technique** | Schema layer: abstract ontology triples (head_type, relation, tail_type) induced from fact layer. Low-frequency schemas filtered. Conflict-aware construction detects hard conflicts. |
| **Key for Graphiti** | MemGraphRAG's Schema layer = Graphiti's edge_types definition. AutoSchemaKG can auto-induce these from corpus rather than hand-crafting them. |

### LLM-Driven Ontology Construction for Enterprise KGs (ICSC 2026)

| Field | Detail |
|-------|--------|
| **Paper** | *LLM-Driven Ontology Construction for Enterprise Knowledge Graphs* |
| **arXiv** | 2602.01276 (Feb 1, 2026) |
| **Venue** | **ICSC 2026** (20th International Conference on Semantic Computing) |
| **Institution** | Abdulsobur Oyewale, Tommaso Soru — (European/international, ICSC venue) |
| **Technique** | OntoEKG: two-phase pipeline. Phase 1: Extract classes and properties from unstructured enterprise data. Phase 2: Entailment module structures them into hierarchy, serializes to RDF. Validates with SHACL + OWL constraints. Continuous graph updates. |
| **Quantified Benefit** | **Fuzzy-match F1-score of 0.724 in Data domain**. Reveals limitations in scope definition and hierarchical reasoning. |
| **Hermes Feasibility** | **High** — two-phase pipeline is implementable with any LLM API + rdflib. |
| **Hermes Action** | Apply OntoEKG's two-phase pipeline to Graphiti's edge_type vocabulary: (1) extract common edge types from existing episodes; (2) entailment-module structures into edge_type hierarchy. |

### Automatic Ontology Construction with LLMs as External Memory Layer (arXiv Apr 2026)

| Field | Detail |
|-------|--------|
| **arXiv** | 2604.20795 (Apr 22, 2026) |
| **Institution** | Pavel Salovskii, Iuliia Gorshkova — **Partenit.io** (San Francisco, Russian-speaking founders) 🇷🇺/🇺🇸 |
| **Technique** | Hybrid architecture: LLM + external RDF/OWL ontological memory layer. Automated pipeline: entity recognition → relation extraction → normalization → triple generation → SHACL/OWL validation → continuous graph updates. Inference: LLM uses combined context of vector retrieval + graph-based reasoning. |
| **Quantified Benefit** | Tower of Hanoi benchmark: ontology augmentation improves multi-step reasoning vs. baseline LLM. SHACL validation enables generation-verification-correction pipeline. |
| **Hermes Relevance** | The `generation-verification-correction` pattern is directly applicable to Graphiti: after each episode extraction, run SHACL check on new facts → flag violations → correct before committing. |

**Non-English coverage:**
- Chinese (HKUST KnowComp / AutoSchemaKG): **STRONGEST CONTRIBUTION** in this topic. HKUST KnowComp lab is a top Hong Kong/Chinese institution for knowledge graphs. 92% alignment, 5.9B edges, zero manual intervention.
- Chinese (Xiamen University / MemGraphRAG KDD 2026): Confirmed prior sweep. Schema-Fact-Passage 3-layer with ontology induction.
- Russian-origin (Partenit.io / Salovskii+Gorshkova): Russian-speaking founders at a US company. Hybrid RDF/OWL ontology memory with SHACL validation.
- European (ICSC 2026 / OntoEKG): European/international conference venue.
- Cross-language convergence: **STRONG** (ZH/HK, European, Russian-origin all independently developing LLM-driven ontology induction from corpus, with 92% / 0.724 F1 / SHACL validation as distinct technique families).

---

## Topic 5 — Deep Dream / Nightly Memory Distillation

### NEMORI — Adaptive Memory Distillation via Predictability (arXiv Aug 2025 / Apr 2026)

| Field | Detail |
|-------|--------|
| **Paper** | *What Deserves Memory: Adaptive Memory Distillation for LLM Agents* (NEMORI) |
| **arXiv** | 2508.03341 (Aug 5, 2025; v4 Apr 16, 2026 — ACL 2026) |
| **Venue** | **ACL 2026** (confirmed from search snippet "aclanthology.org/2026") |
| **Institution** | Wenquan Ma, Jiayan Nan, Wenlong Wu, Yize Chen — (institution unspecified in abstract; ACL 2026) |
| **GitHub** | github.com/nemori-ai/nemori |
| **Technique** | Two-module cascading pipeline: (1) **Episodic Memory Integration**: transforms raw interactions into coherent narratives (removes clutter, structures); (2) **Semantic Knowledge Distillation**: uses *prediction error* as the signal — experiences the LLM finds hard to predict (high prediction error = high future utility) get distilled into semantic memory. **Dual-pillar principles**: Two-Step Alignment (faithful representation) + Predict-Calibrate (proactive distillation). Asynchronous predict-calibrate pipeline. Top-down intelligent boundary detector. |
| **Quantified Benefit** | "Strong performance, efficiency, and storage reduction" — no single headline metric in abstract. See paper. Storage reduction confirmed. State-of-the-art on long-range contextual benchmarks. |
| **Hermes Action** | **HIGH PRIORITY**. Replace the current heuristic-based importance scoring in `agent-memory-consolidation` with NEMORI's predict-calibrate: run a small LLM over recent episodes, measure prediction error per episode segment → distill high-error segments (= novel/unexpected information) into MEMORY.md. Low-error segments (= routine/predictable) → prune or archive only. |

### SCM — Sleep-Consolidated Memory with NREM/REM Phases (arXiv Apr 2026)

| Field | Detail |
|-------|--------|
| **Paper** | *SCM: Sleep-Consolidated Memory with Algorithmic Forgetting for Large Language Models* |
| **arXiv** | 2604.20943 (Apr 22, 2026) |
| **Institution** | Saish Sachin Shinde (independent) |
| **Technique** | 5 components inspired by human memory: limited-capacity working memory; multi-dimensional importance tagging; **offline sleep-stage consolidation with distinct NREM and REM phases**; **intentional value-based forgetting**; computational self-model for introspection. NREM phase = consolidation of recent memories into structured form. REM phase = cross-referencing and integration with long-term memory. |
| **Quantified Benefit** | **Perfect recall accuracy over 10-turn conversations** (benchmark suite of 8 tests). **90.9% reduction in memory noise** through adaptive forgetting. Memory search latency below 1ms. |
| **Hermes Feasibility** | **High** — well-defined NREM/REM phases map directly to a 2-stage cron job. No ML training required. |
| **Hermes Action** | Restructure `agent-memory-consolidation` cron into 2 phases: **NREM** (consolidate: merge recent episodes into structured summaries, deduplicate, update daily MEMORY section) → **REM** (integrate: cross-reference with existing long-term MEMORY.md, resolve conflicts, promote novel patterns to skill candidates). |

### Human-Inspired Memory Architecture — Sleep-Phase Consolidation (arXiv May 2026)

| Field | Detail |
|-------|--------|
| **Paper** | *Human-Inspired Memory Architecture for LLM Agents* |
| **arXiv** | 2605.08538 (May 8, 2026) |
| **Institution** | Doga Kerestecioglu, Alexei Robsky, Clemens Vasters, Anshul Sharma, Yitzhak Kesselman — (multi-institution, likely Microsoft given author surnames/affiliations pattern) |
| **Technique** | 6 mechanisms: (1) sleep-phase consolidation; (2) interference-based forgetting; (3) engram maturation; (4) reconsolidation upon retrieval; (5) entity knowledge graphs; (6) hybrid multi-cue retrieval. **Deduplication-based consolidation** during sleep phase. Synthetic calibration methodology derives thresholds without benchmark data exposure (avoids leakage). |
| **Quantified Benefit** | **97.2% retention precision with 58% store reduction** on VSCode issue-tracking dataset (13K issues, 120K events). **+13.3 pp preference recall** at S-tier scale (50 sessions). At M-tier 200K-token budget: matches raw retrieval accuracy (70.1% vs. 71.2%) while exposing tunable accuracy/store-size curve. |
| **Hermes Feasibility** | **High** — deduplication-based consolidation is prompt-engineerable. +13.3 pp recall improvement is meaningful. |
| **Hermes Action** | Add deduplication step to consolidation cron: before writing to MEMORY.md, check new content against existing entries for semantic similarity (ChromaDB query) → merge duplicates → write only genuinely new information. The 97.2%/58% numbers (retain nearly everything of value, cut store by more than half) are directly applicable to MEMORY.md bloat management. |

**Implementation schedule for Hermes Dream / nightly consolidation:**
```
NREM phase (22:00 daily):
1. Collect today's episodes from session_search (FTS5)
2. Run NEMORI predict-calibrate on each: measure LLM prediction error
3. High-error segments → extract key facts → candidate MEMORY.md additions
4. Dedup check (SCM/2605.08538): cosine distance to existing MEMORY.md entries
5. Low-error, high-similarity = prune. High-error, low-similarity = keep.

REM phase (23:00 daily):  
6. Cross-reference new facts with Graphiti KG
7. Conflict detection (MemGraphRAG pattern, 2606.00610)
8. Resolve conflicts → update Graphiti + MEMORY.md
9. Identify L1 traces exceeding promotion threshold → create L2 policy candidates
10. Signal skill crystallization for patterns appearing ≥3 episodes
```

**Non-English coverage:**
- Chinese (PyTorchKR surfaced): MemAgent (ByteDance + Tsinghua AIR, arXiv:2507.02259) has dream-adjacent fixed-size overwrite memory — different mechanism (RL-trained overwrite) rather than sleep-phase distillation.
- Russian: CyberLeninka search for `консолидация памяти ИИ` (AI memory consolidation) returned only general AI adoption articles. **GAP** — Russian academic cycle too slow for this fast-moving topic.
- Korean: PyTorchKR digest surfaces sleep-phase consolidation papers; no KR-origin independent research. Consumers not producers.
- Cross-language convergence: **MODERATE** (Multiple EN papers independently converging on sleep-phase consolidation / NREM+REM metaphor; Chinese community has adjacent work on RL-based overwrite memory). Non-English original research: GAP confirmed.

---

## Topic 6 — CowAgent-Style 3-Tier Memory (STM → MTM → LPM/MEMORY.md)

### MemoryOS — Short-Term / Mid-Term / Long-Term Personal Memory (arXiv May 2025)

| Field | Detail |
|-------|--------|
| **Paper** | *Memory OS of AI Agent* |
| **arXiv** | 2506.06326 (May 30, 2025) |
| **Venue** | **ACL 2025** (from aclanthology.org/2025 hit in search) |
| **Institution** | Jiazheng Kang, Mingming Ji, Zhe Zhao, Ting Bai — **BAI-LAB** (Beijing Academy Institute – Ting Bai's lab) 🇨🇳 |
| **GitHub** | github.com/BAI-LAB/MemoryOS |
| **Technique** | 3 storage tiers: **STM** (short-term: dialogue pages `{Q, R, T}`), **MTM** (mid-term: segmented paging by topic — FIFO dialogue-chain principle), **LPM** (long-term personal memory: persistent user/agent preferences). Key update rules: STM→MTM = dialogue-chain-based FIFO (full pages, topic grouping). MTM→LPM = segmented page organization strategy (topic segments with multiple pages get merged). Memory Storage → Updating → Retrieval → Generation pipeline. |
| **Quantified Benefit** | **+49.11% F1** improvement on LoCoMo benchmark (GPT-4o-mini baseline). **+46.18% BLEU-1** improvement on LoCoMo. "Contextual coherence and personalized memory retention in long conversations." |
| **Hermes Feasibility** | **Very High** — Python, open-source, directly maps to Hermes architecture. |

### CowAgent Memory Architecture (Production System, not paper)

*Source: docs.cowagent.ai + github.com/nludd25/CowAgent (Mar 2026)*

| Field | Detail |
|-------|--------|
| **Source** | CowAgent documentation + GitHub |
| **Architecture** | Exact 3-tier: conversation context (short-term) → daily memory summaries (mid-term) → MEMORY.md (long-term). A **nightly Deep Dream pass** distills scattered memories into refined long-term entries + narrative journal. |
| **STM** | In-context conversation window (default context length) |
| **MTM** | Daily memory: per-day summaries, auto-generated, not permanent |
| **LPM** | ~/cow/MEMORY.md: long-term user preferences, important decisions, key facts. Agent reads+writes via tools. |
| **Deep Dream** | Nightly background LLM pass: takes today's MTM daily summaries → distills → updates MEMORY.md with refined entries. Also generates a "narrative journal" (separate artifact). |
| **Hermes Fit** | **This IS the Hermes pattern.** session_search (STM), agent-memory-consolidation cron (MTM→LPM), MEMORY.md (LPM). The nightly Deep Dream = agent-memory-consolidation.py. |

### AutoMem — Dual-Loop Automated Memory Optimization (arXiv Jul 2026)

*Already in multilingual-agent-efficiency-sweep-jun-jul-2026.md baseline*

| Field | Detail |
|-------|--------|
| **arXiv** | 2607.01224 (Jul 2026) |
| **Institution** | Stanford (Wu, Zhu, Zhang, Wang, Yeung-Levy) |
| **Technique** | Outer loop: meta-LLM revises memory scaffold (prompts, file schemas, action vocabulary). Inner loop: fine-tunes dedicated memory specialist from agent's own good decisions. File-system operations promoted to first-class memory actions. |
| **Quantified Benefit** | 2×–4× improvement on Crafter/MiniHack/NetHack. 32B open model approaches Claude Opus 4.5. |
| **Hermes Action** | Use AutoMem's outer-loop self-revision to evolve agent-memory-consolidation.py: after each nightly run, evaluate output quality → LLM proposes edits to the consolidation prompt → patch → re-run. This is the "meta-memory" improvement loop. |

### Memora — Harmonic Memory (Microsoft Research, ICML 2026)

*Already in multilingual-agent-efficiency-sweep-jun-jul-2026.md baseline, surfaced by Korean community*

| Field | Detail |
|-------|--------|
| **arXiv** | 2602.03315 (Feb 2026) |
| **Institution** | Microsoft Research |
| **Venue** | ICML 2026 |
| **Key Innovation** | Decouples content storage from retrieval indexing. Multi-hop retrieval captures beyond semantic similarity. Harmonic representation = multiple indexing views of the same memory item. |
| **Hermes Action** | Apply harmonic multi-view indexing to MEMORY.md entries: index each entry by (1) semantic embedding, (2) entity mentions via Graphiti, (3) FTS5 keywords. Retrieval combines all 3 views. |

**Comparison table — 3-tier implementations:**

| System | STM | MTM | LPM/L4 | Promotion STM→MTM | Promotion MTM→LPM | Score |
|--------|-----|-----|---------|------------------|--------------------|-------|
| MemoryOS (BAI-LAB) | Dialogue pages | Topic segments (FIFO paging) | User preferences DB | Page full → topic group | Topic segment matures → LPM | +49.1% F1, +46.2% BLEU |
| CowAgent | In-context window | Daily summaries | MEMORY.md | End-of-day MTM cron | Nightly Deep Dream | Qualitative (no benchmark) |
| Hermes (current) | session_search FTS5 | L1-promote.py | MEMORY.md + Graphiti | Cron: haiku extraction | agent-memory-consolidation.py | Not benchmarked |
| MemAgent | Sliding window | Fixed-size buffer (RL overwrite) | None (overwrite only) | RL-trained overwrite gate | — | <5% degradation at 3.5M tokens |

**Gap identified**: Hermes STM→MTM promotion is triggered by cron schedule. MemoryOS uses FIFO page-full trigger. The +49% F1 improvement suggests **trigger mechanism matters**: page-full (topic continuity) beats time-based cron. Consider hybrid: cron as fallback, plus page-full trigger when session reaches token threshold.

**Non-English coverage:**
- Chinese (BAI-LAB / MemoryOS): **STRONGEST CONTRIBUTION** in this topic. Beijing lab, ACL 2025. +49.1% F1 / +46.2% BLEU quantified improvement. Direct implementation at github.com/BAI-LAB/MemoryOS.
- Chinese (ByteDance + Tsinghua AIR / MemAgent 2507.02259): RL-trained fixed-size memory buffer — adjacent but different mechanism (RL vs. heuristic promotion rules).
- Russian (Malakhov, CyberLeninka): Redis/ChromaDB/files 3-tier — independent Russian practitioner documentation of the same pattern (no benchmark, qualitative only).
- Korean (PyTorchKR / Memori SQL-native memory): Korean independent implementation — discusses tiered SQL memory but no benchmarks.
- Cross-language convergence: **VERY STRONG** (ZH academic: MemoryOS with quantified results; RU practitioner: Redis/ChromaDB/files; KR practitioner: SQL-native tiers; JP practitioner: Zenn articles on hot/cold memory). Four independent tracks converging on the same 3-tier architecture as the answer.

---

## Quick Reference Table

| arXiv | Title | Year | Venue | Institution | Topic | Key Metric |
|-------|-------|------|-------|-------------|-------|------------|
| 2505.22101 | MemOS (short) | 2025 | arXiv | Zhejiang/SJTU/ECNU (🇨🇳) | T1 | MemCube abstraction |
| 2507.03724 | MemOS (full) | 2025 | arXiv | Zhejiang/SJTU/ECNU (🇨🇳) | T1 | 36pp, 5 tables |
| MemTensor/MemOS | L1/L2/L3/L4 | 2026 | GitHub | MemTensor (🇨🇳) | T1 | Promotion heuristics documented |
| 2604.15484 | vstash hybrid retrieval | 2026 | arXiv | Independent | T2 | +21.4% NDCG@10, 20.9ms @50K chunks |
| autosre-ai/agentmemory | agent-memory-toolkit | 2026 | GitHub | autosre.ai | T2 | 95.2% R@5 LongMemEval-S |
| 2604.16394 | Agentic Hybrid Retrieval | 2026 | arXiv | Multi-inst. | T2 | Architecture reference |
| 2410.12788 | Meta-Chunking | 2024/2025 | arXiv cs.CL | IAAR-Shanghai (🇨🇳) | T3 | Perplexity/margin chunking |
| 2603.25333 | Adaptive Chunking | 2026 | LREC 2026 | Ekimetrics (🇫🇷) | T3 | +10pp correctness, +33% Qs answered |
| infiniflow/ragflow | RAGFlow chunking | 2026 | GitHub | InfiniFlow (🇨🇳) | T3 | 80K stars, production |
| 2505.23628 | AutoSchemaKG/ATLAS | 2025 | arXiv cs.CL | HKUST KnowComp (🇭🇰) | T4 | 92% schema alignment, 5.9B edges, 0 manual |
| 2606.00610 | MemGraphRAG | 2026 | KDD 2026 | Xiamen Univ (🇨🇳) | T4 | Schema-Fact-Passage + conflict detection |
| 2602.01276 | OntoEKG | 2026 | ICSC 2026 | European/intl | T4 | F1=0.724 Data domain |
| 2604.20795 | Auto Ontology (LLM memory) | 2026 | arXiv | Partenit.io (🇷🇺/🇺🇸) | T4 | SHACL validation, planning improvement |
| 2508.03341 | NEMORI (ACL 2026) | 2025/2026 | ACL 2026 | (unspecified) | T5 | Predict-calibrate distillation, storage reduction |
| 2604.20943 | SCM sleep memory | 2026 | arXiv cs.LG | Independent | T5 | 100% recall, 90.9% noise reduction |
| 2605.08538 | Human-Inspired Memory | 2026 | arXiv | Multi-inst. | T5 | 97.2% precision, 58% store reduction, +13.3pp |
| 2506.06326 | MemoryOS (ACL 2025) | 2025 | ACL 2025 | BAI-LAB, Beijing (🇨🇳) | T6 | +49.1% F1, +46.2% BLEU LoCoMo |
| nludd25/CowAgent | CowAgent Deep Dream | 2026 | GitHub | nludd25 | T6 | STM→MTM→MEMORY.md + nightly distill |
| 2607.01224 | AutoMem | 2026 | arXiv | Stanford | T6 | 2×–4× Crafter/NetHack |
| 2602.03315 | Memora | 2026 | ICML 2026 | Microsoft Research | T6 | Harmonic multi-view memory |

---

## Hermes Implementation Priority Ranking

| Priority | Topic | Action | Feasibility | Key Metric |
|----------|-------|--------|-------------|------------|
| **P1** | T3 (Chunking) | Implement 5 intrinsic metrics (RC/ICC/DCC/BI/SC) for per-document strategy selection in Hindsight | **Very High** | +10pp correctness, +33% Qs answered |
| **P2** | T6 (3-tier) | Switch STM→MTM trigger from time-based cron to hybrid (page-full topic boundary + cron fallback) | **High** | +49.1% F1 (MemoryOS) |
| **P3** | T5 (Distillation) | Add NEMORI predict-calibrate step to consolidation cron: predict error → distill high-error segments | **High** | Storage reduction + state-of-the-art recall |
| **P4** | T2 (Hybrid retrieval) | Add Ebbinghaus time-decay weighting + 3-source RRF (FTS5+ChromaDB+Graphiti) to Hindsight | **Very High** | 95.2% R@5 (agentmemory) |
| **P5** | T5 (Sleep phases) | Restructure consolidation cron into NREM (consolidate) + REM (integrate+conflict-resolve) phases | **High** | 97.2% precision, 58% store reduction |
| **P6** | T4 (Ontology) | Apply AutoSchemaKG schema induction to Graphiti's edge_type vocabulary (batch discovery cron) | **Medium** | 92% schema alignment, 0 manual |
| **P7** | T2 (Hybrid retrieval) | Implement adaptive IDF-weighted RRF in session_search/Hindsight combined query | **Very High** | +21.4% NDCG@10 |
| **P8** | T1 (MemOS L1→L2) | Implement cross-episode consistency check for L1→L2 promotion (FTS5 recurring n-gram across N sessions) | **High** | Architecture validation |
| **P9** | T6 (Meta-memory) | AutoMem outer loop: evaluate consolidation quality → LLM proposes prompt edits → patch | **Medium** | 2×–4× gain |

---

## Cross-Language Convergence Summary

| Technique | Tracks | Strength | Notes |
|-----------|--------|----------|-------|
| 3-tier hierarchical memory (STM→MTM→LPM) | ZH (MemoryOS/BAI-LAB, MemAgent/ByteDance+Tsinghua), RU (Malakhov CyberLeninka), KR (PyTorchKR Memori), JP (Zenn practitioners) | **VERY STRONG** | 4 independent communities, quantified (ZH: +49% F1) |
| Sleep-phase / nightly consolidation as first-class mechanism | EN (SCM, NEMORI, Human-Inspired), ZH (adjacent: MemAgent overwrite) | **STRONG** | EN monopolizes original research; ZH has adjacent mechanism |
| Adaptive/metric-guided chunking (not fixed-size) | ZH (Meta-Chunking/IAAR-Shanghai), FR (Adaptive Chunking/Ekimetrics LREC 2026) | **STRONG** | Independent French + Chinese convergence |
| LLM-driven ontology induction from corpus | HK/ZH (AutoSchemaKG/HKUST, MemGraphRAG/Xiamen), EU (OntoEKG/ICSC), RU-origin (Partenit.io) | **STRONG** | 3 independent tracks, quantified (92%, F1=0.724) |
| Hybrid BM25+vector retrieval with RRF fusion | EN (vstash), KR (PyTorchKR Memori/SQL-native), ZH (CSDN commentary) | **MODERATE** | EN leads; KR independently implements same pattern |

---

## Non-English Coverage Gap Log

| Language | Topic | Status | Notes |
|----------|-------|--------|-------|
| Chinese | T1 (MemOS tiers) | ✅ **HIT** | MemOS originates from Chinese consortium (Zhejiang/SJTU/ECNU) |
| Chinese | T3 (Chunking) | ✅ **HIT** | Meta-Chunking (IAAR-Shanghai) + RAGFlow (InfiniFlow) |
| Chinese | T4 (Ontology) | ✅ **HIT** | AutoSchemaKG (HKUST) + MemGraphRAG (Xiamen) |
| Chinese | T6 (3-tier) | ✅ **HIT** | MemoryOS (BAI-LAB, +49% F1) + MemAgent (ByteDance+Tsinghua) |
| Chinese | T2 (hybrid retrieval) | ⚠️ **PARTIAL** | CSDN commentary only; no independent academic paper |
| Chinese | T5 (distillation) | ⚠️ **PARTIAL** | MemAgent RL-overwrite is adjacent but different mechanism |
| French | T3 (chunking) | ✅ **HIT** | Adaptive Chunking at LREC 2026 (Ekimetrics) — strongest FR contribution |
| Russian | T4 (ontology) | ✅ **HIT** | Partenit.io founders (Russian-origin) — OntoEKG RDF/OWL |
| Russian | All other topics | ❌ **GAP** | CyberLeninka: no original research; consuming EN papers |
| Korean | All topics | ⚠️ **PARTIAL** | PyTorchKR curates EN papers well; no original KR-venue academic research found |
| Japanese | All topics | ❌ **GAP** | IPSJ/Zenn: practitioners consume EN papers; no original research |
