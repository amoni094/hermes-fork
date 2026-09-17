# PubMed Cookie-Wall Bypass via OpenAlex — Confirmed Aug 2026

## Problem

PubMed abstract pages (`pubmed.ncbi.nlm.nih.gov/{PMID}`) frequently return near-empty
content when accessed via `web_extract`. This is NOT a paywall — it's a session-cookie /
JavaScript rendering requirement that web_extract cannot satisfy. The page returns the
skeleton HTML without the actual abstract/metadata content.

Confirmed in Aug 2026 biomedical research session (keratosis pilaris treatment review):
web_extract on 3 PubMed URLs returned only page chrome with no abstract text. OpenAlex
returned full abstract + metadata for all 3 via the same PMIDs.

## Solution: OpenAlex API

OpenAlex (api.openalex.org) indexes all PubMed/MEDLINE content. No API key required.
Add `&mailto=your@email.com` for the polite pool (10 req/s vs shared rate limits).

### Search by topic (replaces PubMed search)
```
https://api.openalex.org/works?search=TERMS&filter=publication_year:YYYY-YYYY&per-page=10&mailto=...
```
- `search=` does full-text search including title/abstract
- `filter=` supports: `publication_year:2020-2024`, `is_oa:true`, `primary_topic.id:T...`
- `per-page` max is 200; use `page=2` etc. for pagination

### Fetch by PMID (direct lookup)
```
https://api.openalex.org/works/pmid:{PMID}?mailto=...
```

### Fetch by DOI
```
https://api.openalex.org/works/https://doi.org/{DOI}?mailto=...
```

### Fetch by OpenAlex ID
```
https://api.openalex.org/works/W{ID}?mailto=...
```

## Key Fields to Extract

| Field | What it contains |
|-------|-----------------|
| `title` / `display_name` | Paper title |
| `abstract_inverted_index` | Abstract as inverted index (see below) |
| `ids.pmid` | PubMed ID |
| `ids.doi` | DOI |
| `publication_year` | Year |
| `cited_by_count` | Citation count |
| `fwci` | Field-weighted citation impact |
| `open_access.oa_url` | Free PDF URL if OA |
| `primary_location.source.display_name` | Journal name |
| `authorships[].author.display_name` | Author names |
| `authorships[].institutions[].display_name` | Affiliations |
| `type` | "review", "article", "book-chapter", etc. |

## Abstract Reconstruction

`abstract_inverted_index` format: `{"word": [position1, position2, ...], ...}`

To reconstruct: invert to `{position: word}`, sort by position key, join with spaces.

Python one-liner:
```python
inv = work["abstract_inverted_index"]
abstract = " ".join(w for _, w in sorted((pos, word) for word, positions in inv.items() for pos in positions))
```

## Citation Normalized Percentile

`citation_normalized_percentile.value` gives a 0-1 score relative to papers in the
same field and year. Values:
- > 0.90 = top 10% of field (high impact)
- > 0.99 = top 1% (seminal)
- `is_in_top_10_percent` / `is_in_top_1_percent` booleans also available

## Retraction Warning

OpenAlex does NOT flag retracted papers. For any paper with contested claims,
cross-check at: https://retractionwatch.com/retracted-articles-database/

## Confirmed Biomedical Use Case (Aug 2026)

Session: keratosis pilaris treatment research
- Key systematic review found: Maghfour et al. 2020, J Dermatol Treatment
  (PMID 32886029, OpenAlex W3083132179) — "Treatment of keratosis pilaris and its
  variants: a systematic review" — 47 studies included, QS:Nd:YAG laser as most-
  supported treatment, topical keratolytics effective for appearance improvement.
- Also used for: Ibrahim et al. 2015 (JAMA Derm) RCT on 810nm diode laser — confirmed
  via DermNet NZ reference since OpenAlex returned the review paper, not the original.
- StatPearls (NBK546708) was accessible directly via web_extract — NIH Bookshelf
  doesn't have the same cookie-wall issue as PubMed abstract pages.

---

## PMC full-text blocked — Europe PMC + OA PDF chain (confirmed Aug 2026)

