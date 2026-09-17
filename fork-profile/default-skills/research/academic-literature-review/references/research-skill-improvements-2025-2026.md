# Research-Skill Improvements: 2025-2026 Findings

Synthesized from: arXiv, ACL Anthology, GitHub awesome lists, r/MachineLearning community, and multilingual academic search sources.

---

## Agentic Academic Search

- **PaSa** (ByteDance, ACL 2025): RL-trained paper search agent. Surpasses Google+GPT-4o by 37.78% recall@20, 39.90% recall@50. Uses: invoke search tools -> read papers -> select references (ReAct loop). github.com/bytedance/pasa / pasa-agent.ai
- **OpenScholar** (Nature 2025): RAG-LM grounded on scientific corpora. Best for science synthesis with verifiable citations.
- **SPAR** (Semantic Scholar 2025): LLM agent over S2AG (Semantic Scholar Academic Graph), largest open scientific literature graph.
- **Semantic Scholar Academic Graph API** (api.semanticscholar.org): Free. 200M+ papers, citation graph, bulk JSONL download, Python client.
- **arXiv sidecars** (attached directly on arxiv.org pages): alphaXiv (discussion), CatalyzeX (code finder), Connected Papers (citation graph), Litmaps (temporal map), scite.ai (smart citations: supporting/contrasting/mentioning).

---

## Deep Research Agent Architecture — SOTA Survey Map

| Paper | arXiv ID | Key claim |
|---|---|---|
| Agentic RAG survey | 2501.09136 | Taxonomy: reflection/planning/tool-use/multi-agent |
| LLM Deep Search Agents survey | 2508.05668 | SFT vs RL training for search agents; open challenges |
| AutoResearch survey | 2605.23204 | L0-L4 autonomy; "Vibe Research" (L1-L2) practical today |
| BLAZE | 2608.02775 | Socialized scientific intelligence: persistent KG + collective reasoning |
| AI Scientist / AI Scientist-v2 | - | End-to-end ideation→experiment→paper (SakanaAI) |
| Verification Gap survey | 2608.05179 | Only 38% of 24 runnable AI-scientist systems release reproducibility artifacts |

### Critical insight from Verification Gap (2608.05179)
Code release is now common (83% of systems). But only 38% release seeds/traces for reproducibility. Only 38% verify novelty. No LLM-era system in the coded corpus demonstrates an externally validated closed-loop oracle. The harder problem is verifying claims, not making them.

---

## GitHub Research Mining

- **PaperFlow** (papersflow.ai): auto-extracts GitHub repos from papers by arXiv ID/DOI.
- **Papers With Code API** (paperswithcode.com/api): benchmark tracking, code linking, structured paper metadata.
- **MSR field** (Mining Software Repositories): LLM-based repo analysis survey arXiv:2604.00787.
- **ToolMaker** (AI4Science GitHub): converts papers with code into callable agent tools.
- **AutoResearchClaw** (aiming-lab GitHub): paper→sandbox experiments→multi-agent review→LaTeX output.
- **AIDE** (Weco AI): ML engineering agent integrating arXiv + PwC for code/research plans, auto-debugging.
- **RD-Agent** (Microsoft): R&D automation, paper-to-code, Kaggle automation.

### GitHub search patterns for research
1. Search "awesome {topic} papers 2025" or "awesome {topic} survey" — curated entry points.
2. Filter by topics + recently updated (< 6 months) to avoid stale lists.
3. Use paperswithcode.com as the canonical bridge: paper→code→benchmark→leaderboard.
4. Star-count alone is misleading; check last commit date + issue activity.

---

## Multilingual / Cross-lingual Academic Search

| Resource | Language | Notes |
|---|---|---|
| CNKI / CNKI Overseas | Chinese (Simplified) | Largest Chinese academic DB; MCP crawler: mcpmarket.com/server/cnki-crawler |
| CiNii Research | Japanese | National academic bibliography |
| J-STAGE | Japanese | Open-access scientific journals |
| Cyberleninka | Russian | Open-access Russian academic corpus |
| Redalyc | Spanish/Portuguese | Latin American and Iberian journals |
| SciELO | Spanish/Portuguese/French | Open science for developing countries |
| BASE | Multi | Bielefeld Academic Search Engine, 300M+ documents |
| CORE | Multi | Open-access aggregator, 230M+ papers |

