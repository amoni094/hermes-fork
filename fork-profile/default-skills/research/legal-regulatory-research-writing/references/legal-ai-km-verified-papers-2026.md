# Verified Legal AI & Knowledge Management Papers — July 2026

All arXiv IDs confirmed against live abstracts July 21 2026.
Flags: ✅ live-verified | ⚠️ partially verified (abstract/snippet only) | ❌ do not cite

---

## Legal NLP & Information Extraction

### CUAD Dataset — Contract Clause Extraction
- **Citation:** Hendrycks et al. (2021). CUAD: An Expert-Annotated NLP Dataset for Legal Contract Review. arXiv:2103.06268 ✅
- **What it shows:** Expert-annotated benchmark covering 41 clause types across 510 commercial contracts. F1 scores 85–95% for well-defined clause types (termination, limitation of liability, governing law) in standard commercial contracts; lower for non-standard drafting.
- **Key use:** Accuracy ground-truth for auto-extraction claims. Do NOT round up to "near-perfect" for non-standard or multi-jurisdictional documents.

### ContractNLI — Contract Natural Language Inference
- **Citation:** Koreeda & Manning (2021). ContractNLI: A Dataset for Document-level Natural Language Inference for Contracts. arXiv:2110.01799. Accepted EMNLP 2021 Findings. ✅
- **What it shows:** NLI task for contracts (entailment / contradiction / neutral for hypothesis-vs-contract). 607 annotated contracts; strong baseline using multi-label span classification.
- **Key use:** Supports "clause-level understanding" claims. Stronger evidence for structured inference than CUAD (which is classification, not inference).

### Legal IE Survey — NER/RE/Event Detection Across Jurisdictions
- **Citation:** Premasiri, Ranasinghe et al. (2025). Survey on legal information extraction: current status and open challenges. *Knowledge and Information Systems* 67:11287–11358. DOI:10.1007/s10115-025-02600-5. Open access CC BY 4.0. ✅
- **What it shows:** Comprehensive review of NER, RE, and event detection in legal text across multiple jurisdictions and languages. NER in contracts is most mature; RE less so; event detection least mature. Multi-jurisdictional NLP remains a significant open challenge.
- **Key use:** Ground-truth for "what AI can and cannot extract from legal work product" claims.

### Legal NLP Survey — 131 Papers (ACM Computing Surveys)
- **Citation:** Ariai, Mackenzie, Demartini (2024/2025). Natural Language Processing for the Legal Domain: A Survey of Tasks, Datasets, Models, and Challenges. ACM Comput. Surv. 58(6):163. arXiv:2410.21306. DOI:10.1145/3777009. ✅
- **Institution:** University of Queensland, Australia.
- **What it shows:** PRISMA review of 154 studies (131 after filtering). Document summarisation for legal texts near-production quality for structured court decisions; less mature for internal work product (memos, opinions, drafts). Domain-adapted models (LegalBERT, CaseLaw-BERT) consistently outperform general models.
- **Key use:** Confirms auto-extraction works well for public structured documents, requires domain adaptation for internal/proprietary work product.

### IRAC Structured Extraction with Hallucination Control
- **Citation:** Piccioli, Fidelangeli, Santin, Vivo (2026). From Judgments to Issues: Structured Extraction of Legal Reasoning with Citation-Hallucination Control. arXiv:2607.03325. Submitted July 3 2026. ✅
- **What it shows:** Automated pipeline extracting Italian tax court judgments (~330,000 decisions) into IRAC-structured XML with a hallucination-detection filter (Linkoln citation parser comparing AI extractions against normalised URN-NIR/ECLI/CELEX IDs). Validated on 50 judgments by two PhD-level tax lawyers.
- **Key use:** THE academic basis for (a) IRAC as the right knowledge card structure; (b) citation-grounding as the correct hallucination-control mechanism. "First expert-validated, issue-level structured extraction pipeline with hallucination control."