Session: migraine stretching clinical literature brief (email deliverable).

`pmc.ncbi.nlm.nih.gov/articles/PMC…` often fails the same way PubMed abstracts do
(empty/chrome-only via `web_extract`). Do **not** stop at abstract-only when the claim
is a **protocol parameter** (session count, hold time, frequency, duration).

### Working full-text ladder (biomedical RCTs / open journals)
1. **OpenAlex** by DOI/PMID — metadata + OA URL if present (`open_access.oa_url`).
2. **Europe PMC** article HTML: `https://europepmc.org/article/PMC/PMC{id}` or
   `https://europepmc.org/article/MED/{pmid}` — often readable when NCBI PMC is not.
3. **Publisher OA PDF** when known (Springer/BMC common for *J Headache Pain*):
   `https://link.springer.com/content/pdf/{doi}.pdf`
4. **sci-research pack** (on-demand): `~/.hermes/resources/scientific-research/` +
   CLI `sci-research` / `~/.hermes/bin/sci-research` for OpenAlex/PubMed/Crossref
   structured lookups. Prefer pack for API work; keep this skill for synthesis +
   Firecrawl/web_extract on OA pages.
5. If still blocked: cite **abstract-only with inline flag** and refuse to invent
   session counts / hold times.

### HIGH pitfall: abstract ≠ full-text protocol
PubMed/EuropePMC **abstracts compress or misstate methods**. Confirmed example:
Rezaeian et al. 2021 soft-tissue migraine RCT — secondary listings/abstract framing
read like a short course; **full text** specifies **6 sessions over 2 weeks
(3×/week), ~20 min each**. Citing the abstract-only session count as the protocol
is a HIGH correctness error in clinical briefs.

**Rule:** any dose/frequency/duration/hold-time claim in a routine or efficacy
section must be anchored to **full text** (or explicitly labeled abstract-only /
clinical synthesis). Never promote abstract methods language to a home program.

### NMA rank vs CPG grade — not a contradiction if labeled
Same session: Woldeamanuel et al. 2022 NMA ranked strength training #1 on migraine
days; formal comment (Han & Cho 2022) flagged inclusion/bias issues; La Touche 2023
exercise CPG still gives resistance training only **C-grade** while aerobic/yoga
are **B-grade**. Present both tiers; do not collapse “NMA top rank” into “best
practice prescription.” Benatto 2022 (neck CMSE vs sham+home stretch) failed on
primary migraine outcomes — useful counter to neck-only strength as a frequency
cure.

### Clinical home routine = synthesis, not a trial copy
When the user asks for a stretch/exercise **routine**, default label:
“clinical synthesis for home use, not a copy of one trial protocol.”
Map components to source classes (yoga package / soft-tissue targets / aerobic
baseline) without inventing hold times as if they were RCT endpoints.

### Deliverable form
If the user wants the report **as an email**: Subject + body + sign-off **Alexey**,
red-flag disclaimer, executive ranking, routine, safety, Sources, then recursive
adversarial self-review appendix (see `adversarial-review` →
`references/scientific-paper-adversarial-synthesis.md` clinical-brief vectors).
Do not auto-send unless they ask to send.

**Consolidation rules (user corrections, Aug 2026 migraine brief):**
1. **One version only** — on disk and when printing in chat. If mid-file duplication
   or “printed twice” appears, rewrite the whole email; never leave two bodies.
2. **No triple restatement** — drop separate “design goals” and closing “one-line
   takeaways” that repeat the same three recommendations already in ranking +
   routines.
3. **References only at the end** when asked — author–year / short study names in
   body; single `## Sources` after sign-off. No mid-body `[n]`; no Sources mid-doc.
   Ledger + full-text quotes still required behind the scenes.
4. **Split effect size vs prescription** — e.g. Varkey ~0.9 attacks/month in
   efficacy; 15 min RPE 11–13 + 20 min 14–16 + 5 min cool-down only once under
   aerobic routine.
5. Adversarial appendix: after Sources or sibling `*-adversarial-review.md` — not
   interleaved so the email body is not a double print.
