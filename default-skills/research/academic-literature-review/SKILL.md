---
name: academic-literature-review
depends_on: [arxiv, firecrawl-research, grounded-citations, domain-research-synthesis]
or_deps: [firecrawl-research]
provides: [academic-literature-review, paper-discovery, academic-survey, institution-attribution]
related_skills:
  - arxiv
  - firecrawl-research
  - domain-research-synthesis
  - grounded-citations
  - blocked-page-recovery
  - obsidian-research-ingestion
triggers:
  - Conducting a structured academic literature survey across institutions or technique clusters
  - Searching arXiv, CNKI, IPSJ, CiNii, Cyberleninka, or other non-English academic venues
  - User wants native-language queries against non-English academic repositories
  - Building a systematic review from multiple paper sources with gap analysis
  - NOT for finding individual arXiv papers by keyword/ID (use arxiv skill)
  - NOT for community/tool/framework landscape research (use domain-research-synthesis)
  - NOT for applying sweep findings to Hermes skills (use arxiv-sweep-findings)
description: >
  Use when conducting structured academic literature surveys across institutions, geographies, and technique clusters. Combines arXiv API, web_search for institutional attribution, and web_extract for paper details. Produces structured markdown with arXiv IDs, quantified benefits, and implementation feasibility.
version: 1.0.0
license: MIT
platforms: [linux, macos, windows]
metadata:
  tags: [research, literature-review, arxiv, academic, institutions, survey, NLP, ML]
---

# Academic Literature Review

Use when the task is a structured survey of recent academic work — across multiple institutions, geographic regions, or technique families. The goal is a citable, quantified knowledge bank, not just a list of titles.

## Model Routing

Use **deepseek-v4-pro** (via `deepseek` provider) for long-horizon literature synthesis:

  Eligible: multi-source literature sweeps, synthesis/summary passes, precedent audits,
  fabrication checks — any task using only web_search/web_extract/read_file.
  Command: `hermes chat -m deepseek-v4-pro --provider deepseek -q "..."`
  Or route subagents: delegate_task with model: deepseek-v4-pro, provider: deepseek.

  NOT eligible: tasks requiring execute_code/terminal — reasoning_content 400 bug
  in multi-turn tool chains with thinking mode.

  Fallback: grok-4.6 when DeepSeek is unavailable or rate-limited.
  Avoid Beijing peak hours (09:00-12:00, 14:00-18:00 CST) — 2x pricing surge.
  Non-think mode only (do not pass reasoning param).

## When to trigger this skill

- User asks for "latest research" on a technical topic with institutional focus
- User specifies geographic regions (France, Israel, Korea, etc.) or named labs (KAIST, INRIA, Weizmann, etc.)
- User wants a comparison of techniques across papers (e.g., KV cache methods, speculative decoding variants)
- User wants implementation feasibility assessed for each paper finding
- **Not ML-only**: this skill applies equally to non-ML-efficiency domains — legal/AI-governance, security standards, evaluation methodology, policy — whenever the ask is "sweep academic literature (incl. non-English) for additions/updates to X". Confirmed July 2026 on a legal AI-agent-evaluation critique: the same native-language-venue-targeting workflow surfaced substantive findings from arXiv, CiNii (Japan), and Cyberleninka (Russia) applicable to agent governance/evaluation, not inference speed. Confirmed again July 2026 on a trading-strategy/portfolio-optimization survey: the same access-matrix and fabrication-discipline workflow applies to finance/quantitative investing literature. See `references/trading-strategy-finance-papers-2026.md` for the verified paper reference bank (15 primary sources, finance-repository access matrix, and domain-specific fabrication risk areas).

## Recursive Sweep Until Convergence (focused topic pass)

When doing a focused topic pass (e.g. metacognition, uncertainty estimation, reasoning calibration)
rather than a broad weekly sweep, run waves until convergence rather than once:

1. Extract covered paper IDs first — grep the skill or reference file for existing arXiv IDs to
   avoid re-reporting known papers.
2. Run a parallel batch of 6-8 queries per wave via execute_code (not delegation — faster, no
   subagent overhead for pure-Python arXiv/API calls).
3. Deduplicate against covered IDs; collect net-new only.
4. Convergence criterion: a full fresh-query wave returns 0 net-new papers. Stop there.
   Typical: 4-5 waves find most papers; wave 8-9 confirms convergence.
5. For corpus-audit mode (checking a local JSON bank rather than live arXiv), scan all bank
   files against the same topic keywords; report only papers with 2+ keyword hits that are
   not in the covered set. Zero hits across all bank files means corpus is exhausted — say so
   explicitly rather than recommending another live sweep.

Pitfall: do not conflate corpus-exhausted (0 hits in local bank) with topic-exhausted
(nothing published). The bank has a cutoff date; a fresh arXiv sweep may still find papers
postdating the bank. State which mode you ran.

## Alternate output mode: incremental delta sweep against a known baseline

When the user hands you an explicit "known baseline" (a list of institutions/techniques/findings already documented — typically because a prior sweep of this same skill produced a reference file) and asks for an update, the job is NOT to re-run a full survey and re-report everything found. It is a **delta sweep**: report only what's genuinely new, and explicitly confirm "checked, no new findings" for any topic axis that turned up nothing beyond the baseline.

Verified workflow (July 2026, Chinese-language sweep across 6 Hermes-agent-architecture topics: memory topology, memory maintenance, token optimization, LLM routing, agent workflows, skill/tool optimization):

