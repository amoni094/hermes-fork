# Australian Legal AI Regulation — Verified Authority Set (July 2026)

Condensed knowledge bank for fast retrieval. Research date: 29 July 2026.
Source type key: 🔴 Primary law/binding | 🟠 Regulatory guidance | 🟡 Professional guidance | 🔵 Commentary

---

## Court Practice Notes — Complete Table

All currently in force as of July 2026. Breach → potential costs orders, exclusion of evidence, or professional conduct referral.

| Court | Document | Date | URL | Key obligations |
|-------|----------|------|-----|-----------------|
| Federal Court of Australia | **GPN-AI** (Practice Note) | 16 April 2026 | fedcourt.gov.au/law-and-practice/practice-documents/practice-notes/gpn-ai | Disclosure readiness (what tool, how used, how checked); accuracy obligation; confidential/privileged material prohibited in public AI |
| Federal Circuit & Family Court | **PD-AI** (Practice Direction) | 29 May 2026 | fcfcoa.gov.au/pd/pd-ai | 6 principles (Integrity, Accountability, Accuracy, Confidentiality, Safety, Education); affidavit content must express witness's own words; hard prohibition on discovery/suppression-order material in public AI tools (s 5.5) |
| NSW Supreme Court | **PN_SC_Gen_23** | 28 January 2025 | supremecourt.nsw.gov.au — search PN_SC_Gen_23 | GenAI must NOT generate affidavit/witness statement content; disclose AI assistance in court docs |
| Victoria Supreme Court | **SC Gen 25** | 14 May 2026 | supremecourt.vic.gov.au/areas/legal-resources/practice-notes/sc-gen-25-... | Replaces 2024 guidelines; human verification required; AI-generated portions of documents must be identified; explicitly ENDORSES TAR/purpose-built legal AI over general-purpose tools for document review |
| Queensland Supreme Court | **PD 5/25** | 2025 | courts.qld.gov.au/going-to-court/prepare-for-court/representing-yourself/using-generative-ai | AI hallucinations in submissions targeted; expert AI disclosure required in criminal proceedings; applied to QCAT and other tribunals |
| South Australia | **Generative AI Guidelines** | 1 January 2026 | courts.sa.gov.au/2026/01/19/supreme-court-issues-guidelines-for-the-use-of-generative-ai/ | Applies to Supreme, District, Magistrates, Youth, ERD Courts; practical examples of ethical vs improper use |
| Western Australia | Consultation note (draft) | 2025 | supremecourt.wa.gov.au/_files/AI_practice_direction.pdf | Formal PD expected; WA Law Society advocated principles-based approach. No binding WA PD as of July 2026. |

**No ACT, NT, or Tasmania practice notes issued as of July 2026.**

---

## Professional Body Guidance — Key Documents

### Joint 7-State Law Societies — AI Selection & Use Checklist 🟡
- URL: qls.com.au/getmedia/b3bf168b-8374-496a-bfc3-92b0ea0c4296/2026-FINAL-RISK-ASSESSMENT-TOOL-CON-BODS-AI-IN-LEGAL-PRACTICE-CONSULTING-COMMITTEE.pdf
- Date: February 2026; Issuer: QLS, LIV, LSSA, LSWA, ACTLS, LSNT & LST
- **Operative requirements:**
  - PIA (Privacy Impact Assessment) MANDATORY before deploying AI that processes personal information
  - Data security accreditation required: SOC 2, ISO 27001, or ISO 27017
  - Public AI tools: NOT appropriate for confidential client information
  - Jurisdiction: client data stored/processed offshore → APP 8 compliance required
  - AI prompts may not be privileged and may disclose litigation weaknesses
  - Model client disclosure template (Annexure B) provided in the document

### QLS Guidance Statement No. 37 🟡
- URL: qls.com.au/practising-law-in-qld/ethics/guidance-statements/no-37-artificial-intelligence-in-legal-practice
- Date: 31 May 2024; updated 24 October 2024
- ASCR rules engaged: 4, 5, 9, 17, 19, 37 + fiduciary obligations
- **Most detailed professional body guidance in Australia.** Covers competence, confidentiality (data access/use, cybersecurity accreditation, privilege risk, anonymisation), supervision, billing ethics (time billing accuracy; fixed fee preferred for AI work), and client disclosure

