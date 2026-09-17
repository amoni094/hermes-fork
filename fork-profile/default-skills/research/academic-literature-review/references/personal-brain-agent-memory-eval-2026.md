# Personal Brain / Agent Memory Evaluation Benchmarks — Reference Bank
*Research conducted 2026-07-29. All arXiv IDs independently verified via HTML search.*

## Quick Reference Table

| Benchmark/Framework | arXiv ID | Venue | Legal? | Key Metric | Install |
|---|---|---|---|---|---|
| LongMemEval | 2410.10813 | ICLR 2025 | Partial | QA accuracy, Session Recall@k | `pip install -r requirements-lite.txt` |
| LongMemEval-V2 | — | 2026 | Partial | Agentic task completion with memory | same repo |
| AMA-Bench | 2602.22769 | ICML 2026 | Partial | MCQ+open QA on agent trajectories | `pip install -r requirements.txt` |
| MemDelta | 2606.29914 | ACL 2026 Findings | No | Marginal utility of external memory | Custom (LongMemEval harness) |
| LoCoMo | — | Snap Research | Partial | QA accuracy, event summarization, dialogue gen | Custom |
| DMR (MemGPT/Letta) | — | Industry (Letta team) | No | Retrieval accuracy % | Custom |
| Zep/Graphiti | 2501.13956 | Jan 2025 | Partial | LongMemEval +18.5%, DMR 94.8% | `pip install zep-python` |
| Oracle Agent Memory | 2607.13157 | Tech report 2026 | YES | LongMemEval 93.8%, 10.7× token reduction | Commercial (Oracle DB) |
| Maximem/ACM | 2607.21503 | Tech report 2026 | Partial | LongMemEval 92%, LoCoMo 93.2% | Commercial |
| NapMem | 2607.05794 | Jul 2026 | Partial | Competitive on PersonaMem-v2, LongMemEval, LoCoMo | Research |
| LRAGE | 2504.01840 | ACL 2025 Demo | **YES** | Task accuracy on legal QA datasets | `pip install lrage` |
| RAGAS | — | OSS | Partial | Faithfulness, ContextPrec/Recall, AnswerRel | `pip install ragas` |
| DeepEval | — | OSS | Partial | GEval, DAGMetric, 50+ metrics | `pip install deepeval` |
| TruLens | — | OSS | Partial | RAG Triad | `pip install trulens` |
| DynamicMCPBench | 2607.20531 | Jul 2026 | YES (applicable) | pass^3, effect checkpoints | Custom (reusable framework) |
| ProvenanceGuard | 2606.18037 | Jun 2026 | **YES** | Block F1 0.802, Source Acc 0.858 | Custom |
| RAS-Eval | 2506.15253 | 2025 | Applicable | TCR under attack, CWE mapping | pip + custom |
| kg-eval | — | OSS | **YES** | 4 pillars, 21 metrics (Neo4j) | `python kg_eval.py` |
| WorkSurface-Bench | 2607.25765 | Jul 2026 | **YES** | Route F1, Answer accuracy | Custom |
| MemGraphRAG | 2606.00610 | KDD 2026 | Partial | QA vs GraphRAG baseline | Custom |
| OrgForge | 2603.14997 | Mar 2026 | **YES** | Prose-to-GT fidelity +0.46 abs | Open-source |

---

## Section 1: Agent Memory Benchmarks

### LongMemEval (ICLR 2025)
- **GitHub:** https://github.com/xiaowu0162/LongMemEval ⭐970
- **arXiv:** 2410.10813
- **Authors:** Di Wu, Hongwei Wang, Wenhao Yu, Yuwei Zhang, Kai-Wei Chang, Dong Yu
- **500 questions** across multi-session timestamped chat histories
- **5 abilities tested:** Information Extraction, Multi-Session Reasoning, Knowledge Updates, Temporal Reasoning, Abstention
- **Variants:** LongMemEval-S (~40 sessions, ~115k tokens), LongMemEval-M (~500 sessions), Oracle (oracle retrieval upper-bound)
- **Eval:** LLM-as-judge via GPT-4o; also session-level and turn-level recall metrics
- **2026 update:** LongMemEval-V2 extends to agentic contexts (memory used during task execution, not just QA)
- **Benchmark score context:** Zep +18.5% vs baseline; Oracle Agent Memory 93.8%; Maximem 92%
- **Legal relevance:** Temporal reasoning + knowledge updates are critical for legal matters spanning months

