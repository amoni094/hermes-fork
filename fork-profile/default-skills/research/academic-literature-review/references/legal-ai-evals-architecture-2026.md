# Legal AI Evals — Architecture & Benchmark Reference Bank
## Session: July 2026 | Domain: AI evals for legal team cowork architecture (AU context)
## System: cowork multi-agent + legal reasoning MCP + personal second-brain + team brain MCP

All arXiv IDs verified against live abstract pages. Fabricated citations explicitly excluded.
This file covers evals for: contract negotiation, litigation/discovery, personal second-brain
(email/Teams ingestion), team brain MCP (templates/playbooks), multi-agent cowork.

---

## Quick Reference Table

| ID | arXiv/URL | Title | Year | Eval Task | AU? | Priority |
|----|-----------|-------|------|-----------|-----|----------|
| L1 | 2308.11462 | LegalBench | 2023 | Legal reasoning (162 tasks) | No (US) | HIGH |
| L2 | 2408.10343 | LegalBench-RAG | 2024 | Legal RAG retrieval | No (US) | CRITICAL |
| L3 | 2508.03080 | ContractEval | 2025 | Contract clause extraction | No (US) | HIGH |
| L4 | atticusprojectai.org/cuad | CUAD | 2021 | Contract corpus (41 categories) | No (US) | FOUNDATION |
| L5 | EACL 2026 ASU | CLAUSE discrepancy | 2026 | What models miss (omissions) | No | HIGH |
| L6 | 2110.00976 | LexGLUE | 2022 | General legal NLP (7 tasks) | No (EU/US) | MEDIUM |
| L7 | 2507.21108 | Singh LCC Survey (UNSW) | 2025 | Contract classification taxonomy | YES (UNSW AU) | HIGH |
| L8 | 2604.23585 | ComplianceNLP | 2026 | Compliance KM 3.1x deployed | No (HKU) | HIGH |
| L9 | 2606.13184 | LAUKIN | 2026 | AU+UK+IN contract dataset | YES (AU+UK+IN) | CRITICAL |
| HLB-01 | github.com/harveyai/biglaw-bench | BigLaw Bench | 2025 | Transact+litigation tasks, SPAs | No (US) | VERY HIGH |
| HLB-02 | github.com/harveyai/harvey-labs | Harvey LAB | 2026 | 1,671 agentic legal tasks | Partial (common-law) | CRITICAL |
| A1 | 2412.17259 | LegalAgentBench | 2024 | Legal agent (ACL 2025, Chinese) | No (CN) | HIGH |
| A2 | 2503.01935 | MultiAgentBench (MARBLE) | 2025 | Cowork milestone KPIs | No | HIGH |
| A3 | 2507.21504 | Agent Eval Survey | 2025 | Enterprise eval gaps taxonomy | No | HIGH |
| A5 | 2606.30906 | Multi-Agent Deliberation in Law | 2026 | Legal reasoning via deliberation | No | HIGH |
| A6 | 2606.07805 | MAC-Bench | 2026 | Compliance under adversarial pressure | No | HIGH |
| A7 | 2606.02282 | POIROT | 2026 | MAS failure detection | No | HIGH |
| A8 | 2602.11510 | AgentLeak | 2026 | Inter-agent privacy leakage | No | CRITICAL |
| PART | 2606.04602 | Parthenon Law | 2026 | Self-evolving legal agent | No | VERY HIGH |
| GAVEL | 2601.04424 | Gavel | 2026 | Long-context legal summarization | No | HIGH |
| M1 | github.com/Accenture/mcp-bench | MCP-Bench (Accenture) | 2025 | MCP tool use (28 servers, 250 tools) | No | CRITICAL |
| M2 | github.com/mcp-tool-bench/MCPToolBenchPP | MCPToolBench++ | 2025 | MCP large-scale (4k+ servers) | No | MEDIUM |
| M3 | 2508.13220 | MCPSecBench | 2025 | MCP security (injection, poisoning) | No | CRITICAL |
| B1 | github.com/xiaowu0162/LongMemEval | LongMemEval (ICLR 2025) | 2024 | Agent long-term memory (5 abilities) | No | CRITICAL |
| B2 | 2605.12493 | LongMemEval-V2 | 2026 | Agentic memory extension | No | HIGH |
| B3 | 2606.29914 | MemDelta (ACL 2026) | 2026 | Controlled memory ablation | No | HIGH |
| B4 | 2501.13956 | Zep/Graphiti | 2025 | Temporal KG memory (+18.5% LME) | No | REFERENCE |
| B5 | 2607.13157 | Oracle Agent Memory | 2026 | Enterprise memory (93.8% LME) | No | HIGH |
| R1 | github.com/explodinggradients/ragas | RAGAS | 2023+ | RAG: faithfulness/recall/precision | No | HIGH |
| R2 | github.com/confident-ai/deepeval | DeepEval | 2023+ | CI/CD LLM eval (50+ metrics) | No | HIGH |
| R3 | github.com/truera/trulens | TruLens | 2023+ | Production monitoring/tracing | No | MED-HIGH |
| R4 | pip install lrage | LRAGE (ACL 2025) | 2025 | Legal RAG benchmark (pip install) | Partial (KBL) | HIGH |
| J1 | 2511.21140 | Lee et al. judge bias correction | 2025 | LLM-as-judge calibration | No | CRITICAL |
| J2 | DOI:10.11517/pjsai.jsai2025 | JSAI2025 Microsoft Japan | 2025 | Judge fine-tuning for house standards | No (JP) | HIGH |
| K1 | 2605.28120 | LegalGraphRAG (ACL 2026) | 2026 | 3-tier legal KG | No | HIGH |
| K2 | 2606.00610 | MemGraphRAG (KDD 2026) | 2026 | KG conflict detection | No | HIGH |
| E1 | SIGIR 2014/2024 | Grossman/Cormack TAR | 2014/2024 | eDiscovery recall/precision | No | CRITICAL |
| E3 | 2604.23577 | RouteNLP | 2026 | Legal risk routing (conformal) | No | HIGH |

