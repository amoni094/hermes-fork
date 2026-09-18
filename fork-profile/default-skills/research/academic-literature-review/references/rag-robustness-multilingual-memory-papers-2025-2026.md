# RAG Robustness, Multilingual RAG, Agent Memory Architecture — Research Survey July 2026

Sweep scope: RAG robustness to irrelevant/noisy context (extending ret-robust baseline),
multilingual RAG retrieval, agent memory architecture taxonomy, ontology-enhanced GraphRAG,
and agent externalization frameworks. Delta against existing baselines in
multilingual-agent-efficiency-sweep-jun-jul-2026.md and token-optimization-papers-2024-2026.md.

---

## 1. RAG Robustness — Core Papers (extending ret-robust 2310.01558)

### RetRobust (origin — the Yoran et al. 2023 paper)

| Field | Detail |
|-------|--------|
| **Paper** | *Making Retrieval-Augmented Language Models Robust to Irrelevant Context* |
| **arXiv** | 2310.01558 (v2 May 2024) |
| **Venue** | arXiv / EMNLP-adjacent 2023 |
| **Institution** | Tel Aviv University (Ori Yoran, Tomer Wolfson, Ori Ram, Jonathan Berant) |
| **GitHub** | github.com/oriyor/ret-robust — 77 stars, 2 forks (MIT, July 2026) |
| **Technique** | Two-method approach: (1) NLI-based filtering — DeBERTa NLI model filters retrieved passages that don't entail the answer; (2) Fine-tuning on 1K auto-generated mixed relevant+irrelevant examples makes LLM intrinsically robust without needing a filter. |
| **Quantified Benefit** | 1K examples suffice for robustness to irrelevant context while maintaining performance on relevant-context examples; multi-hop gains most critical (cascading-error problem solved). |
| **Hermes Feasibility** | **Medium** — NLI filtering works with any black-box API; fine-tuning requires white-box model access. The NLI-filter pattern is immediately applicable to Hermes RAG pipelines as a pre-generation gate. |
| **Hermes Action** | Apply NLI filtering before the generation call: retrieve N passages → run DeBERTa NLI (entailment check against query+expected-answer) → pass only entailed passages. pip-installable via transformers. |

### CQC-RAG (2026) — Cross-Query Consistency

| Field | Detail |
|-------|--------|
| **Paper** | *CQC-RAG: Robust Retrieval-Augmented Generation via Cross-Query Consistency* |
| **arXiv** | 2606.13438 (June 2026) |
| **Venue** | arXiv June 2026 |
| **Institution** | Multi-institution (Yanjia Sun, Sifan Liu, Jie Shao) |
| **Technique** | Cross-Query Consistency Hypothesis: correct answers maintain high confidence across semantically equivalent but syntactically diverse query rewrites; noise-induced hallucinations show unstable confidence. Rewrites query → retrieves shared pool → ranks by cross-query confidence stability → selects most consistent answer. No external supervision needed. |
| **Quantified Benefit** | +4.76 pp EM over strongest multi-query baseline on TriviaQA; +9.12 pp EM on MuSiQue (multi-hop). Self-evaluation without external supervision. |
| **Hermes Feasibility** | **High** — pure prompt engineering + query rewriting; works with any black-box LLM API. |
| **Hermes Action** | Add CQC step to Hindsight/GraphRAG recall: rewrite query 3 ways → retrieve → vote. Particularly powerful for multi-hop Graphiti queries. |

### RARE — Retrieval-Aware Robustness Evaluation (2025)

| Field | Detail |
|-------|--------|
| **Paper** | *RARE: Retrieval-Aware Robustness Evaluation for Retrieval-Augmented Generation Systems* |
| **arXiv** | 2506.00789 (June 2025, v3 Oct 2025) |
| **Venue** | arXiv preprint |
| **Institution** | Multi-institution US (Zeng, Cao, Wang, Zhao, Qiu, Ziyadi, Wu, Li) |
| **Technique** | Unified framework + benchmark jointly stress-testing query AND document perturbations over dynamic, time-sensitive corpora. KG-driven synthesis pipeline (RARE-Get) auto-extracts single/multi-hop relations from corpus, generates multi-level question sets without manual intervention. Constructs RARE-Set: 527 finance/economics/policy docs, 48,295 questions evolving with source changes. Defines retrieval-conditioned robustness metrics (RARE-Met). |
| **Quantified Benefit** | Reveals RAG systems unexpectedly sensitive to perturbations; consistently lower robustness on multi-hop vs single-hop queries across all domains. No single "fixed" number — diagnostic framework. |
| **Hermes Feasibility** | **Medium** — KG synthesis pipeline is framework-level tooling. Useful as an evaluation lens for Graphiti/Hindsight retrieval quality. |

