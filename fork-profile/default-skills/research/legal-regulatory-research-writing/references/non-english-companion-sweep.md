# Non-English companion sweep — reusable recipe + worked DACH example

Companion sweeps supplement the main critique with language/jurisdiction-specific literature. This file records the reusable recipe and one worked example (German/DACH, NAB LIP critique project, `Documents/Legal Architecture/critique-workspace/research/research_german_sweep.md`).

## Recipe

1. **Read the prior sweep file first** and adopt its format verbatim. In this project the template was `research/research_regulatory_and_nonenglish_sweep_2.md`. Structure to copy:
   - Prerequisite-confirmation preamble (state which files you read and what format you're adopting; state you did NOT modify `critique.md`).
   - A per-combination table: `| Language | Topic | Result | Detail |`. One row per (language × topic-family) combination — including the ones that turn up nothing.
   - "Track summary judgment (explicit, not padded)" — bulleted: what's genuine, what's professional-not-peer-reviewed, what's confirmed-absent, and a "no hard access-barrier" note.
   - "Corrections/notes flagged for the critique document (recommendations only)" — numbered, actionable.
   - Footer: which files were created vs. only read; where cached extracts live.
2. **Query native venues in native language**: university repositories (edoc.hu-berlin.de, epub.uni-regensburg.de, HAL, CiNii, RISS/ScienceON), regulator sites in-language (BfDI, BaFin, Bundesnetzagentur), profession bodies (Anwaltsblatt/DAV), and the EU AI-Act German/French Service Desk (`ai-act-service-desk.ec.europa.eu/de`).
3. **Every genuine hit carries author + venue + date + DOI/URL.** A resolving DOI is the strongest anti-fabrication signal.
4. **State each null as an exhaustive negative** (ran multiple targeted variants, genuinely absent) vs incomplete negative (tool failed before exhausting variants).
5. **Cross-language absence corroborates fabrication findings** — if a gap holds across every language swept, say so; it upgrades a single-language null into strong evidence a suspiciously-specific citation is fabricated.

## Worked DACH example — genuine sources verified

- **(a) legal AI/LLM** — Mielke & Wolff (2023), peer-reviewed ("Begutachtet: Ja"), Uni Regensburg, **DOI 10.5283/epub.55537**. And **Mähler, Melina Felicitas, "KI-Einsatz und Anwaltsrecht – Harmonie oder Dissonanz?", HU-Berlin Juristische Fakultät, 12 Jul 2024, DOI 10.18452/28744** (CC-BY, full PDF open) — strongest German academic source; examines § 43a / § 1 / § 43 / § 2 BRAO compatibility with AI.
- **(c) Verschwiegenheit duty** — Mähler dissertation (duty-level) + Anwaltsblatt/DAV "KI – Berufsrechtliche Risiken und anwaltliche Regulierung" (1 Jul 2026): § 43a Abs. 2 BRAO, sanctioned via § 203 StGB, concretised § 2 BORA; cloud-GKI as the risk vector.
- **(d) AI + evidence** — Anwaltsblatt/DAV "KI, Simulation und digitale Beweismittel: Beweisaufnahme 2.0" (28 Apr 2026, Dr. Nicolas Rücker & Prof. Dr. Hans-Patrick Schroeder), reporting VZPR Frühjahrstagung Hamburg 17 Mar 2026. Covers § 371a ZPO Inaugenscheinnahme, deepfakes as Prozessbetrug, Art. 50(4) KI-VO labelling, DRiG human-decision requirement. Professional/conference-level, NOT peer-reviewed.
- **(g) EU AI Act German regulatory** — **BfDI KI-Handreichung "KI in Behörden – Datenschutz von Anfang an mitdenken" (22 Dec 2025)**, LLM/TOM-lifecycle focus; **BaFin "KI bei Banken und Versicherern: Automatisch fair?" (BaFinJournal, 1 Aug 2024)** — substantive on fairness/Bias/Diskriminierung (AGG §§ 19–20, Art. 9 DSGVO, direkte/indirekte/intersektionelle Diskriminierung, incompatible fairness metrics, Explainable-AI limits, simple-model preference); plus Bundesnetzagentur Hochrisiko-KI portal and the German AI-Act Service Desk (Art. 6 / Annex III).

## Worked DACH example — confirmed gaps (genuine absences, not paywall artifacts)

- **(b)** No German legal-ops case/matter *allocation fairness* literature — only judicial "gesetzlicher Richter"/Geschäftsverteilung (Art. 101 GG) doctrine, a different problem. Gap now confirmed across **all five** swept languages (DE + ZH/JA/KO/FR) → strengthens the judgment that "Case Assignment Fairness Corpus" / "Legal Allocation Bias Dataset" are fabricated.
- **(c-sub)** No German-specific *technical* privilege-preserving / information-barrier AI literature (duty is covered, technical control is not) — only English arXiv work.
- **(d-sub)** No German treatment of AI decision-*logs* as forensically-admissible ZPO records (distinct from AI-generated *content* as evidence).
- **(e)** No German source linking AI-generated artifacts to § 47 GwG tipping-off / Informationsweitergabeverbot; ML-AML material (BaFin BDAI 2021) is detection-only.
- **(f)** No fairness-*audited burnout prediction* for professional-services staffing — only OR shift-scheduling fairness (FU Berlin "Gerechtigkeitsaspekte in der Personaleinsatzplanung"; Fraunhofer Austria) and BAuA occupational-health burnout science (project f2318), neither of which is the EN-tag proposition nor in a legal context.

## Scope-distinction calls made this sweep (the subtle findings)

- Beweisaufnahme 2.0 = AI-*generated content* as evidence, NOT AI-decision-*logs* as forensic records → PB-tag question stays a gap.
- Mähler/Anwaltsblatt = confidentiality *duty*, NOT *technical* privilege-preserving architecture → technical-control layer stays a gap.
- BaFin BDAI = ML detection efficacy, NOT AI-artifact-as-tipping-off → § 47 GwG question stays a gap.

## Worked ZH/FR example (NAB LIP round 3, July 2026) — venues, resolvers, anchors, gaps

Output: `research/research_round3_fresh_zh_fr.md` (7 topics: COI/ethical-wall, prompt-injection, legal KGs, multi-agent failure modes, chatbot/access-to-justice, e-billing, XAI/legal-AI regs). Findings written in English; queries native-language.

**Native venues that produced genuine hits**
- **ZH academic:** `crad.ict.ac.cn` (计算机研究与发展 / Journal of Computer Research and Development — CCF-recognized), CSSCI journals via `journal12.magtechjournal.com` (情报科学 / Information Science), 百度学术 (xueshu.baidu.com) for cross-check.
- **ZH regulatory/primary:** `cac.gov.cn` (CAC — algorithm filing 备案, GenAI service registration counts), `gov.cn` (Deep Synthesis / Algorithm Recommendation Provisions), `court.gov.cn` + `cicc.court.gov.cn` (smart-court / internet-court deployments with metrics).
- **FR primary:** `legifrance.gouv.fr` (Décret n° 2023-552 code de déontologie), `justice.gouv.fr` (IA-strategy report, "Judi"/"Mon Assistant Justice" chatbots), `cnil.fr` (2025 IA-RGPD recommendation fiches), `cnb.avocat.fr` (CNB déontologie-IA guide), `courdecassation.fr`/Judilibre (open data judiciaire), HAL (`hal-01191914` legal ontology, `tel-05035018` legal-KM thesis).

**Anchors VERIFIED LIVE before writing** (the credibility spine)
- DOI **10.7544/issn1000-1239.202440630** → 《大语言模型对抗性攻击与防御综述》, CRAD 62(3):563–588, 2025. Resolves at `crad.ict.ac.cn/article/doi/<doi>`. Explicitly taxonomizes 提示注入 + 间接提示注入 (direct + indirect prompt injection) — the exact LIP §5.4 threat split.
- **Décret n° 2023-552 du 30 juin 2023** art. 7 (conflict-of-interest rule) → resolves at Legifrance JORFTEXT000047774060.
- 情报科学 39(2):133-140 (2022) judicial-KG paper → ~30k entities / 180k relations, Neo4j, network-fraud judgments — verified at the magtech journal page.

**Genuine strengths by track:** T2 ZH (peer-reviewed survey, direct+indirect injection), T3 ZH (multiple CSSCI, concrete metrics, 智慧法院 program) + T3 FR (HAL ontology + Judilibre), T5 ZH (deployed internet-court metrics) + T5 FR (govt strategy + named chatbots), T7 ZH (algorithm-filing regime, 538 services filed by Aug 2025) + T7 FR/EU (CNIL fiches + GDPR Art. 22 + AI Act), T1 FR (Décret 2023-552 art.7 + CNB/CCBE guides).

**Confirmed gaps / weak tracks (reported honestly, not padded):**
- **T4 (multi-agent failure modes):** ZH material is *syntheses/translations of English primary work* (three-failure-mode framing 上下文污染/角色混乱/故障扩散; Supervisor/Pipeline/Swarm patterns), not original CN peer-reviewed; FR practitioner-only → recommendation: anchor in English primary (e.g. MetaAgent, ICML 2025), treat ZH/FR as corroborating.
- **T6 (e-billing):** vendor-only in ZH; in FR the real driver is the general Factur-X e-invoicing mandate (mandatory for avocats 1 Sept 2026) — **no LEDES/UTBMS-equivalent legal task-code standard exists in either jurisdiction**. Buildspec consequence: LIP must impose a task-code taxonomy, not adopt a market standard.
- **T1 ZH** (automated info-barrier / ethical-wall): commercial/vendor only, no CSSCI academic modelling.
- **T2 FR / T5 FR (aide-juridictionnelle sub-angle):** no French peer-reviewed academic anchor (field is English arXiv); a €380k "average incident cost" figure seen in FR blogs is unsourced — do not cite.

**Corrections flagged to parent critique (jurisdiction-specific hard gates, framed as precision corrections not reversals):** (1) no LEDES/UTBMS equivalent in FR/ZH; (2) China's autonomy-ladder gate is mandatory algorithm filing + security assessment, stricter than generic "explainability"; (3) L3 fully-automated decisions on EU individuals likely require a human-review path under GDPR Art. 22 (reinforced by the FR justice ministry's own human-supervision framing).