### Cross-lingual retrieval strategies
- **XRAG** (arXiv:2505.10089): cross-lingual RAG — mono + multilingual retrieval comparison.
- **CLIR survey** (arXiv:2510.00908): advances in cross-lingual information retrieval.
- **"Better to Ask in English"** (ACM 2024): translate queries to English first, then retrieve, then back-translate. Effective practical fallback.
- LLM-native strategy: prompt in target language, retrieve in English, synthesize back in target language. Outperforms naive cross-lingual retrieval for most languages.

---

## Open-Source Research Pipeline Tools (2025-2026)

| Tool | Stars est. | Notes |
|---|---|---|
| AI-Scientist (SakanaAI) | 12k+ | Full end-to-end research automation |
| GPT-Researcher (assafelovic) | - | Modular OSS deep research agent |
| deer-flow (ByteDance) | - | Open deep research pipeline |
| STORM (Stanford-oval) | - | Wikipedia-style synthesis from web search; storm.genie.stanford.edu |
| local-deep-research (LearningCircuit) | - | Offline/local variant of deep research |
| AutoResearchClaw (aiming-lab) | - | paper→code→review→LaTeX |
| OpenScholar | - | Scientific RAG, grounded citations |

---

## Benchmarks for Research Agent Evaluation

- **RealScholarQuery** (ByteDance/PaSa): real-world academic query benchmark.
- **SAGE** (arXiv:2602.05975): retrieval for deep research agents.
- **AIRS-Bench / FIRE-Bench**: frontier research agent evaluation.
- **DeepHalluBench** (arXiv:2601.22984): hallucination in research trajectories.
- **FML-bench** (arXiv:2605.17373): AI research agent strategies from search dynamics perspective.
- **AutoScholarQuery** (ByteDance): 35k fine-grained academic queries + papers from top AI conferences.

---

## Community-Validated Practitioner Stack

From r/MachineLearning and r/PhD threads (2025-2026):

1. **NotebookLM** (Google): distillation + RAG. Shared spaces for team use. Best for ingesting and distilling a corpus.
2. **SciSpace / Typeset.io** (scispace.com): 280M+ papers, structured evidence search, PDF reading, data extraction. Avoids raw Google crawl.
3. **Consensus** (consensus.app): scientific agreement scoring across peer-reviewed papers. Best for "what does the literature say about X?"
4. **STORM** (storm.genie.stanford.edu): natural summarization pipeline for holistic topics. Good for open-ended domain overviews.
5. **scite.ai**: smart citations — identifies whether a paper supports, contrasts, or merely mentions a claim. Critical for adversarial literature review.
6. **ResearchRabbit / Litmaps**: citation graph visualization. Find adjacent work you wouldn't have searched for.
7. **Sugaku** (sugaku.net, math): surfaces diverse rather than similar papers — exploration over exploitation.
8. **Connected Papers** (connectedpapers.com): visual citation map, good for entering a new field.

### Workflow that practitioners use
Finding new papers → NotebookLM (distill) → domain note tool → add structured evidence via SciSpace → STORM for synthesis.

---

## Where Search Agents Are Weakest (Gaps to exploit manually)

1. Novelty verification — agents hallucinate novelty claims; check citing papers manually.
2. Non-English corpora — most agents are English-first; use CNKI/CiNii/SciELO directly.
3. Informal/grey literature — GitHub repos, preprints, blog posts, workshop papers not indexed in Semantic Scholar.
4. Contradictory evidence — agents synthesize toward consensus; use scite.ai to surface dissenting citations.
5. Reproducibility check — verify code releases, seeds, and experiment logs; do not trust agent summaries about results.
6. Temporal blind spots — Semantic Scholar and arXiv have 1-7 day indexing lag; check Hugging Face Papers daily for zero-lag paper drops.

---

## Practical API References

- Semantic Scholar API: `api.semanticscholar.org/graph/v1/paper/search?query=...&fields=title,authors,year,citationCount,externalIds`
- arXiv API: `export.arxiv.org/api/query?search_query=all:{query}&max_results=20&sortBy=lastUpdatedDate`
- Papers With Code API: `paperswithcode.com/api/v1/papers/?q={query}`
- CORE API: `api.core.ac.uk/v3/search/works?q={query}` (open access focus)
- BASE API: `api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi?func=PerformSearch&query={query}&hits=20&format=json`
- OpenAlex API: `api.openalex.org/works?search={query}&filter=open_access.is_oa:true` — growing fast, 250M+ works, fully open.

