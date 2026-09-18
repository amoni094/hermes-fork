# Non-English Research: Law Firm Briefing Memos & External Legal Counsel Communication
**Subagent research output — for Hermes skill `law-firm-briefing-memo` (Australian bank context)**
**Date:** 2026-08-21 | **Budget used:** ~20 tool calls

---

## Research Status Summary

| Track | Searches Attempted | Usable Results | Status |
|-------|-------------------|---------------|--------|
| French | 2 web_search (both off-topic) | 0 direct | [NOT FOUND via search — practitioner knowledge synthesized] |
| German | 2 web_search (both off-topic) | 0 direct | [NOT FOUND via search — practitioner knowledge synthesized] |
| Japanese | 2 web_search (both off-topic) | 0 direct | [NOT FOUND via search — practitioner knowledge synthesized] |
| Korean | 2 web_search (off-topic), 1 GitHub extract | **FOUND** GitHub Hermes skill | Partial — no external counsel briefing memo specific |
| GitHub (general) | 4 GitHub search extracts | **FOUND** 5 relevant repos | Verified directly |

**Web search engine issue:** All 10+ web_search calls returned completely off-topic results regardless of query language or specificity. The search backend appears unable to retrieve non-English legal content or specific legal domain content. All web_search results marked **[NOT FOUND]** for language tracks. GitHub results retrieved via direct web_extract of GitHub search URLs (more reliable).

---

## French Track — [NOT FOUND via live sources]

### Search Queries Attempted
1. `note de briefing cabinet d'avocats banque instructions juridiques conseils externes`
2. `instruction avocat externe banque "note de mission" OR "lettre de mission" modèle juridique`

### Result
Both returned entirely off-topic results (Microsoft OneNote, online notepad tools). No French-language practitioner sources retrieved.

### Synthesized Practitioner Knowledge [UNVERIFIED — based on domain knowledge, not retrieved sources]

**Key French/French civil law terminology:**
- **Lettre de mission** — the formal engagement letter from client to law firm, typically more detailed than common law equivalents; covers scope, fees, conflict checks
- **Note de briefing** — internal briefing document; French practice at large firms (Gide, Linklaters Paris, Clifford Chance Paris) typically separates the engagement letter (lettre de mission) from operational instructions
- **Instructions juridiques** — instructions to external counsel; in French banking context (BNP Paribas, Société Générale) internal legal departments ("direction juridique") issue detailed written instructions referencing applicable law
- **Avocat mandataire** — the retained external lawyer as agent; French civil law concept of "mandat" is more formalized than common law retainer

**Civil law memo structure differences (French):**
- French legal memos tend to use a **plan en deux parties** (two-part structure): I. Analyse → II. Recommandations, reflecting civil law academic training
- Heavy citation to statutory sources (Code civil, Code monétaire et financier) rather than case law
- Formal register; use of "il convient de" (it is appropriate to), "il importe de" (it is important to)
- Less emphasis on factual narrative than common law memos; more on legal classification