### AMA-Bench (ICML 2026)
- **GitHub:** https://github.com/AMA-Bench/AMA-Bench ⭐64
- **arXiv:** 2602.22769
- **HuggingFace:** AMA-bench/AMA-bench (dataset + live leaderboard)
- **Authors:** Yujie Zhao, Boqin Yuan et al. (UCSD, Meta AI)
- **Evaluates:** memory on long-horizon agent TRAJECTORIES (coding, planning), not chat sessions
- **Two-stage:** build memory from trajectory → retrieve for QA
- **Metrics:** MCQ accuracy, open-ended QA (LLM-as-judge), evidence retrieval quality
- **Agent harness API:** plug in custom agents via `AgentHarnessMethod` subclass
- **Legal relevance:** Relevant for multi-step legal research agents that need to recall prior decisions

### MemDelta (ACL 2026 Findings)
- **arXiv:** 2606.29914
- **HuggingFace:** memdelta-bench/memdelta-benchmark
- **Author:** Kuan Wang
- **Purpose:** CONTROLLED ABLATION — varies one memory component at a time on LongMemEval-S
- **Reveals:** Hidden confounds in existing memory eval — retrieval oracle assumptions, model family effects, history length effects
- **Use:** Design controlled experiments for your own system; don't run it directly as a feature benchmark
- **Legal relevance:** Methodological tool for rigorous experiment design

### LoCoMo (Snap Research)
- **GitHub:** https://github.com/snap-research/LoCoMo
- **Evaluates:** long-term conversational memory (multi-session, persistent personas, temporal events)
- **Three tasks:** QA, Event Summarization, Multi-modal Dialogue Generation
- **Metrics:** QA accuracy, ROUGE/BERTScore/LLM-judge for summarization, generation relevance
- **Legal relevance:** Persona-based dialogues model client relationships well

### DMR (Deep Memory Retrieval) — MemGPT/Letta Benchmark
- **Origin:** Letta/MemGPT team (established as their primary eval metric)
- **Scope:** Retrieval accuracy from simulated long-term multi-session memory
- **Known scores:** MemGPT 93.4%, Zep/Graphiti 94.8%
- **Status (2026):** Community consensus is that DMR is too narrow; LongMemEval is the preferred standard
- **Legal relevance:** Low — single-domain conversational retrieval, no legal specifics

---

## Section 2: Legal RAG Evaluation

### LRAGE — Legal Retrieval Augmented Generation Evaluation
- **GitHub:** https://github.com/hoorangyee/LRAGE ⭐78
- **arXiv:** 2504.01840
- **Venue:** ACL 2025 Demo
- **Authors:** Minhu Park, Hongseok Oh, Eunkyung Choi, Wonseok Hwang (University of Seoul)
- **Install:** `pip install lrage`
- **Extends:** EleutherAI's lm-evaluation-harness with retriever/reranker modules
- **Legal datasets bundled:**
  - LegalBench (HazyResearch) — US legal reasoning tasks
  - LawBench (OpenCompass) — Chinese legal benchmark
  - KBL — Korean Bar/Legal benchmark
  - Legal RAG Benchmarks (RegLab Stanford) — bar exam QA, housing law QA
  - Pile-of-law — case opinions, US Code, CFR, EU law
- **Pre-compiled BM25 indices** for Pile-of-law (pile-of-law-subsets-bm25 on HuggingFace)
- **Metrics:** task accuracy, LLM-as-a-judge with legal rubrics, retrieval quality, agent effectiveness
- **GUI:** available on HuggingFace Spaces
- **Limitations:** No privilege/confidentiality dimension; Korean/Chinese focus in some sub-tasks

### General RAG Frameworks (abbreviated — see domain-research-synthesis for full landscape)
| Framework | Install | Core Legal Metric |
|---|---|---|
| RAGAS | `pip install ragas` | Faithfulness (no hallucination), ContextPrecision |
| DeepEval | `pip install deepeval` | GEval (custom legal rubrics via CoT LLM-judge) |
| TruLens | `pip install trulens` | RAG Triad (context relevance, groundedness, answer relevance) |

---

## Section 3: MCP Evaluation