---

## Section 1: Core Legal Reasoning Benchmarks

### LegalBench (arXiv:2308.11462)
- Authors: Guha, Nyarko, Ho, Ré et al. (40 contributors) — Stanford, Chicago, Dartmouth
- 162 tasks, 6 reasoning categories: issue spotting, rule recall, rule application, interpretation, rhetorical understanding, conclusion
- 20 LLMs benchmarked; strong on rule recall, weak on multi-step application
- GitHub: github.com/HazyResearch/legalbench (CC BY 4.0)
- AU use: methodology template — build 20-30 AU-specific tasks (Corporations Act 2001, ACL, PPSA) using same 6-category format
- Venue/Institution confirmed: NeurIPS 2023 Datasets and Benchmarks

### LegalBench-RAG (arXiv:2408.10343)
- Authors: Pipitone, Houir Alami (ZeroEntropy)
- 6,858 query-answer pairs over 79M character corpus; all human-annotated by legal experts
- Tests retrieval step specifically; emphasizes minimal high-relevance snippets over doc IDs
- GitHub: github.com/zeroentropy-cc/legalbenchrag (includes -mini)
- Key insight: large imprecise chunks degrade LLM performance; minimal snippets reduce hallucination and support citations
- Apply to: team brain MCP retrieval of templates/playbooks/precedents