### Noise Filtering is Inherently Difficult (2026)

| Field | Detail |
|-------|--------|
| **arXiv** | 2601.06048 (Jan 2026, "Tackling the Inherent Difficulty of Noise Filtering in RAG") |
| **Venue** | arXiv Jan 2026 |
| **Technique** | Argues noise filtering in RAG is fundamentally hard; limited transformer layers cannot effectively solve it — requires LLM to be intrinsically robust to noise rather than relying purely on filtering. Proposes training the generator to be noise-robust as a first-class objective. |
| **Hermes Relevance** | Validates RetRobust/fine-tuning approach over pure NLI filtering. Confirms the NLI filter (RetRobust Method 1) has recall cost — both methods should be used. |

### RAG as Noisy ICL (2025)

| Field | Detail |
|-------|--------|
| **arXiv** | 2506.03100 (June 2025) |
| **Venue** | arXiv |
| **Technique** | Frames retrieved texts as query-dependent noisy in-context examples; recovers classical ICL and standard RAG as limit cases. Shows an intrinsic ceiling on generalization error exists in RAG that ICL doesn't have. Theoretical framing with practical implications for robustness ceiling. |
| **Hermes Relevance** | Theoretical basis for why RAG robustness has an irreducible floor; informs when to switch from RAG to parametric knowledge (intrinsic ceiling argument). |

---

## 2. Multilingual RAG — New Papers

### mRAG Context Consistency (EMNLP 2025 Best Paper)

| Field | Detail |
|-------|--------|
| **Paper** | *On the Consistency of Multilingual Context Utilization in Retrieval-Augmented Generation* |
| **arXiv** | 2504.00597 (Apr 2025, v4 Nov 2025) |
| **Venue** | MRL Workshop @ EMNLP 2025 — **Best Paper Award** |
| **Institution** | University of Groningen (Jirui Qi, Raquel Fernández, Arianna Bisazza) |
| **GitHub** | github.com/Betswish/mRAG-Context-Consistency |
| **Technique** | Extensive assessment of LLMs' ability across 4 LLMs × 3 QA datasets × 48 languages: (i) consistent use of relevant passage regardless of its language, (ii) respond in expected language, (iii) focus on relevant passage when multiple distracting passages in different languages present. Uses accuracy + feature attribution techniques. |
| **Key Findings** | Surprising: LLMs CAN extract info from passages in different language than query. Weak: LLMs struggle to formulate full answer in correct language. Distracting passages harm quality regardless of language; BUT distractors in the QUERY language exert slightly stronger negative influence. |
| **Hermes Action** | For multilingual Hindsight retrieval: if distractor is in English (same as query), be MORE careful about filtering. mRAG pipeline design: retrieve in target language, then distractor-filter by query-language match. |

### Retrieval or Representation? (ICLR 2026 Workshop)

| Field | Detail |
|-------|--------|
| **Paper** | *Retrieval or Representation? Reassessing Benchmark Gaps in Multilingual and Visually Rich RAG* |
| **arXiv** | 2603.04238 (Mar 2026) |
| **Venue** | ICLR 2026 Workshop "I Can't Believe It's Not Better" |
| **Institution** | Asenov, Benkirane, Goldwater, Ghodsi |
| **Technique** | Systematically varies transcription and preprocessing methods while holding retrieval mechanism fixed. Shows BM25 can recover large gaps on multilingual and visual benchmarks when document REPRESENTATION (transcription/preprocessing) is improved. Claims better document representation is the primary driver of benchmark improvements, not retrieval sophistication. |
| **Key Finding** | For multilingual RAG: improve the representation/preprocessing of documents BEFORE improving the retrieval mechanism. BM25 + good preprocessing beats dense retrieval + poor preprocessing. |
| **Hermes Action** | For Religion corpus and Hindsight: preprocessing and chunk metadata are the primary levers — not switching embedding models. Text normalization, language detection, script normalization matter more than retrieval algorithm changes. |

### Language Preference in Multilingual RAG (2025)

