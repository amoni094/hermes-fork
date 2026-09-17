# Multilingual Research Sweep: 6 Hermes Agent Skill Topics — 2025–2026
**Sweep date:** July 2026  
**Scope:** arXiv 2025–2026 + non-English GitHub repos across ZH/JA/KO/RU/DE/FR  
**Topics:** (1) CRAAP/source credibility scoring, (2) Vision PDF parsing/DeepDoc pattern,  
(3) Domain-specific chunking, (4) Cognee ontology induction, (5) PreCompact KG sync,  
(6) model: frontmatter routing field  

---

## TOPIC 1 — CRAAP Criteria / Source Credibility Scoring for Web Crawl Pipelines

### Primary papers (verified)

#### SemCAFE — Entity-level Web Source Reliability (2025)
| Field | Detail |
|-------|--------|
| **Paper** | *SemCAFE: When Named Entities make the Difference — Assessing Web Source Reliability through Entity-level Analytics* |
| **arXiv** | 2504.08776 (Apr 2025, v2 Sep 2025) |
| **Venue** | arXiv cs.CL |
| **Institution** | Gautam Kishore Shahi (Uni Duisburg-Essen 🇩🇪), Oshani Seneviratne (RPI), Marc Spaniol (Université de Caen 🇫🇷) |
| **Technique** | NLP-based semantic fingerprinting using YAGO knowledge base entity-relatedness; distinguishes credible/unreliable by comparing entity graphs of articles against YAGO. Validated on 46,020 credible + 3,407 unreliable articles about the 2022 Russia-Ukraine war. |
| **Quantified Benefit** | +12% macro F1 over SOTA methods for war-related disinformation detection |
| **Hermes Feasibility** | **High** — entity-level fingerprinting with YAGO is pipeable into a Firecrawl post-processing step |
| **Non-English note** | 🇩🇪 German institution (Uni Duisburg-Essen); 🇫🇷 French institution (Université de Caen Normandie) as co-authors — one of the clearest cross-European credibility scoring contributions |
| **Code** | GitHub code available (see paper) |

#### CrediBench — Web-Scale Network Dataset for Credibility (KDD 2026)
| Field | Detail |
|-------|--------|
| **Paper** | *CrediBench: Building Web-Scale Network Datasets for Information Integrity* |
| **arXiv** | 2509.23340 (Sep 2025, v4 Jun 2026) |
| **Venue** | KDD 2026 |
| **Institution** | McGill University / Mila (Jean-François Godbout 🇨🇦, Reihaneh Rabbany), Oxford (Michael Bronstein), multi-institutional |
| **Technique** | Multi-modal credibility prediction over a temporal web graph: 8 months of Common Crawl snapshots, 40M+ nodes per month, 1B+ hyperlink edges. Combines graph topology, text content, and temporal evolution. Supports both regression (continuous score) and binary classification. Labels: 662,575 domains across misinformation/malware/phishing/crowd-sourced categories. |
| **Quantified Benefit** | Multi-modal classifier: accuracy 56% → 85%; regression MAE 0.162 → 0.107 |
| **Hermes Relevance** | Direct analog to CRAAP pipeline: domain-level credibility via graph + text + temporal signals, not just per-article text analysis |
| **Non-English note** | JF Godbout (Univ. Montréal 🇨🇦/🇫🇷) brings French-Canadian political communication research perspective |
| **Dataset** | HuggingFace: available |

#### Document Quality Scoring for Web Crawling (WOWS 2025)
| Field | Detail |
|-------|--------|
| **Paper** | *Document Quality Scoring for Web Crawling* |
| **arXiv** | 2504.11011 (Apr 2025) |
| **Venue** | WOWS 2025 (Workshop on Web-scale Open-domain Search @ SIGIR) |
| **Institution** | Francesca Pezzuti + Nicola Tonellotto (Università di Pisa 🇮🇹), Sean MacAvaney (Univ. Glasgow 🇬🇧) |
| **Technique** | Neural semantic quality estimators from Chang et al. (2024) applied to crawl prioritization; Docker container for quality scoring deployable in web search crawl pipelines. Prioritizing semantically high-quality pages improves downstream search effectiveness. |
| **Quantified Benefit** | Improved downstream search effectiveness; Docker container for plug-in integration |
| **Non-English note** | 🇮🇹 Italian institution (Uni Pisa) — European IR research cluster |
| **GitHub** | github.com/fpezzuti/quality_crawling |

#### Credibility Assessment Survey (ACM TIST 2025) — Multi-European
| Field | Detail |
|-------|--------|
| **Paper** | *A Survey on Automatic Credibility Assessment Using Textual Credibility Signals in the Era of LLMs* |
| **arXiv** | 2410.21360 (Oct 2024, v2 Oct 2025) |
| **Venue** | ACM Transactions on Intelligent Systems and Technology, 2025 |
| **Institution** | Ivan Srba + Maria Bielikova (Slovak University of Technology 🇸🇰), Denis Teyssou + Valentin Porcellini (AFP 🇫🇷), Sara Tonelli (FBK 🇮🇹), Ipek Baris Schlicht (Univ. Stuttgart 🇩🇪), Kalina Bontcheva (Univ. Sheffield 🇬🇧) |
| **Technique** | Systematic review of 175 papers on automatic credibility assessment (factuality, subjectivity/bias, persuasion techniques, logical fallacies, fact-checking). Signal taxonomy: 9 categories. Reviews LLM-based approaches for credibility aggregation. |
| **Key finding** | Current research highly fragmented — no system integrates multi-signal credibility simultaneously. Gap directly addressable by CRAAP-style orchestration. |
| **Non-English note** | 🇸🇰 Slovak, 🇫🇷 French (AFP), 🇩🇪 German (Stuttgart), 🇮🇹 Italian institutions as primary contributors — strongest multi-European non-English coverage in this sweep |