### Law Society NSW (LSNSW) 🟡
- Solicitor's Guide (2026): lawsociety.com.au/AI-hub/solicitors-guide-responsible-use-artificial-intelligence
- AI Hub with court protocols cross-jurisdictional index: lawsociety.com.au/AI-hub/court-protocols-ai
- Updated: January 2026

### Joint Regulator Statement (VLSB+C + LSNSW + LPBWA) 🟠
- URL: lsbc.vic.gov.au/news-updates/news/statement-use-artificial-intelligence-australian-legal-practice
- Date: December 2024
- **Key quote:** "Lawyers cannot safely enter confidential, sensitive or privileged client information into public AI chatbots/co-pilots (like ChatGPT) or any other public tools."

### LIV Guidance Note 🟡
- URL: liv.asn.au/download.aspx?DocumentVersionKey=69158983-87f3-4c1d-be99-8c300b5c7afd
- Date: July 2024; Hub: liv.asn.au/aihub

### Law Council of Australia 🟡
- Portal: lawcouncil.au/policy-agenda/advancing-the-profession/artificial-intelligence-and-the-legal-profession
- Aggregates constituent body resources; last updated 3 September 2025; no separate national binding AI standard

---

## Australian Privacy Act — AI-Specific Obligations 🔴

### Applicable APPs for AI systems processing legal correspondence

| APP | Requirement | AI Second-Brain Impact |
|-----|-------------|----------------------|
| APP 3 | Collect PI only if reasonably necessary; lawful & fair means | Email/Teams ingestion must have a specified lawful purpose; AI inference of PI = collection |
| APP 5 | Notify individuals of collection purpose, who receives data, overseas disclosure likelihood | Lawyers AND clients must be notified before email ingestion begins |
| APP 6 | Secondary use/disclosure only: within primary purpose, or reasonable expectation, or consent | AI analysis of email content must align with original collection purpose |
| APP 8 | Cross-border disclosure: take reasonable steps to ensure overseas recipient complies with APPs | Cloud AI with offshore processing triggers full APP assessment |
| APP 11 | Reasonable security of PI | AI system security: encryption, access controls, audit logging |
| APP 13 | Individuals' right to correct PI | AI memory must be correctable |

### OAIC AI Guidance 🟠
1. **Deployers:** oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-the-use-of-commercially-available-ai-products (January 2025)
   - PIA recommended; privacy policy must disclose AI use; human oversight required; AI inference = collection under APP 3
2. **Developers:** oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/guidance-on-privacy-and-developing-and-training-generative-ai-models (October 2024)
   - Using existing correspondence to train/fine-tune AI models requires APP 6 secondary-purpose compliance or consent

---

## Legal Professional Privilege and AI — Current Australian Position 🔴🟡

### Governing principle
LPP (client legal privilege under Part 3.10 Evidence Act 1995 (Cth)) requires confidentiality. Conduct inconsistent with maintaining confidentiality can waive privilege. Assessed **objectively** — inadvertent disclosure can waive. See Glencore [2019] HCA 26: privilege cannot be restored once confidentiality is lost.

### Current judicial statements (first-instance, not binding appellate authority)
1. **Helmold v Mariya (No 2)** [2025] FedCFamC1A 163 — "input of documents arising out of the proceedings into a generative AI program which stores, collates and replicates data **may waive privilege** or fall foul of the requirements that certain matters be treated as commercial in confidence" — court said "extreme caution" required
2. **Mertz v Mertz (No 3)** [2025] FedCFamC1A 222 — "there is a risk that entering draft documents into an AI program will…give rise to a waiver of legal professional privilege"

*Note: Both are first-instance observations. No appellate authority yet. But joint regulator statement (December 2024) reflects regulator consensus: public AI tools create LPP risk.*

### The operative distinction: Public vs Enterprise AI
- **Public/consumer AI** (ChatGPT, Gemini, Claude.ai consumer tier): Terms often permit retention, training, third-party disclosure → LPP confidentiality undermined → privilege at risk
- **Enterprise/closed AI** (contractually closed, no retention/training, enforceable data isolation): Can preserve confidentiality → privilege potentially maintained IF dominant-purpose and lawyer-supervision requirements also met
- **Key vendor contract terms required:** Express prohibition on data retention, model training on inputs, third-party disclosure; encryption; access controls; audit rights; Australian data residency preferred