| Field | Detail |
|-------|--------|
| **arXiv** | 2502.11175 (Feb 2025) |
| **Venue** | arXiv |
| **Technique** | Systematic investigation of language preferences in retrieval AND generation of mRAG. Retrievers tend to prefer high-resource and query languages, but this preference does NOT consistently improve generation performance. |
| **Key Finding** | Retriever language bias != generation quality. Retrieving in a non-query language can improve generation if the passage is more informative despite language mismatch. |
| **Hermes Action** | Confirms: for Religion corpus multilingual retrieval, the native-language collection should be queried independently — retriever preference for English will suppress native-language results. |

### M4-RAG — Multilingual Multimodal (CVPR 2026)

| Field | Detail |
|-------|--------|
| **Paper** | *M4-RAG: A Massive-Scale Multilingual Multi-Cultural Multimodal RAG* |
| **Venue** | CVPR 2026 |
| **Institution** | Anugraha et al. (multi-institution) |
| **Technique** | Comprehensive evaluation framework for multilingual, multicultural, and multimodal RAG. Spans multiple languages + modalities (text-text, text-image). Covers cultural sensitivity dimension absent from most RAG benchmarks. |
| **Hermes Relevance** | Evaluation framework reference for any cross-lingual corpus work (Religion corpus, future multilingual sweep). Cultural sensitivity = important for mythology corpus where ethnocentric frames distort retrieval. |

---

## 3. Agent Memory Architecture — New Survey Papers

### Memory for Autonomous LLM Agents (2026 Survey)

| Field | Detail |
|-------|--------|
| **Paper** | *Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers* |
| **arXiv** | 2603.07670 (Mar 2026) |
| **Venue** | arXiv (single author survey, Pengfei Du) |
| **Technique** | Structured survey from 2022 to early 2026. Formalizes memory as a **write-manage-read loop** coupled with perception and action. Three-dimensional taxonomy: (1) temporal scope, (2) representational substrate, (3) control policy. Five mechanism families: context-resident compression, retrieval-augmented stores, reflective self-improvement, hierarchical virtual context, policy-learned management. Covers four benchmarks exposing "stubborn gaps" in current systems. |
| **Key Taxonomy** | The 3-axis taxonomy (temporal × representational × control) is the most compact formalization available. Maps directly to Hermes: sessions (temporal-short), skills (representational-procedural), Hindsight (retrieval-augmented), GraphRAG/Graphiti (hierarchical+graph), memory (policy-managed). |
| **Hermes Action** | Use this taxonomy to audit the Hermes memory surface coverage. Current gaps: policy-learned management (no RL-based write-path control); continual consolidation (no periodic contradiction resolution). |

### Externalization in LLM Agents (2026 Survey)

| Field | Detail |
|-------|--------|
| **Paper** | *Externalization in LLM Agents: A Unified Review of Memory, Skills, Protocols and Harness Engineering* |
| **arXiv** | 2604.08224 (Apr 2026, 54 pages) |
| **Institution** | SJTU + multi-institution (Zhou, Chai, Chen, Guo, Shan, Song, Xu, Yang, Yu, Weinan Zhang et al.) |
| **Technique** | Frames agent infrastructure through "cognitive artifacts" lens. Memory externalizes STATE across time; skills externalize PROCEDURAL EXPERTISE; protocols externalize INTERACTION STRUCTURE; harness = unification layer. Historical progression: weights → context → harness. Analyzes memory+skills+protocols as three coupled externalization forms. Predicts self-evolving harnesses and shared agent infrastructure as next wave. |
| **Key Insight for Hermes** | Hermes skills ARE the procedural externalization layer. Hermes memory (Hindsight+graphiti) IS the state externalization. The "harness" = Hermes session runtime + tool router. This paper's framework VALIDATES the Hermes architecture pattern and names it in the academic literature. |
| **Hermes Action** | (1) Skills should be treated as persistent procedural memory subject to the same freshness/consolidation hygiene as episodic memory. (2) The "shared agent infrastructure" thesis = Hermes as the context layer shared across agents. Cite this paper in harness-first-agent-design skill as theoretical backing. |

---

## 4. Ontology-Enhanced GraphRAG

### MemGraphRAG (KDD 2026)

