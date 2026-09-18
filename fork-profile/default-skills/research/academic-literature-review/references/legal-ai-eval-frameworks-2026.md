# Legal AI Evaluation Frameworks — Verified Paper Bank (July 2026)

**Research session:** 2026-07-29  
**Task context:** AI evaluation frameworks for a legal AI cowork system with multi-agent architecture, MCP skill sets, personal second-brain, team brain MCP server. Primary use case: contract negotiation (AU jurisdiction).  
**Output file produced:** `/tmp/legal_ai_evals_sweep_1.md`

---

## Quick-Reference Table (verified via web_extract or web_search)

| ID | arXiv / URL | Title | Year | Task Type | Key Metric | AU? |
|----|-------------|-------|------|-----------|------------|-----|
| LB-01 | arXiv:2308.11462 | LegalBench | 2023 | 162 legal reasoning tasks (6 types) | Exact-match (HELM) | No |
| HLB-01 | github.com/harveyai/biglaw-bench | BigLaw Bench (Core/Workflows/Retrieval) | 2025 | Transactional + Litigation, SPA deal points, Discovery | % lawyer-quality work | No |
| HLB-02 | github.com/harveyai/harvey-labs | Harvey LAB (Legal Agent Benchmark) | 2026 | 1,671 agentic tasks, 24 practice areas | All-pass rate; per-criterion accuracy | Partial |
| CE-01 | arXiv:2508.03080 | ContractEval (CUAD-based) | 2025 | Clause-level risk, 4 prop + 15 OSS LLMs | Correctness + output effectiveness | No |
| LA-01 | github.com/CSHaitao/LegalAgentBench | LegalAgentBench | 2024 | 300 tasks, 37 tools, multi-hop | Final success rate + process rate | No |
| J1-01 | arXiv:2507.04037 | J1-Bench / Ready Jurist One | 2025 | Dynamic interactive legal env, 6 scenarios | Task + procedural compliance | No |
| MAD-01 | arXiv:2606.30906 | Multi-Agent Deliberation in Law | 2026 | MAD for legal reasoning (ICAIL 2026) | Accuracy vs single LLM baseline | No |
| MAC-01 | arXiv:2606.07805 | MAC-Bench | 2026 | Multi-agent compliance, adversarial pressure | CSR + Machiavellian Gap | No |
| POI-01 | arXiv:2606.02282 | POIROT | 2026 | MAS failure detection; BLAME benchmark | OR=1.60, p=0.008 | No |
| AGK-01 | arXiv:2602.11510 | AgentLeak | 2026 | Privacy leakage in multi-agent LLM (IEEE Access) | 68.8% inter-agent leakage | No |
| PART-01 | arXiv:2606.04602 | Parthenon Law | 2026 | Self-evolving legal agent; 12,510 Harvey LAB trajectories | Per-criterion accuracy; all-pass | No |
| GAVEL-01 | arXiv:2601.04424 | Gavel | 2026 | Long-context legal summarization; 12 frontier LLMs | Checklist + factual coverage | No |
| LAUKIN-01 | arXiv:2606.13184 | LAUKIN | 2026 | **AU/UK/IN** contract clause equivalence | Macro-F1 65.11% | **YES** |
| BADGER-01 | arXiv:2606.02109 | BADGER | 2026 | Enterprise agentic reasoning eval | Cohen's κ=0.717 | No |
| OAM-01 | arXiv:2607.13157 | Oracle Agent Memory | 2026 | Enterprise memory substrate eval | LongMemEval 93.8%; 10.7x fewer tokens | No |
| DLAWB-01 | arXiv:2606.13931 | DLawBench | 2026 | Multi-turn legal consultation, 461 cases | Best GPT-5.5 = 0.562 | No |
| LEXRUB-01 | arXiv:2606.09389 | LexRubric | 2026 | Open-ended Chinese legal tasks, 649 instances | 6-dim rubric score | No |
| BENGER-01 | arXiv:2605.28183 | BenGER | 2026 | German law subsumption, 596+531 tasks | Pearson r=0.76, κ=0.60 LLM judge | No |
| TWLB-01 | arXiv:2606.18699 | TW-LegalBench | 2026 | Taiwanese law MCQ+OEQ+LJP | Accuracy; LLM-as-Judge rubric | No |
| PWORK-01 | arXiv:2607.06008 | PolyWorkBench | 2026 | Multilingual workplace workflows incl. legal | Task accuracy + linguistic consistency | No |
| RAG-FR-01 | arXiv:2607.24449 | RAG French Immigration Law | 2026 | RAG for legal QA (ECML-PKDD 2026) | Permit-type accuracy | No |
| LLMF-01 | arXiv:2605.31167 | LLM-FACETS | 2026 | Privacy-preserving LLM eval (RAG Triad) | Faithfulness, Relevance, Context Rel. | No |
| MAS-LAB | arXiv:2606.30546 | MAS-Lab | 2026 | Spec-driven validation for MAS | Automated spec compliance | No |