### Requirements to preserve privilege when using AI
1. Closed enterprise environment (no data leaves controlled perimeter without contractual prohibition on training/retention)
2. Lawyer-directed workflow (AI use on privileged matters directed/supervised by a lawyer in their legal capacity)
3. Dominant purpose (AI analysis for legal advice or litigation, not general business purposes)
4. Per-matter documentation (what AI was used, by whom, at whose direction, for what purpose)
5. Prompt hygiene (prompts revealing litigation strategy/weaknesses may themselves not be privileged)

*Sources: Hall & Wilcox (December 2025) hallandwilcox.com.au/news/beware-of-artificial-intelligence...; Clayton Utz (April 2026) claytonutz.com/insights/2026/april/ai-and-legal-professional-privilege-why-common-workflows-now-carry-uncommon-risk*

---

## eDiscovery / TAR — Australian Legal Framework

### Court approval (binding precedent) 🔴
1. **McConnell Dowell Constructors v Santam** [2016] VSC — First AU endorsement of TAR; found TAR "as accurate, if not more so, than human review, and vastly more efficient" (Justice Vickery)
2. **Money Max v QBE Insurance** VID 513/2015 (Federal Court) — Established TAR **reporting criteria** used in subsequent AU cases; court ordered respondent to explain TAR workflow
3. **SA Uniform Civil Rules (2020)** — Standardised protocols for electronic document exchange; prescribes collection, processing, production

### Victoria SC Gen 25 on TAR (May 2026) — direct judicial endorsement 🟡
"AI, in the form of Technology Assisted Review (TAR), already plays [a significant role] in reducing the time and cost of large-scale document review. Specialised, legally focused AI tools are likely to be more useful and reliable for parties in litigation than general purpose AI tools."

### Discovery material prohibition (FCFCOA PD-AI s 5.5) 🔴
Material produced under court order, under suppression/non-publication orders, or on subpoena **must NOT enter any GenAI tool** unless:
(a) closed environment guaranteed (not accessible to unauthorised third parties); (b) not used for LLM training; (c) used only for the specific proceeding

### Recall/precision standards
- **No Australian court has set a numerical recall threshold.**
- Informal industry norm: **75%+ recall** as minimum defensible threshold (from Grossman-Cormack research and EDRM TAR framework)
- Money Max: established reporting requirements (describe system, training methodology, validation protocol with statistical sampling, recall/precision estimates with confidence intervals) — no numerical floor set
- TAR 2.0/CAL (Continuous Active Learning) preferred over TAR 1.0 for higher recall and auditability

### Required TAR disclosures in Australian proceedings (from Money Max reporting criteria)
1. TAR software/system used
2. Training seed set methodology
3. Validation protocol (statistical sampling)
4. Recall and precision estimates with confidence intervals
5. QC steps applied
6. Expert data scientist involvement (courts value this)

---

## Contract AI — No Australian Standards Exist

⚠️ **Confirmed gap:** No Australian court, law society, or regulator has published accuracy benchmarks for contract review AI. The operative Australian standard is ASCR Rule 4 (competence) — practitioner must have sufficient skill to detect errors in AI output.

### International benchmarks applicable to AU (from WCC/IACCM + Forrester TEI studies)
- **Playbook coverage ceiling:** 70–80% of clause changes fall within a well-designed playbook (WCC annual benchmarking)
- **Autonomous resolution rate (mature deployment):** 50–75% of clause changes (vendor TEI, WCC)
- **Cycle time reduction (steady-state):** 30–50% (Forrester TEI studies; selection-biased — successful implementations only)
- **Negotiations rounds eliminated:** 1–2 rounds per typical 3–5 round commercial deal
- **Lawyer hour reduction on routine clauses:** 50–70% in mature deployments

### Pilot baseline metrics to capture pre-deployment
1. Average contract cycle time (request to signature)
2. Average negotiation rounds per contract
3. Lawyer hours per contract on routine work
4. Percentage of contracts requiring escalation
5. Error rate on standard clauses (sampled)
6. Contract volume per FTE