#### Web Search Credibility Assessment for Chat Assistants (2025)
| Field | Detail |
|-------|--------|
| **arXiv** | 2510.13749 (Oct 2025, updated Feb 2026) |
| **Venue** | arXiv cs.IR |
| **Technique** | Evaluates source credibility and groundedness of web-search-enabled LLM assistants. Novel methodology for auditing which sources get cited, how grounded answers are. |
| **Hermes Relevance** | Direct match to Firecrawl post-processing: score credibility of retrieved sources before incorporating them |

### Non-English landscape for CRAAP/Credibility

**Russian (CyberLeninka):** Found multiple Russian-language articles on "достоверность информации" (information credibility) targeting *educators and students*, not automated pipelines. These are pedagogical frameworks (VVIT, Lipetsk State Technical University), not engineering-grade credibility scoring systems. **Verdict: GAP** — Russian academic work on automated web credibility scoring is absent from open-access venues. CyberLeninka coverage on this topic is pedagogical, not ML/NLP.

**German (arXiv/DFKI):** German researchers publish primarily in English (Uni Stuttgart/Schlich, Uni Duisburg-Essen/Shahi in SemCAFE above). No German-language native-venue papers on automated credibility pipelines. **Verdict: German contribution is via English-language arXiv papers from German institutions, not native-language venues.**

**French (TALN/HAL):** AFP (French news agency) contributed to the ACM TIST survey above — practitioner-led, not TALN-academic. Searched TALN 2025/2026 archives: no French-language papers on source credibility pipelines. **Verdict: French contribution is via AFP practitioner knowledge in multi-institution surveys.**

**Chinese (arXiv):** Chinese NLP community focuses on factuality evaluation and hallucination detection in LLMs rather than source credibility pipelines for web crawlers. No Chinese-specific CRAAP-equivalent pipeline found. **Verdict: GAP** — Chinese researchers approach this as LLM factuality evaluation, not source credibility at the crawl level.

**Japanese/Korean:** No relevant IPSJ or KIISE papers on automated web source credibility scoring. **Verdict: GAP** — both communities focus on Japanese/Korean language fake news detection, not web crawl pipeline integration.

---

## TOPIC 2 — Vision-Based PDF Parsing: Layout Detection + Table Structure Recognition

This is the most active non-English research domain — dominated by Chinese institutions.

### Primary Chinese-institution papers (verified)

#### MinerU2.5 — Chinese OpenDataLab / Shanghai AI Lab (Sep 2025)
| Field | Detail |
|-------|--------|
| **Paper** | *MinerU2.5: A Decoupled Vision-Language Model for Efficient High-Resolution Document Parsing* |
| **arXiv** | 2509.22186 (Sep 2025) |
| **Venue** | Technical Report |
| **Institution** | OpenDataLab / Shanghai AI Lab 🇨🇳 (Junbo Niu, Bin Wang, Conghui He, Dahua Lin, Bo Zhang, 60+ authors from CASIA, USTC, SIMS) |
| **GitHub** | github.com/opendatalab/MinerU (18K+ stars) |
| **Technique** | Coarse-to-fine two-stage parsing: (1) global layout on downsampled images → (2) targeted content recognition on native-resolution crops. 1.2B-parameter VLM. Decoupled layout/content stages avoid high-res processing overhead. Comprehensive data engine for diverse training corpora. |
| **Quantified Benefit** | OmniDocBench: 90.67 (SOTA); Ocean-OCR: F1 0.945; surpasses Gemini 2.5 Pro on parsing benchmarks at 1.2B params |
| **Hermes Feasibility** | **High** — open source, pip-installable, MIT license, runs on consumer GPU |
| **Non-English note** | 🇨🇳 Flagship Chinese institution PDF parsing project; most widely deployed Chinese-origin document parser |

#### PaddleOCR-VL — Baidu / PaddlePaddle (Oct 2025)
| Field | Detail |
|-------|--------|
| **Paper** | *PaddleOCR-VL: Boosting Multilingual Document Parsing via a 0.9B Ultra-Compact Vision-Language Model* |
| **arXiv** | 2510.14528 (Oct 2025, v4 Nov 2025) |
| **Venue** | Technical Report |
| **Institution** | Baidu / PaddlePaddle 🇨🇳 (Cheng Cui, Ting Sun, Dianhai Yu, Yanjun Ma, 18 authors) |
| **GitHub** | github.com/PaddlePaddle/PaddleOCR |
| **Technique** | NaViT-style dynamic resolution visual encoder + ERNIE-4.5-0.3B language model. 0.9B total. 109 languages supported. Handles text, tables, formulas, charts. Benchmarked against OmniDocBench. |
| **Quantified Benefit** | SOTA on OmniDocBench; "significantly outperforms existing solutions" and "strong competitiveness against top-tier VLMs" at 0.9B params |
| **Hermes Relevance** | Drop-in replacement for DeepDoc's vision module; smallest SOTA VLM for document parsing |