---

## Key GitHub Repos

| Repo | Stars | Notes |
|------|-------|-------|
| harveyai/harvey-labs | 566 | Harvey LAB: harness + 1,671 tasks, MIT license, open |
| harveyai/biglaw-bench | 173 | BigLaw Bench Core/Workflows/Retrieval; full dataset by request |
| HazyResearch/legalbench | ~2,000 | 162 tasks, HELM-compatible, HuggingFace: nguha/legalbench |
| Vaquill-AI/awesome-legaltech | 176 | Curated registry; MCP servers for legal (vaquill-mcp, courtlistener-mcp, canlii-mcp) |
| CSHaitao/LegalAgentBench | 49 | 300 agentic Chinese legal tasks |
| FudanDISC/J1Bench | 14 | ACL 2026; interactive Chinese legal environments |
| leonardeee/MAC-Bench | N/A | Multi-agent compliance adversarial benchmark |
| Privatris/AgentLeak | ~50 | Privacy leakage benchmark, legal domain included |
| SebastianNagl/benger-platform | N/A | BenGER German legal benchmark |
| SKYLENAGE-AI/DLawBench | N/A | Multi-turn legal consultation benchmark |
| CSHaitao/LexEval | ~200 | Chinese legal LLM eval (NeurIPS 2024) |
| open-compass/LawBench | ~500 | LawBench Chinese legal knowledge |

---

## AU-Specific Finding: LAUKIN

**Only confirmed AU contract dataset as of July 2026.**

- arXiv:2606.13184, Singh et al., June 2026
- 14,727 clause pairs from 204 contracts × 8 agreement types
- Jurisdictions: AU–UK, UK–IN, IN–AU clause equivalence pairs
- Labels: Equivalent / Not Equivalent (boolean), 3,000 manually annotated by legal experts
- Best: Macro-F1 65.11% (challenging benchmark)
- 11,727 unlabelled pairs for semi-supervised learning
- Key finding: AU and UK drafting conventions diverge significantly despite shared heritage

**Zero other AU legal AI benchmarks found on arXiv.** This is a critical gap.

---

## arXiv Search Results Summary

Queries that produced results:
- `LLM evaluation legal reasoning benchmark` → 116 results (top results: PolyWorkBench, MAD, LexRubric, LegalReasoningBenchmarks, DLawBench)
- `multi-agent evaluation legal tasks` → 28 results (top: Messier, MAD, MAC-Bench, Agentic GraphRAG, JurisCQA, Sabiá-4)
- `RAG evaluation legal domain` → 60 results (top: RAG French immigration, AILQA, Nepali RAG, LLM-FACETS)
- `AI agent evaluation methodology enterprise` → 13 results (top: Oracle Agent Memory, Data Leakage, BADGER, Constrained Process Maps, LegalOne)
- `legal NLP evaluation benchmark Australia` → **1 result** (LAUKIN)

Queries that returned 0:
- `legal AI evaluation benchmark contract negotiation` → 0
- `contract AI accuracy evaluation CUAD` → 0
- `法律大模型评测` (Chinese) → 0 (arXiv does not index CJK queries)

---

## Non-English Coverage

### German ✅
- BenGER arXiv:2605.28183 — verified, open access
- GradeLegal arXiv:2605.21076 — verified (automated grading German legal exams, QWK up to 0.91)