### DynamicMCPBench
- **arXiv:** 2607.20531
- **Authors:** Jerzy Kamiński et al.
- **Submitted:** 2026-07-10
- **FIRST benchmark specifically for LLM agents over live MCP servers**
- **Key design:** reusable framework, not fixed dataset — run on YOUR own MCP servers
- **Scoring: pass^3** — task counts as solved only if 3 independent attempts all succeed
- **Effect checkpoints:** distilled from golden trajectory; scores on side-effects, not final answer
- **Scale validation done:** 24 models, 121 servers, 750 tasks, 15 categories
  - Best agents: ~50% solve rate
  - 31% of tasks: no model solves them
  - Accuracy vs tool-chain length: 39% (short) → 13% (long)
  - Human validation: κ=0.76
- **Legal use:** pass^3 is the right threshold for legal-critical tools (policy lookup, template retrieval)

### ProvenanceGuard
- **arXiv:** 2606.18037
- **Authors:** Ander Alvarez, Santhiya Rajan, Samuel Mugel, Román Orús
- **Problem addressed:** "cross-source conflation" — claim is true somewhere but attributed to wrong source
- **Pipeline:**
  1. Capture MCP traces (tool IDs, source IDs, raw outputs)
  2. Decompose answers into atomic claims
  3. Route each claim to source-specific evidence
  4. NLI + token-alignment proxy verification
  5. Attribution check: stated source vs. routed source
  6. Per-claim verdict + answer-level allow/block + repair-and-reverify
- **Metrics (medical domain, 281 traces):**
  - Block F1: 0.802
  - Source Accuracy: 0.858
  - Multi-source Block F1: 0.846
  - Source+relation accuracy (hard): 0.229
  - Repair resolves 100% of blocked answers in test set
- **Legal relevance: VERY HIGH** — citing wrong statute/case is a serious professional risk; medical→legal transfer is direct

### RAS-Eval (Real-world Agent Security Evaluation)
- **GitHub:** https://github.com/lanzer-tree/RAS-Eval
- **arXiv:** 2506.15253
- **Authors:** Yuchuan Fu, Xiaohan Yuan, Dongxia Wang
- **Evaluates:** LLM agent security including MCP-format tools
- **Scale:** 80 test cases, 3,802 attack tasks, 11 CWE categories
- **Tool formats:** JSON, LangGraph, **MCP** — directly relevant
- **Metrics:**
  - TCR (Task Completion Rate) under attack: avg drop 36.78%
  - Attack Success Rate: 85.65% in academic settings
  - Larger models outperform smaller on security
- **Legal relevance:** Adversarial documents could manipulate legal RAG analysis (prompt injection risk)

---

## Section 4: Knowledge Graph Quality Evaluation

### kg-eval (4-Pillar, 21-Metric Neo4j Evaluator)
- **GitHub:** https://github.com/Jayluci4/kg-eval
- **Install:** `python kg_eval.py` (requires running Neo4j instance)
- **Framework: 4 pillars**
  1. **Structural Integrity:** connectivity, dangling edges, temporal overlap violations (<0.1% target), property completeness, index usage
  2. **Temporal & Evolutionary Fidelity:** temporal coherence, event-state consistency, version continuity, staleness (>90 days), change rate
  3. **Retrieval & Reasoning Performance:** P95 query latency, query success rate, provenance completeness, reasoning path length
  4. **Operational & System Health:** ingestion success rate, event coverage, data lineage tracking
- **Output:** Pass/fail per metric + overall score → "PRODUCTION-READY" at ≥80%
- **Customization:** Modify Cypher queries for your node labels/relationship types and adjust pass/fail thresholds
- **Legal relevance:** Temporal coherence (legal facts change over time), provenance completeness (citation chains), staleness all directly relevant

### WorkSurface-Bench
- **GitHub:** https://github.com/haolpku/WorkSurface-Bench
- **arXiv:** 2607.25765
- **Authors:** Hao Liang et al.
- **Evaluates:** whether enterprise agents correctly select the knowledge surface type (document vs. table vs. graph) before answering
- **1,151 atomic tasks** across document/table/graph/cross-surface questions
- **Key finding:** correct routing is necessary but not sufficient — Answer drops from ~99% Route F1 to 56-75% Answer accuracy
- **Legal relevance:** Legal work requires selecting the right source type (statute vs. case vs. regulatory guidance vs. internal memo)