### LAUKIN (arXiv:2606.13184) — THE ONLY VERIFIED AU CONTRACT DATASET ⭐
- Authors: Singh, Joshi, Jiang, Paik, Cheong (Monash + mixed) | June 2026 | accepted paper
- 14,727 clause pairs from 204 contracts, 8 agreement types
- Jurisdictions: Australia–UK, UK–India, India–Australia
- 3,000 manually labelled (boolean: Equivalent / Not Equivalent); 900 train / 600 dev / 1,500 test
- Best model: Macro-F1 65.11% — challenging; drafting conventions diverge significantly even within common-law family
- 11,727 unlabelled pairs for semi-supervised learning
- CRITICAL: only verified benchmark with Australian contract law coverage
- Use for: evaluating team brain MCP's AU-specific clause understanding and cross-jurisdiction template mapping

### Singh LCC Survey (arXiv:2507.21108) — UNSW (first AU academic contract AI eval survey)
- July 2025 | University of New South Wales (Australia)
- Comprehensive survey: 7 task types, 14 datasets, evaluation criteria (Section 7)
- KEY FINDING: "Amendment-category extraction" is NOT a recognized benchmarked task as of 2025
- Use to: name eval tasks correctly; see Section 7 for evaluation criteria taxonomy

### ContractEval (arXiv:2508.03080)
- Aug 2025 | CMU/Rutgers/Stanford/NJIT
- 19 LLMs on CUAD 4,128 data points / 41 clause categories
- Critical findings:
  1. Proprietary > open-source consistently
  2. Open-source shows "laziness failure" (false "no clause found" on rare categories)
  3. "Thinking mode" REDUCES correctness on span extraction (counterintuitive)
  4. Accuracy non-uniform — drops on rare/long clause categories
- Implication: report per-clause-category accuracy, not blended F1; rarer AU-specific clauses will underperform

### CLAUSE Discrepancy Benchmark (EACL 2026 ASU)
- 12,869+11,086 perturbations across CUAD/ContractNLI; 10 perturbation categories
- KEY FINDING: LLMs weakest on "omission"-type contradictions (missing clauses) vs explicit changes
- Direct legal implication: counterparty dropping a clause is harder to detect than counterparty changing a clause; this is the primary failure mode for contract negotiation AI

### ComplianceNLP (arXiv:2604.23585)
- ACL 2026 Industry Track | University of Hong Kong
- 12,847 regulatory provisions; 4-month production deployment
- Numbers: F1 87.7, grounding 94.2%, 3.1x analyst efficiency (sustained), recall 96.0%, precision 90.7%
- KG re-ranking = +4.6 F1 (largest single factor)
- Benchmark for team brain MCP ROI claims in production

---

## Section 2: Legal Agent Eval Frameworks

### Harvey LAB (github.com/harveyai/harvey-labs) — PRIMARY LEGAL AGENT BENCHMARK ⭐
- Harvey AI | May 2026 | MIT license | 566 stars, 139 forks
- 1,671 agentic legal tasks across 24 practice areas including contracting explicitly
- Agents given avg 8 documents (range 2-55); includes M&A data-room tutorial task
- Architecture: tasks/ + harness/ + evaluation/ + sandbox/ (fully self-hostable)
- Metric: All-pass rate (strict: ALL rubric criteria met) + per-criterion accuracy
- LLM-judge + rubric-based scoring; penalizes hallucination
- From Parthenon study (12,510 trajectories): frontier agents far from single-pass completion; per-criterion accuracy improves with model strength while strict all-pass stalls
- Use as: PRIMARY benchmark for cowork architecture; all-pass rate is the right metric for contract negotiation quality
- Companion: BigLaw Bench (github.com/harveyai/biglaw-bench, 173 stars) — same Harvey AI, includes "Negotiation Strategy" task explicitly + SPA Workflows + Discovery Emails retrieval

### LegalAgentBench (arXiv:2412.17259)
- ACL 2025 | GitHub: github.com/CSHaitao/LegalAgentBench
- 17 real-world corpora, 37 tools; Chinese law; multi-step legal task completion
- Framework (tool taxonomy + eval protocol) applicable regardless of jurisdiction
- Adapt tool taxonomy to your MCP skill set