#### OmniDocBench — OpenDataLab / Shanghai AI Lab (CVPR 2025)
| Field | Detail |
|-------|--------|
| **Paper** | *OmniDocBench: Benchmarking Diverse PDF Document Parsing with Comprehensive Annotations* |
| **arXiv** | 2412.07626 (Dec 2024, CVPR 2025) |
| **Venue** | CVPR 2025 |
| **Institution** | OpenDataLab / Shanghai AI Lab 🇨🇳 (Linke Ouyang, Yuan Qu, Bin Wang, Zhiyuan Zhao et al.) |
| **GitHub** | github.com/opendatalab/OmniDocBench |
| **Technique** | Benchmark covering 9 document types (academic papers, textbooks, handwritten notes, newspapers), dense annotations for text/table/formula/reading-order. Evaluates both modular pipelines AND multimodal end-to-end VLMs. Standard benchmark for all major document parsing models. |
| **Non-English note** | This is the canonical Chinese-institution benchmark that now defines the evaluation standard globally |

#### Dolphin — ByteDance Document Image Parsing (ACL 2025)
| Field | Detail |
|-------|--------|
| **Paper** | *Dolphin: Document Image Parsing via Heterogeneous Anchor Prompting* |
| **arXiv** | 2505.14059 (May 2025) |
| **Venue** | ACL 2025 |
| **Institution** | ByteDance 🇨🇳 (Hao Feng, Can Huang, 13 authors) |
| **GitHub** | github.com/ByteDance/Dolphin |
| **Technique** | Analyze-then-parse paradigm: Stage 1 generates layout elements in reading order; Stage 2 feeds them as "heterogeneous anchors" with task-specific prompts for parallel content parsing. 30M+ training samples, multi-granularity. Lightweight architecture with parallel parsing = superior efficiency. |
| **Quantified Benefit** | SOTA across diverse page-level and element-level settings; "superior efficiency" through lightweight architecture + parallel parsing |
| **Non-English note** | 🇨🇳 ByteDance (TikTok parent), published at ACL 2025 — strongest ByteDance contribution to document parsing |

#### MinerU Pro-5 — OpenDataLab (2026)
| Field | Detail |
|-------|--------|
| **arXiv** | 2604.04771 (Apr 2026) |
| **Institution** | OpenDataLab 🇨🇳 |
| **Technique** | "Pushing the Limits of Data-Centric Document Parsing at Scale" — next iteration of MinerU series |

#### MinerU-Diffusion (2026) — novel approach
| Field | Detail |
|-------|--------|
| **arXiv** | 2603.22458 (Mar 2026) |
| **Institution** | OpenDataLab 🇨🇳 |
| **Technique** | Rethinks document OCR as *inverse rendering via diffusion decoding* — novel paradigm distinct from detection-then-recognition |

### Non-English GitHub repos for Topic 2
- **github.com/opendatalab/MinerU** 🇨🇳 — 18K+ stars, Python, most deployed Chinese PDF parser
- **github.com/PaddlePaddle/PaddleOCR** 🇨🇳 — 41K+ stars, Baidu's multilingual OCR + layout pipeline
- **github.com/ByteDance/Dolphin** 🇨🇳 — ACL 2025, parallel parsing
- **github.com/infiniflow/ragflow** 🇨🇳 — Contains DeepDoc; 30K+ stars
- **github.com/opendatalab/OmniDocBench** 🇨🇳 — CVPR 2025 benchmark

**Non-Chinese landscape:** Russian, Japanese, Korean, German, French institutions are almost entirely absent from PDF layout/TSR research. This is Chinese-dominated. Searching IPSJ, IEICE (Japan), KIISE (Korea), and CyberLeninka found no independent native-language vision-based PDF parsing work. The global community uses Chinese-published benchmarks (OmniDocBench) as the standard.

**Cross-language convergence:** VERY STRONG (Chinese monopoly) — 5 of 5 top-cited 2025-2026 vision PDF parsing papers are from Chinese institutions. Western and Japanese/Korean communities benchmark *against* Chinese-built systems.

---

## TOPIC 3 — Domain-Specific Chunking Templates

### Primary papers (verified)

#### Systematic Investigation of Document Chunking — 36 Methods (2026)
| Field | Detail |
|-------|--------|
| **Paper** | *A Systematic Investigation of Document Chunking Strategies and Embedding Sensitivity* |
| **arXiv** | 2603.06976 (Mar 2026) |
| **Venue** | arXiv cs.CL |
| **Institution** | Muhammad Arslan Shaukat, Muntasir Adnan, Carlos C. N. Kuhn — University of Technology Sydney 🇦🇺 / multi-institution |
| **Technique** | First large-scale cross-domain evaluation: 36 segmentation methods × 6 knowledge domains × 5 embedding models = 1,080 configurations. Methods: fixed-size, semantic, structure-aware, hierarchical, adaptive, LLM-assisted. Metric: nDCG@5 (graded relevance). |
| **Key Findings** | • **Top performer overall**: Paragraph Group Chunking (mean nDCG@5 = 0.459, Precision@1 = 24%, Hit@5 = 59%) vs. fixed-size char chunking baseline (nDCG@5 < 0.244, Precision@1 = 2-3%) — **10× improvement** in top-1 precision. • **Domain-specific**: Dynamic token sizing is strongest in biology/physics/health; paragraph grouping is strongest in **legal and math**. • Larger embedding models + better chunking are complementary (not substitutable). |
| **Hermes Feasibility** | **Very High** — benchmark tells exactly which chunking method to use per domain |
| **Non-English note** | UTS is an Australian institution; no Chinese/Japanese/Korean/Russian/French institutions among authors |

#### Beyond Chunk-Then-Embed — Taxonomy and Evaluation (2026)
| Field | Detail |
|-------|--------|
| **arXiv** | 2602.16974 (Feb 2026) |
| **Venue** | arXiv cs.CL |
| **Technique** | Comprehensive taxonomy: structure-based, semantic, contextualized. Structure-based methods outperform LLM-guided alternatives for *in-corpus* retrieval; LumberChunker performs best for *in-document* retrieval. Task-dependent recommendation: match chunking strategy to retrieval type. |