| Field | Detail |
|-------|--------|
| **Paper** | *MemGraphRAG: Memory-based Multi-Agent System for Graph Retrieval-Augmented Generation* |
| **arXiv** | 2606.00610 (2026) |
| **Venue** | KDD 2026 |
| **Institution** | Xiamen University (XMUDeepLIT) — Wu, Xiang, Tang, Chen, Zhang, Su |
| **GitHub** | github.com/XMUDeepLIT/MemGraphRAG — 122 stars, 23 forks (MIT, July 2026) |
| **Technique** | Three-layer memory architecture: (1) Schema layer — abstract ontology triples (head_type, relation, tail_type); (2) Fact layer — concrete relation triples extracted from corpus; (3) Passage layer — original text chunks supporting facts. Bidirectional links among all three layers. Ontology induction: abstracts facts into reusable schemas, filters low-frequency patterns. Conflict-aware construction: detects hard conflicts with passage evidence, resolves conflict groups. Graph-enhanced retrieval: embedding similarity + Personalized PageRank. |
| **Quantified Benefit** | Evaluated on GraphRAG-Bench (ICLR 2026). Improves multi-hop reasoning over GraphRAG baseline via conflict resolution + ontology filtering. Specific metrics in paper (see arXiv:2606.00610). |
| **Hermes Feasibility** | **Medium** — Python 3.10+, OpenAI-compatible endpoint, local HuggingFace embedding model. Requires LLM-based OpenIE at index time (expensive). Chunk-size 256, overlap 32. |
| **Hermes Action for Religion Corpus** | The Schema-Fact-Passage 3-layer pattern is EXACTLY the Comparative Religion DB architecture (myth_ontology.ttl + myth_knowledge_graph.ttl + sacred_texts chunks). MemGraphRAG provides: (a) conflict detection that can find contradictions between traditions; (b) ontology induction that auto-abstracts motifs from facts. The conflict-aware construction directly addresses the Religion corpus challenge of contradictory cosmogonies across traditions. |
| **Action** | Port MemGraphRAG's ontology induction + conflict-detection approach into ~/Religion/scripts/ as an addition to the existing knowledge graph pipeline. |

### ZEP — Temporal Knowledge Graph for Agent Memory (2025)

| Field | Detail |
|-------|--------|
| **arXiv** | 2501.13956 (Jan 2025) |
| **Venue** | arXiv |
| **Institution** | Zep AI |
| **Technique** | Temporal knowledge graph architecture for agent memory. Temporal edges: tracks WHEN facts were valid, allowing time-aware queries. Used by Graphiti (which powers Hermes memory layer). Enables LLM agents to develop more sophisticated memory structures aligned with human memory systems. |
| **Hermes Relevance** | Confirms Graphiti's temporal KG approach is academically grounded. Zep is the upstream project Graphiti derives from. |

---

## 5. Cross-Language Non-English Sweep — RAG/Memory Topics (July 2026)

### Russian track (CyberLeninka)
- Searched: `расширенная поисковая генерация надёжность`, `мультиязычный RAG`, `память агента онтология`
- Found: Russian LLM adoption articles (IDE integration — GitHubCopilot, IntelliCode, Alice Code Assistant) and general AI-in-academia survey (2021–2025). No independent Russian academic research on RAG robustness or multilingual RAG beyond derivative commentary on English-language sources.
- Verdict: **GAP** — topic too fast-moving for Russian academic cycle; Russian NLP community is consuming English RAG/memory research, not producing independent findings on robustness. Not an access barrier — CyberLeninka was open and returned results.