*Source: bindlegal.com/resources/best-software/ai-contract-negotiation-benchmarks-2026/ (May 2026)*

---

## Government AI Framework 🟠

### Voluntary AI Safety Standard (VAISS)
- URL: industry.gov.au/publications/voluntary-ai-safety-standard
- Date: 5 September 2024; Issuer: National AI Centre, DISR
- Status: VOLUNTARY for private sector; 10 guardrails
- 10 Guardrails: (1) Accountability, (2) Transparency, (3) Risk identification, (4) Data governance, (5) Robust testing, (6) Incident response, (7) Privacy protection, (8) Human oversight, (9) Contestability, (10) Responsible AI culture

### AS ISO/IEC 42001:2023 — AI Management System
- Adopted by Standards Australia: February 2024
- Status: VOLUNTARY, certifiable (JAS-ANZ accredited certification bodies)
- 38 controls, 9 categories (policies, internal org, resources, impact assessment, lifecycle, data, transparency, use/oversight, third-party relationships)
- Maps to VAISS 10 guardrails; complements ISO 27001 (Annex D)
- Source: standards.org.au/news/standards-australia-adopts-the-international-standard-for-ai-management-system-as-iso-iec-42001-2023

### Mandatory AI legislation — announced but not yet law
- PM Albanese announced (15 July 2026): plans to legislate Australian Standards for AI; established Office of AI in Department of PM and Cabinet. **Legislation not passed as of research date.**

---

## ASCR Rules Engaged by AI Use 🔴

| Rule | What it requires | AI application |
|------|-----------------|----------------|
| 4 | Best interests, competence | Must understand AI tool limitations; must detect errors in output |
| 5 | Honesty and integrity | Cannot allow AI to mislead court/counterparty |
| 7 | Paramount duty to court | Cannot file AI-hallucinated citations or fabricated authorities |
| 9 | Confidentiality | Must protect client information; tool selection must maintain confidentiality |
| 17 | Supervision | Must properly supervise staff AI use |
| 19 | Dealing with opposing parties | No AI-generated misleading communications |
| 37 | Management systems | Firm must have AI governance policy |

*Source: QLS Guidance Statement No. 37 (May 2024, updated October 2024)*

---

## Enforcement Precedent 🔴 AU-first

**First Australian disciplinary sanction for AI hallucination (August 2025):** A Victorian solicitor lost the ability to practise as a principal, handle trust money, and operate their own practice after submitting fictional AI-generated cases to the FCFCOA.
*(Source: VLSB+C 2025 Victorian Lawyer Census, April 2026, citing Taylor, The Guardian, 3 September 2025)*

---

## Key Gaps (as of July 2026)

| Gap | Status |
|-----|--------|
| Contract review AI accuracy thresholds | No AU standard; ASCR Rule 4 competence is operative test |
| Email/Teams ingestion compliance framework for legal AI | No specific guidance; Privacy Act + professional duty applies |
| Multi-lawyer team AI systems (shared memory) | No guidance from any AU body |
| eDiscovery AI numerical recall floor | No AU court has set a number; 75% informal norm from international practice |
| WA binding practice direction | Expected; not issued as of July 2026 |
| AI agent liability allocation | No AU guidance; supervisor lawyer bears full professional responsibility |

---

## Adoption Statistics (Victoria, 2025) 🔵

*Source: VLSB+C 2025 Victorian Lawyer Census (April 2026)*
- 36.7% of Victorian lawyers use AI tools in practice
- Barristers: 14.6% (lowest); Government lawyers: 11.2%
- In-house/non-legal employers: 53.9% (highest)
- 64.8% use general-purpose tools (ChatGPT, Claude, Gemini, Copilot)
- 88.7% of users take steps to verify accuracy
- **60% had NOT read the relevant court AI guidelines** (including ~half of AI users)
- 95.5% agree lawyers have a duty to ensure AI use complies with professional obligations
- Workplace AI guidelines existed for only 42% of respondents

---

*Research date: July 29, 2026. Verify practice notes for any subsequent amendments before relying on them.*