#### Reliable Retrieval in RAG for Legal Datasets (2025)
| Field | Detail |
|-------|--------|
| **arXiv** | 2510.06999 (Oct 2025) |
| **Venue** | arXiv |
| **Technique** | Chunk enhancement with document-level synthetic summary — injects global context into chunks. Tested specifically on large legal document corpora. |
| **Hermes Relevance** | Direct template for legal-domain chunking: each chunk gets a summary header with document-level context. Addresses the "context loss during standard chunking" problem. |

### Domain-specific chunking findings

**Legal domain:** Paragraph Group Chunking (2603.06976) > dynamic token sizing for legal. Add document-level summary injection (2510.06999). Legal structure (sections, clauses, definitions) maps naturally to paragraph groups.

**Academic paper domain:** Structure-aware chunking (section/subsection boundaries) consistently outperforms semantic similarity for academic papers. Dynamic token sizing works well for biology/physics abstracts.

**Financial domain:** No dedicated financial-domain chunking paper found in 2025-2026. METIS (arXiv:2412.10543) addresses RAG configuration adaptation including chunk count, but is query-adaptive rather than template-based.

**Code domain:** No 2025-2026 papers specifically on code-aware chunking for RAG pipelines. AST-based chunking is mentioned as best practice in tooling docs but lacks academic validation in this sweep window.

### Non-English landscape for Topic 3

**Chinese:** Searched `文档切分` (document chunking), `语义切块` (semantic chunking), `法律文本RAG切分` — found practitioner articles on CSDN/Zhihu translating/applying English chunking strategies. No independent Chinese academic chunking research found on arXiv. **Verdict: DERIVATIVE** — Chinese community applies English methods, doesn't produce independent chunking research.

**Japanese (IPSJ/Zenn/Qiita):** Qiita/Zenn posts discuss English chunking papers. No IPSJ academic papers on domain-specific chunking found. **Verdict: DERIVATIVE**.

**Korean (KIISE/RISS):** No Korean-language academic papers on domain-specific chunking. **Verdict: GAP**.

**Russian (CyberLeninka):** No Russian papers on automated document chunking strategies. **Verdict: GAP**.

**German/French:** German and French researchers work on legal NLP (German legal NLP at TU Darmstadt; French legal AI at Inria) but in the context of NER/classification, not chunking strategies for RAG. No German/French chunking papers found. **Verdict: GAP**.

**Cross-language convergence:** ABSENT. Chunking strategy research is English-dominated (US/UK/AU institutions). Non-English communities are derivative consumers.

---

## TOPIC 4 — Cognee cognify() Automated Ontology Induction Pipeline

### Primary papers (verified)

#### AutoSchemaKG — HKUST (ACL 2026)
| Field | Detail |
|-------|--------|
| **Paper** | *AutoSchemaKG: Autonomous Knowledge Graph Construction through Dynamic Schema Induction from Web-Scale Corpora* |
| **arXiv** | 2505.23628 (May 2025, v3 Aug 2025) |
| **Venue** | ACL 2026 |
| **Institution** | HKUST (Hong Kong University of Science and Technology 🇭🇰🇨🇳) — Jiaxin Bai, Yangqiu Song, + 19 authors; collaboration includes Renhai Chen (Huawei), Gong Zhang (Huawei) |
| **GitHub** | github.com/HKUST-KnowComp/AutoSchemaKG |
| **Technique** | Fully autonomous KG construction without predefined schemas. Simultaneously extracts knowledge triples AND induces schemas directly from text. Models both entities and events. Uses conceptualization to organize instances into semantic categories. Processed 50M+ documents → ATLAS family KGs: 900M+ nodes, 5.9B edges. |
| **Quantified Benefit** | 92% semantic alignment with human-crafted schemas with **zero manual intervention**; outperforms SOTA on multi-hop QA; enhances LLM factuality |
| **Hermes Feasibility** | **Medium** — requires large-scale LLM calls for schema induction; works with OpenAI-compatible endpoint |
| **Non-English note** | 🇭🇰 HKUST — Hong Kong institution, Chinese-majority research team; directly relevant to Cognee cognify() pattern |

#### LLM-Driven Ontology Construction for Enterprise KGs — OntoEKG (ICSC 2026)
| Field | Detail |
|-------|--------|
| **Paper** | *LLM-Driven Ontology Construction for Enterprise Knowledge Graphs* (OntoEKG) |
| **arXiv** | 2602.01276 (Feb 2026) |
| **Venue** | ICSC 2026 (20th International Conference on Semantic Computing) |
| **Institution** | Abdulsobur Oyewale + Tommaso Soru (Leeds Beckett University 🇬🇧) |
| **Technique** | Two-phase pipeline: (1) extraction module identifies core classes and properties; (2) entailment module logically structures them into hierarchy → RDF serialization. Benchmarks on Data, Finance, and Logistics sector documents. |
| **Quantified Benefit** | Fuzzy-match F1-score 0.724 in Data domain; reveals limitations in scope definition and hierarchical reasoning |
| **Hermes Relevance** | Direct analog to Cognee cognify() OntoEKG gives a 2-phase pipeline: extract → entail → serialize as RDF. The F1 0.724 is a calibration baseline for assessing Cognee pipeline quality. |