### French track (TALN 2026)
- Known from prior sweep: Sem-G-RAG (#30, TALN 2026) adds FrameNet semantic frames to RAG; and parametric vs contextual memory conflict paper (EvalLLM@TALN 2026 with Qwen3.5) quantifies RAG context-override unreliability. No new FR papers on retrieval robustness specifically — the Qwen3.5 conflict paper is the closest.
- Verdict: **COVERED** by prior sweep (multilingual-agent-efficiency-sweep-jun-jul-2026.md). Delta: the Qwen3.5 parametric-vs-contextual paper directly maps to the RetRobust problem space.

### Korean track (discuss.pytorch.kr)
- The June–July 2026 PyTorchKR digest (already in prior sweep baseline) surfaced PreAct, Latent Agents — both address context efficiency, not RAG noise robustness specifically. No KR-specific RAG robustness research found.
- Verdict: **GAP** (expected — KR community curates EN research, doesn't produce independent RAG robustness findings).

### Japanese track (IPSJ/Zenn/Qiita)
- No Japanese-language academic work on RAG robustness or multilingual RAG surfaced. Confirmed independent of access barrier — practitioner commentary (Zenn/Qiita) discusses English papers.
- Verdict: **GAP** (consistent with prior sweeps — JP academic RAG work is mostly in English at NLP venues).

### Cross-Language Convergence (mRAG)
- EN: retrieval robustness = active research area with RARE benchmark + CQC-RAG + mRAG consistency work
- FR: parametric vs contextual conflict quantification (TALN 2026)
- RU/JP/KR: consumers of EN research, not producers — no independent mRAG findings
- Convergence signal: **WEAK** on non-English tracks. This confirms the skill pitfall note: non-English RAG research is commentary, not independent. All quantified results originate from EN-language venues.

---

## 6. Implementation Priority Ranking (Hermes-Specific)

| Priority | Paper | Action | Feasibility |
|---|---|---|---|
| P1 | CQC-RAG (2606.13438) | Add cross-query consistency to Graphiti/Hindsight recall: rewrite query 3 ways → retrieve → vote | HIGH — prompt only |
| P2 | RetRobust NLI filter (2310.01558) | Add NLI pre-filter gate before LLM generation in RAG pipelines: pass only entailed passages | MEDIUM — pip DeBERTa |
| P3 | mRAG Context Consistency (2504.00597) | Apply query-language distractor insight: when multiple passages retrieved, passages in SAME language as query act as slightly stronger distractors — filter first | HIGH — re-ranking logic |
| P4 | MemGraphRAG 3-layer pattern (2606.00610) | Port Schema-Fact-Passage + conflict detection to Religion corpus pipeline | MEDIUM — needs LLM OpenIE |
| P5 | Representation > Retrieval (2603.04238) | Before improving Hindsight embedding model, improve text preprocessing/normalization — this is the primary lever | LOW effort, HIGH leverage |
| P6 | Memory write-manage-read taxonomy (2603.07670) | Use 3-axis taxonomy to audit Hermes memory surface gaps; document them explicitly | ZERO effort — framework only |
| P7 | Externalization paper (2604.08224) | Cite in harness-first-agent-design skill; use "cognitive artifacts" framing to explain Hermes skills + memory | LOW effort |

---

## Quick Reference Table

| arXiv / ID | Title | Year | Venue | Key Finding |
|---|---|---|---|---|
| 2310.01558 | RetRobust (ret-robust) | 2023/2024 | arXiv/EMNLP | NLI filter + 1K fine-tune makes RAG robust to irrelevant context |
| 2606.13438 | CQC-RAG | 2026 | arXiv | Cross-query consistency +4.76pp TriviaQA, +9.12pp MuSiQue |
| 2506.00789 | RARE benchmark | 2025 | arXiv | KG-driven 48K-question robustness benchmark; multi-hop worst case |
| 2601.06048 | Noise filtering inherently difficult | 2026 | arXiv | Filtering can't fully solve noise — LLM must be intrinsically robust |
| 2506.03100 | RAG as noisy ICL | 2025 | arXiv | Intrinsic generalization ceiling in RAG vs ICL |
| 2504.00597 | mRAG Context Consistency | 2025 | MRL@EMNLP 2025 Best Paper | 48 langs: LLMs extract cross-lingual info well; query-lang distractors strongest |
| 2603.04238 | Retrieval or Representation | 2026 | ICLR 2026 Workshop | Representation/preprocessing > retrieval mechanism for multilingual gaps |
| 2502.11175 | Language Preference in mRAG | 2025 | arXiv | Retriever language bias ≠ generation quality; query-lang preference misleading |
| M4-RAG CVPR 2026 | Multilingual multimodal RAG | 2026 | CVPR 2026 | Multicultural + multimodal evaluation framework for mRAG |
| 2603.07670 | Memory for LLM Agents survey | 2026 | arXiv | Write-manage-read taxonomy; 3-axis framework (temporal × substrate × control) |
| 2604.08224 | Externalization in LLM Agents | 2026 | arXiv (54pp) | Memory=state, Skills=procedure, Protocols=interaction, Harness=coordination |
| 2606.00610 | MemGraphRAG | 2026 | KDD 2026 | 3-layer Schema-Fact-Passage memory; ontology induction; conflict detection |
| 2501.13956 | ZEP temporal KG | 2025 | arXiv | Temporal KG for agent memory (upstream of Graphiti) |

---

## Notes on Non-English Coverage
- Russian (CyberLeninka): GAP confirmed. Non-English RAG robustness research absent — topic is too fast-moving. Russian community reads EN papers.
- French (TALN 2026): COVERED from prior sweep. Sem-G-RAG + Qwen3.5 conflict paper.
- Korean (PyTorchKR): GAP on RAG robustness specifically; broader memory/efficiency covered in prior sweep.
- Japanese (IPSJ/Zenn): GAP. No Japanese-venue RAG robustness work.
- Cross-language convergence: WEAK. EN monopolizes original RAG robustness research. This is a topic-maturity-vs-academic-cycle gap, not an access barrier.