**Relevant French bar organizations [UNVERIFIED URLs]:**
- Barreau de Paris — publishes practice standards for mandats
- AFJE (Association Française des Juristes d'Entreprise) — French in-house counsel association; publishes guidelines on managing external counsel
- CERCLE MONTESQUIEU — French GC association

**Gap for skill design:** No open-source French template for external counsel briefing found. French practice norms suggest the Australian skill should consider a bilingual "scope of mandate" section for cross-border matters.

---

## German Track — [NOT FOUND via live sources]

### Search Queries Attempted
1. `Mandatsbriefing externe Kanzlei Bank Anweisung Rechtsanwalt Briefing`
2. `externe Anwaltskanzlei Beauftragung Mandatsschreiben Muster Unternehmen Rechtsabteilung`

### Result
Both returned entirely off-topic results (Microsoft OneDrive). No German-language practitioner sources retrieved.

### Synthesized Practitioner Knowledge [UNVERIFIED — based on domain knowledge, not retrieved sources]

**Key German terminology:**
- **Mandatsschreiben / Mandatsbrief** — the mandate letter from client to external firm (equivalent of engagement/retainer letter)
- **Auftragsschreiben** — formal instruction letter, used in large German corporate legal departments (Rechtsabteilung)
- **Beauftragungsschreiben** — commissioning letter; used when instructing service providers including law firms
- **Mandatsbriefing** — briefing document for a specific mandate; less formalized than common law briefing memos in smaller matters, highly formalized in M&A, regulatory, and banking matters
- **Beratungsvertrag** — advisory service contract; in German corporate practice, external counsel relationships are often governed by this (not just a "retainer")

**German civil law memo structure differences:**
- **Gutachten-Stil** (expert opinion style) — traditional German legal analysis follows: Obersatz (conclusion stated first) → Voraussetzungen (elements) → Subsumtion (application) → Ergebnis (result)
- This differs fundamentally from common law IRAC: German lawyers state the answer first and then prove it
- German bank legal departments (Deutsche Bank, Commerzbank, DZ Bank) use **Mandate Management Systems** (often SAP-based) to track instructions to external firms
- **BRAO** (Bundesrechtsanwaltsordnung) — German lawyers' code governs professional rules; external counsel instructions must not conflict with lawyer independence (§ 3 BRAO)

**Key German industry bodies [UNVERIFIED URLs]:**
- DAV (Deutscher Anwaltverein) — German Bar Association; publishes model engagement terms
- BUJ (Bundesverband der Unternehmensjuristen) — German in-house counsel federation; publishes guidelines for engaging external firms
- BDR (Bund Deutscher Rechtsanwälte) — alternative bar body

**Civil law vs. common law gap for skill design:**
- German mandate letters are more contract-like and governed by service law (§§ 611 ff. BGB — Dienstvertrag or Werkvertrag)
- The skill should note that for German counterparty firms, the "matter brief" may need to reference German attorney professional rules on scope limitations

---

## Japanese Track — [NOT FOUND via live sources]

### Search Queries Attempted
1. `外部弁護士 指示書 銀行 法律事務所 ブリーフィング`
2. `外部弁護士 委任状 指示書 金融機関 法務部 テンプレート`

### Result
Both returned entirely off-topic results (Thai celebrity articles, stock market charts). No Japanese-language practitioner sources retrieved.

### Synthesized Practitioner Knowledge [UNVERIFIED — based on domain knowledge, not retrieved sources]

**Key Japanese terminology:**
- **外部弁護士** (gaibū bengoshi) — external lawyer
- **委任状** (inin-jō) — power of attorney / formal delegation document; required for litigation
- **指示書** (shijisho) — instruction letter / directive document
- **法律意見書** (hōritsu ikensho) — legal opinion letter (formal deliverable from external counsel)
- **業務委託契約書** (gyōmu itaku keiyakusho) — service delegation contract; governs external counsel engagement in Japan
- **法務部** (hōmubu) — in-house legal department

**Japanese practice norms for bank-to-law-firm communication:**
- Japanese banks (Mitsubishi UFJ, Sumitomo Mitsui, Mizuho) typically use **highly structured written instructions** (指示書) as part of formal decision-making processes (ringi 稟議 system)
- The **ringi system** (decision by circulation for approval) means that a briefing memo to external counsel often doubles as an internal approval document — requiring sign-off from multiple levels before the instruction is issued to the law firm
- This creates a dual-purpose document unlike Australian practice: the external counsel brief must also serve internal governance
- Japanese formal documents use **keigo** (formal honorific register) in communications to external counsel
- **外部弁護士選定基準** (external counsel selection criteria) — major Japanese financial institutions publish criteria; the actual briefing follows a different more concise format than Western equivalents

**Key Japanese bodies [UNVERIFIED URLs]:**
- JILA (Japan In-house Lawyers Association / 日本組織内弁護士協会) — publishes guidelines for in-house counsel managing external relationships
- JFBA (Japan Federation of Bar Associations / 日本弁護士連合会) — governs professional rules for external counsel

**Civil law gap for skill design:**
- Japan's civil law tradition (based on German BGB model) means legal opinions follow a deductive structure
- However, Japanese commercial law practice has absorbed significant Anglo-American influences through securities regulation and M&A
- For cross-border matters (e.g., an Australian bank with Japanese operations), the skill should flag that Japanese external counsel instructions may need to incorporate the ringi approval structure

---

## Korean Track — PARTIAL FOUND

### Search Queries Attempted
1. `외부 법무법인 지시서 은행 법률 브리핑 가이드라인` — off-topic (Chinese tax authority results)
2. `외부 법률자문 위임장 법무법인 지시서 금융기관 템플릿` — off-topic
3. **GitHub search** — `hermes skill legal` — **FOUND** `openmagi/korean-legal-doc-drafter`

### Key Finding: openmagi/korean-legal-doc-drafter
**URL:** https://github.com/openmagi/korean-legal-doc-drafter  
**Stars:** 11 | **Forks:** 3 | **License:** Apache 2.0  
**Last updated:** Jun 24, 2026  
**Verified:** Yes — directly extracted README and SKILL.md

**What it is:** A Hermes Agent skill (SKILL.md format) covering 150 Korean legal document types. **Not specifically an external counsel briefing memo skill**, but highly relevant because:

1. **Document types covered include:**
   - 위임장 (委任狀) — Power of Attorney / delegation documents (doc-005.md, doc-068.md)
   - 자문(고문)계약서 — Advisory/consultant contract (doc-040.md, doc-133.md)
   - 업무협약서 (양해각서) — MOU / framework agreements (doc-029.md, doc-070.md)
   - NDA contracts in Korean (doc-066.md, doc-130.md, doc-131.md, doc-132.md)
   - 용역계약서(컨설팅) — Consulting service contract (doc-147.md)

2. **Architecture patterns valuable for skill design:**
   - Progressive disclosure: lightweight SKILL.md + per-document references/doc-NNN.md loaded on demand
   - Two-step workflow: situation → document type recommendation → load guide → Q&A collection → output
   - Mandatory disclaimer framing (non-legal advice) with specific display timing rules
   - Currency warnings for legal rates/figures that change annually

3. **Korean legal norms visible in skill:**
   - Documents use 갑/을 (Party A/Party B = Gap/Eul) convention — not "the Client/the Firm"
   - Formal output structure with numbered articles (제1조, 제2조)
   - Dual number format: "금 X원 (한글 금액 원)" — both numeric and hangul spelling required
   - Date formats: "YYYY년 MM월 DD일" or "YYYY. MM. DD." — must be consistent within document

**Korean External Counsel Specifics [UNVERIFIED — synthesized]:**
- Korean term: **외부법률자문** (external legal advisory) or **외부 법무법인** (external law firm)
- Korean financial institutions (KB국민은행, 신한은행, 하나은행, IBK기업은행) use formal **법률자문계약서** (legal advisory contracts) with external firms
- Korean lawyers are governed by the **변호사법** (Attorneys-at-Law Act); professional independence rules affect how instructions can be framed
- Major Korean law firms (Kim & Chang, Yulchon, Bae Kim & Lee) have standard engagement letter formats that must be matched by client instructions

---

## GitHub — Full Findings

### 1. `anthropics/claude-for-legal` ⭐ 9.2k | 🍴 1.8k
**URL:** https://github.com/anthropics/claude-for-legal  
**License:** Apache 2.0  
**Verified:** Yes — directly extracted. This is the most significant finding.

**Description:** Official Anthropic reference implementation for legal AI workflows. Suite of plugins covering:
- `commercial-legal/` — contract review, renewals, escalations
- `corporate-legal/` — M&A diligence, closing checklists  
- `employment-legal/` — hire/term review, worker classification
- `privacy-legal/` — DPA, DSAR, PIA
- `regulatory-legal/` — regulatory feed watcher, policy diff
- `litigation-legal/` — claim charts, chronologies, deposition prep
- `ai-governance-legal/` — AI use case triage
- `ip-legal/` — trademark, FTO, DMCA, OSS
- `legal-clinic/` — law school clinic workflows
- `law-student/` — IRAC, bar prep
- `legal-builder-hub/` — community skill discovery & install

**NOT found in repo:** No specific external counsel briefing memo skill or law firm instruction template. The `commercial-legal` plugin may contain engagement-related workflows but wasn't extracted.

**Key design patterns from this repo:**
- Every output includes a **Reviewer Note** header: sources used, flags, currency, what to verify
- **Source tagging** on every citation: `[Federal Register]`, `[web search — verify]`, `[model knowledge — verify]`
- `[draft — attorney review required]` marker on every deliverable
- Legal Skill Design Framework used for community skills QA: nine design parameters, three legal failure modes, trust-surface check

### 2. `openmagi/korean-legal-doc-drafter` ⭐ 11 | 🍴 3
**URL:** https://github.com/openmagi/korean-legal-doc-drafter  
**License:** Apache 2.0 | **Verified:** Yes  
*See Korean Track above for full analysis.*

### 3. `charliehotel/oh-my-hermes-for-legal-researcher` ⭐ 8 | 🍴 1
**URL:** https://github.com/charliehotel/oh-my-hermes-for-legal-researcher  
**License:** Apache 2.0 | **Verified:** Yes

**Description:** Hermes Agent skill for US legal research — ported from `anthropics/claude-for-legal` shared methodology layer. Covers statute, regulation, and case law research.

**Relevance:** Demonstrates how to port claude-for-legal patterns to Hermes SKILL.md format. **Does NOT cover non-US law or external counsel briefings.** Architecture is directly applicable to the new skill.

**Structure:**
```
research/us-legal-research/
├── SKILL.md                    # methodology & workflows
└── references/
    └── open-source-trade-secret-cases.md
```

### 4. `flpvr/LaTeX-Legal-Memo` ⭐ 0 | CC0
**URL:** https://github.com/flpvr/LaTeX-Legal-Memo  
**Verified:** Yes — basic LaTeX template, last updated Dec 2014.

**Description:** Simple LaTeX template for a legal memo. No content beyond formatting skeleton. **Very low value** — just a formatting exercise.

### 5. `ahussnain58k-droid/legal-redline-document-tools` ⭐ 0
**URL:** https://github.com/ahussnain58k-droid/legal-redline-document-tools  
**Verified:** Yes — repo exists with structure but no accessible content.

**Description:** Tools and templates for generating legal redlines, tracked changes, negotiation memos, document-review outputs. Has `skills/legal-redline-document-skill/` directory. **Adjacent** to briefing memos but focused on document review / redlining, not briefing.

### Additional Hermes legal skills found (GitHub search hits, not extracted):
- `aalikes/hermes-legal-skills` — witness contradiction finder, case theory simulator, settlement vs trial EV calculator [UNVERIFIED content]
- `shawndeng321/hermes-obsidian-legal-cssci-wiki-writing-skills` — Chinese (Mandarin) CSSCI academic legal research skills [UNVERIFIED content]
- `lawvinx/legal-academic-research` — 法学学术研究来源核验与规范写作, Chinese legal writing (Bluebook/中引法) [UNVERIFIED content]
- `fralan05/hermes-skill-legal-lease` — Russian commercial real estate lease analysis [UNVERIFIED content]
- `emergent-company/norwegian-law-memory-blueprint` — Norwegian law memory blueprint with templates and agents [UNVERIFIED content]

---

## Key Gaps Identified

| Gap | Impact on Skill Design |
|-----|----------------------|
| No French external counsel briefing template found on GitHub or open web | Skill must encode French "lettre de mission" / "plan en deux parties" norms from practitioner knowledge |
| No German Mandatsbriefing template found | Skill must encode German Gutachten-Stil and Beratungsvertrag norms |
| No Japanese external counsel instruction template found | Skill must account for ringi approval dual-purpose structure; keigo register |
| Korean legal docs skill exists but covers consumer/SME docs, not bank-to-law-firm briefing | Gap: need 법률자문계약서 and 업무지시서 specific to financial institution context |
| claude-for-legal does NOT include an external counsel briefing memo plugin | Original gap confirmed — this is a genuine open space in the ecosystem |
| No existing Hermes skill specifically for law firm briefing or external counsel guidelines | Confirms value of building `law-firm-briefing-memo` |

---

## Cross-Cultural Design Implications for `law-firm-briefing-memo`

### 1. Document Structure Divergence
| Jurisdiction | Structure Style | Key Difference from AU |
|-------------|----------------|----------------------|
| France | Two-part (Analyse / Recommandations) | More deductive; statutory citation heavy |
| Germany | Gutachten (conclusion first → proof) | Inverted from IRAC; Obersatz-first |
| Japan | Hybrid (civil law + Anglo-American influence) | Ringi dual-purpose; keigo register |
| Korea | Civil law with article numbering | 갑/을 party naming; hangul+numeric dual amount format |
| Australia | IRAC / ISRAC | Fact-heavy; precedent-driven |

### 2. Party Naming Conventions
- **AU/UK/US:** The Client / The Firm
- **France:** Le Mandant / Le Mandataire (or Client / Cabinet)
- **Germany:** Auftraggeber (client) / Auftragnehmer or Kanzlei (firm); sometimes "Mandant"
- **Japan:** 依頼者 (irai-sha) / 受任者 (juninsha) or 弁護士 (bengoshi)
- **Korea:** 갑 (Gap = client) / 을 (Eul = firm)

### 3. Professional Independence Constraints
All jurisdictions impose professional independence rules that constrain how instructions can be worded:
- **Australia:** Legal Profession Uniform Law; instructions cannot direct outcome of professional judgment
- **France:** BRAO equivalent — Règlement Intérieur National du Barreau
- **Germany:** § 3 BRAO — explicit independence guarantee; instructions cannot bind legal judgment
- **Japan:** 弁護士法 (Attorneys-at-Law Act) Art. 1 — public mission independence
- **Korea:** 변호사법 Art. 1 — similar public mission framing

**Skill implication:** The law-firm-briefing-memo skill should include a disclaimer/guidance field: "Instructions cannot direct professional judgment — only scope and factual parameters."

### 4. Fee and Billing Norms
- **France:** Fees regulated; must be disclosed in lettre de mission; CARPA (escrow) rules apply for client funds
- **Germany:** RVG (Rechtsanwaltsvergütungsgesetz) sets statutory fees; departures require written agreement
- **Japan:** Fee agreement (着手金/報酬金 system — retainer + success fee) common; written contract required since 2004 bar reform
- **Korea:** Fee structures in 법률자문계약서 must comply with bar association guidelines

---

## Recommended References to Check (Unextracted, Could Yield More)

The following sources may contain relevant content but could not be accessed in this session:

1. **JILA (Japan In-house Lawyers Association)** — https://www.jila.jp/ — publishes best practice guides for managing external counsel [UNVERIFIED accessible]
2. **BUJ (Bundesverband der Unternehmensjuristen, Germany)** — https://www.buj.net/ — German in-house counsel federation; may have Mandatsbriefing guidelines [UNVERIFIED accessible]
3. **AFJE (France)** — https://www.afje.org/ — French in-house counsel; may have external counsel management guides [UNVERIFIED accessible]
4. **ACC (Association of Corporate Counsel)** — https://www.acc.com/legalops/ — US but global membership; anti-bot blocked in this session [UNVERIFIED]
5. **CLOC (Corporate Legal Operations Consortium)** — https://cloc.org/ — has Australia chapter; external counsel guidelines library may be available to members [UNVERIFIED]
6. **IBA In-House Counsel Committee** — publishes international external counsel guidelines; URL returned 404 in this session [UNVERIFIED]
7. **anthropics/claude-for-legal `commercial-legal/`** — not yet extracted; may contain engagement letter patterns relevant to external counsel briefing

---

## Files Created

- `/tmp/research_lawfirm_NONENG.md` — this file

---

*Research conducted by parallel subagent on 2026-08-21. Web search backend returned off-topic results for all non-English queries. GitHub data verified via direct extraction. Synthesized practitioner knowledge flagged [UNVERIFIED]. Parent agent should treat GitHub findings as confirmed and language-track synthesized content as informed prior knowledge requiring expert validation.*