### FineREX — Domain Fine-Tuning for NER/RE
- **Citation:** Feldman, Meher, Domeniconi (2026). FineREX: Fine-Tuned NER-RE for Human Smuggling Knowledge Graphs. arXiv:2606.19710. ✅
- **Institution:** George Mason University / IBM.
- **What it shows:** With 512 annotated examples: +15.5% entity F1, +31.46% relationship F1 vs. larger general-purpose baseline; 50% processing time reduction; node duplication 17.78%→11.17%.
- **Key use:** Empirical basis for "modest annotation investment produces large accuracy gains" argument. The 512-example figure is the specific calibration point.

---

## Knowledge Graph Architectures

### GraphRAG — Tiered Community Hierarchy (Microsoft)
- **Citation:** Edge et al. (10 authors) (2024). From Local to Global: A Graph RAG Approach to Query-Focused Summarization. arXiv:2404.16130. v2 Feb 2025. ✅
- **Institution:** Microsoft Research.
- **What it shows:** Two-stage KG construction → hierarchical community summaries mapping entity → cluster → community → corpus. Substantial improvements over conventional RAG on global sensemaking over 1M-token corpora.
- **Key use:** The open-source implementation (microsoft.github.io/graphrag) of a tiered hierarchy that directly maps to personal→team→department. **Deployable today.**

### LegalGraphRAG — Hierarchical Legal Graph with Multi-Agent Verification
- **Citation:** Chen, Zhang, Xiang, Wei, Gao, Huang, Zhang, Su (2026). LegalGraphRAG: Multi-Agent Graph Retrieval-Augmented Generation for Reliable Legal Reasoning. arXiv:2605.28120. **Accepted ACL 2026 Main Conference.** ✅
- **Institution:** Xiamen University (XMUDeepLIT).
- **What it shows:** Hierarchical legal graph (factual → applied rules → abstract principles) with three-agent system (Researcher → Auditor → Adjudicator). State-of-the-art on legal reasoning tasks. Code: github.com/XMUDeepLIT/LegalGraphRAG.
- **Key use:** Legal-domain-specific validation of the three-tier architecture (factual → rule → principle = clause/position → team standard → department policy). The Auditor agent's function = the safety gate/human review function.

### Falkor-IRAC — Falsifiability Oracle for Legal Knowledge Cards
- **Citation:** Bose (2026). Falkor-IRAC: Graph-Constrained Generation for Verified Legal Reasoning in Indian Judicial AI. arXiv:2605.14665. ✅
- **What it shows:** Ingests judgments as IRAC node structures in FalkorDB. "Falsifiability Oracle" — LLM answers only accepted if a valid supporting path can be traced through the graph. Detects doctrinal conflicts as a first-class output. Validated on 51 Supreme Court judgments.
- **Key use:** Production-grade hallucination control architecture. "A card is only promoted if a valid path can be traced through the knowledge graph to the source document." Also: conflict detection between teams/positions.

### ComplianceNLP — Strongest Quantified ROI Evidence (ACL 2026)
- **Citation:** Guo, Wu, Yiu (2026). ComplianceNLP: Knowledge-Graph-Augmented RAG for Multi-Framework Regulatory Gap Detection. arXiv:2604.23585. **Accepted ACL 2026 Industry Track.** ✅
- **Institution:** University of Hong Kong.
- **What it shows:** 4-month real deployment at a financial institution: **3.1× analyst efficiency gain**; 96.0% recall, 90.7% precision; 9,847 regulatory updates processed; F1 87.7 on gap detection (+3.5 vs GPT-4o+RAG); KG re-ranking = +4.6 F1 (single largest improvement factor).
- **Key use:** THE strongest peer-reviewed quantified benefit figure for legal/regulatory AI KM. Use as the primary ROI anchor; it is real deployment data, not survey extrapolation.