OpenAlex is increasingly preferred over Semantic Scholar for open-access bulk queries (no rate limit with API key, full DOI/ORCID graph).
---

## New Papers Found via arXiv Script (August 2026)

Three new verified papers from the improved arxiv search script (3-tier fallback: export API -> Firecrawl -> HTML):

### SkillProx: Self-Evolving Agent Skills via Proximal Textual Gradient Descent
arXiv:2608.07449 (cs.AI/cs.CL) — 7 Aug 2026 — Zheng et al., Imperial College/HKU
Proximal-gradient-inspired forward-backward framework for skill evolution.
Forward stage: closed-loop diagnosis, roll back regressions. 
Backward stage: leave-one-out utility audit per knowledge unit, validation-gated consolidation/demotion/removal.
+3.0pp accuracy over strongest gradient-based baseline on in- and out-of-distribution benchmarks.
Caveat: tested only on agent task benchmarks, not on academic research workflows specifically.
Relevant here: the framework directly addresses Hermes skill consolidation — the "backward stage" maps to our skill pruning and utility audit problem.

### DocArena: Turning Raw Documents into Controllable Training Environments for Document Search Agents
arXiv:2606.26122 (cs.CV) — 27 May 2026 — Wang et al., Adobe Research
Automated pipeline: raw document collection -> RL-training environment for search agents. 
79K QA pairs from 8,336 documents across 16 domains and 49 languages.
Decouples visual perception from policy model (text LLMs as reasoning backbone for multimodal retrieval).
Caveat: cs.CV framing; primarily about enterprise document QA, not open-web academic search.
Relevant here: 49-language coverage is the largest multimodal document search dataset found; the Doc-Search agent architecture is directly applicable.

### Tensor Manifold-Based Graph-Vector Fusion for AI-Native Academic Literature Retrieval
arXiv:2604.16416 (cs.IR) — 2 Apr 2026 — Wei, Yu
Geometry-unified graph-vector fusion framework for academic literature retrieval.
Four modules: temporal diffusion signature update, hierarchical temporal manifold encoding, Riemannian manifold indexing, AI-agent programmable retrieval.
Linear time/space complexity. Tested on large-scale dynamic academic literature graphs.
Caveat: "accepted for publication" without named venue; no code released; 2 authors, 0 figures — warrants scrutiny before citing.
Relevant here: the "AI-agent programmable retrieval" module concept aligns with building structured retrieval harnesses on top of OpenAlex/Semantic Scholar APIs.

### Papers Found by Adversarial Subagent (not in original files)

**AI4Research: A Survey of AI for Scientific Research**
arXiv:2507.01903 (cs.CL/cs.AI) — 2 Jul 2025, updated 5 Aug 2025 — Chen et al. (25 authors), Harbin Institute of Technology
Most comprehensive 2026 survey of AI for science. Covers reasoning, search, experiment coding, paper generation.
Caveat: survey papers tend to be descriptive, not evaluative — check primary papers for numbers.

**Reinforcement Learning Foundations for Deep Research Systems**
arXiv:2509.06733 (cs.AI/cs.CL/cs.IR) — 8 Sep 2025, updated 5 Nov 2025 — Li et al., Sea AI Lab/NUS
RL survey specifically for agentic deep research: Planner/Coordinator/Executor hierarchy, training full stacks end-to-end.
Caveat: "deep research" framing includes enterprise knowledge retrieval, not just academic search.

**AI for Auto-Research: Roadmap & User Guide**
arXiv:2605.18661 (cs.AI) — 18 May 2026, updated 20 Jul 2026 — Kong et al. (19 authors), NUS/A*STAR
Practical roadmap for fully automated research pipelines. Notable: papers can be generated for ~$15; flags integrity crisis explicitly.
Caveat: roadmap paper, not an empirical benchmark — useful for framing, not for performance comparisons.

### OpenAlex Coverage Note (from arXiv search: 2406.15154)
Analysis confirms OpenAlex diverges from Scopus/WoS on document type classification.
Also: 2403.13339 found OpenAlex does NOT reliably flag retracted papers — check Retraction Watch separately when paper quality matters.