### MemGraphRAG (KDD 2026)
- **GitHub:** https://github.com/XMUDeepLIT/MemGraphRAG
- **arXiv:** 2606.00610
- **Authors:** Chuanjie Wu et al. (Xiamen University)
- **Problem:** Addresses thematically inconsistent, logically conflicting, structurally fragmented graphs from existing GraphRAG
- **Solution:** Multi-agent system with shared memory for global context during extraction; memory-aware hierarchical retrieval
- **Legal relevance:** Legal KGs require conflict resolution (statute can't have two effective dates); pattern directly applicable

---

## Section 5: Enterprise/Synthetic Corpus Frameworks

### OrgForge (Verifiable Synthetic Enterprise Corpus)
- **arXiv:** 2603.14997
- **Author:** Jeffrey Flynt
- **Purpose:** Generate synthetic enterprise corpora (emails, tickets, CRM, incidents) with verifiable ground truth for RAG evaluation
- **Architecture:** Deterministic Python engine maintains SimEvent ground-truth bus; LLMs only generate prose
- **15 artifact categories:** emails, tickets, CRM, wikis, incidents, SLA invoices, etc.
- **Metric:** prose-to-ground-truth fidelity +0.46 absolute vs. chained LLM baselines
- **Legal relevance: VERY HIGH** — exactly models the "personal second brain" scenario; use to generate synthetic legal team corpora with known ground truth

---

## Section 6: Recommended Eval Stack (3 Tiers)

### Tier 1 — pip-installable, low setup
```bash
pip install ragas            # baseline RAG quality
pip install deepeval         # custom legal rubrics via GEval
# LongMemEval:
git clone https://github.com/xiaowu0162/LongMemEval && pip install -r requirements-lite.txt
# LRAGE:
pip install lrage
```

### Tier 2 — domain-specific, moderate setup
```bash
# kg-eval (Neo4j required):
git clone https://github.com/Jayluci4/kg-eval && python kg_eval.py
# AMA-Bench:
git clone https://github.com/AMA-Bench/AMA-Bench && pip install -r requirements.txt
```

### Tier 3 — custom patterns (implement from methodology)
- **DynamicMCPBench pattern** — adapt for your MCP servers; use pass^3 threshold for legal tools
- **ProvenanceGuard pattern** — implement claim→source routing for all Team Brain MCP query answers
- **OrgForge-inspired** — generate synthetic legal team corpus with verifiable ground truth

---

## Section 7: Gaps in Coverage (No Benchmark Exists Yet)

These are open problems as of July 2026:
1. **Attorney-client privilege classification** — no benchmark for RAG correctly identifying/protecting privileged information
2. **Multi-jurisdiction consistency** — no benchmark for jurisdiction-specific differences in legal answers
3. **Legal temporal validity** — no legal QA benchmark testing whether cited statutes are in effect at the relevant date (kg-eval covers structurally; no domain-specific QA benchmark)
4. **Cowork consistency** — no benchmark for two AI agents collaborating on contract review reaching consistent conclusions
5. **Long-form faithfulness** — RAGAS faithfulness validated on short passages; no benchmark for faithfulness over 50-page contracts
6. **Email extraction accuracy** — no dedicated benchmark for structured entity/event/decision extraction from professional email threads (MMORE covers email as one of 15 file types in multimodal pipeline; OrgForge provides methodology)

---

## Section 8: Multilingual Coverage

### Japanese
- RAGAS and LLM-as-a-judge dominant in practice (Zenn: hibari_inc, daijobu articles)
- SynRAG (JLR Workshop 2025): Japanese RAG eval dataset construction using RAGEval; shows standard RAG performs poorly on Japanese domain QA
- No LRAGE equivalent for Japanese law

### Chinese
- RAGAS, RECALL, ARES used (CSDN, Zhihu — confirmed active community)
- LawBench (OpenCompass) = primary Chinese legal benchmark; integrated into LRAGE
- No Chinese equivalent of LRAGE

### Korean
- Allganize RAG leaderboard: covers legal domain (금융/공공/의료/법률/커머스) with public test datasets including complex tables/images
- KBL (Korean Bar/Legal) integrated into LRAGE
- MediaGen (미디어젠) patented agentic RAG for legal AI (patent registered July 2026)
- Active Korean legal RAG construction community (cloudjini.tistory.com tutorials)

---

*All papers verified against arXiv HTML search pages. GitHub repos verified. No sources fabricated.*
*Scores quoted directly from paper abstracts or repo documentation.*