#### LLM-Empowered KG Construction Survey (2025)
| Field | Detail |
|-------|--------|
| **Paper** | *LLM-empowered knowledge graph construction: A survey* |
| **arXiv** | 2510.20345 (Oct 2025) |
| **Venue** | arXiv cs.AI |
| **Institution** | Haonan Bian (single author — affiliation not specified in abstract) |
| **Technique** | Comprehensive overview: LLMs reshape KG construction pipeline. Analyzes schema-based (structured, normalized) vs. schema-free (flexible, open discovery) paradigms. Covers ontology engineering, knowledge extraction, knowledge fusion. |
| **Hermes Relevance** | Best available survey on Cognee cognify()-adjacent techniques. Schema-free paradigm = Cognee's approach; schema-based = traditional Graphiti. |

#### Ontology Learning vs. KG Construction for RAG (2025)
| Field | Detail |
|-------|--------|
| **Paper** | *Ontology Learning and Knowledge Graph Construction: A Comparison of Approaches and Their Impact on RAG Performance* |
| **arXiv** | 2511.05991 (Nov 2025) |
| **Venue** | arXiv cs.IR |
| **Institution** | Tiago da Cruz, Bernardo Tavares, Francisco Belo (Portugal 🇵🇹) |
| **Technique** | Compares standard RAG, GraphRAG, and ontology-guided KGs from: (a) relational DB ontologies, (b) text-extracted ontologies. Key finding: DB-derived ontologies = one-time cost, competitive performance. Text ontologies = better coverage but merge complexity. |
| **Quantified Benefit** | Ontology-guided KGs competitive with GraphRAG SOTA; substantially outperform vector retrieval. DB ontologies have dual advantage: one-time learning + no merge complexity. |
| **Non-English note** | 🇵🇹 Portuguese institution |

#### OntoTune — Zhejiang University (WWW 2025)
| Field | Detail |
|-------|--------|
| **Paper** | *OntoTune: Ontology-Driven Self-training for Aligning Large Language Models* |
| **GitHub** | github.com/zjukg/OntoTune |
| **Venue** | WWW 2025 |
| **Institution** | Zhejiang University KG Group 🇨🇳 (zjukg) |
| **Technique** | Ontology-driven self-training framework: aligns LLM responses with ontology via in-context learning; enables ontology-guided generation. Inverse of cognify() — instead of extracting ontology from data, uses ontology to guide LLM. Complementary to cognify() pipeline. |
| **Non-English note** | 🇨🇳 ZJU KG Group is one of the premier Chinese KG labs; see zjukg GitHub org |

#### Ontology Induction from Text — Pipeline 2506.00664
| Field | Detail |
|-------|--------|
| **arXiv** | 2506.00664 (May 2025) |
| **Technique** | Automated pipeline to derive ontologies from unstructured text. Abstract describes "an automated pipeline designed to derive ontologies from unstructured data" — directly matching cognify() pattern. |

### Non-English landscape for Topic 4

**Chinese (strong presence):** HKUST (AutoSchemaKG, ACL 2026), ZJU KG Group (OntoTune, WWW 2025), Renhai Chen/Gong Zhang (Huawei, co-authors on AutoSchemaKG). Chinese researchers are producing leading ontology induction work. The ZJU KG group (github.com/zjukg) maintains multiple ontology/KG repos.

**Japanese:** AIST/NII work on ontology induction (Hozo, OntoEditor) is well-established but pre-2025. No 2025-2026 Japanese-language papers on LLM-driven schema induction found in IPSJ. **Verdict: established community but no recent breakthrough papers in scope.**

**Korean:** KAIST has KG research (KGQA work) but no specific 2025-2026 ontology induction papers from Korean institutions found. **Verdict: GAP in this sweep window.**

**Russian (SPIIRAS, mathnet.ru):** Previous NeSy sweep found Russian ontology-oriented NeSy work (Smirnov/Shilov/Ponomarev, SPC RAS) via mathnet.ru. For schema induction specifically in LLM era: no new papers found. **Verdict: GAP for LLM-driven schema induction; Russian ontology work remains pre-LLM paradigm.**

**German (DFKI):** DFKI Hamburg has ontology engineering work but publishes in English. Sciencedirect article (Accelerating KG and ontology engineering with LLMs, 2025) includes German contributors. **Verdict: German contribution via English venues.**

**Portuguese (notable):** da Cruz et al. 2511.05991 is Portuguese institution — unexpected contributor with directly relevant work.

---

## TOPIC 5 — Cognee PreCompact / Session-End Async KG Sync Before Context Compaction

### Primary papers (verified)

#### Agentic Context Management (ACM) — Jul 2026
| Field | Detail |
|-------|--------|
| **Paper** | *Agentic Context Management: Solving Agent Memory and Cost by Treating Them as Lifecycle and Architecture Problems* |
| **arXiv** | 2607.21503 (Jul 2026) |
| **Venue** | arXiv cs.AI |
| **Institution** | Gaurav Dadhich (independent / Maximem Synap) |
| **Technique** | Defines "Agentic Context Management" (ACM) as 5 primitives: architecting, ingesting, scoping, anticipating, **compacting & consolidation**. Makes economic case: naive context accumulation = quadratic cost; crude summarization = linear cost but accuracy cliff; **validated compaction = linear cost + preserved fidelity**. Compaction must be done against next-turn need prediction, not just history compression. |
| **Quantified Benefit** | Reference impl (Maximem Synap): 92% on LongMemEval, 93.2% on LoCoMo |
| **Hermes Relevance** | Direct theoretical grounding for PreCompact pattern: the "anticipating" primitive = pre-compaction KG sync. "Compacting checked against what the next turn needs is the only path to linear cost with memory intact." |