1. **Read the existing reference file first** (e.g. `references/chinese-ai-agent-papers-2024-2026.md`) — this IS the known baseline. Don't ask the user to restate it if a reference file already exists from a prior sweep.
2. Run the native-language query batch per topic axis (same Phase 1 parallel-discovery pattern as a fresh survey).
3. For each candidate hit, check it against the baseline's Quick-Reference Table and Institutional Key Contacts section before treating it as new — a paper from an already-listed institution on an already-listed technique (e.g. another OmniKV-style KV-cache paper from AntGroup) is *not* new unless the technique itself is materially different.
4. Per-topic-axis output requirement: every axis gets a row/verdict, even negative ones. Do not silently drop an axis that yielded nothing — write "checked, no new findings beyond known baseline" for it. This mirrors the non-English-coverage-gap distinction elsewhere in this skill (access barrier vs. topic too new) — here the distinction is "genuinely absent" vs. "omitted because it looked unproductive," and only the former is honest.
5. Format as a compact table (finding / arXiv ID / institution / technique in 1-2 sentences / quantified benefit / delta vs. baseline) plus short prose — NOT a full per-paper block survey. Delta sweeps are read by someone who already has the baseline in their head; verbosity there is a cost, not a service.
6. After the sweep, append new findings to the SAME reference file the baseline came from (don't create a parallel/duplicate file) so the next delta sweep has an updated baseline to diff against.

Pitfall: distinguish a genuinely new institution/technique from a same-institution incremental paper. E.g., a second Tsinghua KV-cache paper using a different quantization trick (channel rotation vs. attention-similarity layer filtering) IS new — the mechanism differs, not just the institution. Judge novelty on technique, not on institution name recognition.

## Alternate output mode: standalone tag-applicability findings file with an inherited fabrication blacklist

Some sweeps aren't a full survey or a delta against a reference file or a patch to an existing living document — they're a **fresh standalone findings file** commissioned as one part of a larger, multi-round adversarial critique (e.g. "research sweep 3, part C" of a critique of an internal AI build-spec), where each of several topics maps to a specific named tag/clause in the target document. Verified workflow (July 2026, NAB "Legal Intelligence Platform" AI build-spec critique, round 3 — four topics: in-house-legal KM/succession AI, AFA fee-recalibration automation, burnout/engagement fairness auditing, privilege-specific training-data leakage):

1. **Per-finding structure is non-negotiable**: for every finding, give (a) a quantified claim with full citation (authors/source, venue, date, arXiv ID/DOI when available), then (b) a separate **applicability paragraph** that ties the finding precisely to the specific tag/clause/claim in the target spec — not a generic "this is relevant" gloss. A finding without an explicit tag-linkage paragraph is incomplete for this output mode.
2. **Explicit non-finding is a valid, required outcome — say so, don't pad.** If a topic yields only generic/adjacent baseline literature and nothing specific to the actual claim being critiqued (e.g. general AFA-adoption surveys exist but no independent validation of a named "effective price recalibration" *methodology*; general fairness-audit tooling exists but nothing applies it to burnout/engagement models in a legal-staffing context), state that gap explicitly as the finding. This is usually the most valuable and most citable output of the sweep — an honestly-reported absence is stronger evidence for a critique than a padded tangential citation.
3. **Inherited fabrication blacklist — verify by attempting to re-surface, not by memory.** When continuing a multi-round critique, the task will often hand you a list of previously-flagged fabricated/unverifiable sources from earlier rounds (author names, dataset names) that must not be re-cited even if they resurface in search. Treat this as an active check, not a passive filter: run the sweep's normal searches, and explicitly record in the output file whether any blacklisted source resurfaced (and was excluded) or whether none did. Silently avoiding them isn't enough — the audit trail needs "these did/did not reappear in this round's searches" stated in the file, so a future round can verify the blacklist is still being honored rather than just trusting a prior round's word for it.
4. **Flag every unverifiable/paywalled/abstract-only source inline, at the point of citation, not in a disclaimer footnote.** If `web_extract` fails on a journal page (e.g. tandfonline.com anti-bot block) and you fall back to an abstract-only confirmation via search snippet or PubMed/HAL listing, say so directly next to that citation ("abstract-only in this sweep; full text not independently verified") rather than presenting it with the same confidence as a fully-extracted arXiv paper. Same treatment for any secondary-source number that only appears in a listing/aggregator page — flag the number itself as unconfirmed, not just the source.
5. **Close with a summary table scoring each topic on two axes**: "new finding beyond generic baseline?" (yes/partial/no) and a qualitative strength rating, plus a cross-cutting note confirming the blacklist check from point 3. This table is what gets skimmed first in a multi-round critique — treat it as the load-bearing element, not a formality.
6. **File path and naming discipline**: these sweeps are typically one lettered/numbered part of a larger round (e.g. `research_sweep_3_partC.md`) living alongside sibling files from the same round and prior rounds in a shared `research/` directory. Use `write_file` to the exact path given — do not invent a different naming convention or merge into a prior round's file; each round's file is a discrete, dated artifact in the critique's paper trail.
7. **Read a sibling/prior-round file in the same `research/` dir BEFORE writing, to inherit the exact format** — even when you (the orchestrator) are writing directly, not delegating. The SKILL notes this for context-isolated subagents, but it applies to first-person writing too: `read_file` one existing sweep file, copy its section order (per-combination table → explicit track-summary judgment → corrections-flagged section → files-produced footer), then write. This keeps a multi-round critique's paper trail visually consistent and self-verifiable. Confirmed July 2026, NAB LIP round-3 JA+KO sweep (7 topics × 2 languages): reading round-2's `research_regulatory_and_nonenglish_sweep_2.md` first gave the exact table/summary/corrections shape to reproduce.
8. **Per-combination discipline for a bilingual sweep**: when the same topic is swept in two languages, give BOTH a row — never collapse to one. Each cell carries (a) verdict word (HIT / GAP / Institutional / Market-data), (b) the concrete citation (venue + ID/DOI/node-id in original script), (c) primary-vs-secondary flag. An honestly-reported GAP in one language when the other is a HIT is itself a load-bearing finding for the critique (e.g. round-3: KO AI 기본법 Art. 34 is a *binding* explanation duty while JA has only non-binding METI guidance — that asymmetry is the finding). See `references/legal-ai-japanese-korean-sweep-2026.md`.

## Alternate output mode: precedent / novelty audit of a source document's mechanisms

Distinct from a fresh survey, a delta sweep, a tag-applicability findings file, and a document-patch. Here the source document *proposes mechanisms* (e.g. an internal memo prescribing controls) and the task is to research what's OUTSIDE it — assessing each proposed mechanism against external precedent and judging novelty. The user will often say explicitly "do NOT re-validate the source's own content — research what's outside it." Verified July 2026 on a legal/AI-governance critique "Cluster D" (human oversight / HITL decay / automation bias / vigilance decrement / autonomy-gating).

1. **Per-mechanism precedent ladder**: for each mechanism the source proposes, find the strongest external anchor along a ladder — foundational science → operational instantiation → regulatory codification. (E.g. the source's "vigilance probes" = foundational vigilance-decrement/SDT theory → operational **Threat Image Projection** in airport screening → EU AI Act four-eyes verification.)
2. **Comparison table is the load-bearing element**: columns `mechanism | precedent status (well-precedented / partially novel / novel) | key external anchor`. This is what the critique author skims first.
3. **Three-part novelty verdict** at the close — separate (a) the *diagnosis* (usually textbook, cite the foundational review), (b) the *individual mechanisms* (usually precedented as concepts; the source's contribution is *porting* them into a new domain), and (c) any genuinely-novel *composite* (frame as an operationalization/synthesis, not a restatement). Tell the author what to cite as established vs. what is the source's own contribution — don't re-prove the memo right.
4. **Gap honesty carries over**: a language track whose *academic* search couldn't complete (backend failure, paywall) is an OPEN GAP flagged as "not confirmed absent," never a null result. A track that returned only commercial/blog material is reported as such ("popular coverage abundant, peer-reviewed primary not confirmed"), not dressed up as academic coverage.

See `references/human-oversight-hitl-vigilance-precedent-2026.md` for the verified anchor set (Parasuraman & Manzey 2010, Klein & Feltmate 2025 vigilance-decrement review, Threat Image Projection literature, Santoni de Sio & van den Hoven 2018 MHC, EU AI Act Art. 14), the Chinese/Japanese/French track results, and the reusable novelty-verdict template.

## Alternate output mode: patching an existing document (not a standalone survey)

Sometimes the sweep's job isn't to produce a new survey doc but to **update an existing deliverable** (a critique, a plan, a spec) with research-backed fixes. Use this format instead of the technique-cluster survey structure in "Output Format" below:

- Add an **"Addendum — Academic Literature Sweep (date)"** section to the existing document, one block per finding:
  - **Finding**: what the paper/source shows, in plain language, tied to a specific existing issue/section number where possible ("extends Issue 3", "sharpens Issues 5, 14").
  - **Action**: the concrete change to make to the existing document — a new control, a tightened threshold, a corrected claim.
  - **Sources**: full citation, non-English titles kept in the original script with an English gloss in parentheses.
- Explicitly log languages/venues that were checked but yielded nothing beyond derivative restatement of already-cited English sources ("checked, not omitted") rather than either padding the doc with weak citations or silently dropping the language from the sweep. This is the honest middle ground between fabricating coverage and hiding a gap.
- Corroboration-only findings (a non-English source independently confirms a position already taken, without new action) still get their own block — mark the block "no new action required" rather than omitting it, since corroboration from an independent research community is itself evidence worth citing in a professional-standards document.

## Core principle: web_search is the primary tool for institutional attribution

The arXiv API returns paper metadata but NOT institution affiliations reliably. Institution names are often only in the PDF body. The correct workflow is:
- **arXiv API / web_extract on abs pages** → title, abstract, arXiv ID, submission date, venue (if in comments field)
- **web_search for "[paper title] [institution name] arXiv"** → verifies/finds actual institution
- **web_search for "[author name] affiliation"** → author homepage confirms institution

Never assume institution from author names or country. Always verify.

## Standard Research Workflow

### Canonical web extraction fallback chain

For any URL that needs full-text access, try in this order:
1. `web_extract(url)` — fast, no auth, works on open-access pages
2. If blocked/empty: `defuddle` skill (Mozilla Readability extraction via local server)
3. If still blocked: `firecrawl-research` skill (local Firecrawl, stealth headers)
4. If still blocked: `blocked-page-recovery` skill (archive.org, Google Cache, Unpaywall, PubMed Central)
5. If all fail: cite abstract-only with explicit inline flag: "(abstract-only; full text not independently verified)"

The `firecrawl-stealth-fallback` skill combines steps 3-4 as a single dispatch. For research
pipelines running at scale, load it once and use it for all fallback resolution.

This chain applies to all research skills. `domain-research-synthesis` and `arxiv-sweep-findings`
both delegate to this skill for full-text access — do not implement ad-hoc fallbacks.

### Phase 0 — Non-English Language Targeting (when geographic scope is specified)

When the user specifies non-English countries or regions, this is NOT satisfied by finding
papers *authored* by researchers from those countries — it requires native-language queries
against native-language venues. The distinction matters: Chinese/Japanese/Korean researchers
mostly publish in English on arXiv; their native-language work appears in paywalled domestic
venues. What you CAN access is practitioner commentary and open venues.

Workflow when geographic scope includes non-English regions:
1. Translate query terms into each target language (see pitfalls section for verified term banks)
2. Search native open-access venues directly: TALN (French), CyberLeninka (Russian),
   ACL UNLP workshop (Ukrainian), IPSJ record pages (Japanese metadata), RISS abstract pages (Korean)
3. Search Chinese-language commentary (Zhihu, BAAI hub) for links to arXiv preprints
4. Pull accessible content; translate relevant findings back to English
5. Report access failures honestly: CNKI, Wanfang, IPSJ full text, KIISE/DBpia, eLibrary.ru,
   HAL.science, GI Digital Library are paywalled/login-walled — report titles/abstracts only

Do NOT report "non-English countries represented" when you only accessed their English arXiv
submissions. That conflates institution of origin with language of publication.

Dispatch as parallel subagents per language cluster when coverage is required (e.g. CJK
together, European together) to avoid sequential latency across 6+ languages.

**When dispatching, inline the full ruleset into each subagent's context/goal — do not reference this skill by name and assume it carries over.** Leaf subagents (`delegate_task`) get no access to the orchestrator's loaded skills, conversation history, or this SKILL.md — they only see what's written in their `context`/`goal` strings. Confirmed July 2026, NAB LIP critique continuation: 3 parallel language-cluster subagents (Russian/Hebrew/German) were dispatched for the same recurring critique, each with the full anti-fabrication ruleset (no fabricated citations, name+venue+date+URL required per claim, absence-of-literature is a valid finding, explicit blacklist-recheck instruction) spelled out verbatim in the delegation prompt, plus explicit instructions to read the sibling sweep file first as a template for format/rigor. Don't shorten this to "follow the usual non-English sweep methodology" — that sentence means nothing to a context-isolated subagent. Also point each subagent at the specific existing sweep file(s) to match structure/tone against (table format, summary-judgment section) so parallel sweeps come back consistent rather than each inventing its own shape.

### Phase 1 — Multi-axis Parallel Discovery

Batch independent searches in a single tool call. For each major axis (KV cache, speculative decoding, CoT compression, RAG efficiency, etc.) AND each geographic region, run parallel web_search calls.

Typical batch (example for LLM inference survey):
```
# Technique axis (6 concurrent)
"KV-cache optimization LLM inference 2024 2025 arXiv"
"prompt compression LLMLingua context compression 2024 2025"
"speculative decoding speedup 2024 2025 benchmark"
"chain-of-thought length reduction token budget 2025"
"RAG retrieval context reduction efficiency 2024 2025"
"[specific named technique] arXiv paper"

# Geographic axis (6 concurrent)
"[Lab1] [Lab2] LLM efficient inference 2024 2025 paper"
"[Country] [Institution] NLP ML 2024 2025 NeurIPS ICML"
...

# Community/practitioner axis (run in parallel with above)
# Reddit: web_search only — web_extract always blocked.
# Pattern: web_search("site:reddit.com r/[subreddit] [topic] [year]")
# Key subs: r/MachineLearning, r/LocalLLaMA, r/artificial, r/LanguageTechnology
# Hacker News: web_search("site:news.ycombinator.com [topic]") OR
# web_extract("https://hn.algolia.com/?q=[topic]&dateRange=last6Months") — Algolia HN is scrapable.

# X/Twitter axis — practitioner signal (run in parallel with above)
# Use web_search with site:x.com — Google indexes public tweets reliably.
# Do NOT use browser_navigate on x.com (confirmed timeout in this env).
# Do NOT use web_extract on x.com tweet URLs as primary path (unreliable without auth).
# Pattern: web_search("site:x.com [topic] since:[YYYY-MM-DD]")
# Examples:
"site:x.com agent memory architecture 2026"
"site:x.com karpathy memory LLM"
"site:x.com [researcher_handle] [topic]"
# Key AI/ML accounts: karpathy, ylecun, lilianweng, srush_nlp, rasbt, emollick
# If snippet is short: web_extract("https://x.com/user/status/ID") gets full text.
```

### Phase 2 — Verify Key Papers

For each candidate that looks substantive:
1. `web_extract(urls=["https://arxiv.org/abs/{id}"])` — confirms title, authors, venue from comments field
2. If institution not clear: `web_search("[first author] [institution] affiliation")`
3. Extract: arXiv ID, full title, authors, institution, venue, submission date, abstract key claim

### Phase 3 — Quantify Benefits

For each paper, extract at minimum:
- **Quantified benefit**: exact numbers (2.8×, 40%, 50% reduction), not vague claims
- **Conditions**: which model family, what sequence length, what task type
- **Baseline compared against**: what does the speedup beat?

If a paper only has vague claims ("significant improvement"), note that explicitly — it lowers the finding's reliability.

### Phase 4 — Implementation Feasibility Assessment

Rate each finding for the specific deployment context:

| Rating | Meaning |
|--------|---------|
| **Very High** | Pure prompt engineering, no model modification, works with black-box APIs |
| **High** | pip-installable library, API-independent, minimal integration |
| **Medium** | Framework integration (vLLM/SGLang patch), local open-weight models only |
| **Low** | Requires model fine-tuning, white-box KV cache access, or significant infra changes |

Always note the *blocker* for lower-feasibility items (e.g., "requires KV cache access — not available via Anthropic API").

## Output Format

### Per-paper block (minimum viable)

```markdown
### [Short Name] — [One-line description] ([Venue Year])

| Field | Detail |
|-------|--------|
| **Paper** | *Full Title* |
| **arXiv** | XXXX.XXXXX |
| **Venue** | Conference/Journal Year |
| **Institution** | Name 🇺🇸/🇰🇷/🇮🇱 etc. |
| **Technique** | [2–3 sentence description of method] |
| **Quantified Benefit** | [Exact numbers, conditions, baseline] |
| **CLI Feasibility** | **[Rating]** — [one sentence on why/blocker] |
```

### Document structure for large surveys

```
# [Topic]: Research Survey [Year Range]
## 1. [Technique Cluster 1]
   ### 1.1 [Paper Name]
   ### 1.2 [Paper Name]
## 2. [Technique Cluster 2]
...
## N. Regional Academic Contributions
   ### N.1 [Country/Lab]
## N+1. Implementation Roadmap
   ### Tier 1 — High Feasibility, High Impact
   ### Tier 2 — Medium Feasibility
   ### Tier 3 — Watch List
## N+2. References (Quick Index)
   | arXiv | Title | Year | Venue |
```

Always include a **quick-reference table** at the end with arXiv IDs — this is the most reused part.

## Subagent research loop design (multilingual / multi-cluster sweeps)

When dispatching subagents for a multi-topic research sweep (e.g. 8+ topics across several
markets or languages), the single most common failure mode is the **web_search loop-cap**:
the subagent retries the same query repeatedly when results are off-topic, consuming its
entire tool-call budget without making progress.

**Prevention — embed these rules in every research subagent prompt:**
- At most 2 web_search attempts per topic with DIFFERENT queries; then move on and note [NOT FOUND]
- If search returns weather data, medical results, unrelated content: IMMEDIATELY change the
  query or skip the topic — do not retry the same string
- Total tool-call budget is finite; pacing matters (budget ~3-4 calls/topic for an 8-topic sweep)
- Write the output file BEFORE stopping — label it CRITICAL in the prompt

**Recovery:** if a subagent hits the loop-cap (exits with ~10 api_calls and no output file),
retry with an explicit `SEARCH STRATEGY` block at the top of the prompt:
```
SEARCH STRATEGY (mandatory — prevents loop-cap failure):
- For each topic: at most 2 web_search attempts with DIFFERENT queries, then move on with [NOT FOUND]
- Off-topic results (weather/medical/unrelated): immediately change query or skip
- Do NOT repeat the same search twice in a row
- Total budget: 30 tool calls max
- CRITICAL OUTPUT STEP: write the file with write_file BEFORE stopping; confirm with ls -la
```

**File-write failure pattern:** a subagent that completes all research (10+ search calls)
but runs out of context budget before the write_file call will exit cleanly (status=completed)
but leave no output file. Prevention: add this to the prompt:
```
CRITICAL: You MUST write the output file before finishing. Do not stop after compiling
findings — the final step is ALWAYS write_file. If write_file fails, use terminal with
heredoc. Confirm file exists with terminal('ls -la /tmp/<output>.md') before declaring done.
```

**Orchestrator decomposition for large sweeps (6+ clusters, multilingual):**
Spend ONE Opus-4-8 call to design the cluster decomposition before dispatching Sonnet workers.
Pattern (Aug 2026 trading strategy sweep):
```bash
hermes chat -q 'Design N parallel research clusters for [topic]. Each cluster must have:
  scope, search targets (multilingual), anti-fabrication rules, access tips, output format.
  Workers are claude-sonnet-4-6. Make each prompt self-contained.' \
  -m claude-opus-4-8 --provider anthropic -Q
```
The Opus call produces ready-to-use worker prompts. Workers execute on Sonnet (~10-22 api_calls
each). This avoids overlapping scopes and ensures access tips are baked in per cluster.

## API + Tool Upgrades (Aug 2026)
Full detail: references/research-skill-improvements-2025-2026.md | Adversarial synthesis: references/research-master-synthesis-2026.md
- **Local scientific-research pack** (on-demand, no always-on tools): `~/.hermes/resources/scientific-research/` + CLI `sci-research` (or `~/.hermes/bin/sci-research`). 80 DB API refs + paper API refs + OpenAlex/PubMed/Crossref/pagination scripts. `sci-research list` / `sci-research ref databases uniprot` / `sci-research search openalex "QUERY" --max 5`. Prefer this pack for structured API lookups; keep Hermes `arxiv` skill for arXiv keyword search + Firecrawl fallback. INDEX: that pack's `INDEX.md`.
- **OpenAlex**: api.openalex.org/works?search=QUERY (250M+; polite pool via mailto/api_key). Single-work by OpenAlex ID or plain DOI works; some arXiv-style DOI forms 404 — use OpenAlex work ID from search. Does NOT flag retractions — check Retraction Watch separately. CLI: `sci-research search openalex …`
- **PaSa** (pasa-agent.ai): RL-trained paper agent +37-39% recall vs Google+GPT-4o. Caveat: only tested on own benchmark.
- **arXiv sidecars**: Connected Papers / CatalyzeX / Litmaps / scite.ai / alphaXiv on arxiv.org/abs/ pages. Caveat: Connected Papers misses papers < 2 weeks old.
- **SkillProx** (arXiv:2608.07449): utility audit per knowledge unit; backward stage maps to Hermes skill consolidation (+3pp accuracy).
- **DocArena** (arXiv:2606.26122): 79K QA pairs, 49 languages, decoupled visual/text reasoning search agent.
- **GitHub mining**: PaperFlow (papersflow.ai) by arXiv ID; PwC API. Load via `skill_view(name='domain-research-synthesis', file_path='references/github-research-mining-2026.md')` — that file is **not** in this skill's `references/`. Star counts stale — check commit date.
- **Multilingual**: CNKI, CiNii/J-STAGE, Cyberleninka, Redalyc/SciELO, BASE/CORE. Default: translate query to English first. Caveat: loses ZH/JA domain-specific terminology.
- **scite.ai**: supporting/contrasting/mentioning citations. Subscription for full access; free tier limited.
- **Temporal lag**: huggingface.co/papers for zero-lag drops (S2/arXiv: 1-7 day delay).
- **arXiv script**: 3-tier fallback (export API → Firecrawl → HTML) — arxiv skill scripts/search_arxiv.py.
- **CORE**: api.core.ac.uk/v3/search/works?q=QUERY - 10 req/s, free key at core.ac.uk, 230M+ open-access
- **BASE**: api.base-search.net/cgi-bin/BaseHttpSearchInterface.fcgi?... - ~1 req/s, no auth, 300M+ multilingual
- **S2 citation traversal**: api.semanticscholar.org/graph/v1/paper/arXiv:ID/references?fields=title,citationCount&limit=20 (what it cites); .../citations?fields=title,year&limit=10 (what cites it)
- **Useful S2 fields**: influentialCitationCount, isOpenAccess, openAccessPdf, fieldsOfStudy, publicationVenue, externalIds (arXiv, DOI, GitHub)
- **Useful OpenAlex fields**: cited_by_count, open_access.oa_url, concepts, referenced_works, related_works, primary_location.source.display_name
- **arXiv API (2026-08)**: export.arxiv.org/api/query?search_query= is IP-level CDN-blocked - always use id_list=ID1,ID2 when IDs are known. Never search_query= directly in 2026.

## Pitfalls

Full confirmed pitfall catalogue: **references/pitfalls-confirmed-2026.md**

Load with: `skill_view(name='academic-literature-review', file_path='references/pitfalls-confirmed-2026.md')`

Quick reference (top 5 recurring — load the full file for details on all ~30 pitfalls):

1. **Loop-cap vs. context-exhaustion**: Two failure modes look identical (subagent exits without writing file) but need different fixes. Loop-cap (api_calls < 15, todos incomplete) → retry with SEARCH STRATEGY block; cap 2 attempts/topic. Context-exhaustion (api_calls > 15, todos completed) → retry with CRITICAL write-file instruction at top of prompt. Do NOT apply loop-cap fix to context-exhaustion.

2. **Inherited/baseline citation fabrication**: Compacted-context summaries launder prior-session hallucinations as "established fact." Re-verify every named-author/named-dataset citation independently before building on it. Confirmed: "Sugimoto et al. (2025) CiNii", "ISO/IEC 27043:2026 Annex C", "NIST IR 8497" — all absent from authoritative sources despite appearing in compacted summaries.

3. **Check skill's own reference files BEFORE running fresh live searches**: On any repeat/incremental pass, `skill_view(name='academic-literature-review', file_path='references/<matching-file>.md')` is the first move. A session wasted 20+ search calls re-deriving content already in `references/legal-ai-evidentiary-and-risk-papers-2025-2026.md`, then hit SerpApi 429 and ran out of budget.

4. **arXiv API endpoint times out; use HTML search page instead**: `web_extract` on `export.arxiv.org/api/query` times out after 60s. Use `web_extract` on `https://arxiv.org/search/?searchtype=all&query=TERMS&start=0` instead. Never pipe `curl | python3` for XML — security scanner blocks it.

5. **SerpApi 429 fallback**: After 2 consecutive web_search 429s, stop retrying and switch to `web_extract` on the arXiv API URL directly for the rest of that session: `web_extract(urls=["http://export.arxiv.org/api/query?search_query=abs:%22topic%22&start=0&max_results=15"])`.

6. **Semantic Scholar API returns empty body inconsistently (confirmed Aug 2026)**: `web_extract` on `api.semanticscholar.org/graph/v1/paper/arXiv:{ID}` returns empty string for some arXiv IDs with no error — same endpoint works for other IDs in the same session. ReAct (2210.03629), Wang Survey (2308.11432), CoALA (2309.02427), AgentBench (2308.03688) all returned empty while Toolformer (2302.04761) and ToT (2305.10601) returned valid JSON. Do NOT retry the same ID — switch to fallbacks: arXiv.gg snippet (web_search returns "Cited by N"), Papers With Code page snippet, or `site:semanticscholar.org [title]` web_search. See `references/ai-agent-research-taxonomy-aug2026.md` for confirmed fallback order.

7. **arXiv cross-listed papers don't show titles in compact recent/new listing** (confirmed Aug 2026): `arxiv.org/list/{cat}/recent` and `arxiv.org/list/{cat}/new` compact format shows titles only for papers where that category is PRIMARY. Cross-listed papers show only the arXiv ID link plus a `(cross-list from cs.XX)` tag — no title, no abstract. To get titles/abstracts for cross-listed papers you MUST fetch `https://arxiv.org/abs/{id}` individually. This matters for exhaustive sweeps of `cs.AI/recent` which can be 70%+ cross-lists: plan for per-abstract fetches on all relevant IDs, not just title-scanning the listing page. Budget ~1 web_extract call per 3 IDs when batching. The `/new` page separates into "New submissions" (primary, have titles) and "Cross-lists" (no titles) sections — scan both but expect cross-list section to require individual fetches.

8. **50-web_search-per-turn hard cap (loop_web_search_cap guardrail)**: Hermes enforces a hard limit of 50 web_search calls per turn. Multi-market sweeps will hit this if searched sequentially. Required discipline: (1) ONE large parallel batch (12+ calls simultaneously); (2) ONE follow-up batch on best hits; (3) write findings - 3 rounds max. When guardrail fires mid-sweep, write partial findings and flag incomplete coverage explicitly. Never iterate one-search-at-a-time. See also: references/pitfalls-confirmed-2026.md.

## Hermes-Specific Implementation Notes

**Reading .odt source documents**: `read_file` and officecli cannot read binary `.odt` files. Use `toolbox run python3` with `odfpy` (pre-installed in the toolbox container). Pattern and full code in `references/odt-file-reading-technique.md`.

From the July 2025 LLM inference survey, highest-value actions for Hermes CLI:

1. **LLMLingua-2** (`pip install llmlingua`) — replace Haiku as primary context compressor for extractive compression. Works with Anthropic API. 3–6× faster than LM-based compression.
2. **TALE budget hints** — calibrate at P80 per task type: math-reasoning ~800 tokens, code-gen ~600, factual-retrieval ~200, creative ~400.
3. **Adaptive compression threshold** — replace fixed 0.4 threshold with query-complexity estimator. Signals: query perplexity, entity density, sentence count.
4. **Hybrid RAG strategy**: LLMLingua-2 extractive pass → selective Haiku abstractive merge only for complex queries.

See `references/token-optimization-papers-2024-2026.md` for the full verified paper index from the July 2025 survey.

## Reference Files Index

All prior sweep findings are preserved in `references/`. Load the index with:
  skill_view(name='academic-literature-review', file_path='references/reference-files-index.md')

Then load any individual file with:
  skill_view(name='academic-literature-review', file_path='references/<filename>')

Quick-access pinned files (most frequently needed):
| File | Why |
|------|-----|
| `pitfalls-confirmed-2026.md` | **Full pitfall catalogue** — load before any sweep |
| `research-skill-improvements-2025-2026.md` | Tool/API upgrades (Aug 2026) |
| `arxiv-sweep-source-access-aug2026.md` | arXiv listing pitfalls + non-English access status |
| `pubmed-openalex-biomedical-bypass-2026.md` | Biomedical: PubMed/PMC bypass, Europe PMC + OA PDF, abstract≠protocol, clinical brief rules |
| `reference-files-index.md` | Full index of all 40+ reference files |

### Biomedical / clinical literature briefs (not ML surveys)

When the user wants clinical literature (RCT/NMA/CPG) turned into ranked efficacy +
a practical routine (often email form):
1. Prefer OpenAlex / Europe PMC / publisher OA PDF over NCBI PubMed/PMC HTML (see
   `references/pubmed-openalex-biomedical-bypass-2026.md`). Optional structured APIs:
   local `sci-research` pack under `~/.hermes/resources/scientific-research/`.
2. Never take session count / dose / hold time from abstract alone — full text or
   explicit abstract-only flag. For protocol **tables/asana lists/RPE**, pull
   Europe PMC JATS: `…/europepmc/webservices/rest/{PMCID}/fullTextXML`.
3. Home routines = **clinical synthesis**, not a single-trial protocol copy.
4. Keep NMA rankings and CPG grades separate when they disagree.
5. **Ledger still owns URLs** (`grounded-citations` / `sources.py` + full-text
   quotes). **Default chat/report mode:** inline `[n]` + end Sources. **Email /
   “refs only at end” mode (user override, Aug 2026):** body uses author–year or
   short study names only; single `## Sources` at end; no mid-body `[n]`; no
   second Sources mid-file. Do not mix modes.
6. Pair with `adversarial-review` recursive loop + scientific-paper ref
   (clinical-brief attack vectors section). Run the loop **after** the final
   consolidated draft, not only on an earlier verbose version.
7. If the user expands “best yoga / best aerobic” into the body: use the protocol
   bank `references/migraine-yoga-aerobic-protocols-2026.md` (Hatha+Mehta core,
   Varkey RPE template, effect-size honesty) — full prescriptions, not name-only.

**Email deliverable shape (user-enforced):**
- One file, one print: Subject + greeting + short answer + efficacy + routines
  once each + safety + sign-off Alexey + Sources (+ optional adversarial
  appendix after Sources or a sibling `*-adversarial-review.md`).
- **No triple restatement:** do not stack “design goals” + full A/B/C routines +
  “one-line takeaways” saying the same three recommendations. Efficacy =
  ranking/effect sizes; routines = dose/RPE/asana once; no closing recap list.
- **No protocol bleed:** Varkey RPE / yoga holds live in the routine section only;
  efficacy keeps absolute effect size (e.g. ~0.9 attacks/month), not a second
  copy of the 15+20+5 template.
- If the draft duplicates mid-file or the user says “you printed it twice /
  consolidate,” **rewrite the whole email** rather than stacking patches; print
  the single clean version once.

## Reference File Implementation Status

Tracks which reference file findings have been absorbed into actionable skill body text or code. Updated Aug 2026.

| Reference file | Status | Notes |
|---|---|---|
| `memory-topology-research-2026-08.md` | Absorbed | Core findings in llm-agent-memory-pipeline-research Priority 1+2 |
| `skill-architecture-aug2026-sweep.md` | Absorbed | skill_prune_audit.py four-tier matrix + 0.92 merge threshold |
| `agent-runtime-aug2026-sweep.md` | Absorbed | agent-runtime-loop-patterns skill body |
| `agent-runtime-aug2026-sweep2.md` | Absorbed | agent-runtime-loop-patterns skill body |
| `agent-improvement-aug12-2026-sweep.md` | Absorbed | arxiv-sweep-findings + pitfalls |
| `agent-improvement-aug12-2026-sweep6.md` | Absorbed | adversarial-review, trajectory-risk-guardrail |
| `agent-improvement-aug12-2026-sweep7.md` | Absorbed | hermes-swarm-consensus, merge-reconciler |
| `agent-improvement-aug12-2026-sweep8.md` | Absorbed | pitfalls (EIA, DARR, debate critic, SIRIN) in llm-agent-memory-pipeline-research |
| `agent-improvement-aug12-2026-sweep9.md` | Absorbed | arxiv-sweep-findings sweep 13 |
| `agent-improvement-aug12-2026-sweep10.md` | Absorbed | arxiv-sweep-findings sweep 13, security pitfall |
| `agent-community-engineering-aug12-2026.md` | Absorbed | hermes-cron-and-agents, dispatching-parallel-agents |
| `agent-engineering-aug12-2026-community-sweep.md` | Absorbed | hermes-context-hygiene |
| `anthropic-api-agent-engineering-aug2026.md` | Absorbed | anthropic-agent-api-patterns |
| `multilingual-agent-research-aug12-2026.md` | Paper bank | Non-English venue access matrix. No pending code items. |
| `multilingual-agent-research-aug13-2026.md` | Paper bank | Sweep 13 multilingual findings. No pending code items. |
| `practitioner-community-sweep-aug13-2026.md` | Absorbed | pitfalls in llm-agent-memory-pipeline-research |
| `community-sweep-aug12-2026.md` | Paper bank | Practitioner lessons. No pending code items. |
| `community-sweep-aug12-2026b.md` | Paper bank | Multilingual sources. No pending code items. |
| `rumba-memory-eval-taxonomy-aug2026.md` | Paper bank | Benchmark reference. No pending code items. |
| `research-links-2026-08-11.md` | Paper bank | Link index. No pending code items. |
| `memory-topology-aug2026-sweep.md` | Absorbed | Partial — RippleMem + AgentMemBench in llm-agent-memory-pipeline-research body |
| `agent-memory-skill-aug11-2026-sweep.md` | Absorbed | Priority 1+2 pipeline |
| `blast-direction-risk-taxonomy.md` | Absorbed | trajectory-risk-guardrail skill |
| `audit-corrections-aug2026.md` | Absorbed | Corrected pitfalls in relevant skills |
| `zero-mem-note.md` | Paper bank | Single-paper note. No pending code items. |
| `agent-memory-sweep-aug14-2026.md` | PENDING REVIEW | Sweep 13 findings — not yet assessed for pending implementation items |
| `arxiv-sweep-source-access-aug2026.md` | Absorbed | Pitfalls section of this skill |
| `research-master-synthesis-2026.md` | Absorbed | Methodology section of this skill |
| `research-skill-improvements-2025-2026.md` | Absorbed | API + Tool Upgrades section of this skill |
| `pitfalls-confirmed-2026.md` | Absorbed | Pitfalls section of this skill |
| `reference-files-index.md` | Index | Navigation only |

**AI agent research taxonomy** (`references/ai-agent-research-taxonomy-aug2026.md`): Citation-ranked paper bank for agent research categories (reasoning/planning, tool use, memory, multi-agent, eval, evolution). Includes Hermes component mapping and S2 API citation-count fallback pattern. Sweep: Aug 2026.

**Finance/trading refs** (factor-crossasset-momentum, pead-earnings-momentum, technical-trading-strategies, noneng-markets-ml-altdata): Paper bank — no Hermes code items; findings inform trade strategy, not agent pipeline.

**Legal/governance refs** (agent-evaluation-governance, legal-ai-eval-frameworks, legal-ai-evals-architecture, legal-km-ai, knowledge-drift-expert-finding, au-legal-product-evals, human-oversight-hitl-vigilance): Paper bank — domain-specific deliverables; no pending Hermes skill code items.

**Other domain refs** (neurosymbolic-ai, cognitive-bias-ml-skill-scoring, token-economics-skill-roi-scoring, mcp-protocol-optimization, rag-robustness-multilingual, multilingual-agent-efficiency, multilingual-institutional-aug2026, noneng-agent-papers-aug2026-sweep7, personal-brain-agent-memory-eval): Paper banks — assess individually if implementing a specific finding.

**To update this table:** when a paper bank ref's findings get implemented, change status from "Paper bank" to "Absorbed" and note the target skill/file. When a new sweep ref is added, start it as "PENDING REVIEW".
## OpenScholar RAG — Grounded Scientific Corpus Retrieval (research-skill-improvements-2025-2026.md)

OpenScholar (Allen AI) retrieves from a 45M-paper datastore and grounds every claim in
cited passages, not parametric memory. Better recall and citation quality than web_search
for scientific literature.

**When to use over web_search / web_extract:**
- Need a specific paper's content and web_extract returns a paywall
- Need to find papers that cite or replicate a specific result (forward citations)
- Need to verify a claim's experimental basis, not just its abstract

**Access:** https://openscholar.allen.ai (free, no API key needed). Also available as
a Hugging Face Space. Use web_extract on the result pages to pull cited passages.

**Papers With Code bridge** (paperswithcode.com):
The canonical paper → code → benchmark → leaderboard bridge.
Use when: you have a paper and need to know if code exists, or need to benchmark
a technique against the current SOTA.
Pattern: `web_extract(["https://paperswithcode.com/paper/<arxiv-id>"])`

## MAD Taxonomy — Reflective Orchestrator Pattern (agent-improvements-2026-08.md)

Multi-Agent Debate (MAD) research: adding a reflective orchestrator that classifies
disagreement type before merging agent outputs reduces errors by 13.5%.

**4-type disagreement taxonomy:**
1. Factual (different facts cited) — resolve by checking sources, not averaging
2. Interpretive (same facts, different readings) — resolve by identifying assumption differences
3. Methodological (different approaches to same task) — synthesize or pick based on task type
4. Spurious (one agent confused/off-topic) — discard the outlier

When using hermes-swarm-consensus or dispatching-parallel-agents and results disagree,
classify the disagreement type before merging. Don't average across types.

## Sweep script design (from references/hermes-sweep-script-design-2026.md)

When building or consolidating multi-source academic sweep scripts:
- Merge categories only when `arxiv_cats` lists match AND conceptual space overlaps; keep ≤5 unique query strings. Listing-fetch cost dominates wall-clock.
- Apply a compiled off-topic regex to (title + source) BEFORE the seen cache. Do not filter on broad tokens (`learning`, `neural`, `agent`, `optimization`).
- Pre-flight core CS listings (`cs.AI`, `cs.CL`, `cs.MA`, `cs.LG`, `cs.SE`) before the per-category loop.
- Crossref is low-value for cs.AI (mostly published versions of arXiv papers); drop if latency matters.
- If the seen-cache exceeds MAX_SEEN, old IDs reappear — raise MAX_SEEN or persist to SQLite. After structural changes: AST-parse + importlib load + assert category/query counts.

## Reference files — Agent Efficiency Research — July 2026 Delta Sweep
- `references/agent-efficiency-jul2026.md` — July 2026 delta sweep paper bank (memory, multi-agent, routing, harness); findings applied to other skills, not re-surveyed here
- `references/hermes-sweep-script-design-2026.md` — Sweep-script consolidation, off-topic pre-filter, listing pre-flight, MAX_SEEN, post-change verification
- `references/agent-evaluation-governance-papers-2025-2026.md` — Agent Evaluation & Governance Literature — July 2026 Sweep
- `references/agent-memory-architecture-6topics-2025-2026.md` — Agent Memory Architecture — 6-Topic Research Survey (July 2026)
- `references/agent-memory-aug2026.md` — Agent Memory Systems: August 2026 Paper Sweep
- `references/arxiv-api-fallback-and-multilingual-sweep.md` — arXiv API Fallback & Multilingual Research Sweep — Field Notes
- `references/arxiv-api-fallback-and-pitfalls.md` — arXiv API Fallback & Research Sweep Pitfalls
- `references/arxiv-direct-id-fallback-aug2026.md` — arXiv Direct-ID Fallback Pattern (Aug 2026)
- `references/arxiv-sweep-source-access-aug2026.md` — arXiv sweep source-access notes (on disk; load on demand)
- `references/au-legal-product-evals-2026.md` — AU Legal AI Product Evals — Trust Deed Review & Marketing Compliance (domain bank; not core literature-review procedure)
- `references/cognitive-bias-ml-skill-scoring-2026.md` — Cognitive Bias Correction & ML/AI Skill Scoring Reference Bank (July 2026)
- `references/factor-crossasset-momentum-papers-2026.md` — Factor Investing & Cross-Asset Momentum — Verified Paper Bank (August 2026)
- `references/hermes-agent-skills-multilingual-sweep-jul2026.md` — Multilingual Research Sweep: 7 Hermes Agent Skill Topics — July 2026
- `references/hermes-skill-topics-multilingual-sweep-2025-2026.md` — Multilingual Research Sweep: 6 Hermes Agent Skill Topics — 2025–2026
- `references/japanese-korean-ai-agent-papers-2024-2025.md` — Japanese & Korean AI Agent Research — Verified Paper Index 2024–2025
- `references/knowledge-drift-expert-finding-legal-ai-2025-2026.md` — Knowledge Drift, Leaver Capture, Expert Finding & Legal AI Adoption — Verified R
- `references/legal-ai-eval-frameworks-2026.md` — Legal AI Evaluation Frameworks — Verified Paper Bank (July 2026)
- `references/legal-ai-evals-architecture-2026.md` — Legal AI Evals — Architecture & Benchmark Reference Bank
- `references/legal-km-ai-papers-2025-2026.md` — Legal AI Knowledge Management — Verified Paper Reference Bank
- `references/mcp-protocol-optimization-2025-2026.md` — MCP (Model Context Protocol) Optimization — Schema Bloat, Response Bloat, Effici
- `references/multilingual-academic-sources-access-matrix-2026.md` — Multilingual Academic Sources — Live-Tested Access Matrix (Aug 2026)
- `references/multilingual-agent-efficiency-sweep-jun-jul-2026.md` — Multilingual Agent Efficiency Sweep — June/July 2026
- `references/multilingual-agent-papers-fr-ru-uk-2024.md` — Multilingual AI Agent Research: French / Russian / Ukrainian (2024)
- `references/multilingual-institutional-agent-papers-aug2026.md` — Multilingual/Institutional AI Agent Papers — August 2026 Sweep 2
- `references/neurosymbolic-ai-research-2026.md` — Neurosymbolic AI: Reference Index (July 2026)
- `references/noneng-agent-papers-aug2026-sweep7.md` — Non-English Agent Research — Sweep 7 (Aug 12, 2026)
- `references/noneng-markets-ml-altdata-papers-2026.md` — Non-English Markets + ML/Alternative Data Finance Papers — August 2026 Sweep
- `references/pead-earnings-momentum-papers-2026.md` — PEAD + Earnings Momentum Academic Literature — Verified Reference Bank
- `references/personal-brain-agent-memory-eval-2026.md` — Personal Brain / Agent Memory Evaluation Benchmarks — Reference Bank
- `references/rag-robustness-multilingual-memory-papers-2025-2026.md` — RAG Robustness, Multilingual RAG, Agent Memory Architecture — Research Survey Ju
- `references/subagent-loop-cap-and-retry-patterns.md` — Subagent Loop Cap and Retry Patterns
- `references/technical-trading-strategies-english-2026.md` — Technical Trading Strategies — English-Language Academic Reference Bank
- `references/token-economics-skill-roi-scoring-2026.md` — Token Economics, Skill ROI & Multi-Signal Scoring — Research Bank
- `references/zen-elt-memo-skill-research-2026.md` — zen / elt-memo AI Writing Skill — Research Supplement (domain bank; optional load, not core literature-review procedure)
- `references/migraine-yoga-aerobic-protocols-2026.md` — domain paper bank (optional; not core literature-review procedure)
- `references/trading-strategy-finance-papers-2026.md` — domain paper bank (optional; not core literature-review procedure)

## OpenScholar — RAG Grounded on Scientific Corpora

OpenScholar (Allen AI) is a RAG system grounded specifically on scientific paper corpora
(Semantic Scholar, PubMed, arXiv). Use it when:
- Standard web search returns pop-science, not primary literature
- You need grounded citations with supporting/contrasting classification
- Topic is biomedical, cognitive science, or CS/AI

Access: https://openscholar.allen.ai — free web UI, no API yet (Aug 2026).
Workflow: run OpenScholar query first for grounded paper list, then verify IDs on arXiv/S2
before citing them in Hermes output.

## Papers With Code API Bridge

Papers With Code indexes ML papers with linked code repos and benchmark leaderboards.
API: https://paperswithcode.com/api/v1/ — free, no auth required.

Useful calls:
- GET /papers/?q=<query>&format=json — search papers with code
- GET /methods/ — browse methods by paper
- GET /sota/ — state-of-the-art leaderboard results

Use PwC as the bridge from paper → reproducible implementation:
1. Find paper on arXiv
2. Look up PwC entry: https://paperswithcode.com/paper/<arxiv-id>
3. Check "Code" tab for linked repos (star count + last-commit date matters more than count)
4. Cross-reference with leaderboard for benchmark context
