---
description: 'Use when: producing legal/regulatory research findings or critique reports. Strict citation discipline, primary-source
  preference, explicit gap-reporting instead of fabrication.'
name: legal-regulatory-research-writing
triggers:
  - Task involves legal, regulatory, or compliance research (legislation, case law, regulator guidance)
  - User asks for an analysis, critique, or risk assessment of a legal/regulatory document
  - Task requires primary-source discipline (AU law, ASIC, AUSTRAC, FATF, AI regulation)
related_skills:
  - grounded-citations
  - law-firm-briefing-memo
  - pii-redaction
  - academic-literature-review
---


# Legal & Regulatory Research Writing

## When to use
Any task that asks you to research legal/regulatory sources (legislation, regulator guidance such as AUSTRAC/ASIC/FATF, case law, parliamentary bills) and produce a written finding, critique, or risk assessment that a human will rely on. This includes iterative "final check" or "latest developments" sweeps on a report that already exists — a very common pattern in these projects (see `references/` for the specific ongoing NAB LIP critique project history).

Also applies to **domain-wide regulatory landscape sweeps** — e.g. "deep research on Australian legal AI regulation," "what are the professional responsibility standards for AI in legal practice," "eDiscovery AI evaluation standards in Australia." These produce a structured findings file rather than a critique of a specific artefact, but the same source-discipline, gap-reporting, and primary-source-first rules apply. A pre-built AU legal AI authority set is available at `references/australian-legal-ai-regulation-2026.md` — load it before starting any sweep touching AU AI regulation, legal professional privilege and AI tools, eDiscovery TAR standards, or Privacy Act obligations for legal AI systems.

For legal AI EVALUATION specifically (benchmarks, eval frameworks, eval architecture for multi-agent legal systems), load via `skill_view(name='academic-literature-review', file_path='references/legal-ai-evals-architecture-2026.md')` — that file is **not** in this skill's `references/`. It covers: Harvey LAB (primary agentic legal benchmark), LAUKIN (only AU contract dataset), MAC-Bench (adversarial compliance), AgentLeak (inter-agent privacy leakage), MCPSecBench (MCP security), LongMemEval family (personal second-brain memory eval), RAGAS/DeepEval/LRAGE (RAG eval tooling), LLM-as-judge calibration (Lee et al. 2511.21140 bias correction), and the full AU court practice note table.

## Core finding format: QUANTIFIED CLAIM + CITATION + APPLICABILITY

Every finding in the report body must follow this three-part structure, every time:

1. **QUANTIFIED CLAIM** — the specific, falsifiable statement of what the law/regulator/case says. Prefer numbers where they exist (penalty units, timeframes, dates, percentages from a regulator's own review) over vague characterizations.
2. **CITATION** — source name, document title, date, and URL/DOI. State clearly whether it is a **primary source** (statute text, regulator's own page/report, court judgment, parliament bill-status page) or **secondary source** (law-firm client alert, news coverage). If secondary, say so explicitly in the citation line — never let a law-firm summary masquerade as the underlying primary authority.
3. **APPLICABILITY** — a paragraph connecting the claim to the specific system/product/process under review. This is where you say what it *means* for the thing being critiqued, not just what the source says in the abstract.

Do not paraphrase a finding without CITATION, and do not add a CITATION without an APPLICABILITY paragraph tying it back to the artifact under review — bare citation dumps are not findings.

See `templates/finding_format.md` for copy-paste-ready blocks (standard finding, confirmed-gap finding, and critical-risk disclaimer).

## Source discipline

- **Primary-source-first.** Prioritize: statute/legislation text (legislation.gov.au), regulator's own site (AUSTRAC, ASIC, FATF), parliament bill-status pages, and court/tribunal judgments (fwc.gov.au, austlii.edu.au). Use law-firm alerts and news coverage only to (a) interpret a primary source, (b) surface a case citation you then try to verify against a primary database, or (c) flag something primary sources haven't caught up to yet.
- **Case citations sourced only from secondary reporting must be explicitly flagged** as "secondary-sourced, pending primary verification" in both the finding and any summary table — do not present a case as confirmed law until you've either read the judgment directly or corroborated the citation across multiple independent secondary sources (and even then, flag it).
- **Maintain and honor an explicit exclusion list** of any fabricated/hallucinated sources named by the user or discovered in prior sessions (e.g. invented author names, invented "corpus"/"dataset" citations that don't resolve to a real DOI or publisher page). Check new findings against this list before writing them in. If a source name resembles something on the exclusion list, verify it resolves to a real, retrievable document before using it — don't assume good faith on a superficially plausible citation.
- **"Known baseline, not re-researched" is a debt, not a settled fact — track it and pay it off.** When a research sweep inherits a citation from a lost/prior context and labels it "known baseline" or "assumed, not verified this pass," that label tends to get silently carried forward across every subsequent synthesis pass without anyone actually spending the verification budget on it. Treat any such label as an open item in the report's needs-further-verification section (not a footnote to ignore), and when the user asks you to double-check research completeness, checking these named-but-never-verified baseline citations against primary sources is exactly the kind of delta that answers the question — don't just re-confirm the sweeps that were already done and skip the ones marked "assumed."
- **Cross-check dates and enactment status.** Bills move (introduced → passed → assented → commenced) — always confirm which stage a piece of legislation is actually at via the parliament's own bill-status page, not just a law-firm article's prose (which can lag behind the actual date, e.g. an article saying "has not yet received assent" written before assent actually occurred). State the confirmed stage and date explicitly.

## Report gaps honestly — this is the most important discipline

When targeted searches turn up nothing directly on point, **say so explicitly as a "genuine gap confirmed" finding** — do not stretch a tangentially-related source to sound like it resolves the question, and do not silently omit the topic. A gap is itself a valid, valuable finding: it tells the reader "no regulator or court has spoken to this yet, so you are in undecided territory and should get a conservative internal legal opinion rather than assume a permissive or restrictive reading."

Distinguish two kinds of negative result:
- **Exhaustive negative** — you ran multiple targeted query variants and found nothing on point; state this plainly as a confirmed gap.
- **Incomplete negative** — a search errored out (timeout, rate-limit, provider failure) before you could exhaust query variants. Flag this as *incomplete*, not as a confirmed absence, and note it should be revisited. Do not conflate a tool hiccup with "no such source exists."

## Search resilience

Web-search providers occasionally time out or rate-limit (HTTP 429, read timeouts) mid-sweep. When that happens: retry with a reformulated query or a different angle rather than treating the single failed call as a completed negative search. If a retry also fails, explicitly label that specific line of inquiry as an incomplete search in the report's methodology notes so a future pass knows to redo it — never let a silent tool failure get reported as "nothing found."

**Escalation ladder when the search tool itself is rate-limited across an entire session** (not just one query): don't burn retries on the same broken backend. Step down through: (1) `web_search` with a reformulated query — if it 429s repeatedly across unrelated queries, the backend is down for the session, not the query; (2) `web_extract` directly against a *guessed* primary-source URL — arXiv abstract pages (`arxiv.org/abs/<id>`), a regulator's own artifact/blog path, a known repository's search endpoint (J-STAGE, Cyberleninka) — this bypasses the search layer entirely and is often faster than search anyway when you already know roughly where the source lives; (3) `browser_navigate` to a search engine as a last resort — in practice this is unreliable for headless/no-JS scraping and frequently doesn't return usable results; (4) `web_extract` against `html.duckduckgo.com/html/?q=...` as a lightweight unauthenticated search-proxy fallback when you need discovery rather than a known URL. Don't stop at step 1 and report "search is down, couldn't verify" — steps 2 and 4 usually get you there.

## Quantification pass: web_extract the primary source even when search worked fine

The QUANTIFIED CLAIM half of the finding format lives or dies on hard numbers, and web-*search* snippets almost never carry the specific figures you need — they give you the topic and the URL, not "14 failure modes / 3 categories / κ=0.88 / 1,600+ traces" or "LEDES XML 2.2 = 18 segments / 206 data elements" or "mis-categorisation dropped 23%→9% under a 30%→50% staged rollout." Those precise numbers come from actually pulling the primary document. So the standard two-phase rhythm on a fresh sweep is:

1. **Discovery** — `web_search` per topic to identify the strongest primary source (arXiv abstract, Wikipedia standard page, Springer/DOI article, regulator page, Gartner press release).
2. **Quantification** — `web_extract` (batched, several URLs in one call) directly against those identified primary URLs to lift the exact figures, version counts, dates, and effect sizes into the claim.

This is distinct from the search-resilience ladder below, which frames web_extract as a *fallback for when search is rate-limited*. Here web_extract is the *primary quantification step* even when search is working perfectly — you extract because snippets don't carry numbers, not because search failed. Batch the extracts (arXiv + Wikipedia + a journal page in a single call) to keep it cheap. A finding that says "MAST identifies multiple failure modes" is weak; "14 failure modes in 3 categories, 1,600+ traces, κ=0.88 (arXiv:2503.13657)" is the bar — and you only clear it by extracting the source.

## Coverage verdicts: three-state (yes / partial / gap), not binary

On a multi-topic sweep, the per-topic verdict and the summary table should use a three-state scale, not just found/not-found:
- **yes** — on-point, current, quantified coverage exists.
- **partial** — one layer is well-supported but another is a confirmed gap. The recurring shape: a *commercial product category* or a *primary normative rule set* is mature, but *peer-reviewed academic literature on that exact sub-question* is thin/absent (e.g. Topic "automated legal-practice conflict-of-interest detection": Intapp Walls/Conflicts + ABA Model Rule 1.10 are solid, but academic COI-detection literature for legal practice is a near-gap; the one arguably-academic hit was about *research-integrity* COI, a different question — a Scope-distinction catch). Label it partial, name which layer is the gap, and recommend treating the spec item as an "integration-against-existing-product" requirement rather than a research-backed one.
- **gap** — nothing on point; confirmed absence.

Carry the exact same three-state verdict into the summary table's "Coverage found" column so the reader sees at a glance which items are only partially grounded. Don't round a "partial" up to "yes" just because the commercial/normative layer is strong.

## Visual formatting conventions for critical risk items

- Use a distinct, consistent visual marker for critical/disclaimer-level findings — e.g. a `⚠️` symbol plus a bold label like `**D-2 Disclaimer**`, followed by an *italic* block, or a blockquote box. Pick one convention per report and apply it consistently to every disclaimer so critical items are visually scannable against ordinary findings.
- Risk tables should score on **objective criteria**: probability of regulatory/legal change or enforcement, impact on the system under review, and concrete mitigating measures — not vague adjectives without a basis. Tie the probability/impact rating in the table back to the specific citation that justifies it.

## Diff hygiene for iterative reports

These reports get revised across multiple passes (new legal developments found, risk ratings updated). When regenerating a diff between versions:
1. Generate the raw diff.
2. Strip artifacts that are not intentional content changes: automatic markdown link-syntax rewrites, whitespace-only changes, reformatting noise.
3. Confirm the cleaned diff contains only the substantive edits you intended (new findings, updated risk ratings, new disclaimers) — spot-check line counts against your own list of intended changes before calling the diff "clean."
4. Version the clean diff file distinctly (e.g. `_diff_clean_v2.md`, `_diff_clean_v3.md`) rather than overwriting, so the revision history stays auditable.

## Commissioning a new research round: gap-check first, then dispatch parallel subagents by language-group

Before starting a third (or Nth) research round on a multi-session project, don't pick new topics from intuition — do an explicit gap-check first: read INDEX.md and the structural extract's gap list, enumerate every topic the *existing* research files already cover by name (not by vague category), and only commission research on what's genuinely untouched. Confirmed working pattern (NAB LIP, round 3, July 2026): read INDEX.md + structural extract, identified 15 already-covered gap items across 9 existing files, then identified 7 genuinely-untouched topics touched by the spec but never researched (conflicts/ethical-wall automation, prompt-injection defense, legal-KG-as-academic-field, multi-agent orchestration failure modes, legal chatbot/A2J triage, e-billing standards/market data, legal-specific XAI).

**Dispatch shape: parallel subagents split by language-GROUP, each covering the FULL topic set — not split by topic.** For a round needing both a general-English sweep and non-English companion sweeps, dispatch N parallel leaf subagents where each owns one language-group (e.g. English solo; Japanese+Korean paired; Chinese+French paired) and every subagent researches the *same* topic list in its assigned language(s). This beats splitting by topic because: (a) each subagent needs only one exclusion-list/already-covered briefing instead of N of them; (b) findings land in per-language-group files matching the established companion-sweep format directly; (c) a topic that's a gap in one language but covered in another surfaces cleanly in a per-topic-per-language status table instead of getting buried in a topic-centric file.

**Inline the full "do not re-research" list by name into every subagent's delegation prompt.** Don't say "check INDEX.md for what's covered" — a leaf subagent won't necessarily redo your gap-check. Spell out the specific already-covered topics and the exact fabricated-citation exclusion list in every task's context block, even though it repeats across dispatches. Same discipline as inlining the exclusion list for citations, extended to *topic* exclusion.

**After subagents return: verify on disk before touching INDEX.md.** Confirm the reported files actually exist (search_files), then grep every returned file for the exclusion-list terms to confirm they appear only in "not cited" provenance statements, never as live citations — a subagent's "exclusion list held" claim is a self-report, not proof. Only then update INDEX.md: one paragraph per new file (what it covers, yes/partial/gap per topic), flag the existing critique.md as behind disk until an integration pass runs, and set "Next step" to the specific integration task with standout findings (confirmed cross-language gaps, right-sizing corrections) named explicitly so the next session doesn't have to re-read all the files to find them.

## Synthesizing at scale: delegate the final write-up when sources exceed context budget

These projects accumulate a structural extract (tens of KB) plus multiple research-sweep files (each 25-40KB+) across sessions. Once total source material is large enough that reading it all yourself and then writing a 400-700 line critique in the same context is wasteful or risky, delegate the synthesis step itself to a subagent rather than doing it inline:

- Give the subagent an **ordered list of files to read in full** before writing anything (index/provenance file first, then the structural extract, then research sweeps in a stated order).
- Inline the **exact exclusion list** of fabricated/unverified sources in the delegation prompt itself (don't just say "check the exclusion list in the files" — name them explicitly), and inline the **exact list of sources flagged as unverified/paywalled/secondary-pending-verification** that must be carried forward as caveats, not silently dropped or upgraded to confirmed.
- Specify the **target document structure** section-by-section (exec summary, methodology, per-topic-family findings, dedicated regulatory-gaps section, dedicated excluded-sources section, dedicated needs-further-verification section, recommendations) so the subagent doesn't have to infer report shape from scratch.
- Require the subagent's own **self-verification step**: read back the file's line count and head/tail before reporting done, and report the absolute path + line count in its summary. This gives you a cheap, concrete artifact to spot-check against without re-reading the whole thing yourself.
- After the subagent reports back, still do your own spot-check pass (grep for the excluded-source names to confirm they only appear in the "explicitly excluded" section, not as live citations) — a subagent's self-report of "no fabricated sources used" is a claim, not proof.

## Multi-session project continuity: keep a durable INDEX.md

When one of these critique/research projects spans multiple sessions (likely, given the volume of research involved) and a context compaction or crash can wipe in-progress work, maintain a plain **INDEX.md** at the project folder root that states: what files exist and what each contains (one paragraph each), what was genuinely lost and is not recoverable (be honest — don't imply coverage you don't have), and the concrete next step. This is what makes recovery from a lost context window fast: a new session (or subagent) can read INDEX.md first and immediately know the state of the project without reconstructing it from session_search or guessing.

**INDEX.md itself goes stale — reconcile it against disk before trusting it.** It's written once during a recovery/checkpoint and then not touched while later sessions add new research-sweep files or produce the actual synthesized report. Before relying on INDEX.md's claims (e.g. "no critique.md exists yet," "only sweep_2 files present"), do a quick `search_files` pass on the project folder and diff what you find against what INDEX.md claims. Update INDEX.md every time you finish a synthesis or verification pass — it should always describe the *current* file set and the *current* deliverable status, not the state at last checkpoint.

## Tool-usage pitfall: read_file's JSON output escapes quotes — don't paste that into patch old_string

`read_file` returns file content JSON-encoded, so literal `"` in the source file shows up as `\"` in the tool's response. When you copy that displayed text straight into `mcp__patch`'s `old_string`/`new_string`, you're pasting a literal backslash that doesn't exist in the actual file — the match fails (often silently matching zero or the wrong number of times) even though the text looks identical to what you just read. Strip the JSON escaping before using it as a patch anchor: use the real `"` character, not `\"`, in old_string/new_string. This bit repeatedly (3 failed patch attempts in one session) when editing a critique/report document with heavy quoting.

## Integrating an incremental sweep round into an already-existing critique: audit cascading counts, not just the new section

When a new research round (e.g. a third language-sweep batch) needs folding into a critique document that already has prior rounds baked in, the new material rarely lives in one place — it touches the methodology/provenance section, several per-topic finding sections, a delta-verification log, the recommendations section, and a closing summary line, all in the same pass. Confirmed July 2026, NAB LIP critique: integrating a Russian/Hebrew/German round (round two of the non-English sweep) into a critique that already had a Chinese/Japanese/Korean/French round (round one) baked in required touching 9 separate locations in one file via parallel patch calls.

The failure mode this creates: the document accumulates small **cardinal-number claims tied to enumeration** — "six pre-existing work products," "3 of 5 baseline items confirmed," "a four-language sweep," "citations in one of the five research sweep files" — and adding a new round makes some of these stale (file count 6→9, confirmed-count 3 of 5→4 of 5) while others must NOT be touched because they correctly describe a specific *historical* round, not the cumulative total (e.g. "the four-language finding already in §2/§3" correctly refers to the first CJK/French round even after a second round exists, and must stay "four-language" rather than being bumped to "seven-language").

Rule: after integrating an incremental round,
1. Grep the whole document for cardinal-number-plus-noun patterns tied to counting (`search_files` for digits adjacent to "file", "sweep", "language", "of 5", "baseline", "pre-existing") before considering the integration done.
2. For each hit, read its surrounding sentence to determine whether it's a **cumulative total** (must be bumped) or a **scoped historical reference** to one specific prior round (must stay as-is) — don't blanket-replace on pattern match alone.
3. Only after that audit passes should the closing "end of critique" provenance line and the methodology section's file list be treated as reconciled.

This is a stronger, more specific version of the "diff hygiene" spot-check above — that section governs whitespace/formatting noise between versions; this one specifically targets numeric-scope staleness introduced by additive integration.

## AI × Legal Knowledge Management — pre-seeded authority sets

For research touching AI use in legal practice (privilege, confidentiality, multi-jurisdiction KM compliance), two pre-built authority sets are available:

**`references/ai-legal-privilege-km-framework.md`** — case law matrix, statutory frameworks, privilege analysis:
- Verified case law matrix (*Heppner*, *Munir*, *Warner*, *Asia Global Crossing*) with verification status
- Statutory framework per jurisdiction: Australia (Privacy Act, Workplace Surveillance Acts, Fair Work), Germany (§203 StGB + §43e BRAO), EU/UK (GDPR Arts 5/6/25/28/35/88), Japan (弁護士法, APPI, JFBA/Tokyo Bar guidance), France (CNB position, secret professionnel)
- Enterprise-vs-public AI analytical framework (the determinative LPP distinction from 2025–2026 case law)
- Cross-matter contamination framework (AI memory/RAG risk → ABA Rules 1.6/1.10)
- Meeting transcript privilege analysis; trust/adoption survey data; practitioner guidance quick-reference

**`references/legal-ai-km-verified-papers-2026.md`** (July 2026) — 14 verified arXiv papers with live-confirmed IDs:
- Legal NLP benchmarks: CUAD (arXiv:2103.06268), ContractNLI (arXiv:2110.01799); accuracy figures (85–95% for well-defined clause types)
- IRAC card extraction + hallucination controls: Piccioli 2026 (arXiv:2607.03325), Bose Falkor-IRAC 2026 (arXiv:2605.14665)
- Tiered KG: GraphRAG Microsoft (arXiv:2404.16130), LegalGraphRAG ACL 2026 Main (arXiv:2605.28120)
- Passive capture: DySECT ACL 2026 Demo (arXiv:2603.06915)
- Strongest quantified ROI: ComplianceNLP 3.1× efficiency gain, real deployment (arXiv:2604.23585, ACL 2026 Industry)
- Leaver knowledge: Schmitt & Borzillo 2023 (91 empirical studies); expert finding: Balog 2012 (55% can't locate expertise)
- Verified legal-tech product name table (Lexis+ AI, Westlaw Advantage/Edge/CoCounsel Legal, iManage Knowledge Unlocked)
- Jurisdiction pre-deployment compliance checklist (GDPR Art.35 DPIA, APP 6 secondary-use, NSW 14-day notice, German §203 StGB)

Load both files before starting any AI-legal-privilege or legal-KM-compliance sweep to avoid re-verifying arXiv IDs or re-researching compliance prerequisites.

## Non-English / multi-jurisdiction companion sweeps

A recurring sub-task on these projects is a **language- or jurisdiction-specific literature sweep** that companions the main critique (e.g. a German/DACH sweep, or Chinese/Japanese/Korean/French sweeps). These follow their own conventions — see `references/non-english-companion-sweep.md` for a worked DACH example and the reusable recipe. Key points:

- **Match the format of the prior sweep file exactly.** Read the earlier sweep (e.g. `research_regulatory_and_nonenglish_sweep_2.md`) *before* writing and adopt its structure verbatim: a per-combination table `Language | Topic | Result | Detail`, an explicit "Track summary judgment (explicit, not padded)" section, and a "Corrections flagged for the critique document" section. Consistency across sweep files is what lets a synthesis pass (or subagent) merge them mechanically.
- **Query native venues in the native language.** University institutional repositories (edoc/epub, HAL, CiNii, RISS/ScienceON, CNKI-adjacent), the regulator's own site in-language (BfDI, BaFin, Bundesnetzagentur), and the EU AI-Act German/French service desk — not just English search. Capture author + venue + date + DOI/URL for every genuine hit; a DOI that resolves is the strongest anti-fabrication signal.
- **Cross-language absence corroborates a fabrication finding.** When the same on-topic gap (e.g. "legal-ops case/matter *allocation fairness*") is confirmed absent across every language swept, that is strong evidence a suspiciously-specific citation ("Case Assignment Fairness Corpus", "Legal Allocation Bias Dataset") is fabricated — state the cross-language corroboration explicitly, it's more persuasive than a single-language null.
- **Verify the two or three ANCHOR sources live before writing — resolve the DOI and the statute, don't trust the snippet.** On a native-language sweep, one or two sources carry the credibility of the whole track (e.g. the one genuine peer-reviewed ZH survey, the one governing FR décret). Before writing them in as findings, actually pull them: paste the DOI into its resolver (`crad.ict.ac.cn/article/doi/<doi>`, J-STAGE, CNKI) and confirm it returns the exact title/volume/pages you're about to cite, and open the statute on the official register (Legifrance `JORFTEXT...`, gov.cn) to confirm the article number and effective date. A search snippet that merely *mentions* the DOI is not verification — the resolver returning the article is. Report the verification explicitly in the method note ("DOI X resolves live; Décret Y resolves at Legifrance — verified"), because that line is what tells the downstream reader the anchor is real and not a plausible-looking hallucination. Worked ZH/FR example (NAB LIP round 3, July 2026): DOI `10.7544/issn1000-1239.202440630` and Décret n° 2023-552 art. 7 both verified live before the report was written.
- **"No equivalent standard/regime exists in this jurisdiction" is a first-class finding, not a blank.** A native-language sweep often surfaces that a construct the spec assumes is universal simply has no local counterpart — e.g. France/China have **no LEDES/UTBMS-equivalent legal e-billing task-code standard** (French e-billing rides the general Factur-X e-invoicing mandate, not a legal task-code taxonomy). State the absence explicitly and spell out the consequence for the buildspec ("LIP would have to *impose* a task-code taxonomy, not adopt a market standard"). This is more useful than either omitting the topic or stretching a vendor page to imply a standard exists.
- **Apply the three-state partial verdict per language track, and name which LAYER is the gap.** The recurring ZH/FR shape: the *commercial/deployment* layer or the *primary-regulatory* layer is strong, but the *peer-reviewed academic* layer on that exact sub-question is thin or English-only (e.g. multi-agent orchestration failure modes: ZH has good syntheses that are *translations of English primary work*, no original CN peer-reviewed contribution; FR is practitioner-only). Label the track **partial**, name the missing layer, and give the honest recommendation — "anchor this section in the English primary work (e.g. the ICML/arXiv paper) and treat ZH/FR as corroborating context, not independent evidence." Don't round a strong-commercial/absent-academic track up to a clean "yes."

## Comparative / external-landscape sweep: research what's OUTSIDE the document, don't re-validate its content

A distinct task mode on these projects: "research OTHER pertinent initiatives … do NOT re-validate the source document's own content — research what's outside it for comparison." Here the deliverable is not a citation-check of the memo's claims but an **external landscape map** that a reader uses to judge whether the memo's architecture is coherent against the outside world (peer frameworks, regulators, comparable products, comparable programs). Confirmed July 2026 (AI-governance memo, "Cluster F other initiatives"): frontier-lab responsible-scaling frameworks, AI Safety Institutes, AI-incident databases, a comparable enterprise product's governance, and enterprise-literacy case studies — all researched as *comparators*, none re-litigating the memo's own text.

Conventions for this mode:
- **Honor the scope boundary literally.** If told not to re-validate the source's content, do not quote or fact-check the source — map the *external* analogues and end each section with an explicit "comparison to the document" paragraph (structural alignment, gaps, and what the document should reconcile against). The comparison paragraph is the deliverable's value; a landscape dump with no tie-back is a miss.
- **Structural-analogue framing beats feature-by-feature.** The useful finding is usually "these external frameworks all encode the same skeleton the document uses (capability-threshold → escalating-safeguard), but at a different layer" — e.g. Anthropic RSP ASLs / OpenAI Preparedness High-Critical / DeepMind FSF CCLs all govern the *model* layer while the memo governs the *deployment* layer; complementary, not substitutes. Name the shared skeleton and the layer difference.
- **Reconcile the internal process against the statutory/standard external layer.** An internal incident/kill-switch flow is necessary but not sufficient where a statutory external duty exists (EU AI Act Art. 73 serious-incident reporting) or where a standard taxonomy exists (OECD AIM clusters, AI Incident Database). Recommend the document explicitly reconcile its internal taxonomy against the external one rather than treating the internal process as complete.
- **Watch for renamed / defunct institutions.** AI-safety bodies rename fast: US AISI → CAISI (NIST, June 2025); UK "AI Safety Institute" → "AI Security Institute" (2025); France stood up INESIA (2025); Japan AISI publishes English red-teaming guidance at aisi.go.jp. Cite the *current* name and the specific artifact (UK Inspect, Japan AISI red-teaming guide, France INESIA roadmap), not a generic or superseded "US AISI" label.

## Provenance-tier labeling: separate VERIFIED vs MARKETING vs SPECULATIVE for product/vendor claims

When a comparator is a commercial product (e.g. a competitor's enterprise agent platform), its public material mixes documented facts with promotional framing. Do not flatten them into one "found" bucket. Label every claim into three tiers, explicitly, in the report:
- **Verified** — stated in the vendor's own product docs / changelog / API reference (e.g. admin private-marketplace controls, per-user provisioning, OpenTelemetry monitoring documented at the vendor's docs path). Cite the doc URL.
- **Marketing / promotional** — testimonials, customer quotes, launch-blog capability claims, and especially demos the vendor's own footnote flags as *fictional* (a real trap: a polished enterprise demo whose fine print says the company shown is fictional — that's a capability-signalling artifact, not governance evidence). Treat as claims, not evidence.
- **Speculative / UNCONFIRMED** — a feature the *document under review* assumes the product has, but which is **not found in the vendor's public docs** (e.g. a formal "kill switch," a platform-level "gated training" requirement, a granular per-skill permission model). Flag explicitly as an assumption to verify with the vendor — do not let the document's assumption become an asserted product fact. Note where admin controls *approximate* the assumed feature (revoke provisioning ≈ containment) without *being* it.

This is the product-comparator analogue of the primary-vs-secondary source discipline: there, the risk is a law-firm summary masquerading as the statute; here, the risk is a marketing demo or an untested assumption masquerading as a documented product capability.

See `references/comparative-external-landscape-sweep.md` for the worked Cluster-F recipe (topic families, provenance-tier examples, and the non-English venue-honesty pattern applied to comparator research).

## Comparator-against-a-thesis research (external frameworks vs. a source memo's claims)

A distinct task shape from gap-hunting: the ask is not "does the literature confirm claim X" but "gather **outside comparator frameworks** and evaluate each *against the source artifact's own theses*." Worked example (NAB LIP Cluster A, July 2026): source memo claimed (1) tier AI plugins **by capability/access surface**, not self-attestation; (2) enforce via a **registry acting as a runtime control plane**. Task = find external precedents (standards, statutes, industry practice) in 5 languages and position each relative to those two theses. Conventions that worked:

- **State the reference frame up front and declare non-goals.** Open the document by restating the source artifact's theses in your own words, then explicitly say the document does NOT re-derive or re-validate the source — it only gathers outside comparators. This stops a reviewer from mistaking a comparator sweep for a re-audit of the memo.
- **Every source section ends with an explicit `Compare/Contrast` back to the theses.** Not "here is what NIST AI RMF says" but "RMF's MAP function aligns with capability-derived tiering, BUT prescribes no hard registry gate — the memo operationalizes what RMF leaves to org discretion." The value is in the *positioning*, not the summary.
- **Separate WHERE a claim is validated from WHETHER it is binding.** The strongest recurring finding: a thesis can be validated by *industry practice* (JPMorgan "lethal trifecta" capability model; Korean-practice "Tool Permission Matrix") while every *statutory* regime tiers by use-case/impact instead. Name this split explicitly — "capability-derived tiering is validated by industry, not by law; it runs *against* the grain of current binding law even as it aligns with leading engineering practice." That contradiction is itself a headline finding.
- **"Same architecture, different unit of analysis / different motivating risk" is the precise comparator verdict** — sharper than "similar." China's 备案/登记 (filing/registration) two-tier regime is a real operating registry-as-control-plane, but it gates at the *model/service* level for *public-opinion/content* control, whereas the memo gates at *plugin/skill* level for *tool/data access*. Say "same control-plane architecture, repurposed for a different end" rather than rounding it to "matches."
- **Close with a cross-cutting synthesis matrix + a numbered gaps/contradictions list.** A table with columns `Framework | Tiering basis | Registry precedent | Hard access gate? | Granularity` lets the reader see convergence/divergence at a glance; follow it with a numbered list of *real* gaps and contradictions (e.g. "no external framework tiers at plugin/skill granularity"; "self-attestation is the norm the memo rejects, and the KISDI fintech case — 38 AI systems, 2 documented — is empirical evidence of its failure mode"). Empirical anecdotes that support the memo's move are worth quoting.

See `references/comparator-against-thesis.md` for the full Cluster A worked structure and the 5-language source set.

## Scope-distinction discipline: a genuine on-topic source can still answer the WRONG sub-question

The subtlest failure mode on these sweeps is not fabrication and not a plain gap — it's a source that is real, current, authoritative, AND topically adjacent, but addresses a *different sub-question* than the critique tag actually needs. Treat surfacing that distinction as a first-class finding, not a footnote. Recurring examples:

- **AI-generated content AS evidence ≠ AI decision-logs AS forensic records.** A source on deepfakes/AI-generated material offered as evidence (authentication risk under the ZPO) does NOT address whether an AI system's own audit/decision logs are admissible as business records — a different question for a "provenance/audit-log" (PB) tag family. Flag the distinction; don't let the content-as-evidence source stand in for the logs-as-evidence question.
- **Confidentiality DUTY ≠ privilege-preserving TECHNICAL control.** A dissertation/commentary establishing the § 43a BRAO / secret-professionnel duty as applied to AI does NOT supply *technical* information-barrier / tenant-isolation / fine-tuning-leakage architecture literature. Establish that the duty is well-covered but the technical-control layer is a gap — do not let the duty-level source be read as validating a technical claim it never makes.
- **Detection-efficacy ML-AML ≠ AI-artifact-as-tipping-off.** ML transaction-monitoring literature (BaFin BDAI) is about detecting laundering, not about whether an AI-generated flag/log is itself a prohibited § 47 GwG "Informationsweitergabe." Different question; report as gap.

When you catch one of these, write it as: "genuine + current + authoritative, BUT addresses X not Y — the critique's Y question remains a gap." That precision is exactly what protects the downstream critique from over-claiming coverage it doesn't have.

## Gap analysis → tracked-changes Word deliverable

When the output of a gap-analysis pass is a Word document with revision markup (so the
risk owner can accept/reject each finding individually in Word/LibreOffice), follow this
workflow:

1. **Base document = the v1.0 source transcript**, not a blank document — all original
   text is preserved; annotations are additive only (no deletions unless explicitly asked).
2. **One amber-shaded `w:ins` paragraph per finding**, inserted immediately after the
   paragraph or table block containing the finding's anchor text. Each paragraph is also
   marked as a tracked paragraph insertion (w:ins inside w:pPr) so Word shows the change bar.
3. **Anchor-text scanning must cover ALL element types** — body paragraphs, headings,
   bullet/numbered list items, AND GFM table rows. Table rows are consumed as a block;
   scan the concatenated table block text, not per-line. Failure to do this leaves findings
   whose anchor is inside a table row silently unplaced.
4. **Deduplication is required** — an anchor phrase may appear more than once in the
   document (e.g. a holdout phrase that appears in both §6 and §8). Track emitted finding
   IDs in a set and skip re-emission.
5. **Add a closing summary page**: (a) open-values table for findings that introduce new
   mechanism requirements where the numeric threshold is a risk-sponsor judgment call, and
   (b) pure mechanism/citation findings that need no §17 addition. This separates the
   "you must decide this" items from the "just accept these" items.
6. **Jurisdiction scoping**: when a finding can be framed on either an Australian regulatory
   anchor OR an international one (EU AI Act, DORA, OECD AIM, UK CTP), always lead with
   the Australian obligation (APRA CPS 230, ASIC breach reporting, Privacy Act NDB, etc.)
   as the operative requirement for an AU-domiciled entity. International frameworks may be
   cited as comparative context only, not as the operative anchor. Document this explicitly
   in the finding text ("the operative Australian anchor is…"; "International precedents
   noted for context").
7. **Concentration risk + vendor alternatives**: for findings about single-vendor/single-model
   concentration, always document the specific architectural mitigation pathway available to
   the client (e.g. AWS Bedrock as a direct multi-provider inference pathway independent of
   Claude Cowork), not just the abstract principle. Name it, frame it as an approved mitigation
   option in the concentration risk register, and cite the applicable AU obligation.
   Do **not** treat "APRA CPS 230 §36" as a verified MSP paragraph — CPS 230 paragraph
   numbering has moved across drafts (skill snapshot vs law-firm-briefing-memo uses
   paras 50/60 for MSP register/notification). **Verify with current legislation**
   on apra.gov.au before citing any CPS 230 paragraph as the MSP rule. CPG 235 is
   guidance, not a substitute for the standard.

Prefer `officecli` (`~/.npm-global/bin/officecli`) over python-docx OOXML for iterative
revision passes. Pattern: accept-then-re-annotate.
- `officecli query doc.docx 'revision'` first — stored `@author` often includes a date suffix.
- Address paragraphs by stable `@paraId` from `officecli view doc.docx text`, never positional `p[N]` (shifts after accept).
- `revision.action` (accept/reject existing) and `revision.type` (create) are mutually exclusive; never mix in one call.
- Footnote `add --type footnote` silently drops `revision.author`/`revision.type` (WARNING + exit 2) — footnotes are always plain content.
- `find` fails on text still inside a prior `w:ins` wrapper — accept that author first, then replace.

See `references/officecli-tracked-changes.md` for the full command sequence. The older python-docx recipe is **not** in this skill: `skill_view(name='document-layout-design', file_path='references/tracked-changes-recipe.md')`.

## Pitfalls
- **Fabricated commercial product names are a distinct risk from citation fabrication.** LLMs generate plausible-sounding enterprise product names that don't exist. Confirmed instances in legal-KM research (July 2026): "Lexis+ Protus" (real: Lexis+ AI), "Westlaw Precision" (real: Westlaw Edge / Westlaw Advantage / CoCounsel Legal), "iManage RAVN/Insight" (real: iManage Knowledge Unlocked, powered by RAVN). These names sound like valid brand extensions. Verify any named product in a competitive landscape or build-or-buy section by searching the vendor's own site — a result surfacing a nearby but different name is a fabrication signal. Log verified and corrected names in the adversarial self-review section.
- **arXiv IDs must be verified by actually fetching the abstract page** — don't insert an ID based on guessing a plausible number. Concrete: arXiv:2003.02609 was nearly inserted in a legal NLP context; fetching it showed it is a UAV robotics paper. Verified legal NLP papers: CUAD arXiv:2103.06268 (Hendrycks et al. 2021), ContractNLI arXiv:2110.01799 (Koreeda & Manning, EMNLP 2021). Pattern: `web_extract(["https://arxiv.org/abs/<id>"])` and confirm title/abstract domain before citing.
- **HAL.science and some academic repositories now deploy Anubis proof-of-work anti-bot protection** — automated web_extract will return an anti-bot challenge page, not the paper. When HAL blocks, confirm existence via search snippet, note it as "partially verified," and source the substance from derivative/secondary sources that quote or summarise the blocked paper. Same pattern applies to TandFonline, some MDPI articles, and law-firm sites with aggressive cookie walls (Norton Rose Fulbright, CMS Law). Never let an anti-bot block silently become "nothing found" — existence confirmed via snippet is itself a finding.
- Don't let a secondary source's framing substitute for reading the primary source when the primary source is readily available (e.g. AUSTRAC's own guidance page, ASIC's own media release) — go read it directly rather than relying on a law firm's summary of it.
- Don't let a topically-adjacent source silently answer a *different* sub-question than the critique tag needs (see "Scope-distinction discipline" above) — an on-topic, genuine source is not automatically an on-*question* source.
- Don't round a "genuine gap" up into an implied answer just because adjacent material exists (e.g. a FATF datapooling paper is not evidence that FATF has ruled on knowledge-graph tipping-off risk specifically — say so).
- Don't treat a bill as enacted law without checking the parliament's own bill-status page for the passed/assented/commenced dates.
- Don't skip the exclusion-list check on new citations just because they weren't the ones originally flagged — new fabricated-sounding sources can appear in any sweep.
- **AU legal AI: public/enterprise AI is the determinative LPP distinction, not tool name or vendor size.** The two FedCFamC cases (*Helmold v Mariya* [2025] FedCFamC1A 163; *Mertz v Mertz (No 3)* [2025] FedCFamC1A 222) are first-instance only — no appellate authority yet. **Verify with current legislation / AustLII** before citing; citation strings go stale. The joint regulator statement (December 2024, VLSB+C + LSNSW + LPBWA) is a dated snapshot of regulator consensus, not timeless. The operative test is whether the vendor contract expressly prohibits data retention/training/third-party disclosure + requires encryption/audit rights. "Enterprise" ChatGPT or "Pro" Gemini plans do NOT automatically satisfy this — review the actual data terms. See `references/australian-legal-ai-regulation-2026.md` for the checklist; re-verify cases.
- **AU court practice notes for AI changed 5 times in 18 months (Jan 2025–May 2026 snapshot)** — **verify with current legislation** / the court's live practice-note page before citing. The Victoria SC Gen 25 (May 2026 snapshot) replaced the 2024 guidelines; FCFCOA PD-AI (May 2026 snapshot) and GPN-AI (April 2026 snapshot) are dated. Any research citing 2024 Victoria guidelines or pre-April 2026 Federal Court guidance may be citing superseded material.
- **No Australian standard exists for contract review AI accuracy thresholds** — confirmed gap as of July 2026 (re-confirm; gaps close). Do not invent or import a numerical AU standard. ASCR competence rules (skill snapshot: Rule 4) are the operative professional-conduct test — **verify with current legislation**. WCC/IACCM international benchmarks (70-80% playbook coverage, 75%+ TAR recall) are comparators only, clearly labelled as international.
- **Inter-agent channel leakage is not visible in final outputs — output-only auditing misses a large share of privacy violations.** AgentLeak (arXiv:2602.11510, IEEE Access 2026) reported inter-agent vs final-output leak rates on its own 1,000-scenario test — treat those percentages as **paper-specific, not timeless**. For legal cowork architectures ingesting privileged emails/communications, auditing only the final output is structurally insufficient. Any compliance or privacy eval of a multi-agent legal system must audit all internal communication channels (C2 inter-agent messages, memory reads/writes, tool call parameters), not just what the final output says to the user.
- **Victoria SC endorses purpose-built legal AI over general-purpose LLMs — document your system's purpose-built nature.** SC Gen 25 (May 2026) explicitly states "Specialised, legally focused AI tools are likely to be more useful and reliable for parties in litigation than general purpose AI tools." For litigation matters, documenting that the system is purpose-built + operates in a closed environment (no public AI data sharing) creates favorable regulatory posture vs a system described as "using ChatGPT."

## Legal AI evaluation rubric discipline (Harvey LAB pattern)

When the task is to **define or review evaluation criteria for a legal work product** (a contract review rubric, a due-diligence checklist, a grading standard for an AI legal deliverable), apply the rubric authoring discipline distilled from Harvey LAB (github.com/harveyai/harvey-labs, v1.0, MIT, 2026):

- **All-pass over averaged-score.** Harvey LAB scores each rubric criterion as pass/fail and the task is green only when *every* criterion passes (the "all-pass" rate). The design rationale (from `docs/eval-strategies.md`): a diligence memo that catches 95% of issues but misses one material one is not 95% useful — it's wrong. Implication for rubric writing: treat each criterion as a binary gate, not a component of a weighted average. If the task overall can pass despite one criterion failing, the failing criterion isn't doing work.
- **Only supervisory-attorney criteria belong.** Rubrics should contain only the criteria a supervising attorney would actually check before sending work to a client. Padding criteria with background knowledge, adjacent issues, or "nice-to-have" items that no supervising attorney would reject a memo over degrades the signal — a rubric that's padded produces a low all-pass rate on good work and a high per-criterion rate on bad work, which is exactly the wrong direction.
- **For cross-model consensus on borderline legal quality determinations**, Harvey LAB's dual-judge option (`--dual`) runs criteria through two independent judges (e.g. claude-sonnet-4-6 + gpt-4o) and averages the binary results per criterion. This pattern is directly applicable when you need a defensible quality determination that isn't hostage to one model's biases on a specific legal framing.

Source for full eval methodology: `skill_view(name='academic-literature-review', file_path='references/legal-ai-evals-architecture-2026.md')` (HLB-02 entry), plus `docs/eval-strategies.md` at github.com/harveyai/harvey-labs.

## Scholarly dissertation critique

Political-theory dissertation critique is **out of scope** for this AU legal/regulatory skill. If the deliverable is actually a dissertation critique, load `references/political-theory-critique-sources.md` (kept here only because the file already lives in this skill) and do not mix its SEP/Heidegger workflow into an AU regulatory gap analysis.

## Reference files

- `references/officecli-tracked-changes.md` — officecli accept-then-re-annotate workflow, @paraId addressing, revision.action vs revision.type, footnote props
- `references/political-theory-critique-sources.md` — out-of-scope dissertation-critique map (do not mix into AU regulatory writing)
- `references/australian-legal-ai-regulation-2026.md` — AU legal AI authority set (dated; re-verify)
- `references/ai-legal-privilege-km-framework.md` — LPP/KM framework notes
- `references/legal-ai-km-verified-papers-2026.md` — verified legal-AI KM papers
- `references/comparative-external-landscape-sweep.md` — comparative external landscape
- `references/comparator-against-thesis.md` — comparator-against-thesis notes
- `references/non-english-companion-sweep.md` — non-English companion sweep