#### Zep Temporal KG for Agent Memory (2025)
| Field | Detail |
|-------|--------|
| **arXiv** | 2501.13956 (Jan 2025) |
| **Venue** | arXiv cs.AI |
| **Institution** | Zep AI |
| **Technique** | Temporal knowledge graph architecture. Tracks WHEN facts were valid. Deployed as a memory layer service; outperforms MemGPT on DMR benchmark. Upstream of Graphiti. Session-end sync is implicit in the temporal edge creation process. |
| **Hermes Relevance** | Zep/Graphiti is the existing Hermes KG layer. The session-end sync pattern is validated by this paper — temporal KG edges encode session boundaries. |

#### Memory for LLM Agents Survey (2026)
| Field | Detail |
|-------|--------|
| **arXiv** | 2603.07670 (Mar 2026) |
| **Venue** | arXiv |
| **Technique** | Formalizes memory as write-manage-read loop. Five mechanism families include "reflective self-improvement" (= pre-compaction reflection) and "hierarchical virtual context" (= KG as external memory). Three-axis taxonomy. |
| **Hermes Relevance** | Write path = Cognee ingest + KG build; Manage = consolidation/conflict detection; Read = retrieval. PreCompact is a write-path trigger. |

#### LKD-KGC — Rapid Schema Induction (cited in survey 2510.20345)
| Field | Detail |
|-------|--------|
| **Reference** | LKD-KGC (Sun et al., 2025) — cited in arXiv:2510.20345 |
| **Technique** | Lightweight framework for rapid schema induction for open-domain KGs by clustering entity types extracted from document summaries — specifically designed for fast/cheap per-session induction |
| **Hermes Relevance** | Model for PreCompact: run LKD-KGC-style entity clustering at session-end to extract session-specific schema before compaction |

### Non-English landscape for Topic 5

**Overall verdict:** The PreCompact / session-end async KG sync pattern is an **engineering-applied concept** (not yet a studied academic topic). No dedicated academic paper exists in any language for this exact pattern. The closest approximations are:
- ACM paper (2607.21503) — conceptual framework, English
- Zep/Graphiti (2501.13956) — system description, English

**Russian (Habr.com):** Found a Habr.com technical article on async compaction race conditions in Rust/Tokio — engineering-level discussion, not academic. **Verdict: practitioner knowledge, not peer-reviewed.**

**Chinese (CSDN/Zhihu):** Chinese practitioners discuss KG synchronization in RAG systems (e.g., ragflow discussions), but no academic papers on session-boundary KG sync specifically. **Verdict: practitioner derivative.**

**Japanese/Korean/German/French:** No relevant academic work found. **Verdict: GAP across all non-English academic tracks.** This is an engineering-applied concept too new for the academic publication cycle.

---

## TOPIC 6 — `model:` Frontmatter Routing Field in Agent Skill Definitions

### Primary papers (verified)

#### SkillRouter — Skill Routing for LLM Agents (2026)
| Field | Detail |
|-------|--------|
| **Paper** | *SkillRouter: Skill Routing for LLM Agents at Scale* |
| **arXiv** | 2603.22455 (Mar 2026, v5 Jul 2026) |
| **Venue** | arXiv cs.LG |
| **Institution** | YanZhao Zheng, ZhenTao Zhang, Chao Ma, Gang Yu, 11 authors — **Tencent** 🇨🇳 |
| **Technique** | Addresses skill-routing problem at scale (80K+ candidate skills). Key finding: progressive disclosure (hiding skill body, showing only name/description) causes **37–44 pp drop** in routing accuracy. Body-aware routing via 1.2B retrieve-and-rerank model. Achieves 74.0% Hit@1. 13× fewer params, 5.8× faster than strongest baseline. |
| **Quantified Benefit** | 74.0% Hit@1; 37–44 pp accuracy improvement over name-only routing; 5.8× speedup |
| **Hermes Relevance** | **Direct match to `model:` frontmatter**: SkillRouter shows that skill *body content* (not just name/description) must be exposed for accurate routing. The `model:` field is body metadata — should be included in routing signals, not hidden. |
| **Non-English note** | 🇨🇳 Tencent — major Chinese tech company; this is the most directly relevant Chinese paper to Hermes skill routing |

#### RoBatch — Cost-Effective LLM Routing with Batch Prompting (2026)
| Field | Detail |
|-------|--------|
| **Paper** | *Towards Cost-effective LLMs Routing with Batch Prompting* |
| **arXiv** | 2605.28268 (May 2026) |
| **Venue** | arXiv cs.DB |
| **Institution** | Haotian Xu, Kangfei Zhao, Jiadong Xie — **Chinese University of Hong Kong / multi-institution** 🇨🇳 |
| **Technique** | Route with Batching Problem: jointly optimize model assignment (routing) + batch size for each query under total cost budget. NP-hard → solved with 2-stage RoBatch: batch-aware proxy utility model + greedy scheduling along cost-utility Pareto frontier. Tested on Qwen3 and Gemma3 families. |
| **Quantified Benefit** | Consistently achieves superior cost-performance Pareto frontier vs. LLM routing or batch prompting alone; tested on 6 benchmarks, 2 LLM families |
| **Non-English note** | 🇨🇳 Hong Kong institution; uses Qwen3 (Chinese) models as test suite — shows Chinese model family integration |