### French ✅
- RAG French Immigration Law arXiv:2607.24449 — verified, ECML-PKDD 2026
- TALN 2024/2025/2026: no specific legal AI evaluation paper confirmed (TALN conference proceedings checked via dblp; no legal benchmarks found)

### Chinese ✅ (via English arXiv)
- DLawBench arXiv:2606.13931 — verified (Chinese + US law)
- LexRubric arXiv:2606.09389 — verified (Chinese legal tasks)
- J1-Bench arXiv:2507.04037 — verified (ACL 2026)
- LegalAgentBench github.com/CSHaitao/LegalAgentBench — verified
- Chatlaw arXiv:2306.16092 — verified (journal version 2026, RA-MoE multi-agent)
- CNKI/Wanfang: paywalled — not accessed

### Japanese ❌ (access barrier)
- CiNii search: no peer-reviewed Japanese legal AI evaluation papers surfaced
- Japanese practitioner commentary confirms high AI adoption (79% legal professionals using AI per Clio 2025) but no benchmark papers
- J-STAGE: would require targeted search — not confirmed via available tools

### Korean ⚠️ (partial)
- KoBLEX benchmark (Korean statutory multi-hop LQA) referenced in arXiv:2605.24454 (Lee et al., "Decompose-and-Refine")
- RISS: requires login for full text; no metadata search completed

---

## Practitioner/Industry Context

- **Harvey LAB Leaderboard:** artificialanalysis.ai/evaluations/harvey-lab-aa — live model rankings on legal agent tasks
- **Vals.ai:** vals.ai/benchmarks/hlab — curated Harvey LAB model comparisons
- **Vaquill MCP servers:** vaquill-mcp (US law), canlii-mcp (Canadian law) — closest analog to AustLII MCP
- **Harvey AI ARR:** ~USD 280M ARR (2026), evaluation ~USD 1.1T
- **Industry adoption:** 79% of legal professionals using AI (Clio 2025); 26% using GenAI actively (Thomson Reuters 2025)

---

## Gaps for Legal AI Cowork System (AU)

1. **No AU-specific contract negotiation evaluation dataset** — LAUKIN is the only AU contract dataset (clause equivalence only, not negotiation dynamics)
2. **No MCP skill-set evaluation framework** — MAC-Bench SERV pipeline is closest (synthesizes scenarios from legal policy texts)
3. **No multi-agent cowork eval for transactional law** — Harvey LAB + Parthenon are best available architecturally
4. **No personal second-brain evaluation protocol** — Oracle Agent Memory (OAM-01) provides methodology; no legal-specific variant exists
5. **No AU discovery/e-discovery benchmark** — BigLaw Bench Retrieval (Discovery Emails) is US-only
6. **No RAG eval over private legal playbooks/templates** — LLM-FACETS provides framework; no existing dataset
7. **Japanese/Korean peer-reviewed legal AI benchmarks not confirmed** — access barriers prevent verification

---

## Implementation Priority for Legal Cowork System

| Priority | Action | Based On |
|----------|--------|----------|
| 1 | Harvey LAB as primary agentic eval (MIT, self-hostable) | HLB-02 |
| 2 | BigLaw Bench for practitioner task coverage (Negotiation Strategy, SPA, Discovery) | HLB-01 |
| 3 | Build AU contract eval tasks using LAUKIN format | LAUKIN-01 |
| 4 | LegalBench CUAD/contract subset for clause-level eval | LB-01 |
| 5 | AgentLeak protocol for privacy/confidentiality audit (legal domain explicitly included) | AGK-01 |
| 6 | MAC-Bench SERV pipeline with AU legal policy texts | MAC-01 |
| 7 | LLM-FACETS for RAG quality (self-hosted, compliance officer profile) | LLMF-01 |
| 8 | Oracle Agent Memory metrics for second-brain eval | OAM-01 |
| 9 | MAD-01 framework (courtroom-inspired MAD) for cowork eval design | MAD-01 |
| 10 | Parthenon Law (skills/playbooks self-evolving) as architecture reference | PART-01 |
