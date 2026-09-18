# arXiv Sweep & Non-English Source Access: Confirmed Status (Aug 2026)

For programmatic research sweeps across arXiv categories and multilingual sources.
Confirmed by Hermes subagent sweep, August 11 2026.
Updated Aug 12 2026: added ID-boundary pitfall.

---

## arXiv Programmatic Sweep Pitfalls

### Listing page pagination
- `skip=N&show=M` parameters on `https://arxiv.org/list/{cat}/recent` return **HTTP 400**
- Do NOT use. Each listing page shows exactly 50 papers, no pagination option.
- To get broader coverage: supplement with `https://arxiv.org/search/` keyword queries (different index, different coverage from listing walk)

### Search page HTML parsing
- **Correct split:** `re.split(r'arxiv-result\">', html)` — splits on the class attribute value + closing `>`
- **Incorrect (returns 0 results):** `<li class="arxiv-result">` — this tag form never appears in the actual HTML
- **Title:** `class=\"title[^\"]*\"` followed by `</p>`
- **Abstract:** `class=\"abstract[^\"]*\"` followed by `</p>`  
- **Submission date:** `<meta name="citation_date" content="YYYY/MM/DD">` (from abs page, not search page)
- **GitHub presence:** `'github.com' in page_content` (from abs page)

### Abstract page fetching
```python
def fetch_abstract_full(arxiv_id):
    url = f"https://arxiv.org/abs/{arxiv_id}"
    # title: <meta name="citation_title" content="...">
    # abstract: <blockquote class="abstract..."> ... </blockquote>
    # date: <meta name="citation_date" content="YYYY/MM/DD">
    # code: 'github.com' in content
```

### ⚠️ ID BOUNDARY ≠ SUBMISSION DATE BOUNDARY (confirmed Aug 12, 2026)
When a task says "find papers with IDs > X posted after date D," the arXiv ID ceiling and "new submissions for today" are NOT the same thing. The full monthly listing (`arxiv.org/list/cs.AI/2026-08`) ends at whatever the last submitted ID was at the time the listing was compiled — papers submitted on today's actual date don't appear until the nightly batch runs.

**Example (Aug 12 sweep):**
- Baseline = all IDs through 2608.09925
- Aug 2026 listing topped out at **2608.09930** (only 5 IDs past threshold)
- The 2 papers past the boundary (2608.09928, 2608.09930) were not agent-relevant (CV + TTS)
- Aug 12's actual new submissions had NOT yet been deposited

**Correct approach when "post-baseline" papers are requested:**
1. Check `arxiv.org/list/{cat}/new` — if today's batch isn't there, say so explicitly
2. The real "new" papers are those in the baseline ID range NOT in the named exception list
3. Never assume ID > threshold = posted after date; always verify what the listing ceiling is

**Actionable rule:** Before spending tool calls looking for papers > ID X, confirm: `web_extract("https://arxiv.org/list/cs.AI/new")` — if the "new" listing shows yesterday's date, today's batch is absent and no papers > X will be found in the monthly listing either.

---

## Non-English Source Access Status (Aug 2026)

### Accessible ✅

| Source | Status | Notes |
|--------|--------|-------|
| CyberLeninka (Russia) | Accessible | Returns only survey/review articles for AI/LLM topics. Very low signal-to-noise vs arXiv. Check quickly, don't block on it. |
| HAL API (France) | Accessible | `api.archives-ouvertes.fr/search/?q=QUERY&rows=10&wt=json` works. The web search UI is Anubis-blocked. |
| AMiner API (China) | Accessible | `api.aminer.org/api/search/pub?query=QUERY` — free, no key. Best for Chinese institutional AI output. Better than trying CNKI. |
| OpenAIRE API | Accessible | `api.openaire.eu/search/publications?keywords=QUERY&format=json` — covers EU-funded + Dutch/French content. |

### Blocked or inaccessible in programmatic context ❌

| Source | Block type | Workaround |
|--------|-----------|-----------|
| HAL.science web search UI | Anubis proof-of-work challenge | Use HAL API endpoint instead |
| HAL.science search/index with language filter | Anubis bot-protection (proof-of-work JS challenge) | API only: `api.archives-ouvertes.fr/search/?q=QUERY&rows=10&wt=json&language_s=fr` — confirmed Aug 2026. Direct URL patterns like `hal.science/search/index/?q=...&language_s=fr` fail. |
| J-STAGE (Japan) | "Blocked: URL targets a private or internal network address" in execute_code | Skip; use CiNii API or AMiner instead |
| NII Research Portal (nii.ac.jp) | JavaScript SPA — no extractable content via web_extract | Access via browser_navigate + browser_snapshot; or use AMiner/arXiv author search |
| RIKEN AIP blog (riken.jp/en/research/labs/aip) | JavaScript-heavy; no August 2026 agent posts visible | Check institutional arXiv author affiliations instead |
| Preferred Networks technical blog (preferred.jp) | No Aug 2026 AI agent papers found | Direct URL accessible but no relevant recent content |
| Semantic Scholar API (no key) | HTTP 429 within seconds | Get free API key at semanticscholar.org/product/api; or use curl with 3+ second gaps between calls |
| Semantic Scholar API via web_extract | Antibot-blocked (document_antibot) | Use curl terminal tool instead |
| RISS (Korea) | Connection blocked | Manual search only; no API |
| CNKI | Paywalled | Search arXiv with Chinese institution author names instead; or use AMiner |
| NAVER AI Lab / clova.ai/research | Previously rate-limited; no retry | Check KAIST/POSTECH as alternatives |
| LG AI Research blog | No accessible agent papers Aug 2026 | Search arXiv for "LG Electronics" or "LG AI" in abstract |