### Zep / Graphiti — Temporal Knowledge Graph for Agent Memory
- **Citation:** Rasmussen et al. (2025). Zep: A Temporal Knowledge Graph Architecture for Agent Memory. arXiv:2501.13956. ✅
- **Institution:** Zep AI (commercial research).
- **What it shows:** Temporally-aware hierarchical KG. 94.8% vs 93.4% on DMR benchmark vs MemGPT; up to 18.5% accuracy improvement + 90% latency reduction on LongMemEval. Graphiti synthesises conversational and structured data while maintaining historical relationships.
- **Key use:** Closest existing open-source system to a legal knowledge brain architecture. Provides temporal tracking (what position was correct when), hierarchical memory, and cross-session synthesis. Open source: github.com/getzep/graphiti.

---

## Passive/Zero-Effort Knowledge Capture

### DySECT — Closed-Loop Passive Knowledge Extraction (ACL 2026 Demo)
- **Citation:** Amin-Naseri, Kim, Hruschka (2026). A Dynamic Self-Evolving Extraction System. arXiv:2603.06915. Accepted ACL 2026 Demo Track. ACL:2026.acl-demo.69. ✅
- **What it shows:** DySECT = closed-loop: LLM extracts → populates KB → KB enriches via graph reasoning → feeds back to improve extraction. Explicitly names legal as a target domain. Continual improvement with no manual re-annotation. Three feedback modes: prompt tuning, few-shot sampling, fine-tuning on KB-derived synthetic data.
- **Key use:** Closest academic analogue to the "zero-effort passive capture" model. The closed-loop self-improvement = quality increases as more work product flows through.

---

## Leaver Knowledge Capture & Expert Finding

### Schmitt & Borzillo — Leaver Knowledge Loss (Definitive Meta-Analysis)
- **Citation:** Schmitt & Borzillo (2023). Knowledge loss from employee turnover. *The Learning Organization* 30(2):117. ⚠️ (confirmed via secondary sources; paywall blocks direct access)
- **What it shows:** Systematic review of 91 empirical studies. Key findings: (a) structured exit interviews/documentation sprints capture only EXPLICIT knowledge — tacit knowledge (how to handle a specific regulator, how a panel firm partner actually works) is not captured; (b) knowledge transfer initiated >2 weeks before departure has significantly lower retention; (c) decision-rationale documentation is the highest-value but hardest-to-capture element.
- **Key use:** Calibration for leaver-capture system design. Automated digest captures explicit knowledge only. Tacit dimension requires structured interview/handover template alongside the automation.

### Balog et al. — Expert Finding (Definitive Survey)
- **Citation:** Balog et al. (2012). *Foundations and Trends in Information Retrieval* 6(2-3):127-256. Open access. ✅
- **What it shows:** Definitive survey on expert finding. Document-centric implicit signals consistently outperform self-declared expertise profiles. Only 55% of professional service employees can locate expertise with current systems; >50% need to daily.
- **Key use:** Academic validation for "who-knows-what" routing. The 55% figure quantifies the problem being solved.

---

## Industry Surveys (Not Peer-Reviewed; Treat as Practitioner Evidence)

### Thomson Reuters 2025 GenAI in Professional Services (n=1,700+)
- GenAI adoption in law: 28% of firms (vs 14% 2024); 23% of corporate legal depts.
- **5 hours per week saved per AI-using lawyer** (240 hrs/year) — the most-cited industry efficiency figure.
- 95% expect GenAI central to daily workflow within 5 years. Only 20% measure ROI.
- Source: thomsonreuters.com/en/reports/2025-generative-ai-in-professional-services-report ✅

### ACC/Everlaw 2025 In-House Legal AI Survey (n=657)
- Active GenAI use: 52% (2025) vs 23% (2024) — more than doubled in one year.
- Policy prohibition as barrier: collapsed from 29% (2024) → 9% (2025).
- Remaining barriers: governance (only 41% have AI policies), training, ROI measurement (only 20%).
- Source: ACC/Everlaw joint survey 2025 ⚠️ (cited in secondary sources; primary report not directly extracted)