#### RouteNLP — Closed-Loop LLM Routing (2026)
| Field | Detail |
|-------|--------|
| **arXiv** | 2604.23577 (Apr 2026) |
| **Venue** | arXiv |
| **Technique** | Closed-loop framework routing queries across tiered model portfolio to minimize cost while satisfying per-task quality constraints. Production-validated: one enterprise partner exceeded $200K/month inference costs → 70%+ routine tasks suitable for smaller models. Includes "Legal Risk" benchmark task. |
| **Quantified Benefit** | Production case: $200K/month → 70%+ reducible to small models with quality constraints satisfied |
| **Hermes Relevance** | The `model:` frontmatter field is a static analog to RouteNLP's dynamic routing — both express model preferences per task type. RouteNLP adds closed-loop feedback to make routing adaptive. |

#### OptiRoute — Dynamic LLM Routing and Selection (Feb 2025)
| Field | Detail |
|-------|--------|
| **arXiv** | 2502.16696 (Feb 2025) |
| **Venue** | arXiv |
| **Technique** | kNN-based routing engine matching task embeddings to model capability profiles. Balances performance, cost, and ethics. User-defined requirements as routing signals. |

#### Explainable Model Routing for Agentic Workflows (Apr 2026)
| Field | Detail |
|-------|--------|
| **arXiv** | 2604.03527 (Apr 2026) |
| **Venue** | arXiv cs.AI |
| **Technique** | Explainability layer for LLM routing decisions in agent workflows. Routes complex reasoning to frontier; simple queries to cheaper models. Provides explanations for routing choices. |

#### Route-To-Reason (RTR) — ACL 2026
| Field | Detail |
|-------|--------|
| **Source** | dl.acm.org/doi/10.1145/3774904.3792556 (Apr 2026) |
| **Venue** | ACL 2026 Industry Track |
| **Technique** | Unified routing framework selecting LLMs AND reasoning strategies by query complexity + user budget. First paper to jointly route model + reasoning strategy. |
| **Hermes Relevance** | The `model:` field is a task-level hint; RTR extends this to also selecting reasoning depth. Future `model:` frontmatter could include `reasoning: chain_of_thought | direct`. |

### Non-English landscape for Topic 6

**Chinese (strong):** Tencent (SkillRouter 2603.22455), CUHK/HK (RoBatch 2605.28268) are Chinese institutions producing leading skill routing and cost-optimization routing papers. This is the strongest non-English contribution in this topic.

**Russian:** CyberLeninka searched — no Russian-language papers on LLM routing or skill dispatch. Habr has practitioner articles mentioning routing (in context of comparing models) but no original research. **Verdict: GAP.**

**Japanese:** LLM-jp (llm-jp.github.io) focuses on Japanese LLM training, not routing. No IPSJ papers on model routing found. **Verdict: GAP.**

**Korean:** KIISE/RISS searched — no Korean-language papers on LLM cost-optimized routing. **Verdict: GAP.**

**German/French:** German AI researchers publish model routing work in English (no German-language venue). French researchers similarly at English venues. **Verdict: German/French contribution via English arXiv only.**

---

## Quick Reference Table

| arXiv ID | Title (short) | Year | Venue | Institution | Topic |
|----------|---------------|------|-------|-------------|-------|
| 2504.08776 | SemCAFE | 2025 | arXiv | 🇩🇪 Uni Duisburg-Essen + 🇫🇷 Univ. Caen | 1 |
| 2509.23340 | CrediBench | 2026 | KDD 2026 | 🇨🇦 McGill/Mila + Oxford | 1 |
| 2504.11011 | Doc Quality Scoring Web Crawl | 2025 | WOWS 2025 | 🇮🇹 Uni Pisa | 1 |
| 2410.21360 | Credibility Assessment Survey | 2025 | ACM TIST | 🇸🇰🇫🇷🇩🇪🇮🇹 multi-European | 1 |
| 2510.13749 | Web Search Credibility for Chat | 2026 | arXiv | multi-institution | 1 |
| 2509.22186 | MinerU2.5 | 2025 | Tech Report | 🇨🇳 OpenDataLab/Shanghai AI Lab | 2 |
| 2510.14528 | PaddleOCR-VL | 2025 | Tech Report | 🇨🇳 Baidu/PaddlePaddle | 2 |
| 2412.07626 | OmniDocBench | 2025 | CVPR 2025 | 🇨🇳 OpenDataLab | 2 |
| 2505.14059 | Dolphin | 2025 | ACL 2025 | 🇨🇳 ByteDance | 2 |
| 2604.04771 | MinerU Pro-5 | 2026 | Tech Report | 🇨🇳 OpenDataLab | 2 |
| 2603.06976 | Systematic Chunking Investigation | 2026 | arXiv | 🇦🇺 UTS | 3 |
| 2602.16974 | Beyond Chunk-Then-Embed | 2026 | arXiv | multi-institution | 3 |
| 2510.06999 | Reliable Retrieval Legal RAG | 2025 | arXiv | multi-institution | 3 |
| 2505.23628 | AutoSchemaKG | 2026 | ACL 2026 | 🇭🇰 HKUST + Huawei | 4 |
| 2602.01276 | OntoEKG | 2026 | ICSC 2026 | 🇬🇧 Leeds Beckett | 4 |
| 2510.20345 | LLM KG Construction Survey | 2025 | arXiv | (single author) | 4 |
| 2511.05991 | Ontology Learning + RAG | 2025 | arXiv | 🇵🇹 Portugal | 4 |
| 2506.00664 | Automated Ontology from Text | 2025 | arXiv | multi-institution | 4 |
| 2607.21503 | Agentic Context Management (ACM) | 2026 | arXiv | independent | 5 |
| 2501.13956 | Zep Temporal KG Memory | 2025 | arXiv | Zep AI | 5 |
| 2603.07670 | Memory for LLM Agents Survey | 2026 | arXiv | (single author) | 5 |
| 2603.22455 | SkillRouter | 2026 | arXiv | 🇨🇳 Tencent | 6 |
| 2605.28268 | RoBatch Cost-Effective Routing | 2026 | arXiv | 🇨🇳 CUHK/HK | 6 |
| 2604.23577 | RouteNLP | 2026 | arXiv | multi-institution | 6 |
| 2502.16696 | OptiRoute | 2025 | arXiv | multi-institution | 6 |
| 2604.03527 | Explainable Routing Agentic | 2026 | arXiv | multi-institution | 6 |