### MultiAgentBench MARBLE (arXiv:2503.01935)
- Mar 2025 | GitHub: github.com/MultiagentBench/MARBLE | Zhu et al. (UIUC/Yale)
- Milestone-based KPIs; tests star/chain/tree/graph coordination topologies
- KEY for architecture: graph topology > chain for complex tasks; cognitive planning +3% milestone rate
- Use: milestone-based KPI framework for cowork quality eval

### Multi-Agent Deliberation in Law (arXiv:2606.30906)
- AIDA2J Workshop, ICAIL 2026 (Singapore)
- Legal reasoning via multi-agent deliberation; tests accuracy vs single-LLM baseline
- Directly applicable to cowork agents deliberating on contract positions

### MAC-Bench (arXiv:2606.07805)
- GitHub: github.com/leonardeee/MAC-Bench | 2026
- Evaluates compliance when agents face adversarial pressure to violate rules
- SERV pipeline transforms legal texts into adversarial scenarios; Machiavellian Gap (MG) metric
- KEY FINDING: pervasive Pareto trade-off between task success and rule compliance
- Critical for contract negotiation: counterparty pressure may cause agent to violate playbook; must test this explicitly

### POIROT (arXiv:2606.02282)
- 2026 | Open-source library + BLAME benchmark
- Uses system's own agents as diagnostic layer; fault attribution in MAS
- OR = 1.60, p = 0.008; gains scale with agent count and fault dimensionality
- Use for: self-auditing cowork architecture; agents evaluating each other's contract positions

### AgentLeak (arXiv:2602.11510) — CRITICAL FOR LEGAL PRIVILEGE ⭐
- IEEE Access 2026 | GitHub: Privatris/AgentLeak
- 1,000 scenarios across healthcare, finance, LEGAL, corporate; 5 production LLMs
- KEY FINDING: inter-agent messages (C2) leak at 68.8% vs final outputs at 27.2%
- Output-only audits miss 41.7% of violations
- Total system exposure 68.9% across all internal channels
- CRITICAL: privileged client info in emails entering personal second-brain may leak through inter-agent channels even if final outputs look clean
- Eval requirement: audit ALL inter-agent communication channels, not just final outputs

### Parthenon Law (arXiv:2606.04602)
- 2026
- Large-scale Harvey LAB study (12,510 trajectories); anti-leakage learning loop
- Skills/playbooks evolve from matter outcomes without touching model weights = team brain MCP concept
- Eval dimensions: source traceability, date/number grounding, deliverable compliance
- Architecture reference for how team brain MCP should evolve + how to eval playbook update quality

### Gavel (arXiv:2601.04424)
- 2026 | Dou, Mamut, Xu | Webpage: yao-dou.github.io/gavel
- Long-context legal case summarization (often >100K tokens)
- KEY FINDINGS: models OMIT key info more than hallucinate; performance degrades with length; complex settlements harder than filings; Gavel-Agent reduces tokens by ≥36%
- Reference-free approach (no ground truth needed) — applicable to second-brain where ground truth doesn't exist for real matters

---

## Section 3: MCP Evaluation

### MCP-Bench (github.com/Accenture/mcp-bench) — PRIMARY MCP EVAL
- Accenture | OpenReview: openreview.net/forum?id=fe8mzHwMxN
- 28 MCP servers, 250 tools; tool discovery, selection, multi-step coordination, parameter control
- Apply to: legal reasoning MCP skill set — can the LLM correctly select clause_extraction vs contract_review vs due_diligence tools?

### MCPToolBench++ (github.com/mcp-tool-bench/MCPToolBenchPP)
- 4k+ MCP servers, 45+ categories; single + multi-step tool calls
- Large-scale coverage for comprehensive tool-use capability assessment