### Not yet published (as of Aug 2026) 📅

| Source | Status |
|--------|--------|
| ACL Anthology EMNLP 2026 | Returns 404 — proceedings not yet published |
| ACL Anthology COLM 2026 | Returns 404 — proceedings not yet published |
| ACL 2026 | Published (July 2-7, 2026) — in the baseline window for most agent research sweeps |

---

## Categories Worth Scanning for Agent Runtime Research

Beyond the obvious cs.AI/cs.CL/cs.MA/cs.LG, also check:
- **cs.IR** — high yield for memory/retrieval papers (e.g., DocMemo, missing-evidence memory)
- **cs.SE** — coding agent benchmarks (SWE-Bench ProMax, issue resolution benchmarks)
- **cs.NE** — emergence/cooperation papers (reputation-based cooperation, evolutionary models)
- cs.CR — security papers (latent compromise, trajectory poisoning)

---

## Institutional Affiliation Search: Critical Pitfalls (Aug 2026)

### "All fields" arXiv search does NOT find institutional affiliation
arXiv's "all fields" search (`searchtype=all`) searches title, abstract, and comments — NOT the author affiliation section, which is only in the PDF body. Searching for `agent LLM India` or `agent IIT OR IISc` finds papers only when the institution name appears in the abstract text itself (rare).

**Correct workflow for institution-targeted sweeps:**
1. Search for the lab/group name in abstract text when they're known to self-cite (e.g. "Shanghai AI Lab" or "Noah's Ark" often appear in acknowledgments in the abstract comments field)
2. Use `arXiv HTML abstract page` (`https://arxiv.org/html/{id}v1`) — the affiliation list IS rendered in HTML body: `Authors: ... ¹Shanghai AI Lab ²Fudan University`
3. For broad geographic sweeps: use AMiner API with country/institution filter rather than arXiv keyword search
4. For confirmed papers: always verify affiliation via HTML abstract page, not search page listing

**Searches that consistently fail for affiliation lookup (confirmed Aug 2026):**
- `query=agent+IIT+OR+IISc+OR+IIIT+OR+Indian+Institute` — finds papers mentioning "Indian Institute" in the text (rare), not papers authored by IIT/IISc researchers
- `query=LLM+agent+India` — same issue; "India" is almost never in the abstract text
- `query=LLM+agent+Brazil` — same; "Brazil" absent from abstract text even for Brazilian-authored papers
- `query=agent+LLM+Alibaba+DAMO+tool-use` — zero results; DAMO not in abstract text

**What does work:**
- `query=LLM+agent+memory+Huawei+OR+ByteDance+OR+Baidu` — finds 1962 results because these companies ARE mentioned in the abstract (tool use, datasets, products)
- `query=agent+planning+memory+Shanghai+AI+Lab+OR+SAIL` — finds papers where lab name appears in abstract
- HTML abstract page inspection: author affiliation always present for papers from `arxiv.org/html/{id}v1`

---

## Relevance Filtering: Known Baseline Handling

When running a sweep against a known baseline list of arXiv IDs:
1. Build a `KNOWN_IDS_SET = {set of known IDs}` before parsing listings
2. Check `if arxiv_id not in KNOWN_IDS_SET` before screening relevance
3. Note: papers with IDs in the same `YYMM.XXXXX` range but NOT in the known set are valid new finds
4. arXiv ID doesn't map 1:1 to calendar date — papers submitted across multiple days get the same YYMM prefix
5. "Truly post-deadline" papers = IDs > baseline_max; but prior-sweep misses with lower IDs also count as new
6. **The named exception list ≠ all covered papers** (confirmed Aug 12, 2026): a baseline that says "all IDs 2608.xxxxx through 2608.09925" does NOT mean only the explicitly listed IDs were reviewed — it means the entire range up to that cap was covered. Papers with lower IDs not in the named list are still in-baseline. New finds are those in the range NOT in any named list AND not in the topic coverage list.

---

## Yield Summary by Source (Aug 2026 Agent Runtime Sweep)

| Source | Papers found | Quality |
|--------|-------------|---------|
| cs.AI listing | 6 relevant / 50 total | High — primary venue |
| cs.CL listing | 14 relevant / 50 total | High |
| cs.MA listing | 50 relevant / 50 total (over-inclusive) | Medium (cs.MA over-indexes game theory / robotics) |
| cs.LG listing | 5 relevant / 50 total | High |
| cs.IR listing | 11 relevant / 50 total | High for memory/retrieval papers |
| cs.NE listing | 2 relevant / 37 total | Low but not zero |
| cs.SE listing | 6 relevant / 50 total | Useful for coding benchmarks |
| arXiv keyword search | ~12 additional | High for topic-targeted finds |
| CyberLeninka | 40 results (2026 filter) | Survey/review only — 0 novel techniques |
| HAL | Blocked | — |
| Semantic Scholar | Rate-limited | — |
| ACL Anthology | EMNLP/COLM 404 | — |