### Harvey AI Blog — "Fundamentals of Legal Knowledge Management" (June 2026)
- Vendor blog, not peer-reviewed. Practitioner evidence only.
- "Attorneys at Tiang and Partners save more than 10 hours per week" — vendor case study, not independently audited.
- Source: harvey.ai/blog ⚠️ vendor/commercial

---

## Verified Product Names (Legal Tech)

These are the REAL names. Do not use the fabricated alternatives.

| Vendor | REAL product name | Fabricated names to reject |
|---|---|---|
| LexisNexis | **Lexis+ AI** (AU: lexisnexis.com/en-au/products/lexis-plus-ai) | ~~Lexis+ Protus~~ |
| Thomson Reuters | **Westlaw Edge**, **Westlaw Advantage**, **CoCounsel Legal** | ~~Westlaw Precision~~ |
| iManage | **iManage Knowledge Unlocked, powered by RAVN** | ~~iManage RAVN/Insight~~ |
| Thomson Reuters | **Harvey** (separate company, not TR) | — |
| Luminance | **Luminance** | — |
| EvenUp | **EvenUp** — plaintiff personal injury ONLY; not a KM competitor | ~~General legal AI~~ |

Verification method: `web_search("\"<exact product name>\" site:<vendor domain>")` — if vendor's own site doesn't list it, it's fabricated.

---

## Verified Case Law — AI + Legal Privilege

| Case | Jurisdiction | Year | Key holding | Verification status |
|---|---|---|---|---|
| *Baker v Campbell* (1983) 153 CLR 52 | Australia (HCA) | 1983 | LPP is a fundamental common law right | ✅ established |
| *United States v Heppner* (SDNY) | USA | 2026 | Privilege rejected over AI-processed docs where confidentiality not contractually protected | ⚠️ cited by Hamilton Locke, Clayton Utz Apr 2026; primary judgment not extracted |
| *Warner v Allstate* | USA | 2025 | Similar to Heppner — confidentiality not preserved | ⚠️ secondary only |
| *Munir v Munir* (UK Family Court) | UK | 2025 | Privilege rejected where AI tool processed communications without contractual confidentiality | ⚠️ secondary only |

**Federal Court of Australia GPN-AI Practice Note** — governs AI use in FCA proceedings. Confirms privilege analysis for AI systems turns on whether confidentiality is contractually protected in the enterprise service agreement. ✅ Current official guidance.

---

## Jurisdiction-Specific Compliance Requirements (Pre-Deployment Checklist)

For AI-powered knowledge management systems in legal departments:

1. **GDPR Art. 35 DPIA — Mandatory (EU/UK):** Data Protection Impact Assessment required before deploying any system that systematically processes employee personal data at scale. Not optional. Brain service qualifies as high-risk processing. Must precede Phase 1.

2. **Australian Privacy Act APP 6 — Secondary-Use Legal Basis Required:** Matter work product is personal information. Using it for organisation-wide KM is a secondary use requiring either consent or a statutory exception. Legal basis analysis required before deployment.

3. **NSW Workplace Surveillance Act 2005 — 14-Day Written Notice:** Always-on document capture likely constitutes computer surveillance in NSW. Written notice required 14 days before activation. Hard compliance requirement for NSW-based teams; not a communication preference.

4. **German §203 StGB + §43e BRAO — Criminal Liability:** Professional secrecy laws impose criminal-law technical-access controls beyond GDPR. GDPR compliance alone is insufficient for German-licensed lawyers. Architecture must satisfy these controls.

5. **JFBA (Japan Bar Federation) 2025/2026 Guidance:** AI input treated as external transmission subject to professional secrecy obligations. Check if panel firms or counterparties have Japan-qualified lawyers.

---

*Compiled July 21 2026 from parallel multilingual research sweep. All arXiv IDs live-verified against arxiv.org abstract pages. Product names verified against vendor sites. Case citations flagged where only secondary verification available.*