### MCPSecBench (arXiv:2508.13220) — CRITICAL FOR LEGAL
- First systematic security benchmark for MCP; tests tool poisoning, prompt injection
- CRITICAL: adversarial contract content can manipulate legal advice via MCP prompt injection
- Test: can a maliciously crafted contract clause cause MCP legal skill to give wrong advice?
- This is a direct professional liability risk; must test before production

---

## Section 4: Personal Second-Brain Evaluation

### LongMemEval (github.com/xiaowu0162/LongMemEval) — PRIMARY MEMORY BENCHMARK ⭐
- ICLR 2025 | Wu et al. (UCLA/Tencent AI Lab)
- 500 questions, 5 core memory abilities:
  1. Information extraction
  2. Multi-session reasoning
  3. Knowledge update (new info overrides old)
  4. Temporal reasoning
  5. Abstention (knowing what you don't know)
- Zep/Graphiti benchmark: +18.5% accuracy, -90% latency
- Apply: "Does the personal brain correctly remember what was agreed in the March email? Did the position update after the April negotiation?"

### LongMemEval-V2 (arXiv:2605.12493)
- 2026 — extends LongMemEval toward agentic contexts
- More complex multi-session + agentic scenarios

### MemDelta (arXiv:2606.29914) — ACL 2026 Findings
- HuggingFace: memdelta-bench/memdelta-benchmark
- Controlled evaluation varying ONE component at a time on LongMemEval-S (500Q, 50+ sessions)
- 3 model families tested
- Use for: diagnosing which memory component (embedding, retrieval, KG reasoning) is causing failures
- Methodological: use MemDelta protocol to design controlled experiments for your own legal memory system

### Oracle Agent Memory (arXiv:2607.13157)
- 2026 | LongMemEval score 93.8%; 10.7x token reduction
- Enterprise memory substrate for production agent workloads
- Compare against Zep/Graphiti when selecting second-brain architecture

### Zep/Graphiti (arXiv:2501.13956)
- Zep AI (commercial research) | GitHub: github.com/getzep/graphiti
- DMR benchmark 94.8%, LongMemEval +18.5%, -90% latency
- Architecture: temporal KG synthesizing conversational + document knowledge; tracks who said what when
- Closest existing system to personal second-brain model (email + document knowledge, personal→team→org tiers)
- Use as implementation reference + LongMemEval baseline

---

## Section 5: RAG Eval Tooling

### RAGAS (github.com/explodinggradients/ragas)
- pip install ragas | ground-truth-free 4 core metrics
- Faithfulness: does answer faithfully reflect source (no hallucinated positions)?
- Answer relevancy, context precision, context recall
- Apply to team brain: does the MCP response faithfully reflect the template?
- Start here — fastest way to add RAG quality monitoring from day 1

### DeepEval (github.com/confident-ai/deepeval)
- pip install deepeval | 50+ pytest-native metrics
- G-eval, DAGMetric, hallucination, RAG triad; CI regression gates
- Use for: regression testing every contract review pipeline change

### TruLens (github.com/truera/trulens)
- pip install trulens | RAG feedback + OpenTelemetry tracing
- Production monitoring + alerting on metric degradation
- Use post-deployment for ongoing team brain quality monitoring

### LRAGE (pip install lrage, ACL 2025)
- Legal-domain RAG benchmark
- Includes KBL (Korean Bar/Legal), bar exam QA, housing law QA, Pile-of-law
- LLM-as-judge + task accuracy on legal corpora; BM25 indices included
- Only pip-installable eval framework specifically for legal RAG

### LLM-FACETS (arXiv:2605.31167)
- 2026 | RAG Triad (faithfulness, relevance) + transparency/source citation metrics
- Compliance officer profile — maps to monitoring team brain vs regulatory/playbook sources

---

## Section 6: LLM-as-Judge Calibration

### Lee et al. 2511.21140 — Judge bias correction (MANDATORY for eval pipelines)
- arXiv:2511.21140 | Nov 2025 | Yonsei/UW-Madison/KRAFTON
- Naive judge accuracy: POSITIVELY biased when true accuracy is low (bad systems look better than they are)
- In degenerate case (judge always says correct): naive estimator = 1.0 regardless of ground truth
- Ships: bias-corrected plug-in estimator + valid CIs
- GitHub: github.com/UW-Madison-Lee-Lab/LLM-judge-reporting
- RULE: any LLM-as-judge quality gate must have (a) ground-truth calibration set, (b) bias correction, (c) CIs

### JSAI2025 Microsoft Japan (DOI:10.11517/pjsai.jsai2025.0_2win5102)
- Ito, Kurita, Otake (Microsoft Japan) | JSAI 2025
- KEY: few-shot prompting FAILS to calibrate judge to firm's own standards
- Fine-tuning on human-adjudicated examples works; accuracy scales with data volume
- RULE: your LLM-as-judge for contract quality MUST be fine-tuned on your team's annotated examples; few-shot insufficient for house-style calibration

---

## Section 7: Knowledge Graph Evaluation

### LegalGraphRAG (arXiv:2605.28120) — ACL 2026 Main
- Xiamen University | GitHub: github.com/XMUDeepLIT/LegalGraphRAG
- Three tiers: factual details → applied rules → abstract principles
- Three-agent verification: Researcher → Auditor (verifies vs source) → Adjudicator
- Maps to your architecture: personal brain (deal positions) → team brain (team standard) → policy (department)
- Auditor agent = safety gate for hallucinated clause positions

### MemGraphRAG (arXiv:2606.00610) — KDD 2026
- Schema-Fact-Passage 3-layer memory; ontology induction
- Conflict detection as FIRST-CLASS output (not silently resolved)
- Critical: surfaces when two agents/team members have inconsistent positions
- Eval metric: conflict detection rate (how often are real position conflicts surfaced vs silently resolved?)

---

## Section 8: Litigation/eDiscovery Standards

### Grossman & Cormack TAR Standards (SIGIR 2014/2024)
- SIGIR 2014: doi.org/10.1145/2600428.2609601
- SIGIR 2024 unbiased validation: doi.org/10.1145/3626772.3657903
- THE STANDARD: recall/precision for Technology Assisted Review (predictive coding)
- "Reasonable recall" using defensible CAL methodology (no fixed % in AU courts)
- CAL (Continuous Active Learning) superior to simple TAR 1.0
- SIGIR 2024 provides latest unbiased validation methodology — use this for TAR validation process

### RouteNLP (arXiv:2604.23577)
- Apr 2026 | HKU/Stellaris AI
- Legal Risk task included: 86.1% accuracy under conformal cascade vs 88.3% always-largest ceiling
- 2.2pt gap = LARGEST degradation among all task types — Legal Risk degrades most under cost reduction
- CAUTION: conformal guarantee is marginal (not per-query); coverage violation nearly doubles under 20% domain shift
- Use: risk routing design; monitor for distribution shift when AU law changes

---

## Section 9: Australian Compliance Sources (Primary)

### Federal Court GPN-AI
- URL: fedcourt.gov.au/law-and-practice/practice-documents/practice-notes/gpn-ai
- Published: 16 April 2026 (supersedes earlier drafts)
- Requirements: disclose AI use (what/how/for what); accuracy verification; no confidential material in public AI; preserve integrity of administration of justice; consistent with CPN-1
- First AU sanction: Victorian solicitor lost ability to practise as principal (August 2025) after submitting AI-fabricated cases to FCFCOA
- Eval requirement: litigation AI must log all AI use + prevent hallucinated case citations

### FCFCOA Practice Direction PD-AI
- URL: fcfcoa.gov.au/pd/pd-ai | Published: 29 May 2026
- 6 principles: Integrity, Accountability, Accuracy, Confidentiality/data security, Safety, Education
- HARD PROHIBITION: discovery material + suppression order material cannot enter public AI tools without closed-environment assurance
- GenAI cannot generate affidavit content

### NSW Supreme Court PN_SC_Gen_23
- URL: supremecourt.nsw.gov.au | 28 January 2025
- Disclosure obligations; AI must not generate affidavit/witness statement content

### Victoria Supreme Court SC Gen 25
- URL: supremecourt.vic.gov.au | 14 May 2026 (replaces 2024 guidelines)
- Meaningful human verification; AI-generated portions must be identified
- NOTABLE: EXPLICITLY ENDORSES purpose-built legal AI (TAR, contract review) as more reliable than general-purpose AI
- Implication for eval: documenting that your system is purpose-built + closed-environment creates favorable regulatory posture

### Joint All-States AI Selection Checklist (Feb 2026) — MANDATORY PRE-DEPLOYMENT GATE ⭐
- URL: qls.com.au (Feb 2026) | QLS + LIV + LSSA + LSWA + ACTLS + LSNT + LST
- 9 mandatory requirements:
  1. Privacy Impact Assessment (PIA) MANDATORY before deployment
  2. Data handling: processed/stored/access/resale/training disclosure
  3. Security accreditation: SOC 2, ISO 27001, or ISO 27017 required
  4. Jurisdiction: offshore storage triggers APP 8
  5. Client consent: informed consent required
  6. Privilege: uploading privileged comms "may waive LPP"
  7. AI prompts may not be privileged; may reveal case weaknesses
  8. Public AI: "not appropriate for confidential information"
  9. Model template client disclosure/consent (Annexure B)
- This checklist IS the compliance eval for system deployment
- Annexure B template: "We use [AI tool] for limited tasks such as summarising material, drafting outlines and preparing chronologies. All AI-assisted content is reviewed by a solicitor and citations are independently verified."

### Australian Voluntary AI Safety Standard (VAISS)
- URL: industry.gov.au/publications/voluntary-ai-safety-standard | Sep 2024
- 10 Voluntary Guardrails: Accountability, Transparency, Risk identification, Data governance, Robust testing, Incident response, Privacy protection, Human oversight, Contestability, Responsible AI culture
- Status: voluntary (July 2026); mandatory guardrails proposed (PM Albanese July 15 2026 — not yet legislated)
- Use as system-level governance eval checklist

### Australian Privacy Act (APPs 3, 6, 8, 11) — CRITICAL FOR SECOND-BRAIN
- CRITICAL RISK: emails and Teams messages contain client personal information
- APP 3: collection only for primary purpose
- APP 6: no secondary use without consent
- APP 8: cross-border disclosure (if cloud-processed offshore)
- APP 11: security requirements
- Ingesting ALL email risks APP 3/6 breach for client PII
- Eval requirement: PII detection + redaction BEFORE embedding; audit what personal info is stored

---

## Section 10: Australian Court AI Practice Note Timeline (Confirmed as of July 2026)

| Court | Document | Date | Key Requirements |
|-------|----------|------|-----------------|
| Federal Court | GPN-AI | 16 April 2026 | Disclose AI use; accuracy verification; no privileged material in public AI |
| FCFCOA | PD-AI | 29 May 2026 | 6 principles; HARD: no discovery/suppression material in public AI; no AI affidavit content |
| NSW Supreme | PN_SC_Gen_23 | 28 January 2025 | Disclosure; no AI affidavit/witness statement content |
| Victoria Supreme | SC Gen 25 | 14 May 2026 | Replaces 2024; meaningful human verification; ENDORSES purpose-built legal AI |
| QLD Supreme | PD 5/25 | 2025 | AI hallucinations targeted; expert AI disclosure in criminal; applies to QCAT |
| South Australia | Gen AI Guidelines | 1 January 2026 | All SA courts + tribunals; practical ethical vs improper use examples |
| Western Australia | Consultation Note | 2025 (draft) | No binding PD as of July 2026; formal PD expected |

⚠️ AU court AI practice notes changed 5+ times in 18 months (Jan 2025–May 2026). Confirm current version before citing in any deliverable.

---

## Section 11: Multilingual Findings

### Japanese (confirmed real)
- JSAI2025_4I2GS1103 (UEC): Multi-agent prompt injection defense — MCP security eval design
- JSAI2025_3A1GS1003: Agent evaluation in LLM multi-agent scenarios
- METI AI事業者ガイドライン v1.2 (Mar 2026): Japanese XAI guidance (transparency, non-binding)

### Korean (confirmed real)
- AI 기본법 Art. 34 (Law 20676, eff. 2026-01-22, law.go.kr): BINDING statutory explanation duty for high-impact AI; disclosure of "main criteria for AI result" + training-data overview; fine ≤₩30M — not yet AU law but represents direction
- Allganize Korean RAG Leaderboard (blog-ko.allganize.ai/rag-leaderboard/): Legal domain RAG eval in Korean; open dataset

### French (confirmed real)
- HAL hal-05192500: "IA et justice: la voie française" — French AI/justice meta-analysis + magistrates/avocats GenAI deontology opinion (Sept 2025)
- arXiv 2607.24449: RAG for French immigration law — RAG eval methodology reference

### Russian (CyberLeninka, confirmed)
- Khozhainov & Nesterenko (2025): AI agent testing; OWASP LLM Top 10 as first-order QA concern
- Namiot & Ilyushin (2025): Trust in AI via controls-presence audit (interim proxy for outcome guarantees)

### Cross-language convergence (STRONG — EN+KO+RU+JA+FR)
All 5 communities independently identify: accuracy/hallucination = #1 barrier; data security/LPP = #2; strategic judgment = human-only. This is structural.

---

## Section 12: Confirmed Gaps as of July 2026

1. NO AU-specific legal AI eval benchmark. LAUKIN (L9) is the only paper with AU contract data.
2. NO cowork/multi-agent benchmark for legal tasks specifically. Harvey LAB is closest (common-law, but US).
3. NO eval methodology for privileged legal communications in personal second-brain. Novel territory.
4. NO academic paper addresses mosaic disclosure in multi-matter AI memory. Genuinely open gap.
5. NO Australian body has published accuracy thresholds for contract review AI. Operative standard is ASCR Rule 4 (competence) — "good enough to put your firm's name to it."
6. AgentLeak finding: 41.7% of privacy violations invisible in final outputs; only in inter-agent channels. Output-only evals miss nearly half of actual exposure.

---

## Section 13: Recommended Implementation Sequence

### Week 1-2 (pip install, immediate):
```bash
pip install ragas       # team brain faithfulness baseline
pip install deepeval    # contract review regression CI  
pip install trulens     # production monitoring
pip install lrage       # legal-domain RAG eval
git clone github.com/xiaowu0162/LongMemEval  # memory eval
```

### Weeks 3-8 (download + adapt):
- LegalBench-RAG eval on your template/playbook corpus
- MCP-Bench adaptation for legal reasoning MCP tool selection
- Harvey LAB (self-host): primary cowork agentic eval
- LAUKIN eval: AU contract clause equivalence testing

### Months 2-4 (annotation required):
- LegalBench AU tasks (20-30 tasks in Corporations Act, ACL, PPSA format)
- MultiAgentBench milestone KPIs for contract negotiation workflow stages
- MAC-Bench adversarial scenarios from AU contract law playbooks
- MCPSecBench: MCP security + privilege leakage testing
- AgentLeak: inter-agent channel privacy audit

### Legal gates (before production):
- Joint All-States Checklist (Feb 2026) — mandatory gate
- Privacy Impact Assessment (Privacy Act APPs 3/6/8/11)
- LPP risk assessment for second-brain scope + vendor ToS review
- Court disclosure workflow for litigation matters (GPN-AI)