---

## Non-English GitHub Repositories Summary

| Repo | Stars | Language | Topic | Institution |
|------|-------|----------|-------|-------------|
| github.com/opendatalab/MinerU | 18K+ | 🇨🇳 Chinese | 2 | OpenDataLab/Shanghai AI Lab |
| github.com/PaddlePaddle/PaddleOCR | 41K+ | 🇨🇳 Chinese | 2 | Baidu |
| github.com/ByteDance/Dolphin | ~1K | 🇨🇳 Chinese | 2 | ByteDance |
| github.com/opendatalab/OmniDocBench | ~2K | 🇨🇳 Chinese | 2 | OpenDataLab |
| github.com/infiniflow/ragflow | 30K+ | 🇨🇳 Chinese | 2 | InfiniFlow (DeepDoc inside) |
| github.com/HKUST-KnowComp/AutoSchemaKG | ~300 | 🇭🇰 HK/Chinese | 4 | HKUST |
| github.com/zjukg/OntoTune | ~100 | 🇨🇳 Chinese | 4 | ZJU KG Group |

---

## Cross-Language Convergence Analysis

| Topic | ZH | JA | KO | RU | DE | FR | Strength | Notes |
|-------|----|----|----|----|----|----|----------|-------|
| 1. Credibility | GAP | GAP | GAP | GAP (pedagogical) | HIT (SemCAFE co-author) | HIT (AFP survey + Caen) | MODERATE | EU multi-institution dominates |
| 2. Vision PDF parsing | VERY STRONG | GAP | GAP | GAP | GAP | GAP | VERY STRONG | Chinese monopoly: 5/5 top papers |
| 3. Chunking | DERIVATIVE | DERIVATIVE | GAP | GAP | GAP | GAP | ABSENT | English-language field entirely |
| 4. Ontology induction | HIT (HKUST/ZJU) | established but older | GAP 2025-26 | GAP (pre-LLM paradigm) | English venues | English venues | MODERATE | Chinese leading in LLM era |
| 5. PreCompact KG sync | DERIVATIVE (practitioner) | GAP | GAP | PRACTITIONER (Habr) | GAP | GAP | ABSENT | Too new for academic cycle |
| 6. Model routing | HIT (Tencent/CUHK) | GAP | GAP | GAP | English venues | English venues | MODERATE | Chinese companies leading |

---

## Hermes Implementation Priority from Non-English Findings

| Priority | Paper | Institution | Action | Feasibility |
|----------|-------|-------------|--------|-------------|
| P1 | SkillRouter 2603.22455 | 🇨🇳 Tencent | Expose full skill body (not just name) for routing; `model:` frontmatter belongs to routing signal | HIGH |
| P2 | AutoSchemaKG 2505.23628 | 🇭🇰 HKUST | Use for Cognee cognify() — 92% schema alignment, zero manual intervention, processes 50M docs | MEDIUM |
| P3 | MinerU2.5 2509.22186 | 🇨🇳 OpenDataLab | Drop-in for DeepDoc vision pipeline; SOTA on OmniDocBench at 1.2B params, open source | HIGH |
| P4 | PaddleOCR-VL 2510.14528 | 🇨🇳 Baidu | Smallest SOTA VLM for multilingual document parsing (0.9B, 109 languages) | HIGH |
| P5 | SemCAFE 2504.08776 | 🇩🇪🇫🇷 EU | Entity-level credibility fingerprinting for Firecrawl post-processing; +12% F1 on Ukraine war data | HIGH |
| P6 | ACM paper 2607.21503 | independent | Use 5 primitives (esp. "anticipating" + "compacting") as framework for PreCompact design | HIGH (framework) |
| P7 | Systematic Chunking 2603.06976 | 🇦🇺 UTS | Use domain-specific recommendations: legal → paragraph grouping; biology → dynamic token sizing | VERY HIGH |
| P8 | RoBatch 2605.28268 | 🇨🇳 CUHK | Jointly optimize model routing + batch size for cost-performance Pareto frontier | MEDIUM |

---

## Notes on Access and Coverage Gaps

- **CNKI/Wanfang**: Not accessed (paywalled). Chinese researchers publish relevant work on arXiv; no loss of major papers.
- **IPSJ full text**: Not accessible (2-year embargo). Metadata confirmed no 2025-2026 IPSJ papers directly on these 6 topics.
- **CyberLeninka**: Accessible. Topics 1 and 4 returned only pedagogical/pre-LLM content. Topics 2, 3, 5, 6 returned no relevant papers.
- **TALN 2026**: Fully accessible. No papers on these 6 topics in French. TALN 2026 focus was on LLM evaluation and agent benchmarking, not RAG infrastructure.
- **Korean KIISE/RISS**: Searched. No Korean-language papers on these 6 topics. Korean community derives from English-language research.
- **Habr.com (Russian practitioner)**: Contains engineering discussion on KG agent integration (Graphify project) — practitioner, not peer-reviewed.
